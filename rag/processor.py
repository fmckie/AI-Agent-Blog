"""
Text Processing Module for RAG System.

Handles text chunking, preprocessing, and metadata extraction
for efficient embedding generation and storage.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models import AcademicSource, ResearchFindings

from .config import RAGConfig

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a processed text chunk ready for embedding."""

    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    source_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index,
            "source_id": self.source_id,
        }


class TextProcessor:
    """Processes text for the RAG system."""

    def __init__(self, config: RAGConfig):
        """Initialize with configuration."""
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.min_chunk_size = config.min_chunk_size

        # Compile regex patterns for efficiency
        self._sentence_endings = re.compile(r"[.!?]+\s+")
        self._whitespace = re.compile(r"\s+")
        self._url_pattern = re.compile(r"https?://\S+")

    def chunk_text(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """
        Split text into overlapping chunks while preserving sentences.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of TextChunk objects
        """
        if not text or len(text.strip()) < self.min_chunk_size:
            return []

        # Clean and normalize text
        text = self._normalize_text(text)

        # Split into sentences for better chunking
        sentences = self._split_sentences(text)

        # Create chunks
        chunks = self._create_chunks_from_sentences(sentences)

        # Create TextChunk objects
        result = []
        base_metadata = metadata or {}

        for i, chunk_text in enumerate(chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk_text),
                "processed_at": datetime.utcnow().isoformat(),
            }

            result.append(
                TextChunk(content=chunk_text, metadata=chunk_metadata, chunk_index=i)
            )

        return result

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent processing."""
        # Replace multiple whitespaces with single space
        text = self._whitespace.sub(" ", text)

        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char == "\n")

        # Normalize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse multiple line breaks
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Handle common abbreviations
        text = re.sub(r"\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr)\.\s*", r"\1<DOT> ", text)
        text = re.sub(r"\b(Inc|Ltd|Corp|Co)\.\s*", r"\1<DOT> ", text)
        text = re.sub(r"\b(i\.e|e\.g|vs|etc)\.\s*", r"\1<DOT> ", text)

        # Split by sentence endings
        sentences = self._sentence_endings.split(text)

        # Restore dots
        sentences = [s.replace("<DOT>", ".") for s in sentences]

        # Filter empty sentences
        return [s.strip() for s in sentences if s.strip()]

    def _create_chunks_from_sentences(self, sentences: List[str]) -> List[str]:
        """Create chunks from sentences with overlap."""
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence) + 1  # +1 for space

            # If single sentence exceeds chunk size, split it
            if sentence_size > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Split long sentence
                words = sentence.split()
                temp_chunk = []
                temp_size = 0

                for word in words:
                    word_size = len(word) + 1
                    if temp_size + word_size > self.chunk_size and temp_chunk:
                        chunks.append(" ".join(temp_chunk))
                        temp_chunk = [word]
                        temp_size = word_size
                    else:
                        temp_chunk.append(word)
                        temp_size += word_size

                if temp_chunk:
                    chunks.append(" ".join(temp_chunk))
                continue

            # Check if adding sentence exceeds chunk size
            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))

                # Handle overlap
                if self.chunk_overlap > 0:
                    # Calculate sentences to keep for overlap
                    overlap_size = 0
                    overlap_sentences = []

                    for i in range(len(current_chunk) - 1, -1, -1):
                        sent_len = len(current_chunk[i]) + 1
                        if overlap_size + sent_len <= self.chunk_overlap:
                            overlap_sentences.insert(0, current_chunk[i])
                            overlap_size += sent_len
                        else:
                            break

                    current_chunk = overlap_sentences
                    current_size = overlap_size
                else:
                    current_chunk = []
                    current_size = 0

            current_chunk.append(sentence)
            current_size += sentence_size

        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def process_research_findings(self, findings: ResearchFindings) -> List[TextChunk]:
        """
        Process ResearchFindings into chunks for storage.

        Args:
            findings: Research findings to process

        Returns:
            List of TextChunk objects
        """
        all_chunks = []

        # Process research summary
        summary_metadata = {
            "source_type": "research_summary",
            "keyword": findings.keyword,
            "search_query": findings.search_query_used,
            "total_sources": findings.total_sources_analyzed,
        }

        summary_chunks = self.chunk_text(
            findings.research_summary, metadata=summary_metadata
        )
        all_chunks.extend(summary_chunks)

        # Process each academic source
        for source in findings.academic_sources:
            source_chunks = self._process_academic_source(source, findings.keyword)
            all_chunks.extend(source_chunks)

        # Process key findings
        if findings.main_findings:
            findings_text = "\n\n".join(findings.main_findings)
            findings_metadata = {
                "source_type": "main_findings",
                "keyword": findings.keyword,
                "finding_count": len(findings.main_findings),
            }
            findings_chunks = self.chunk_text(findings_text, metadata=findings_metadata)
            all_chunks.extend(findings_chunks)

        # Process statistics
        if findings.key_statistics:
            stats_text = "\n".join(findings.key_statistics)
            stats_metadata = {
                "source_type": "statistics",
                "keyword": findings.keyword,
                "stats_count": len(findings.key_statistics),
            }
            stats_chunks = self.chunk_text(stats_text, metadata=stats_metadata)
            all_chunks.extend(stats_chunks)

        logger.info(f"Processed {len(all_chunks)} chunks from research findings")
        return all_chunks

    def _process_academic_source(
        self, source: AcademicSource, keyword: str
    ) -> List[TextChunk]:
        """Process a single academic source."""
        # Combine title and excerpt for context
        source_text = f"{source.title}\n\n{source.excerpt}"

        metadata = {
            "source_type": "academic_source",
            "keyword": keyword,
            "source_url": source.url,
            "source_title": source.title,
            "credibility_score": source.credibility_score,
            "is_academic": source.domain in [".edu", ".gov", ".org"],
            "domain": source.domain,
            "publication_date": source.publication_date,
            "journal_name": source.journal_name,
            "authors": source.authors,
        }

        chunks = self.chunk_text(source_text, metadata=metadata)

        # Set source_id for all chunks from this source
        for chunk in chunks:
            chunk.source_id = source.url

        return chunks

    def extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """
        Extract key phrases from text for better searchability.

        Args:
            text: Text to analyze
            max_phrases: Maximum number of phrases to extract

        Returns:
            List of key phrases
        """
        # Simple implementation - can be enhanced with NLP
        # Remove URLs and special characters
        clean_text = self._url_pattern.sub("", text)
        clean_text = re.sub(r"[^\w\s-]", " ", clean_text)

        # Extract noun phrases (simplified)
        words = clean_text.split()  # Keep original case for capitalization detection

        # Find capitalized sequences (potential important terms)
        phrases = []
        i = 0
        while i < len(words):
            if words[i] and len(words[i]) > 0 and words[i][0].isupper():
                phrase = [words[i]]
                j = i + 1
                while j < len(words) and words[j] and words[j][0].isupper():
                    phrase.append(words[j])
                    j += 1
                if len(phrase) <= 4:  # Reasonable phrase length
                    phrases.append(" ".join(phrase))
                i = j
            else:
                i += 1

        # Return unique phrases
        return list(set(phrases))[:max_phrases]

    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).

        Args:
            text: Text to analyze

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4
