"""
Tests for RAG Configuration Module.

This test suite ensures that the RAG configuration properly validates
settings, handles environment variables, and provides correct defaults.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from rag.config import RAGConfig, get_rag_config


class TestRAGConfig:
    """Test RAG configuration functionality."""

    def test_minimal_valid_config(self):
        """Test configuration with minimal required values."""
        # Patch environment variables with only required fields
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-service-key-123456789",
            },
            clear=True,
        ):
            # Create config - should work with just required fields
            config = RAGConfig()

            # Check required fields are set
            assert config.supabase_url == "https://test.supabase.co"
            assert config.supabase_service_key == "test-service-key-123456789"

            # Check defaults are applied
            assert config.embedding_model_name == "text-embedding-3-small"
            assert config.chunk_size == 1000
            assert config.chunk_overlap == 200
            assert config.cache_ttl_hours == 168

    @pytest.mark.skip(
        reason="Pydantic Settings loads .env file automatically, hard to test in isolation"
    )
    def test_missing_required_fields(self):
        """Test that missing required fields raise errors."""
        # Clear any existing singleton
        import rag.config

        rag.config._config_instance = None

        # Clear all environment variables including disabling .env
        with patch.dict("os.environ", {"DISABLE_DOTENV": "true"}, clear=True):
            # Should raise validation error for missing required fields
            with pytest.raises(ValidationError) as exc_info:
                RAGConfig()

            # Check that the error mentions the missing fields
            error_dict = exc_info.value.errors()
            field_names = [error["loc"][0] for error in error_dict]
            assert "supabase_url" in field_names
            assert "supabase_service_key" in field_names

    def test_chunk_overlap_validation(self):
        """Test chunk overlap validation logic."""
        # Test valid overlap (less than chunk size)
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
                "CHUNK_SIZE": "500",
                "CHUNK_OVERLAP": "100",
            },
        ):
            config = RAGConfig()
            assert config.chunk_size == 500
            assert config.chunk_overlap == 100

        # Test invalid overlap (greater than chunk size)
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
                "CHUNK_SIZE": "500",
                "CHUNK_OVERLAP": "600",
            },
        ):
            with pytest.raises(ValidationError) as exc_info:
                RAGConfig()

            # Check error message
            error = exc_info.value.errors()[0]
            assert "chunk_overlap" in str(error)
            assert "must be less than chunk_size" in str(error)

    def test_supabase_url_validation(self):
        """Test Supabase URL format validation."""
        # Test valid URL
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://myproject.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
            },
        ):
            config = RAGConfig()
            assert config.supabase_url == "https://myproject.supabase.co"

        # Test invalid URL (no https)
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "http://myproject.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
            },
        ):
            with pytest.raises(ValidationError) as exc_info:
                RAGConfig()

            error = exc_info.value.errors()[0]
            assert "Invalid Supabase URL format" in str(error)

        # Test invalid URL (wrong domain)
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://myproject.wrongdomain.com",
                "SUPABASE_SERVICE_KEY": "test-key",
            },
        ):
            with pytest.raises(ValidationError):
                RAGConfig()

    def test_embedding_model_validation(self):
        """Test embedding model name validation."""
        # Test valid models
        valid_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ]

        for model in valid_models:
            with patch.dict(
                "os.environ",
                {
                    "SUPABASE_URL": "https://test.supabase.co",
                    "SUPABASE_SERVICE_KEY": "test-key",
                    "EMBEDDING_MODEL_NAME": model,
                },
            ):
                config = RAGConfig()
                assert config.embedding_model_name == model

        # Test invalid model
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
                "EMBEDDING_MODEL_NAME": "invalid-model",
            },
        ):
            with pytest.raises(ValidationError) as exc_info:
                RAGConfig()

            error = exc_info.value.errors()[0]
            assert "Invalid embedding model" in str(error)

    def test_numeric_constraints(self):
        """Test numeric field constraints."""
        # Test embedding batch size constraints
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
                "EMBEDDING_BATCH_SIZE": "0",  # Below minimum
            },
        ):
            with pytest.raises(ValidationError):
                RAGConfig()

        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
                "EMBEDDING_BATCH_SIZE": "3000",  # Above maximum
            },
        ):
            with pytest.raises(ValidationError):
                RAGConfig()

        # Test similarity threshold constraints
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
                "SIMILARITY_THRESHOLD": "1.5",  # Above 1.0
            },
        ):
            with pytest.raises(ValidationError):
                RAGConfig()

    def test_helper_methods(self):
        """Test configuration helper methods."""
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
                "CONNECTION_POOL_SIZE": "20",
                "CONNECTION_TIMEOUT": "30",
                "EMBEDDING_BATCH_SIZE": "50",
            },
        ):
            config = RAGConfig()

            # Test get_supabase_config
            supabase_config = config.get_supabase_config()
            assert supabase_config["url"] == "https://test.supabase.co"
            assert supabase_config["key"] == "test-key"
            assert supabase_config["options"]["db"]["pool_size"] == 20
            assert supabase_config["options"]["db"]["timeout"] == 30

            # Test get_embedding_config
            embedding_config = config.get_embedding_config()
            assert embedding_config["model"] == "text-embedding-3-small"
            assert embedding_config["dimensions"] == 1536
            assert embedding_config["batch_size"] == 50
            assert embedding_config["max_retries"] == 3

            # Test get_chunk_config
            chunk_config = config.get_chunk_config()
            assert chunk_config["chunk_size"] == 1000
            assert chunk_config["chunk_overlap"] == 200
            assert chunk_config["min_chunk_size"] == 100

    def test_singleton_behavior(self):
        """Test configuration singleton pattern."""
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-key",
            },
        ):
            # Clear any existing instance
            import rag.config

            rag.config._config_instance = None

            # Get config instances
            config1 = get_rag_config()
            config2 = get_rag_config()

            # Should be the same instance
            assert config1 is config2

            # Modifications should affect both references
            config1.chunk_size = 2000
            assert config2.chunk_size == 2000

    def test_all_configuration_fields(self):
        """Test all configuration fields with custom values."""
        env_vars = {
            "SUPABASE_URL": "https://custom.supabase.co",
            "SUPABASE_SERVICE_KEY": "custom-key",
            "DATABASE_POOL_URL": "postgresql://custom-pool-url",
            "EMBEDDING_MODEL_NAME": "text-embedding-3-large",
            "EMBEDDING_DIMENSIONS": "3072",
            "EMBEDDING_BATCH_SIZE": "200",
            "EMBEDDING_MAX_RETRIES": "5",
            "CHUNK_SIZE": "2000",
            "CHUNK_OVERLAP": "400",
            "MIN_CHUNK_SIZE": "50",
            "CACHE_SIMILARITY_THRESHOLD": "0.9",
            "CACHE_TTL_HOURS": "336",
            "CACHE_MAX_AGE_DAYS": "60",
            "MAX_SEARCH_RESULTS": "20",
            "SIMILARITY_THRESHOLD": "0.8",
            "CONNECTION_POOL_SIZE": "25",
            "CONNECTION_TIMEOUT": "120",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            config = RAGConfig()

            # Verify all values are loaded correctly
            assert config.supabase_url == "https://custom.supabase.co"
            assert config.supabase_service_key == "custom-key"
            assert config.database_pool_url == "postgresql://custom-pool-url"
            assert config.embedding_model_name == "text-embedding-3-large"
            assert config.embedding_dimensions == 3072
            assert config.embedding_batch_size == 200
            assert config.embedding_max_retries == 5
            assert config.chunk_size == 2000
            assert config.chunk_overlap == 400
            assert config.min_chunk_size == 50
            assert config.cache_similarity_threshold == 0.9
            assert config.cache_ttl_hours == 336
            assert config.cache_max_age_days == 60
            assert config.max_search_results == 20
            assert config.similarity_threshold == 0.8
            assert config.connection_pool_size == 25
            assert config.connection_timeout == 120

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case-insensitive."""
        with patch.dict(
            "os.environ",
            {
                "supabase_url": "https://lowercase.supabase.co",  # lowercase
                "SUPABASE_SERVICE_KEY": "test-key",  # uppercase
            },
        ):
            config = RAGConfig()
            assert config.supabase_url == "https://lowercase.supabase.co"
