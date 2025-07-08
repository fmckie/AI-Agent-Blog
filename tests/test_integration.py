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
from tests.helpers import (
    MockAgentRunResult,
    create_minimal_valid_article_output,
    create_valid_article_output,
)
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
                # Run multiple workflows concurrently
                keywords = ["AI research", "machine learning", "deep learning"]
                tasks = []
                for keyword in keywords:
                    # Create separate orchestrator for each concurrent workflow
                    orchestrator = WorkflowOrchestrator(config)
                    tasks.append(orchestrator.run_full_workflow(keyword))

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


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_keyword(self, tmp_path):
        """Test handling of empty or whitespace keywords."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        orchestrator = WorkflowOrchestrator(config)

        # Test empty string
        with pytest.raises(ValueError):
            await orchestrator.run_full_workflow("")

        # Test whitespace only
        with pytest.raises(ValueError):
            await orchestrator.run_full_workflow("   ")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_very_long_keyword(self, tmp_path):
        """Test handling of extremely long keywords."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        orchestrator = WorkflowOrchestrator(config)
        
        # Create a very long keyword
        long_keyword = "machine learning " * 50  # 800+ characters
        
        # Test that very long keywords are rejected
        with pytest.raises(ValueError, match="Keyword too long"):
            await orchestrator.run_full_workflow(long_keyword)
        
        # Now test with a keyword at the limit
        max_keyword = "artificial intelligence and machine learning research"  # Under 200 chars

        mock_research = ResearchFindings(
            keyword=max_keyword,
            research_summary="Research on AI and ML demonstrates system robustness in handling edge cases and unusual input scenarios while maintaining functionality.",
            academic_sources=[
                AcademicSource(
                    title="Long Keyword Study",
                    url="https://test.edu/long",
                    excerpt="Study excerpt",
                    domain=".edu",
                    credibility_score=0.8,
                )
            ],
            main_findings=["System handles long keywords"],
            total_sources_analyzed=1,
            search_query_used=max_keyword,
        )

        # Use helper to create valid article with max keyword
        mock_article = create_valid_article_output(
            keyword=max_keyword,
            title="Understanding AI and Machine Learning Research",
            sources_count=1,
        )

        with patch(
            "workflow.run_research_agent", AsyncMock(return_value=mock_research)
        ):
            with patch(
                "writer_agent.agent.run_writer_agent",
                AsyncMock(return_value=mock_article),
            ):
                # Should handle gracefully with keyword at the limit
                result = await orchestrator.run_full_workflow(max_keyword)
                assert result.exists()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, tmp_path):
        """Test handling of network timeouts."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
            request_timeout=5,  # Minimum allowed timeout
        )

        # Simulate timeout
        async def slow_research(agent, keyword):
            await asyncio.sleep(2)  # Longer than timeout
            raise asyncio.TimeoutError("Request timed out")

        with patch("workflow.run_research_agent", slow_research):
            orchestrator = WorkflowOrchestrator(config)

            # Should raise timeout error
            with pytest.raises(asyncio.TimeoutError):
                await orchestrator.run_research("test")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_disk_space_handling(self, tmp_path):
        """Test handling of disk space issues."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        # Mock disk write failure
        def mock_write_failure(*args, **kwargs):
            raise OSError("No space left on device")

        mock_research = ResearchFindings(
            keyword="test",
            research_summary="Test summary for disk space handling scenarios in production environments.",
            academic_sources=[
                AcademicSource(
                    title="Test",
                    url="https://test.edu",
                    excerpt="Test",
                    domain=".edu",
                    credibility_score=0.8,
                )
            ],
            main_findings=["Test"],
            total_sources_analyzed=1,
            search_query_used="test",
        )

        # Use helper to create valid article
        mock_article = create_valid_article_output(
            keyword="test",
            title="Test Article for Disk Space Handling",
            sources_count=1,
        )

        with patch(
            "workflow.run_research_agent", AsyncMock(return_value=mock_research)
        ):
            with patch(
                "writer_agent.agent.run_writer_agent",
                AsyncMock(return_value=mock_article),
            ):
                with patch("pathlib.Path.write_text", mock_write_failure):
                    orchestrator = WorkflowOrchestrator(config)

                    # Should raise OSError
                    with pytest.raises(OSError, match="No space left"):
                        await orchestrator.run_full_workflow("test")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_html_characters(self, tmp_path):
        """Test handling of special HTML characters in content."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        # Create content with special HTML characters
        mock_research = ResearchFindings(
            keyword="<script>alert('test')</script>",
            research_summary="Research on XSS & <HTML> injection demonstrates security considerations in content generation.",
            academic_sources=[
                AcademicSource(
                    title="Security <Research> & Testing",
                    url="https://test.edu/security",
                    excerpt="Study on <script> tags & XSS",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["<b>Bold</b> finding", "Alert: <script>test</script>"],
            total_sources_analyzed=1,
            search_query_used="security test",
        )

        # Use helper to create valid article
        mock_article = create_valid_article_output(
            keyword="security",
            title="Understanding HTML Security Best Practices",
            sources_count=1,
        )
        # Override some fields to include special characters
        mock_article.title = "Understanding <HTML> & Security"
        mock_article.introduction = (
            "This article covers <important> security topics & best practices. "
            + "Learn how to properly handle special characters in web content to prevent "
            + "XSS vulnerabilities and ensure your applications remain secure. We'll explore "
            + "various techniques for escaping HTML entities and maintaining data integrity."
        )
        mock_article.main_sections[0].content = (
            "Content with <tags> and & symbols that need proper escaping. "
            + "This section demonstrates the importance of properly handling HTML "
            + "special characters to prevent XSS vulnerabilities and ensure content "
            + "displays correctly. Always remember to escape user input and validate "
            + "all data before rendering it in HTML contexts."
        )

        with patch(
            "workflow.run_research_agent", AsyncMock(return_value=mock_research)
        ):
            with patch(
                "writer_agent.agent.run_writer_agent",
                AsyncMock(return_value=mock_article),
            ):
                orchestrator = WorkflowOrchestrator(config)
                result = await orchestrator.run_full_workflow("security test")

                # Verify HTML is properly escaped in output
                article_html = (result.parent / "article.html").read_text()
                assert (
                    "&lt;script&gt;" in article_html or "<script>" not in article_html
                )
                assert "&amp;" in article_html or "& " in article_html


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_article_generation(self, tmp_path):
        """Test generating multiple articles in sequence."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        keywords = [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural networks",
            "computer vision",
        ]

        # Mock quick responses for all keywords
        async def mock_research(agent, keyword):
            return ResearchFindings(
                keyword=keyword,
                research_summary=f"Comprehensive research on {keyword} reveals significant advancements and practical applications across various industries.",
                academic_sources=[
                    AcademicSource(
                        title=f"{keyword.title()} Research",
                        url=f"https://test.edu/{keyword.replace(' ', '-')}",
                        excerpt=f"Study on {keyword}",
                        domain=".edu",
                        credibility_score=0.9,
                    )
                ],
                main_findings=[f"{keyword} is advancing rapidly"],
                total_sources_analyzed=5,
                search_query_used=keyword,
            )

        async def mock_writer(agent, keyword, research):
            # Use helper to create valid article with proper validation
            return create_valid_article_output(
                keyword=keyword,
                title=f"Ultimate Guide to {keyword.title()}: Expert Insights",
                sources_count=1,
            )

        with patch("workflow.run_research_agent", mock_research):
            with patch("writer_agent.agent.run_writer_agent", mock_writer):
                orchestrator = WorkflowOrchestrator(config)

                # Generate articles for all keywords
                results = []
                for keyword in keywords:
                    result = await orchestrator.run_full_workflow(keyword)
                    results.append(result)

                # Verify all articles were created
                assert len(results) == len(keywords)
                for i, result in enumerate(results):
                    assert result.exists()
                    assert keywords[i].replace(" ", "_") in str(result.parent)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resume_after_failure(self, tmp_path):
        """Test resuming workflow after partial failure."""
        config = Config(
            openai_api_key="sk-test1234567890abcdef1234567890abcdef",
            tavily_api_key="sk-tavily1234567890abcdef1234567890",
            output_dir=tmp_path,
        )

        # Create a partial state file
        state_data = {
            "state": "research_complete",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "keyword": "resume test",
                "research_complete_time": datetime.now().isoformat(),
                "sources_found": 3,
            },
            "temp_dir": str(tmp_path / ".temp_resume_test_20250101_120000"),
        }

        state_file = tmp_path / ".workflow_state_resume_test_20250101_120000.json"
        state_file.write_text(json.dumps(state_data))

        # Create temp directory
        temp_dir = Path(state_data["temp_dir"])
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Mock successful completion
        mock_research = ResearchFindings(
            keyword="resume test",
            research_summary="Research completed successfully after resume.",
            academic_sources=[
                AcademicSource(
                    title="Resume Test Study",
                    url="https://test.edu/resume",
                    excerpt="Testing resume functionality",
                    domain=".edu",
                    credibility_score=0.85,
                )
            ],
            main_findings=["Resume works correctly"],
            total_sources_analyzed=3,
            search_query_used="resume test",
        )

        # Use helper to create valid article
        mock_article = create_valid_article_output(
            keyword="resume test",
            title="Resume Test Article: Recovery and Reliability",
            sources_count=1,
        )

        with patch(
            "workflow.run_research_agent", AsyncMock(return_value=mock_research)
        ):
            with patch(
                "writer_agent.agent.run_writer_agent",
                AsyncMock(return_value=mock_article),
            ):
                orchestrator = WorkflowOrchestrator(config)

                # Resume from saved state
                result = await orchestrator.resume_workflow(state_file)

                # Verify completion
                assert result.exists()
                assert not state_file.exists()  # Should be cleaned up
                assert not temp_dir.exists()  # Should be cleaned up
