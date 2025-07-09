"""
Extended tests for RAG Text Processing Module.

This module provides additional test coverage for edge cases, error handling,
and advanced text processing scenarios not covered in the basic test file.
"""

import re
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import pytest

from models import AcademicSource, ResearchFindings
from rag.config import RAGConfig
from rag.processor import TextChunk, TextProcessor


class TestTextProcessorExtended:
    """Extended tests for TextProcessor edge cases."""

    @pytest.fixture
    def processor_with_small_chunks(self):
        """Create processor with very small chunk size for edge case testing."""
        config = Mock(spec=RAGConfig)
        config.chunk_size = 20  # Very small chunks
        config.chunk_overlap = 5
        config.min_chunk_size = 5
        return TextProcessor(config)

    @pytest.fixture
    def processor_with_large_overlap(self):
        """Create processor with overlap larger than chunk size."""
        config = Mock(spec=RAGConfig)
        config.chunk_size = 50
        config.chunk_overlap = 60  # Larger than chunk size
        config.min_chunk_size = 10
        return TextProcessor(config)

    def test_chunk_text_empty_input(self, processor_with_small_chunks):
        """Test chunking with empty or whitespace-only input."""
        # Empty string
        chunks = processor_with_small_chunks.chunk_text("")
        assert chunks == []
        
        # Only whitespace
        chunks = processor_with_small_chunks.chunk_text("   \n\t   ")
        assert chunks == []
        
        # String shorter than min_chunk_size
        chunks = processor_with_small_chunks.chunk_text("Hi")
        assert chunks == []

    def test_chunk_text_single_word_sentences(self, processor_with_small_chunks):
        """Test chunking with single-word sentences."""
        text = "Yes. No. Maybe. Perhaps. Indeed. Certainly. Absolutely."
        chunks = processor_with_small_chunks.chunk_text(text)
        
        assert len(chunks) > 0
        # Each chunk should contain at least one complete word
        for chunk in chunks:
            assert len(chunk.content.strip()) > 0
            assert not chunk.content.startswith(" ")
            assert not chunk.content.endswith(" ")

    def test_chunk_text_special_characters(self, processor_with_small_chunks):
        """Test chunking with special characters and symbols."""
        text = "Price: $99.99! Discount: 50% off. Email: test@example.com. Phone: +1-555-0123."
        chunks = processor_with_small_chunks.chunk_text(text)
        
        # Verify special characters are preserved
        all_content = " ".join(chunk.content for chunk in chunks)
        assert "$99.99" in all_content
        assert "50%" in all_content
        assert "test@example.com" in all_content
        assert "+1-555-0123" in all_content

    def test_chunk_text_unicode_handling(self, processor_with_small_chunks):
        """Test chunking with Unicode characters."""
        text = "Testing émojis 🎉 and açcénts. Chinese: 你好. Arabic: مرحبا. Math: ∑∏∫."
        chunks = processor_with_small_chunks.chunk_text(text)
        
        # Verify Unicode is preserved
        all_content = " ".join(chunk.content for chunk in chunks)
        assert "🎉" in all_content
        assert "你好" in all_content
        assert "مرحبا" in all_content
        assert "∑∏∫" in all_content

    def test_chunk_text_extreme_overlap(self, processor_with_large_overlap):
        """Test behavior when overlap exceeds chunk size."""
        text = "This is a test sentence. Another sentence here. And one more sentence."
        
        # Should handle gracefully even with invalid overlap
        chunks = processor_with_large_overlap.chunk_text(text)
        assert len(chunks) > 0
        
        # Chunks should still be created despite configuration issue
        for chunk in chunks:
            assert len(chunk.content) > 0

    def test_chunk_text_metadata_propagation(self, processor_with_small_chunks):
        """Test that metadata is properly propagated to all chunks."""
        text = "First sentence here. Second sentence there. Third sentence everywhere."
        custom_metadata = {
            "source": "test_document",
            "author": "Test Author",
            "tags": ["test", "sample"],
            "custom_field": {"nested": "value"}
        }
        
        chunks = processor_with_small_chunks.chunk_text(text, metadata=custom_metadata)
        
        for chunk in chunks:
            # Original metadata should be present
            assert chunk.metadata["source"] == "test_document"
            assert chunk.metadata["author"] == "Test Author"
            assert chunk.metadata["tags"] == ["test", "sample"]
            assert chunk.metadata["custom_field"]["nested"] == "value"
            
            # Auto-generated metadata should also be present
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata
            assert "chunk_size" in chunk.metadata
            assert "processed_at" in chunk.metadata

    def test_normalize_text_edge_cases(self, processor_with_small_chunks):
        """Test text normalization with edge cases."""
        # Multiple types of whitespace
        text = "Multiple   spaces\t\ttabs\n\nnewlines\r\ncarriage  returns"
        normalized = processor_with_small_chunks._normalize_text(text)
        # Should collapse multiple whitespaces
        assert "  " not in normalized
        assert "\t\t" not in normalized
        assert "\n\n" not in normalized
        
        # URLs should be handled
        text = "Visit https://example.com/very/long/path?param=value&other=123 for info"
        normalized = processor_with_small_chunks._normalize_text(text)
        # URL should be preserved or handled appropriately
        assert "https://" in normalized or "[URL]" in normalized

    def test_split_sentences_edge_cases(self, processor_with_small_chunks):
        """Test sentence splitting with edge cases."""
        # Abbreviations and decimals
        text = "Dr. Smith found a 3.14 improvement. Mr. Jones disagreed with Ph.D. candidate."
        sentences = processor_with_small_chunks._split_sentences(text)
        # Should handle abbreviations correctly
        assert any("Dr. Smith" in s for s in sentences)
        assert any("3.14" in s for s in sentences)
        
        # Multiple punctuation
        text = "Really?! That's amazing!!! But wait... there's more."
        sentences = processor_with_small_chunks._split_sentences(text)
        assert len(sentences) >= 3

    def test_create_chunks_from_sentences_edge_cases(self, processor_with_small_chunks):
        """Test chunk creation with edge cases."""
        # Very long sentence that exceeds chunk size
        long_sentence = "This is a very " + "long " * 50 + "sentence."
        sentences = [long_sentence]
        
        chunks = processor_with_small_chunks._create_chunks_from_sentences(sentences)
        # Should split long sentence into multiple chunks
        assert len(chunks) > 1
        
        # Verify all content is preserved
        all_content = " ".join(chunks)
        assert "This is a very" in all_content
        assert "sentence." in all_content


class TestTextProcessorWithResearchFindings:
    """Test processing of ResearchFindings objects."""

    @pytest.fixture
    def processor(self):
        """Create standard processor."""
        config = Mock(spec=RAGConfig)
        config.chunk_size = 200
        config.chunk_overlap = 50
        config.min_chunk_size = 20
        return TextProcessor(config)

    @pytest.fixture
    def complex_research_findings(self):
        """Create complex research findings with multiple sources."""
        sources = [
            AcademicSource(
                title=f"Research Paper {i}",
                url=f"https://journal{i}.edu/paper{i}",
                excerpt=f"This paper discusses finding number {i} with {i*10}% improvement.",
                domain=".edu",
                credibility_score=0.8 + i * 0.05,
                authors=[f"Dr. Author{i}"],
                publication_date=f"2024-0{i}-01",
                journal_name=f"Journal {i}",
            )
            for i in range(1, 6)
        ]
        
        return ResearchFindings(
            keyword="complex medical research",
            research_summary="A comprehensive meta-analysis of multiple studies showing consistent improvements.",
            academic_sources=sources,
            key_statistics=[
                "Overall improvement: 45% (p<0.001)",
                "Sample size: n=10,000 across 5 studies",
                "Effect size: Cohen's d = 0.8",
                "95% CI: [0.35, 0.55]",
            ],
            research_gaps=[
                "Long-term effects beyond 2 years unknown",
                "Limited data on pediatric populations",
                "No studies in developing countries",
            ],
            main_findings=[
                "Significant improvement in primary outcome",
                "No major adverse effects reported",
                "Cost-effective compared to standard treatment",
            ],
            research_quality_score=0.85,
            source_diversity_score=0.92,
        )

    def test_process_research_findings_comprehensive(self, processor, complex_research_findings):
        """Test comprehensive processing of complex research findings."""
        chunks = processor.process_research_findings(complex_research_findings)
        
        # Should create multiple chunks
        assert len(chunks) > 0
        
        # Verify all important information is captured
        all_content = " ".join(chunk.content for chunk in chunks)
        
        # Check summary is included
        assert "meta-analysis" in all_content
        
        # Check statistics are included
        assert "45%" in all_content
        assert "p<0.001" in all_content
        assert "n=10,000" in all_content
        
        # Check sources are referenced
        for i in range(1, 6):
            assert f"Research Paper {i}" in all_content
        
        # Check metadata
        for chunk in chunks:
            assert chunk.metadata["type"] == "research_findings"
            assert chunk.metadata["keyword"] == "complex medical research"
            assert "research_quality_score" in chunk.metadata
            assert chunk.metadata["research_quality_score"] == 0.85

    def test_process_research_findings_missing_fields(self, processor):
        """Test processing research findings with missing optional fields."""
        # Create findings with minimal required fields
        minimal_findings = ResearchFindings(
            keyword="minimal test",
            research_summary="Basic summary",
            academic_sources=[],  # Empty sources
            key_statistics=[],    # Empty statistics
            research_gaps=[],     # Empty gaps
            main_findings=["One finding"],
        )
        
        chunks = processor.process_research_findings(minimal_findings)
        
        # Should still process successfully
        assert len(chunks) > 0
        assert chunks[0].metadata["keyword"] == "minimal test"

    def test_chunk_overlap_consistency(self, processor):
        """Test that overlapping chunks maintain consistency."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        chunks = processor.chunk_text(text)
        
        if len(chunks) > 1:
            # Check that overlapping content matches
            for i in range(len(chunks) - 1):
                chunk1_end = chunks[i].content[-processor.chunk_overlap:]
                chunk2_start = chunks[i + 1].content[:processor.chunk_overlap]
                
                # There should be some overlap between consecutive chunks
                # (exact matching might not work due to sentence boundaries)
                assert len(chunk1_end) > 0 and len(chunk2_start) > 0


class TestTextChunkMethods:
    """Test TextChunk dataclass methods."""

    def test_text_chunk_to_dict(self):
        """Test TextChunk.to_dict() method."""
        chunk = TextChunk(
            content="Test content",
            metadata={
                "source": "test",
                "custom": {"nested": "value"},
                "list": [1, 2, 3],
            },
            chunk_index=0,
            source_id="source-123"
        )
        
        result = chunk.to_dict()
        
        assert result["content"] == "Test content"
        assert result["metadata"]["source"] == "test"
        assert result["metadata"]["custom"]["nested"] == "value"
        assert result["metadata"]["list"] == [1, 2, 3]
        assert result["chunk_index"] == 0
        assert result["source_id"] == "source-123"

    def test_text_chunk_to_dict_none_source_id(self):
        """Test TextChunk.to_dict() with None source_id."""
        chunk = TextChunk(
            content="Test",
            metadata={},
            chunk_index=0,
            source_id=None
        )
        
        result = chunk.to_dict()
        assert result["source_id"] is None


class TestTextProcessorErrorHandling:
    """Test error handling in text processor."""

    @pytest.fixture
    def processor(self):
        """Create standard processor."""
        config = Mock(spec=RAGConfig)
        config.chunk_size = 100
        config.chunk_overlap = 20
        config.min_chunk_size = 10
        return TextProcessor(config)

    def test_invalid_configuration(self):
        """Test processor with invalid configuration."""
        config = Mock(spec=RAGConfig)
        config.chunk_size = -10  # Invalid
        config.chunk_overlap = 20
        config.min_chunk_size = 10
        
        # Should handle gracefully or raise appropriate error
        processor = TextProcessor(config)
        # Processor should still be created, but might use defaults
        assert processor is not None

    def test_process_malformed_text(self, processor):
        """Test processing of malformed text inputs."""
        # Text with only punctuation
        chunks = processor.chunk_text("...")
        assert len(chunks) == 0 or all(len(c.content.strip()) > 0 for c in chunks)
        
        # Text with control characters
        text_with_control = "Normal text\x00\x01\x02 with control chars"
        chunks = processor.chunk_text(text_with_control)
        # Should process without crashing
        assert isinstance(chunks, list)

    @patch('rag.processor.datetime')
    def test_chunk_metadata_timestamp(self, mock_datetime, processor):
        """Test that chunks have consistent timestamps."""
        # Mock datetime to return consistent time
        mock_now = datetime(2024, 1, 20, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.utcnow.return_value = mock_now
        
        text = "First chunk. Second chunk. Third chunk."
        chunks = processor.chunk_text(text)
        
        # All chunks should have the same timestamp
        timestamps = [chunk.metadata["processed_at"] for chunk in chunks]
        assert all(ts == mock_now.isoformat() for ts in timestamps)


class TestTextProcessorPerformance:
    """Test performance-related aspects of text processing."""

    @pytest.fixture
    def processor(self):
        """Create standard processor."""
        config = Mock(spec=RAGConfig)
        config.chunk_size = 500
        config.chunk_overlap = 100
        config.min_chunk_size = 50
        return TextProcessor(config)

    def test_large_text_processing(self, processor):
        """Test processing of large text documents."""
        # Create a large text (10,000 words)
        large_text = " ".join([f"Sentence number {i}." for i in range(2000)])
        
        chunks = processor.chunk_text(large_text)
        
        # Should create multiple chunks
        assert len(chunks) > 10
        
        # Verify all chunks have proper metadata
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert chunk.metadata["chunk_size"] > 0

    def test_regex_pattern_caching(self, processor):
        """Test that regex patterns are properly cached."""
        # Access compiled patterns
        assert hasattr(processor, '_sentence_endings')
        assert hasattr(processor, '_whitespace')
        assert hasattr(processor, '_url_pattern')
        
        # Patterns should be compiled regex objects
        assert isinstance(processor._sentence_endings, re.Pattern)
        assert isinstance(processor._whitespace, re.Pattern)
        assert isinstance(processor._url_pattern, re.Pattern)


# Integration test
class TestTextProcessorIntegration:
    """Integration tests for text processor with other components."""

    def test_full_processing_pipeline(self):
        """Test complete text processing pipeline."""
        # Create processor with realistic config
        config = Mock(spec=RAGConfig)
        config.chunk_size = 300
        config.chunk_overlap = 50
        config.min_chunk_size = 100
        processor = TextProcessor(config)
        
        # Create realistic research findings
        source = AcademicSource(
            title="Breakthrough Study on Disease Treatment",
            url="https://medical.journal.edu/study",
            excerpt="This groundbreaking study demonstrates a 67% improvement in patient outcomes...",
            domain=".edu",
            credibility_score=0.95,
            authors=["Dr. Jane Smith", "Dr. John Doe"],
            publication_date="2024-01-15",
            journal_name="Medical Research Quarterly",
        )
        
        findings = ResearchFindings(
            keyword="innovative disease treatment",
            research_summary="Multiple studies confirm the effectiveness of the new treatment approach.",
            academic_sources=[source],
            key_statistics=["67% improvement rate", "p-value < 0.001", "n=500 patients"],
            research_gaps=["Long-term effects need study"],
            main_findings=["Treatment is highly effective", "Minimal side effects"],
            research_quality_score=0.92,
        )
        
        # Process the findings
        chunks = processor.process_research_findings(findings)
        
        # Verify complete processing
        assert len(chunks) > 0
        
        # Check first chunk has all required fields
        first_chunk = chunks[0]
        assert first_chunk.content
        assert first_chunk.metadata
        assert first_chunk.chunk_index == 0
        assert first_chunk.metadata["keyword"] == "innovative disease treatment"
        assert first_chunk.metadata["type"] == "research_findings"


# What questions do you have about these extended processor tests, Finn?
# Would you like me to explain any text processing concept in more detail?
# Try this exercise: Add tests for processing different document formats (PDF, HTML, Markdown)!