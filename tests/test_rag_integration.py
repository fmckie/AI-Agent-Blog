"""
Integration tests for the complete RAG pipeline.

This module tests the RAG system end-to-end, including
research agent integration and performance improvements.
"""

import asyncio
from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from models import AcademicSource, ResearchFindings
from rag.embeddings import EmbeddingGenerator, EmbeddingResult
from rag.processor import TextChunk, TextProcessor
from rag.retriever import ResearchRetriever
from rag.storage import VectorStorage


class TestRAGIntegration:
    """Integration tests for RAG system."""

    @pytest.fixture
    def mock_configs(self):
        """Create mock configurations."""
        main_config = Mock()
        main_config.openai_api_key = "test-key"
        main_config.tavily_api_key = "test-tavily-key"
        main_config.max_retries = 3

        rag_config = Mock()
        rag_config.embedding_model_name = "text-embedding-3-small"
        rag_config.embedding_batch_size = 10
        rag_config.chunk_size = 500
        rag_config.chunk_overlap = 50
        rag_config.cache_similarity_threshold = 0.8
        rag_config.cache_ttl_hours = 24
        rag_config.supabase_url = "https://test.supabase.co"
        rag_config.supabase_service_key = "test-service-key"
        rag_config.database_url = "postgresql://test:test@localhost:5432/test"
        rag_config.connection_pool_size = 10
        rag_config.connection_timeout = 60

        return main_config, rag_config

    @pytest.fixture
    def sample_research_data(self):
        """Create comprehensive research data."""
        sources = [
            AcademicSource(
                title=f"Study {i}: AI Applications in Healthcare",
                url=f"https://journal{i}.edu/paper",
                authors=[f"Author{i}, A.", f"Author{i}, B."],
                publication_date=f"2024-0{i}-01",
                excerpt=f"This study examines AI application {i} in healthcare settings, showing significant improvements in diagnostic accuracy and patient outcomes.",
                domain=".edu",
                credibility_score=0.9,
                journal_name=f"Journal of AI Research Vol.{i}",
            )
            for i in range(1, 4)
        ]

        return ResearchFindings(
            keyword="AI healthcare applications",
            research_summary="Comprehensive analysis of AI applications in healthcare shows significant improvements in diagnostic accuracy (30-40% increase), reduced costs (20% average), and better patient outcomes across multiple studies.",
            academic_sources=sources,
            key_statistics=[
                "diagnostic_accuracy_improvement: 30-40%",
                "cost_reduction: 20% average",
                "patient_satisfaction: 85% positive",
                "implementation_time: 6-12 months",
            ],
            research_gaps=[
                "Long-term impact studies needed",
                "Ethical considerations require more research",
                "Integration with existing systems needs improvement",
            ],
            main_findings=[
                "AI improves diagnostic accuracy significantly",
                "Cost reductions are measurable within first year",
                "Patient outcomes show consistent improvement",
                "Healthcare professionals require training for effective use",
            ],
            total_sources_analyzed=10,
            search_query_used="AI healthcare applications research",
        )

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_new_research(
        self, mock_configs, sample_research_data
    ):
        """Test complete RAG pipeline with new research."""
        main_config, rag_config = mock_configs

        with patch("config.get_config", return_value=main_config):
            with patch("rag.config.get_rag_config", return_value=rag_config):
                with patch("rag.embeddings.get_config", return_value=main_config):
                    with patch(
                        "rag.embeddings.get_rag_config", return_value=rag_config
                    ):
                        with patch("rag.storage.create_client") as mock_create_client:
                            # Mock Supabase client
                            mock_client = Mock()
                            mock_create_client.return_value = mock_client

                            # Mock storage operations
                            mock_table = Mock()
                            mock_client.table = Mock(return_value=mock_table)

                            # No cache hit
                            mock_table.select = Mock(
                                return_value=Mock(
                                    eq=Mock(
                                        return_value=Mock(
                                            execute=Mock(return_value=Mock(data=[]))
                                        )
                                    )
                                )
                            )

                            # Mock chunk storage
                            mock_table.upsert = Mock(
                                return_value=Mock(
                                    execute=Mock(
                                        return_value=Mock(
                                            data=[
                                                {"id": f"chunk_{i}"} for i in range(10)
                                            ]
                                        )
                                    )
                                )
                            )

                            # Mock embeddings API
                            mock_openai_response = Mock()
                            mock_embedding_data = Mock()
                            mock_embedding_data.embedding = [0.1] * 1536
                            mock_openai_response.data = [mock_embedding_data]

                            with patch(
                                "rag.embeddings.AsyncOpenAI"
                            ) as mock_openai_class:
                                mock_openai_client = Mock()
                                mock_openai_client.embeddings.create = AsyncMock(
                                    return_value=mock_openai_response
                                )
                                mock_openai_class.return_value = mock_openai_client

                                # Mock connection pool
                                with patch(
                                    "rag.storage.asyncpg.create_pool", AsyncMock()
                                ):
                                    # Create retriever
                                    retriever = ResearchRetriever()

                                    # Mock research function
                                    research_called = False

                                    async def mock_research():
                                        nonlocal research_called
                                        research_called = True
                                        return sample_research_data

                                    # Execute retrieval
                                    result = await retriever.retrieve_or_research(
                                        "AI healthcare applications", mock_research
                                    )

                                    # Verify new research was performed
                                    assert research_called
                                    assert (
                                        result.keyword == "AI healthcare applications"
                                    )
                                    assert len(result.academic_sources) == 3

                                    # Verify statistics
                                    assert retriever.stats.cache_misses == 1
                                    assert retriever.stats.exact_hits == 0
                                    assert retriever.stats.semantic_hits == 0

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_with_cache_hit(
        self, mock_configs, sample_research_data
    ):
        """Test RAG pipeline with existing cache."""
        main_config, rag_config = mock_configs

        with patch("config.get_config", return_value=main_config):
            with patch("rag.config.get_rag_config", return_value=rag_config):
                with patch("rag.embeddings.get_config", return_value=main_config):
                    with patch(
                        "rag.embeddings.get_rag_config", return_value=rag_config
                    ):
                        with patch("rag.storage.create_client") as mock_create_client:
                            # Mock Supabase client
                            mock_client = Mock()
                            mock_create_client.return_value = mock_client

                            # Mock cached response
                            cached_entry = {
                                "id": "cache123",
                                "keyword": "AI healthcare applications",
                                "research_summary": sample_research_data.research_summary,
                                "chunk_ids": ["chunk1", "chunk2"],
                                "metadata": {
                                    "key_statistics": sample_research_data.key_statistics,
                                    "research_gaps": sample_research_data.research_gaps,
                                    "main_findings": sample_research_data.main_findings,
                                    "total_sources_analyzed": 10,
                                    "search_query_used": "AI healthcare applications research",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                },
                                "expires_at": "2025-01-01T00:00:00Z",
                                "chunks": [
                                    {
                                        "id": "chunk1",
                                        "content": source.excerpt,
                                        "metadata": {
                                            "source_type": "academic_source",
                                            "source_title": source.title,
                                            "source_url": source.url,
                                            "domain": source.domain,
                                            "credibility_score": source.credibility_score,
                                            "authors": source.authors,
                                            "publication_date": source.publication_date,
                                            "journal_name": source.journal_name,
                                        },
                                    }
                                    for source in sample_research_data.academic_sources
                                ],
                            }

                            # Mock table operations for cache hit
                            mock_table = Mock()
                            mock_client.table = Mock(return_value=mock_table)

                            # First call for cache check
                            mock_select1 = Mock()
                            mock_eq1 = Mock(
                                return_value=Mock(
                                    execute=Mock(return_value=Mock(data=[cached_entry]))
                                )
                            )
                            mock_select1.eq = mock_eq1

                            # Second call for hit count update
                            mock_update = Mock()
                            mock_eq2 = Mock(
                                return_value=Mock(
                                    execute=Mock(return_value=Mock(data=[]))
                                )
                            )
                            mock_update.eq = mock_eq2

                            # Third call for chunks
                            mock_select2 = Mock()
                            mock_in = Mock(
                                return_value=Mock(
                                    execute=Mock(return_value=Mock(data=[]))
                                )
                            )
                            mock_select2.in_ = mock_in

                            mock_table.select = Mock(
                                side_effect=[mock_select1, mock_select2]
                            )
                            mock_table.update = Mock(return_value=mock_update)

                            # Mock connection pool
                            with patch("rag.storage.asyncpg.create_pool", AsyncMock()):
                                # Create retriever
                                retriever = ResearchRetriever()

                                # Mock research function (should not be called)
                                research_called = False

                                async def mock_research():
                                    nonlocal research_called
                                    research_called = True
                                    return sample_research_data

                                # Execute retrieval
                                result = await retriever.retrieve_or_research(
                                    "AI healthcare applications", mock_research
                                )

                                # Verify cache hit
                                assert not research_called
                                assert result.keyword == "AI healthcare applications"
                                assert (
                                    result.research_summary
                                    == sample_research_data.research_summary
                                )

                                # Verify statistics
                                assert retriever.stats.exact_hits == 1
                                assert retriever.stats.cache_misses == 0
                                assert retriever.stats.semantic_hits == 0

    @pytest.mark.asyncio
    async def test_rag_semantic_search_integration(
        self, mock_configs, sample_research_data
    ):
        """Test semantic search functionality end-to-end."""
        main_config, rag_config = mock_configs

        with patch("config.get_config", return_value=main_config):
            with patch("rag.config.get_rag_config", return_value=rag_config):
                with patch("rag.embeddings.get_config", return_value=main_config):
                    with patch(
                        "rag.embeddings.get_rag_config", return_value=rag_config
                    ):
                        # Initialize components with mocked OpenAI
                        with patch("rag.embeddings.AsyncOpenAI"):
                            embeddings = EmbeddingGenerator()
                            processor = TextProcessor(rag_config)

                        # Process research findings into chunks
                        chunks = processor.process_research_findings(
                            sample_research_data
                        )

                        # Verify chunk generation
                        assert len(chunks) > 0

                        # Check chunk types
                        chunk_types = [c.metadata.get("source_type") for c in chunks]
                        assert "research_summary" in chunk_types
                        assert "academic_source" in chunk_types
                        assert "main_findings" in chunk_types
                        assert "statistics" in chunk_types

                        # Mock embedding generation
                        with patch.object(
                            embeddings, "_generate_single_embedding"
                        ) as mock_gen:
                            mock_gen.return_value = EmbeddingResult(
                                text="test",
                                embedding=[0.1] * 1536,
                                model="test",
                                token_count=10,
                            )

                            # Generate embeddings for chunks
                            chunk_texts = [chunk.content for chunk in chunks]
                            chunk_embeddings = await embeddings.generate_embeddings(
                                chunk_texts
                            )

                            assert len(chunk_embeddings) == len(chunks)

                            # Test similarity calculation
                            query_embedding = [0.1] * 1536
                            similarities = []

                            for i, chunk_emb in enumerate(chunk_embeddings):
                                similarity = embeddings.calculate_similarity(
                                    query_embedding, chunk_emb.embedding
                                )
                                similarities.append((chunks[i], similarity))

                            # All should have perfect similarity (same embeddings)
                            assert all(sim == 1.0 for _, sim in similarities)

    @pytest.mark.asyncio
    async def test_rag_performance_metrics(self, mock_configs):
        """Test performance tracking across the RAG system."""
        main_config, rag_config = mock_configs

        with patch("config.get_config", return_value=main_config):
            with patch("rag.config.get_rag_config", return_value=rag_config):
                with patch("rag.embeddings.get_config", return_value=main_config):
                    with patch(
                        "rag.embeddings.get_rag_config", return_value=rag_config
                    ):
                        with patch("rag.storage.create_client"):
                            with patch("rag.embeddings.AsyncOpenAI"):
                                with patch(
                                    "rag.storage.asyncpg.create_pool", AsyncMock()
                                ):
                                    # Create components
                                    embeddings = EmbeddingGenerator()
                                    retriever = ResearchRetriever()

                                    # Simulate cache operations
                                    retriever.stats.record_exact_hit(0.05)
                                    retriever.stats.record_exact_hit(0.03)
                                    retriever.stats.record_semantic_hit(0.1)
                                    retriever.stats.record_cache_miss(2.5)
                                    retriever.stats.record_error()

                                    # Simulate embedding operations
                                    embeddings.cache.hit_count = 15
                                    embeddings.cache.miss_count = 5
                                    embeddings.cost_tracker.add_usage(10000)

                                    # Get combined statistics
                                    retriever_stats = retriever.stats.get_summary()
                                    embedding_stats = embeddings.get_statistics()

                                    # Verify retriever metrics
                                    assert retriever_stats["total_requests"] == 5
                                    assert retriever_stats["exact_hits"] == 2
                                    assert retriever_stats["semantic_hits"] == 1
                                    assert retriever_stats["cache_misses"] == 1
                                    assert retriever_stats["errors"] == 1
                                    assert (
                                        float(
                                            retriever_stats["cache_hit_rate"].rstrip(
                                                "%"
                                            )
                                        )
                                        == 60.0
                                    )

                                    # Verify embedding metrics
                                    assert embedding_stats["cache_hit_rate"] == "75.0%"
                                    assert embedding_stats["total_tokens"] == 10000
                                    assert (
                                        float(
                                            embedding_stats["total_cost_usd"].lstrip(
                                                "$"
                                            )
                                        )
                                        == 0.0002
                                    )

    @pytest.mark.asyncio
    async def test_rag_error_handling_integration(self, mock_configs):
        """Test error handling across RAG components."""
        main_config, rag_config = mock_configs

        with patch("config.get_config", return_value=main_config):
            with patch("rag.config.get_rag_config", return_value=rag_config):
                with patch("rag.storage.create_client") as mock_create_client:
                    # Mock storage failure
                    mock_create_client.side_effect = Exception(
                        "Database connection failed"
                    )

                    with patch("rag.embeddings.AsyncOpenAI"):
                        # Storage should fail to initialize
                        with pytest.raises(
                            Exception, match="Database connection failed"
                        ):
                            storage = VectorStorage()

    @pytest.mark.asyncio
    async def test_rag_cache_warming_integration(
        self, mock_configs, sample_research_data
    ):
        """Test cache warming process end-to-end."""
        main_config, rag_config = mock_configs

        with patch("config.get_config", return_value=main_config):
            with patch("rag.config.get_rag_config", return_value=rag_config):
                with patch("rag.embeddings.get_config", return_value=main_config):
                    with patch(
                        "rag.embeddings.get_rag_config", return_value=rag_config
                    ):
                        with patch("rag.storage.create_client") as mock_create_client:
                            # Mock Supabase client
                            mock_client = Mock()
                            mock_create_client.return_value = mock_client

                            # Mock storage operations
                            mock_table = Mock()
                            mock_client.table = Mock(return_value=mock_table)

                            # No existing cache
                            mock_table.select = Mock(
                                return_value=Mock(
                                    eq=Mock(
                                        return_value=Mock(
                                            execute=Mock(return_value=Mock(data=[]))
                                        )
                                    )
                                )
                            )

                            # Mock chunk storage
                            mock_table.upsert = Mock(
                                return_value=Mock(
                                    execute=Mock(
                                        return_value=Mock(
                                            data=[
                                                {"id": f"chunk_{i}"} for i in range(5)
                                            ]
                                        )
                                    )
                                )
                            )

                            # Mock embeddings
                            with patch(
                                "rag.embeddings.AsyncOpenAI"
                            ) as mock_openai_class:
                                mock_openai_client = Mock()
                                mock_response = Mock()
                                mock_response.data = [Mock(embedding=[0.1] * 1536)]
                                mock_openai_client.embeddings.create = AsyncMock(
                                    return_value=mock_response
                                )
                                mock_openai_class.return_value = mock_openai_client

                                with patch(
                                    "rag.storage.asyncpg.create_pool", AsyncMock()
                                ):
                                    # Create retriever
                                    retriever = ResearchRetriever()

                                    # Keywords to warm
                                    keywords = [
                                        "AI healthcare",
                                        "machine learning diagnostics",
                                        "medical AI applications",
                                    ]

                                    # Mock research function
                                    async def mock_research():
                                        return sample_research_data

                                    # Warm cache
                                    results = await retriever.warm_cache(
                                        keywords, mock_research
                                    )

                                    # Verify all keywords were processed
                                    assert results["successful"] == 3
                                    assert results["failed"] == 0
                                    assert results["already_cached"] == 0

                                    # Verify each keyword status
                                    for keyword in keywords:
                                        assert results["keywords"][keyword] == "success"

    @pytest.mark.asyncio
    async def test_research_agent_with_rag_integration(self, mock_configs):
        """Test research agent integration with RAG caching."""
        main_config, rag_config = mock_configs

        with patch("config.get_config", return_value=main_config):
            with patch("rag.config.get_rag_config", return_value=rag_config):
                with patch("research_agent.agent.Agent") as mock_agent_class:
                    # Mock research agent
                    mock_agent = Mock()
                    mock_agent_class.return_value = mock_agent

                    # Import after patching
                    from research_agent import create_research_agent, run_research_agent

                    # Create agent
                    agent = create_research_agent(main_config)

                    # Mock Tavily results
                    mock_result = Mock()
                    mock_result.data = Mock(
                        keyword="test keyword",
                        research_summary="Test summary",
                        academic_sources=[],
                        key_statistics=[],
                        research_gaps=[],
                        main_findings=["Finding 1"],
                        total_sources_analyzed=1,
                        search_query_used="test keyword",
                    )

                    mock_agent.run = AsyncMock(return_value=mock_result)

                    # Run research
                    result = await run_research_agent(agent, "test keyword")

                    # Verify result
                    assert result.keyword == "test keyword"
                    assert result.research_summary == "Test summary"

    @pytest.mark.asyncio
    async def test_text_processing_integration(
        self, mock_configs, sample_research_data
    ):
        """Test text processing pipeline integration."""
        main_config, rag_config = mock_configs

        with patch("rag.config.get_rag_config", return_value=rag_config):
            # Create processor
            processor = TextProcessor(rag_config)

            # Process research findings
            chunks = processor.process_research_findings(sample_research_data)

            # Verify chunks
            assert len(chunks) > 0

            # Check chunk properties
            for chunk in chunks:
                assert isinstance(chunk, TextChunk)
                assert chunk.content
                assert chunk.chunk_index >= 0
                assert chunk.metadata
                assert "source_type" in chunk.metadata

                # Verify chunk size constraints
                assert (
                    len(chunk.content)
                    <= rag_config.chunk_size + rag_config.chunk_overlap
                )

            # Verify all content types are represented
            source_types = {chunk.metadata["source_type"] for chunk in chunks}
            expected_types = {
                "research_summary",
                "academic_source",
                "main_findings",
                "statistics",
            }
            assert expected_types.issubset(source_types)
