"""
Tests for Text Processing Module.

This test suite ensures that text chunking, normalization, and
research findings processing work correctly.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from models import AcademicSource, ResearchFindings
from rag.config import RAGConfig
from rag.processor import TextChunk, TextProcessor


class TestTextProcessor:
    """Test text processing functionality."""

    @pytest.fixture
    def processor(self):
        """Create a text processor with test config."""
        config = Mock(spec=RAGConfig)
        config.chunk_size = 100
        config.chunk_overlap = 20
        config.min_chunk_size = 10
        return TextProcessor(config)

    @pytest.fixture
    def sample_research_findings(self):
        """Create sample research findings for testing."""
        source = AcademicSource(
            title="Test Research Paper",
            url="https://example.edu/paper",
            excerpt="This is a test excerpt about important research findings.",
            domain=".edu",
            credibility_score=0.9,
            authors=["Dr. Smith", "Dr. Jones"],
            publication_date="2024-01-01",
            journal_name="Test Journal",
        )

        findings = ResearchFindings(
            keyword="test keyword",
            research_summary="This is a comprehensive summary of research findings.",
            academic_sources=[source],
            key_statistics=["Stat 1: 50% improvement", "Stat 2: 90% accuracy"],
            research_gaps=["More research needed on X", "Gap in understanding Y"],
            main_findings=[
                "Finding 1: Important discovery",
                "Finding 2: Significant result",
            ],
            total_sources_analyzed=5,
            search_query_used="test keyword academic",
        )

        return findings

    def test_simple_text_chunking(self, processor):
        """Test basic text chunking functionality."""
        # Create text that will require multiple chunks
        text = "This is a test sentence. " * 10  # ~250 characters

        chunks = processor.chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) > 1

        # All chunks should be TextChunk objects
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)

        # Check chunk sizes
        for chunk in chunks:
            assert len(chunk.content) <= 100  # Should respect chunk_size
            assert chunk.metadata["chunk_size"] == len(chunk.content)

    def test_chunk_overlap(self, processor):
        """Test that chunks have proper overlap."""
        # Create text with clear sentence boundaries
        sentences = [
            "First sentence here.",
            "Second sentence here.",
            "Third sentence here.",
            "Fourth sentence here.",
            "Fifth sentence here.",
        ]
        text = " ".join(sentences)

        chunks = processor.chunk_text(text)

        # With overlap, adjacent chunks should share some content
        if len(chunks) > 1:
            # Check if end of first chunk appears in beginning of second chunk
            chunk1_end = chunks[0].content[-20:]  # Last 20 chars (overlap size)
            chunk2_start = chunks[1].content[:50]  # First 50 chars

            # There should be some overlap (not exact due to sentence boundaries)
            # At minimum, we expect some shared words
            chunk1_words = set(chunk1_end.split())
            chunk2_words = set(chunk2_start.split())
            assert len(chunk1_words & chunk2_words) > 0

    def test_text_normalization(self, processor):
        """Test text normalization functionality."""
        # Text with various formatting issues
        messy_text = """
        This    has     multiple   spaces.
        
        
        Too many newlines above.
        \r\nWindows line breaks.\r
        Control chars: \x00\x01\x02
        """

        chunks = processor.chunk_text(messy_text)

        # Should still create chunks
        assert len(chunks) > 0

        # Check normalization
        combined_text = " ".join(chunk.content for chunk in chunks)

        # No multiple spaces
        assert "    " not in combined_text

        # No control characters
        assert "\x00" not in combined_text
        assert "\x01" not in combined_text

        # Normalized line breaks
        assert "\r\n" not in combined_text
        assert "\r" not in combined_text

    def test_sentence_splitting(self, processor):
        """Test sentence splitting with abbreviations."""
        # Test that abbreviations don't cause incorrect splits
        text1 = (
            "Dr. Smith and Prof. Jones work at Example Inc. They study e.g. AI and ML."
        )
        sentences1 = processor._split_sentences(text1)
        # Should keep as one sentence due to abbreviation handling
        assert len(sentences1) == 1
        assert "Dr. Smith" in sentences1[0]
        assert "Prof. Jones" in sentences1[0]
        assert "Example Inc." in sentences1[0]
        assert "e.g." in sentences1[0]

        # Test actual sentence boundaries
        text2 = "This is the first sentence. This is the second sentence."
        sentences2 = processor._split_sentences(text2)
        assert len(sentences2) == 2
        assert "first sentence" in sentences2[0]
        assert "second sentence" in sentences2[1]

    def test_long_sentence_handling(self, processor):
        """Test handling of sentences longer than chunk size."""
        # Create a very long sentence
        long_sentence = "word " * 50  # ~250 characters

        chunks = processor.chunk_text(long_sentence)

        # Should split the long sentence
        assert len(chunks) > 1

        # All chunks should have content
        assert all(chunk.content.strip() for chunk in chunks)

    def test_empty_and_short_text(self, processor):
        """Test edge cases with empty or very short text."""
        # Empty text
        assert processor.chunk_text("") == []
        assert processor.chunk_text("   ") == []

        # Text shorter than min_chunk_size (10)
        assert processor.chunk_text("Short") == []

        # Text exactly at min_chunk_size
        chunks = processor.chunk_text("A" * 10)
        assert len(chunks) == 1

    def test_metadata_handling(self, processor):
        """Test that metadata is properly attached to chunks."""
        text = "Test text for metadata handling."
        custom_metadata = {"source": "test", "type": "unit_test", "custom_field": 123}

        chunks = processor.chunk_text(text, metadata=custom_metadata)

        assert len(chunks) > 0

        for chunk in chunks:
            # Custom metadata should be included
            assert chunk.metadata["source"] == "test"
            assert chunk.metadata["type"] == "unit_test"
            assert chunk.metadata["custom_field"] == 123

            # System metadata should be added
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata
            assert "chunk_size" in chunk.metadata
            assert "processed_at" in chunk.metadata

    def test_process_research_findings(self, processor, sample_research_findings):
        """Test processing of ResearchFindings objects."""
        chunks = processor.process_research_findings(sample_research_findings)

        # Should create chunks for different content types
        assert len(chunks) > 0

        # Check different source types
        source_types = {chunk.metadata["source_type"] for chunk in chunks}
        assert "research_summary" in source_types
        assert "academic_source" in source_types
        assert "main_findings" in source_types
        assert "statistics" in source_types

        # Check academic source chunks
        academic_chunks = [
            c for c in chunks if c.metadata["source_type"] == "academic_source"
        ]
        assert len(academic_chunks) > 0

        # Academic chunks should have rich metadata
        for chunk in academic_chunks:
            assert chunk.metadata["source_url"] == "https://example.edu/paper"
            assert chunk.metadata["credibility_score"] == 0.9
            assert chunk.metadata["is_academic"] is True
            assert chunk.source_id == "https://example.edu/paper"

    def test_extract_key_phrases(self, processor):
        """Test key phrase extraction."""
        text = """
        Machine Learning and Artificial Intelligence are transforming healthcare.
        Natural Language Processing enables better patient care.
        Deep Learning models improve diagnosis accuracy.
        """

        phrases = processor.extract_key_phrases(text)

        # Should extract some phrases
        assert len(phrases) > 0
        assert len(phrases) <= 10  # Respects max_phrases

        # Phrases should be unique
        assert len(phrases) == len(set(phrases))

    def test_token_estimation(self, processor):
        """Test token count estimation."""
        # Known text length
        text = "A" * 400  # 400 characters

        estimated_tokens = processor.estimate_token_count(text)

        # Should be approximately 100 tokens (400/4)
        assert 90 <= estimated_tokens <= 110

    def test_chunk_index_consistency(self, processor):
        """Test that chunk indices are consistent."""
        text = "Test sentence. " * 20

        chunks = processor.chunk_text(text)

        # Check indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.metadata["chunk_index"] == i

        # Total chunks should match
        for chunk in chunks:
            assert chunk.metadata["total_chunks"] == len(chunks)

    def test_to_dict_method(self, processor):
        """Test TextChunk.to_dict() method."""
        chunk = TextChunk(
            content="Test content",
            metadata={"key": "value"},
            chunk_index=0,
            source_id="test-source",
        )

        chunk_dict = chunk.to_dict()

        assert chunk_dict["content"] == "Test content"
        assert chunk_dict["metadata"] == {"key": "value"}
        assert chunk_dict["chunk_index"] == 0
        assert chunk_dict["source_id"] == "test-source"

    def test_unicode_handling(self, processor):
        """Test handling of unicode text."""
        unicode_text = "Test with emojis and special characters"

        chunks = processor.chunk_text(unicode_text)

        # Should handle unicode properly
        assert len(chunks) > 0

        # Content should be preserved
        combined = " ".join(chunk.content for chunk in chunks)
        assert "emojis" in combined
        assert "special" in combined
