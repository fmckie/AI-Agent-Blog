"""
RAG System Configuration Module.

Handles all configuration for the Retrieval-Augmented Generation system,
including embedding settings, chunking parameters, and cache configuration.
"""

import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables (can be disabled for testing)
if os.getenv("DISABLE_DOTENV") != "true":
    load_dotenv()


class RAGConfig(BaseSettings):
    """Configuration for the RAG system."""

    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(
        ..., description="Supabase service role key for admin access"
    )
    database_url: Optional[str] = Field(
        default=None, description="Direct database connection URL"
    )
    database_pool_url: Optional[str] = Field(
        default=None, description="Pooled database connection URL"
    )

    # Embedding Configuration
    embedding_model_name: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model to use"
    )
    embedding_dimensions: int = Field(
        default=1536, description="Dimensions of the embedding vector"
    )
    embedding_batch_size: int = Field(
        default=100, ge=1, le=2048, description="Batch size for embedding generation"
    )
    embedding_max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum retries for embedding API calls"
    )

    # Text Processing Configuration
    chunk_size: int = Field(
        default=1000, ge=100, le=4000, description="Size of text chunks in characters"
    )
    chunk_overlap: int = Field(
        default=200, ge=0, le=1000, description="Overlap between chunks in characters"
    )
    min_chunk_size: int = Field(
        default=100, ge=10, description="Minimum chunk size to process"
    )

    # Cache Configuration
    cache_similarity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for cache hits",
    )
    cache_ttl_hours: int = Field(
        default=168, ge=1, description="Cache time-to-live in hours"  # 7 days
    )
    cache_max_age_days: int = Field(
        default=30, ge=1, description="Maximum cache retention in days"
    )

    # Search Configuration
    max_search_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of search results to return",
    )
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum similarity for search results"
    )

    # Performance Configuration
    connection_pool_size: int = Field(
        default=10, ge=1, le=50, description="Database connection pool size"
    )
    connection_timeout: int = Field(
        default=60, ge=10, description="Database connection timeout in seconds"
    )

    # Google Drive Configuration
    google_drive_enabled: bool = Field(
        default=True, description="Enable Google Drive integration features"
    )
    google_drive_auto_upload: bool = Field(
        default=True,
        description="Automatically upload articles to Drive after generation",
    )
    google_drive_watch_enabled: bool = Field(
        default=False, description="Enable Drive folder watching for new documents"
    )
    google_drive_process_batch_size: int = Field(
        default=10, ge=1, le=50, description="Number of Drive files to process in batch"
    )
    google_drive_sync_on_startup: bool = Field(
        default=False, description="Sync Drive documents on system startup"
    )

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        env_file=".env" if os.getenv("DISABLE_DOTENV") != "true" else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("*", mode="before")
    @classmethod
    def strip_inline_comments(cls, v):
        """
        Strip inline comments from environment variable values.

        Python-dotenv doesn't remove inline comments by default,
        so we need to handle values like "advanced  # Options: basic, advanced"

        Args:
            v: The value to clean

        Returns:
            The cleaned value without inline comments
        """
        if isinstance(v, str):
            # Find the first # that's preceded by whitespace
            # This avoids stripping # that might be part of the actual value
            if "#" in v:
                # Split on # and take the first part
                parts = v.split("#")
                if len(parts) > 1:
                    # Only strip if there's whitespace before the #
                    cleaned = parts[0].rstrip()
                    # Check if we actually had a comment (whitespace before #)
                    if cleaned != v.rstrip():
                        return cleaned
            return v
        return v

    @field_validator("chunk_overlap")
    def validate_chunk_overlap(cls, v: int, info) -> int:
        """Ensure chunk overlap is less than chunk size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})"
            )
        return v

    @field_validator("supabase_url")
    def validate_supabase_url(cls, v: str) -> str:
        """Validate Supabase URL format."""
        if not v.startswith("https://") or not ".supabase.co" in v:
            raise ValueError("Invalid Supabase URL format")
        return v

    @field_validator("embedding_model_name")
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name."""
        valid_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ]
        if v not in valid_models:
            raise ValueError(f"Invalid embedding model. Must be one of: {valid_models}")
        return v

    def get_supabase_config(self) -> dict:
        """Get Supabase client configuration."""
        return {
            "url": self.supabase_url,
            "key": self.supabase_service_key,
            "options": {
                "db": {
                    "pool_size": self.connection_pool_size,
                    "timeout": self.connection_timeout,
                }
            },
        }

    def get_embedding_config(self) -> dict:
        """Get embedding generation configuration."""
        return {
            "model": self.embedding_model_name,
            "dimensions": self.embedding_dimensions,
            "batch_size": self.embedding_batch_size,
            "max_retries": self.embedding_max_retries,
        }

    def get_chunk_config(self) -> dict:
        """Get text chunking configuration."""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "min_chunk_size": self.min_chunk_size,
        }

    def get_drive_config(self) -> dict:
        """Get Google Drive integration configuration."""
        return {
            "enabled": self.google_drive_enabled,
            "auto_upload": self.google_drive_auto_upload,
            "watch_enabled": self.google_drive_watch_enabled,
            "batch_size": self.google_drive_process_batch_size,
            "sync_on_startup": self.google_drive_sync_on_startup,
        }


# Singleton instance getter
_config_instance: Optional[RAGConfig] = None


def get_rag_config() -> RAGConfig:
    """Get or create the RAG configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = RAGConfig()
    return _config_instance
