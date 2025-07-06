"""
RAG (Retrieval-Augmented Generation) System.

This package provides intelligent caching and semantic search capabilities
for the SEO Content Automation System, reducing API costs and improving
response times.
"""

# Import configuration first as other modules depend on it
from .config import RAGConfig, get_rag_config

# Import main components
from .embeddings import EmbeddingGenerator, EmbeddingResult
from .processor import TextChunk, TextProcessor
from .retriever import ResearchRetriever, RetrievalStatistics
from .storage import VectorStorage

__all__ = [
    "RAGConfig",
    "get_rag_config",
    "EmbeddingGenerator",
    "EmbeddingResult",
    "TextProcessor",
    "TextChunk",
    "ResearchRetriever",
    "RetrievalStatistics",
    "VectorStorage",
]

__version__ = "0.1.0"
