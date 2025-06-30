"""
Integration tests for the complete SEO Content Automation System.

These tests verify that all components work together correctly
in realistic scenarios.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Import testing utilities
import pytest

# Import system components
from config import Config, get_config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings
from research_agent import create_research_agent
from workflow import WorkflowOrchestrator
from writer_agent import create_writer_agent


class TestSystemIntegration:
    """Integration tests for the complete system."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_workflow_with_mocked_apis(self, tmp_path):
        """Test complete workflow with mocked external APIs."""
        # Create test configuration
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
            llm_model="gpt-4",
            log_level="DEBUG",
            max_retries=3,
            request_timeout=30,
            tavily_search_depth="basic",
            tavily_include_domains=[".edu", ".gov"],
            tavily_max_results=10,
        )

        # Mock Tavily API response
        mock_tavily_response = {
            "results": [
                {
                    "title": "Machine Learning in Healthcare: A Comprehensive Review",
                    "url": "https://journal.medical.edu/ml-healthcare",
                    "content": "This comprehensive review examines the applications of machine learning in healthcare, including diagnosis, treatment planning, and patient monitoring.",
                    "score": 0.95,
                },
                {
                    "title": "AI-Driven Medical Diagnostics",
                    "url": "https://research.hospital.gov/ai-diagnostics",
                    "content": "Government study on the effectiveness of AI in medical diagnostics shows 94% accuracy in early disease detection.",
                    "score": 0.90,
                },
                {
                    "title": "Ethical Considerations in Healthcare AI",
                    "url": "https://ethics.university.edu/healthcare-ai",
                    "content": "This paper explores the ethical implications of using artificial intelligence in healthcare settings.",
                    "score": 0.85,
                },
            ],
            "answer": "Machine learning is revolutionizing healthcare through improved diagnostics and treatment planning.",
        }

        # Mock research agent behavior
        async def mock_run_research(agent, keyword):
            return ResearchFindings(
                keyword=keyword,
                research_summary="Machine learning is transforming healthcare through applications in diagnosis, treatment planning, and patient monitoring. Studies show up to 94% accuracy in early disease detection, representing a significant advancement in medical technology and patient care.",
                academic_sources=[
                    AcademicSource(
                        title=result["title"],
                        url=result["url"],
                        excerpt=result["content"],
                        domain=".edu" if ".edu" in result["url"] else ".gov",
                        credibility_score=result["score"],
                        publication_date="2024-01-15",
                        authors=["Smith, J.", "Doe, A."],
                    )
                    for result in mock_tavily_response["results"]
                ],
                key_statistics=[
                    "94% accuracy in diagnosis",
                    "50% reduction in false positives",
                ],
                research_gaps=[
                    "Long-term impact studies needed",
                    "Integration with existing systems",
                ],
                main_findings=[
                    "ML significantly improves diagnostic accuracy",
                    "AI reduces healthcare costs",
                    "Ethical frameworks are still developing",
                ],
                total_sources_analyzed=10,
                search_query_used=f"{keyword} academic research",
            )

        # Mock writer agent behavior
        async def mock_run_writer(agent, keyword, research):
            return ArticleOutput(
                title=f"The Complete Guide to {keyword.title()}",
                meta_description=f"Discover how {keyword} is revolutionizing the industry with cutting-edge applications and proven benefits in this comprehensive guide.",
                focus_keyword=keyword,
                introduction=f"{keyword.title()} represents a paradigm shift in modern technology. This comprehensive guide explores the latest developments and applications.",
                main_sections=[
                    ArticleSection(
                        heading=f"What is {keyword.title()}?",
                        content=f"{keyword.title()} is a revolutionary technology that combines advanced algorithms with practical applications. {research.research_summary}",
                    ),
                    ArticleSection(
                        heading="Key Benefits and Applications",
                        content="The benefits are numerous and well-documented across various industries and use cases. "
                        + " ".join(research.main_findings)
                        + " These findings demonstrate the transformative potential of this technology in solving real-world problems and creating value for organizations.",
                    ),
                    ArticleSection(
                        heading="Future Outlook",
                        content="The future looks bright for this technology as research continues to advance and new applications emerge. However, there are important considerations to address: "
                        + " ".join(research.research_gaps)
                        + " Addressing these gaps will be crucial for the continued development and responsible deployment of this technology.",
                    ),
                ],
                conclusion=f"In conclusion, {keyword} will continue to shape our future in profound ways. Stay informed about the latest developments.",
                word_count=1200,
                reading_time_minutes=5,
                keyword_density=0.018,
                sources_used=[source.url for source in research.academic_sources[:2]],
            )

        # Patch the agent functions
        with patch("workflow.run_research_agent", mock_run_research):
            with patch("writer_agent.agent.run_writer_agent", mock_run_writer):
                # Create and run orchestrator
                orchestrator = WorkflowOrchestrator(config)
                result_path = await orchestrator.run_full_workflow(
                    "machine learning healthcare"
                )

                # Verify output files exist
                assert result_path.exists()
                assert result_path.name == "index.html"

                output_dir = result_path.parent
                assert (output_dir / "article.html").exists()
                assert (output_dir / "research.json").exists()

                # Verify article content
                article_html = (output_dir / "article.html").read_text()
                assert (
                    "The Complete Guide to Machine Learning Healthcare" in article_html
                )
                assert "machine learning healthcare" in article_html.lower()
                assert "<style>" in article_html  # CSS was added

                # Verify research JSON
                research_data = json.loads((output_dir / "research.json").read_text())
                assert research_data["keyword"] == "machine learning healthcare"
                assert len(research_data["academic_sources"]) == 3
                assert research_data["academic_sources"][0]["credibility_score"] == 0.95

                # Verify review interface
                review_html = result_path.read_text()
                assert "Content Review: machine learning healthcare" in review_html
                assert "1200" in review_html  # Word count
                assert "5" in review_html  # Reading time
                assert "View Full Article" in review_html

    @pytest.mark.integration
    def test_configuration_loading(self):
        """Test configuration loading from environment."""
        # Create mock environment
        mock_env = {
            "OPENAI_API_KEY": "sk-openai1234567890abcdef1234567890",
            "TAVILY_API_KEY": "sk-tavily1234567890abcdef1234567890",
            "OUTPUT_DIR": "/tmp/test_output",
            "LOG_LEVEL": "DEBUG",
            "LLM_MODEL": "gpt-4-turbo",
        }

        with patch.dict("os.environ", mock_env, clear=True):
            # Mock Path.exists to return True for .env check
            with patch("pathlib.Path.exists", return_value=False):
                config = get_config()

                assert config.openai_api_key == "sk-openai1234567890abcdef1234567890"
                assert config.tavily_api_key == "sk-tavily1234567890abcdef1234567890"
                assert config.output_dir == Path("/tmp/test_output")
                assert config.log_level == "DEBUG"
                assert config.llm_model == "gpt-4-turbo"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_propagation(self, tmp_path):
        """Test that errors propagate correctly through the system."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        # Test research failure
        with patch(
            "workflow.run_research_agent",
            AsyncMock(side_effect=Exception("Tavily API error")),
        ):
            orchestrator = WorkflowOrchestrator(config)

            with pytest.raises(Exception, match="Tavily API error"):
                await orchestrator.run_full_workflow("test keyword")

        # Test writing failure
        mock_research = ResearchFindings(
            keyword="test",
            research_summary="This is a comprehensive test summary that provides detailed information about the research findings and meets the minimum character requirement for validation purposes.",
            academic_sources=[
                AcademicSource(
                    title="Test",
                    url="https://test.edu",
                    excerpt="Test",
                    domain=".edu",
                    credibility_score=0.8,
                )
            ],
            main_findings=["1", "2", "3"],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        with patch(
            "workflow.run_research_agent", AsyncMock(return_value=mock_research)
        ):
            with patch(
                "writer_agent.agent.run_writer_agent",
                AsyncMock(side_effect=Exception("OpenAI API error")),
            ):
                orchestrator = WorkflowOrchestrator(config)

                with pytest.raises(Exception, match="OpenAI API error"):
                    await orchestrator.run_full_workflow("test keyword")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, tmp_path):
        """Test that retry mechanism works correctly."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
            max_retries=3,
        )

        # Track call count
        call_count = 0

        async def flaky_research(agent, keyword):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                raise Exception("Temporary network error")

            return ResearchFindings(
                keyword=keyword,
                research_summary="Success after retries - This research demonstrates the effectiveness of the retry mechanism in handling temporary network failures and ensuring reliable data collection processes.",
                academic_sources=[
                    AcademicSource(
                        title="Test",
                        url="https://test.edu",
                        excerpt="Test",
                        domain=".edu",
                        credibility_score=0.8,
                    )
                ],
                main_findings=["1", "2", "3"],
                total_sources_analyzed=1,
                search_query_used=keyword,
            )

        with patch("workflow.run_research_agent", flaky_research):
            orchestrator = WorkflowOrchestrator(config)
            result = await orchestrator.run_research("test keyword")

            # Should succeed after retries
            assert call_count == 3
            assert "Success after retries" in result.research_summary

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self, tmp_path):
        """Test running multiple workflows concurrently."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        # Mock quick responses
        async def mock_research(agent, keyword):
            await asyncio.sleep(0.1)  # Simulate API delay
            return ResearchFindings(
                keyword=keyword,
                research_summary=f"Comprehensive research findings for {keyword} demonstrate significant advancements in the field with practical applications across multiple industries and domains.",
                academic_sources=[
                    AcademicSource(
                        title=f"{keyword} Study",
                        url=f"https://test.edu/{keyword.replace(' ', '-')}",
                        excerpt=f"Study about {keyword}",
                        domain=".edu",
                        credibility_score=0.8,
                    )
                ],
                main_findings=["Finding 1", "Finding 2", "Finding 3"],
                total_sources_analyzed=1,
                search_query_used=keyword,
            )

        async def mock_writer(agent, keyword, research):
            await asyncio.sleep(0.1)  # Simulate API delay
            return ArticleOutput(
                title=f"Guide to {keyword}",
                meta_description=f"Learn about {keyword} in this comprehensive guide covering fundamental concepts, practical applications, and future developments in the field.",
                focus_keyword=keyword,
                introduction=f"Introduction to {keyword}. This comprehensive guide explores the fundamental concepts, practical applications, and latest developments in {keyword}, providing you with essential knowledge and insights.",
                main_sections=[
                    ArticleSection(
                        heading="Overview Section",
                        content=f"Overview of {keyword}. This section provides a comprehensive introduction to the key concepts and principles underlying {keyword}. We'll explore its historical development, current state, and importance in today's technological landscape.",
                    ),
                    ArticleSection(
                        heading="Key Features",
                        content=f"Key features of {keyword} include advanced capabilities, innovative approaches, and practical applications. This section delves into the specific characteristics that make {keyword} unique and valuable for various use cases across different industries.",
                    ),
                    ArticleSection(
                        heading="Implementation",
                        content=f"Implementation of {keyword} requires careful planning and consideration of various factors. This section provides practical guidance on how to effectively implement {keyword} solutions, including best practices, common pitfalls to avoid, and strategies for success.",
                    ),
                ],
                conclusion=f"Conclusion about {keyword}. In summary, {keyword} represents a significant advancement in technology with wide-ranging applications and future potential.",
                word_count=1000,
                reading_time_minutes=4,
                keyword_density=0.02,
                sources_used=[s.url for s in research.academic_sources],
            )

        with patch("workflow.run_research_agent", mock_research):
            with patch("writer_agent.agent.run_writer_agent", mock_writer):
                orchestrator = WorkflowOrchestrator(config)

                # Run multiple workflows concurrently
                keywords = ["AI research", "machine learning", "deep learning"]
                tasks = [
                    orchestrator.run_full_workflow(keyword) for keyword in keywords
                ]

                results = await asyncio.gather(*tasks)

                # Verify all completed successfully
                assert len(results) == 3
                for i, result in enumerate(results):
                    assert result.exists()
                    assert keywords[i].replace(" ", "_") in str(result.parent)


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    @pytest.mark.integration
    def test_cli_with_real_components(self, tmp_path):
        """Test CLI with real component initialization."""
        from click.testing import CliRunner

        from main import cli

        runner = CliRunner()

        # Create test environment
        test_env = {
            "OPENAI_API_KEY": "sk-test1234567890abcdef1234567890abcdef",
            "TAVILY_API_KEY": "sk-tavily1234567890abcdef1234567890",
            "OUTPUT_DIR": str(tmp_path),
        }

        with patch.dict("os.environ", test_env):
            # Test config command
            result = runner.invoke(cli, ["config", "--check"])
            assert result.exit_code == 0
            assert "Configuration is valid" in result.output

            # Test help
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
            assert "SEO Content Automation System" in result.output


# Performance tests
class TestPerformance:
    """Performance and scalability tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_content_handling(self, tmp_path):
        """Test handling of large content volumes."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        # Create large research findings
        large_sources = [
            AcademicSource(
                title=f"Source {i}",
                url=f"https://test{i}.edu/paper",
                excerpt="Lorem ipsum " * 20,  # Long excerpt but under 500 chars
                domain=".edu",
                credibility_score=0.8 + (i * 0.01),
            )
            for i in range(20)  # Many sources
        ]

        large_findings = ResearchFindings(
            keyword="test",
            research_summary="This is a comprehensive summary of large-scale research findings that demonstrates the system's ability to handle substantial volumes of data while maintaining accuracy and performance. "
            + "The research reveals significant patterns in data processing capabilities, scalability considerations, and optimization strategies. "
            * 3
            + "Our analysis shows robust handling of complex scenarios with consistent results across varied test conditions.",  # Long summary under 1000 chars
            academic_sources=large_sources,
            key_statistics=[f"Stat {i}" for i in range(50)],
            research_gaps=[f"Gap {i}" for i in range(20)],
            main_findings=[f"Finding {i}" for i in range(30)],
            total_sources_analyzed=100,
            search_query_used="test",
        )

        # Create large article
        large_sections = [
            ArticleSection(
                heading=f"Section {i}",
                content="Content paragraph. " * 100,  # Long content
            )
            for i in range(10)
        ]

        large_article = ArticleOutput(
            title="Comprehensive Test Article on Advanced Topics",
            meta_description="Test description covering comprehensive analysis of advanced topics with detailed insights and expert recommendations for practical applications.",
            focus_keyword="test",
            introduction="This comprehensive introduction explores the fundamental concepts of our test topic. "
            * 3
            + "We'll examine various aspects, methodologies, and practical applications to provide a thorough understanding of the subject matter.",
            main_sections=large_sections,
            conclusion="In conclusion, this comprehensive analysis has covered multiple aspects of the test topic. "
            * 2
            + "The insights provided offer valuable guidance for practical implementation.",
            word_count=10000,
            reading_time_minutes=40,
            keyword_density=0.02,
            sources_used=[s.url for s in large_sources[:10]],
        )

        # Test saving large outputs
        orchestrator = WorkflowOrchestrator(config)
        result = await orchestrator.save_outputs("test", large_findings, large_article)

        # Verify files were created and are reasonable size
        assert result.exists()
        article_size = (result.parent / "article.html").stat().st_size
        research_size = (result.parent / "research.json").stat().st_size

        assert article_size > 10000  # Should be substantial
        assert research_size > 5000  # Should contain all data
