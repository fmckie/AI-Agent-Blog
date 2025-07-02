"""
Comprehensive tests for workflow orchestration.

This test file covers the WorkflowOrchestrator class that manages
the complete pipeline from research to article generation.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Import testing utilities
import pytest

from config import Config
from models import AcademicSource, ArticleOutput, ArticleSection, ResearchFindings

# Import workflow components to test
from workflow import WorkflowOrchestrator
from tests.helpers import MockAgentRunResult, create_valid_article_output


class TestWorkflowOrchestrator:
    """Test cases for the workflow orchestrator."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.openai_api_key = "sk-test1234567890abcdef1234567890abcdef"
        config.tavily_api_key = "sk-tavily1234567890abcdef1234567890"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        sources = [
            AcademicSource(
                title="AI Research Paper",
                url="https://journal.edu/paper1",
                authors=["Smith, J."],
                publication_date="2024-01-01",
                excerpt="Important findings about AI",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="ML Study",
                url="https://university.edu/paper2",
                excerpt="Machine learning insights",
                domain=".edu",
                credibility_score=0.85,
            ),
            AcademicSource(
                title="Tech Report",
                url="https://institute.org/report",
                excerpt="Technical analysis",
                domain=".org",
                credibility_score=0.75,
            ),
        ]

        return ResearchFindings(
            keyword="artificial intelligence",
            research_summary="Comprehensive research on AI applications and impacts reveals transformative potential across multiple industries, with significant improvements in efficiency, accuracy, and decision-making capabilities.",
            academic_sources=sources,
            key_statistics=["85% improvement", "2x faster processing"],
            research_gaps=["Long-term effects unclear"],
            main_findings=[
                "AI transforms industries",
                "Ethical considerations crucial",
                "Rapid advancement continues",
            ],
            total_sources_analyzed=10,
            search_query_used="artificial intelligence research",
        )

    @pytest.fixture
    def mock_article_output(self):
        """Create mock article output."""
        sections = [
            ArticleSection(
                heading="Introduction to AI",
                content="Artificial intelligence represents a paradigm shift in technology. This comprehensive introduction explores the fundamental concepts of AI, its historical development, and its growing importance in modern society. We'll examine how AI is transforming various industries and shaping our future.",
            ),
            ArticleSection(
                heading="Applications of AI",
                content="AI applications span numerous industries, from healthcare and finance to transportation and entertainment. In healthcare, AI assists with diagnosis and treatment planning. In finance, it powers fraud detection and algorithmic trading. This section explores these diverse applications in detail.",
            ),
            ArticleSection(
                heading="Future of AI Technology",
                content="The future holds exciting possibilities for artificial intelligence. As technology advances, we can expect more sophisticated AI systems capable of complex reasoning and decision-making. This section examines emerging trends, potential breakthroughs, and the challenges that lie ahead.",
            ),
        ]

        return ArticleOutput(
            title="The Complete Guide to Artificial Intelligence",
            meta_description="Explore the world of artificial intelligence, its applications, benefits, and future prospects in this comprehensive guide.",
            focus_keyword="artificial intelligence",
            introduction="Artificial intelligence (AI) is revolutionizing how we live and work. This comprehensive guide explores the latest developments in AI technology, its practical applications across various industries, and its potential to transform our future.",
            main_sections=sections,
            conclusion="In conclusion, artificial intelligence will continue to shape our future in profound ways. As we embrace these technologies, we must ensure responsible development and deployment.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.015,
            sources_used=[
                "https://journal.edu/paper1",
                "https://university.edu/paper2",
            ],
        )

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create workflow orchestrator with mocked agents."""
        with patch("workflow.create_research_agent") as mock_create_research:
            with patch("workflow.create_writer_agent") as mock_create_writer:
                # Mock agent creation
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()

                return WorkflowOrchestrator(mock_config)

    @pytest.mark.asyncio
    async def test_full_workflow_success(
        self, orchestrator, mock_research_findings, mock_article_output
    ):
        """Test successful execution of full workflow."""
        # Mock the individual steps
        orchestrator.run_research = AsyncMock(return_value=mock_research_findings)
        orchestrator.run_writing = AsyncMock(return_value=mock_article_output)
        orchestrator._save_outputs_atomic = AsyncMock(
            return_value=Path("/tmp/test_output/index.html")
        )

        # Run workflow
        result = await orchestrator.run_full_workflow("artificial intelligence")

        # Verify all steps were called
        orchestrator.run_research.assert_called_once_with("artificial intelligence")
        orchestrator.run_writing.assert_called_once_with(
            "artificial intelligence", mock_research_findings
        )
        orchestrator._save_outputs_atomic.assert_called_once_with(
            "artificial intelligence", mock_research_findings, mock_article_output
        )

        # Check result
        assert isinstance(result, Path)
        assert str(result).endswith("index.html")

    @pytest.mark.asyncio
    async def test_workflow_research_failure(self, orchestrator):
        """Test workflow handling of research failure."""
        # Mock research to fail
        orchestrator.run_research = AsyncMock(
            side_effect=Exception("Research API error")
        )

        # Workflow should propagate the error
        with pytest.raises(Exception, match="Research API error"):
            await orchestrator.run_full_workflow("test keyword")

    @pytest.mark.asyncio
    async def test_workflow_writing_failure(self, orchestrator, mock_research_findings):
        """Test workflow handling of writing failure."""
        # Mock research success but writing failure
        orchestrator.run_research = AsyncMock(return_value=mock_research_findings)
        orchestrator.run_writing = AsyncMock(side_effect=Exception("Writing API error"))

        # Workflow should propagate the error
        with pytest.raises(Exception, match="Writing API error"):
            await orchestrator.run_full_workflow("test keyword")

    @pytest.mark.asyncio
    async def test_workflow_save_failure(
        self, orchestrator, mock_research_findings, mock_article_output
    ):
        """Test workflow handling of save failure."""
        # Mock steps succeed but save fails
        orchestrator.run_research = AsyncMock(return_value=mock_research_findings)
        orchestrator.run_writing = AsyncMock(return_value=mock_article_output)
        orchestrator._save_outputs_atomic = AsyncMock(side_effect=Exception("Disk full"))

        # Workflow should propagate the error
        with pytest.raises(Exception, match="Disk full"):
            await orchestrator.run_full_workflow("test keyword")


class TestResearchPhase:
    """Test cases for the research phase."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        sources = [
            AcademicSource(
                title="AI Research Paper",
                url="https://journal.edu/paper1",
                authors=["Smith, J."],
                publication_date="2024-01-01",
                excerpt="Important findings about AI",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="ML Study",
                url="https://university.edu/paper2",
                excerpt="Machine learning insights",
                domain=".edu",
                credibility_score=0.85,
            ),
            AcademicSource(
                title="Tech Report",
                url="https://institute.org/report",
                excerpt="Technical analysis",
                domain=".org",
                credibility_score=0.75,
            ),
        ]

        return ResearchFindings(
            keyword="artificial intelligence",
            research_summary="Comprehensive research on AI applications and impacts reveals transformative potential across multiple industries, with significant improvements in efficiency, accuracy, and decision-making capabilities.",
            academic_sources=sources,
            key_statistics=["85% improvement", "2x faster processing"],
            research_gaps=["Long-term effects unclear"],
            main_findings=[
                "AI transforms industries",
                "Ethical considerations crucial",
                "Rapid advancement continues",
            ],
            total_sources_analyzed=10,
            search_query_used="artificial intelligence research",
        )

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create workflow orchestrator with mocked agents."""
        with patch("workflow.create_research_agent") as mock_create_research:
            with patch("workflow.create_writer_agent") as mock_create_writer:
                # Mock agent creation
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()

                return WorkflowOrchestrator(mock_config)

    @pytest.mark.asyncio
    async def test_run_research_success(self, orchestrator, mock_research_findings):
        """Test successful research execution."""
        # Mock the research agent run
        with patch(
            "workflow.run_research_agent",
            AsyncMock(return_value=mock_research_findings),
        ):
            result = await orchestrator.run_research("artificial intelligence")

            # Verify result
            assert result == mock_research_findings
            assert len(result.academic_sources) == 3

    @pytest.mark.asyncio
    async def test_run_research_no_sources(self, orchestrator):
        """Test research with no sources found."""
        # Create findings with no sources
        empty_findings = ResearchFindings(
            keyword="obscure topic",
            research_summary="No relevant research found for this obscure topic. Despite extensive searching across multiple academic databases and sources, no credible information could be located.",
            academic_sources=[],
            main_findings=["No findings"],
            total_sources_analyzed=0,
            search_query_used="obscure topic",
        )

        with patch(
            "workflow.run_research_agent", AsyncMock(return_value=empty_findings)
        ):
            # Should raise ValueError for no sources
            with pytest.raises(ValueError, match="No academic sources found"):
                await orchestrator.run_research("obscure topic")

    @pytest.mark.asyncio
    async def test_run_research_minimum_sources_warning(self, orchestrator, caplog):
        """Test warning when minimum source count not met."""
        # Create findings with only 2 sources (below recommended 3)
        sources = [
            AcademicSource(
                title="Source 1",
                url="https://test1.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            ),
            AcademicSource(
                title="Source 2",
                url="https://test2.edu",
                excerpt="Test",
                domain=".edu",
                credibility_score=0.8,
            ),
        ]

        limited_findings = ResearchFindings(
            keyword="limited topic",
            research_summary="Limited research available on this topic. While some sources were found, the coverage is not comprehensive and additional investigation would be beneficial for a complete understanding.",
            academic_sources=sources,
            main_findings=["Finding 1", "Finding 2", "Finding 3"],
            total_sources_analyzed=2,
            search_query_used="limited topic",
        )

        with patch(
            "workflow.run_research_agent", AsyncMock(return_value=limited_findings)
        ):
            result = await orchestrator.run_research("limited topic")

            # Should succeed but log warning
            assert result == limited_findings
            assert "below the recommended minimum of 3" in caplog.text

    @pytest.mark.asyncio
    async def test_run_research_retry_on_failure(self, orchestrator, mock_research_findings):
        """Test research retry mechanism."""
        # Mock to fail twice then succeed
        call_count = 0

        async def mock_research_with_failures(agent, keyword):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary API error")
            return mock_research_findings

        with patch("workflow.run_research_agent", mock_research_with_failures):
            # Should succeed after retries
            result = await orchestrator.run_research("test")

            assert result == mock_research_findings
            assert call_count == 3  # Failed twice, succeeded on third


class TestWritingPhase:
    """Test cases for the writing phase."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        sources = [
            AcademicSource(
                title="AI Research Paper",
                url="https://journal.edu/paper1",
                authors=["Smith, J."],
                publication_date="2024-01-01",
                excerpt="Important findings about AI",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="ML Study",
                url="https://university.edu/paper2",
                excerpt="Machine learning insights",
                domain=".edu",
                credibility_score=0.85,
            ),
            AcademicSource(
                title="Tech Report",
                url="https://institute.org/report",
                excerpt="Technical analysis",
                domain=".org",
                credibility_score=0.75,
            ),
        ]

        return ResearchFindings(
            keyword="artificial intelligence",
            research_summary="Comprehensive research on AI applications and impacts reveals transformative potential across multiple industries, with significant improvements in efficiency, accuracy, and decision-making capabilities.",
            academic_sources=sources,
            key_statistics=["85% improvement", "2x faster processing"],
            research_gaps=["Long-term effects unclear"],
            main_findings=[
                "AI transforms industries",
                "Ethical considerations crucial",
                "Rapid advancement continues",
            ],
            total_sources_analyzed=10,
            search_query_used="artificial intelligence research",
        )

    @pytest.fixture
    def mock_article_output(self):
        """Create mock article output."""
        sections = [
            ArticleSection(
                heading="Introduction to AI",
                content="Artificial intelligence represents a paradigm shift in technology. This comprehensive introduction explores the fundamental concepts of AI, its historical development, and its growing importance in modern society. We'll examine how AI is transforming various industries and shaping our future.",
            ),
            ArticleSection(
                heading="Applications of AI",
                content="AI applications span numerous industries, from healthcare and finance to transportation and entertainment. In healthcare, AI assists with diagnosis and treatment planning. In finance, it powers fraud detection and algorithmic trading. This section explores these diverse applications in detail.",
            ),
            ArticleSection(
                heading="Future of AI Technology",
                content="The future holds exciting possibilities for artificial intelligence. As technology advances, we can expect more sophisticated AI systems capable of complex reasoning and decision-making. This section examines emerging trends, potential breakthroughs, and the challenges that lie ahead.",
            ),
        ]

        return ArticleOutput(
            title="The Complete Guide to Artificial Intelligence",
            meta_description="Explore the world of artificial intelligence, its applications, benefits, and future prospects in this comprehensive guide.",
            focus_keyword="artificial intelligence",
            introduction="Artificial intelligence (AI) is revolutionizing how we live and work. This comprehensive guide explores the latest developments in AI technology, its practical applications across various industries, and its potential to transform our future.",
            main_sections=sections,
            conclusion="In conclusion, artificial intelligence will continue to shape our future in profound ways. As we embrace these technologies, we must ensure responsible development and deployment.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.015,
            sources_used=[
                "https://journal.edu/paper1",
                "https://university.edu/paper2",
            ],
        )

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create workflow orchestrator with mocked agents."""
        with patch("workflow.create_research_agent") as mock_create_research:
            with patch("workflow.create_writer_agent") as mock_create_writer:
                # Mock agent creation
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()

                return WorkflowOrchestrator(mock_config)

    @pytest.mark.asyncio
    async def test_run_writing_success(
        self, orchestrator, mock_research_findings, mock_article_output
    ):
        """Test successful article generation."""
        # Mock the writer agent run
        with patch(
            "writer_agent.agent.run_writer_agent",
            AsyncMock(return_value=mock_article_output),
        ):
            result = await orchestrator.run_writing(
                "artificial intelligence", mock_research_findings
            )

            # Verify result
            assert result == mock_article_output
            assert result.word_count == 1500
            assert len(result.main_sections) == 3

    @pytest.mark.asyncio
    async def test_run_writing_with_context(
        self, orchestrator, mock_research_findings, mock_article_output
    ):
        """Test that research context is passed to writer."""
        # Mock the writer agent run
        mock_run_writer = AsyncMock(return_value=mock_article_output)

        with patch("writer_agent.agent.run_writer_agent", mock_run_writer):
            await orchestrator.run_writing(
                "artificial intelligence", mock_research_findings
            )

            # Verify writer was called with correct arguments
            mock_run_writer.assert_called_once_with(
                orchestrator.writer_agent,
                "artificial intelligence",
                mock_research_findings,
            )

    @pytest.mark.asyncio
    async def test_run_writing_failure(self, orchestrator, mock_research_findings):
        """Test handling of writing failures."""
        with patch(
            "writer_agent.agent.run_writer_agent",
            AsyncMock(side_effect=Exception("API quota exceeded")),
        ):

            with pytest.raises(Exception, match="API quota exceeded"):
                await orchestrator.run_writing("test keyword", mock_research_findings)


class TestOutputSaving:
    """Test cases for output saving functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        sources = [
            AcademicSource(
                title="AI Research Paper",
                url="https://journal.edu/paper1",
                authors=["Smith, J."],
                publication_date="2024-01-01",
                excerpt="Important findings about AI",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="ML Study",
                url="https://university.edu/paper2",
                excerpt="Machine learning insights",
                domain=".edu",
                credibility_score=0.85,
            ),
            AcademicSource(
                title="Tech Report",
                url="https://institute.org/report",
                excerpt="Technical analysis",
                domain=".org",
                credibility_score=0.75,
            ),
        ]

        return ResearchFindings(
            keyword="artificial intelligence",
            research_summary="Comprehensive research on AI applications and impacts reveals transformative potential across multiple industries, with significant improvements in efficiency, accuracy, and decision-making capabilities.",
            academic_sources=sources,
            key_statistics=["85% improvement", "2x faster processing"],
            research_gaps=["Long-term effects unclear"],
            main_findings=[
                "AI transforms industries",
                "Ethical considerations crucial",
                "Rapid advancement continues",
            ],
            total_sources_analyzed=10,
            search_query_used="artificial intelligence research",
        )

    @pytest.fixture
    def mock_article_output(self):
        """Create mock article output."""
        sections = [
            ArticleSection(
                heading="Introduction to AI",
                content="Artificial intelligence represents a paradigm shift in technology. This comprehensive introduction explores the fundamental concepts of AI, its historical development, and its growing importance in modern society. We'll examine how AI is transforming various industries and shaping our future.",
            ),
            ArticleSection(
                heading="Applications of AI",
                content="AI applications span numerous industries, from healthcare and finance to transportation and entertainment. In healthcare, AI assists with diagnosis and treatment planning. In finance, it powers fraud detection and algorithmic trading. This section explores these diverse applications in detail.",
            ),
            ArticleSection(
                heading="Future of AI Technology",
                content="The future holds exciting possibilities for artificial intelligence. As technology advances, we can expect more sophisticated AI systems capable of complex reasoning and decision-making. This section examines emerging trends, potential breakthroughs, and the challenges that lie ahead.",
            ),
        ]

        return ArticleOutput(
            title="The Complete Guide to Artificial Intelligence",
            meta_description="Explore the world of artificial intelligence, its applications, benefits, and future prospects in this comprehensive guide.",
            focus_keyword="artificial intelligence",
            introduction="Artificial intelligence (AI) is revolutionizing how we live and work. This comprehensive guide explores the latest developments in AI technology, its practical applications across various industries, and its potential to transform our future.",
            main_sections=sections,
            conclusion="In conclusion, artificial intelligence will continue to shape our future in profound ways. As we embrace these technologies, we must ensure responsible development and deployment.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.015,
            sources_used=[
                "https://journal.edu/paper1",
                "https://university.edu/paper2",
            ],
        )

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create workflow orchestrator with mocked agents."""
        with patch("workflow.create_research_agent") as mock_create_research:
            with patch("workflow.create_writer_agent") as mock_create_writer:
                # Mock agent creation
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()

                return WorkflowOrchestrator(mock_config)

    @pytest.mark.asyncio
    async def test_save_outputs_success(
        self, orchestrator, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test successful output saving."""
        # Use real temp directory
        orchestrator.output_dir = tmp_path

        # Save outputs
        result = await orchestrator.save_outputs(
            "test keyword", mock_research_findings, mock_article_output
        )

        # Verify files were created
        assert result.exists()
        assert result.name == "index.html"

        # Check directory structure
        output_dir = result.parent
        assert (output_dir / "article.html").exists()
        assert (output_dir / "research.json").exists()
        assert (output_dir / "index.html").exists()

        # Verify directory naming
        assert "test_keyword_" in output_dir.name
        assert datetime.now().strftime("%Y%m%d") in output_dir.name

    @pytest.mark.asyncio
    async def test_save_outputs_special_characters(
        self, orchestrator, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test saving with special characters in keyword."""
        orchestrator.output_dir = tmp_path

        # Keyword with special characters
        result = await orchestrator.save_outputs(
            "C++ & Python: A Comparison!", mock_research_findings, mock_article_output
        )

        # Check sanitized directory name - special chars should be replaced with single underscores
        output_dir = result.parent
        assert "C_Python_A_Comparison" in output_dir.name
        assert result.exists()

    @pytest.mark.asyncio
    async def test_save_outputs_html_content(
        self, orchestrator, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test that HTML content is properly saved."""
        orchestrator.output_dir = tmp_path

        result = await orchestrator.save_outputs(
            "test", mock_research_findings, mock_article_output
        )

        # Read and verify article HTML
        article_path = result.parent / "article.html"
        article_html = article_path.read_text()

        # Check that styling was added
        assert "<style>" in article_html
        assert "font-family:" in article_html
        assert mock_article_output.title in article_html

    @pytest.mark.asyncio
    async def test_save_outputs_json_content(
        self, orchestrator, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test that research JSON is properly saved."""
        orchestrator.output_dir = tmp_path

        result = await orchestrator.save_outputs(
            "test", mock_research_findings, mock_article_output
        )

        # Read and verify research JSON
        research_path = result.parent / "research.json"
        research_data = json.loads(research_path.read_text())

        # Check JSON structure
        assert research_data["keyword"] == "artificial intelligence"
        assert len(research_data["academic_sources"]) == 3
        assert research_data["total_sources_analyzed"] == 10

    @pytest.mark.asyncio
    async def test_save_outputs_review_interface(
        self, orchestrator, mock_research_findings, mock_article_output, tmp_path
    ):
        """Test review interface generation."""
        orchestrator.output_dir = tmp_path

        result = await orchestrator.save_outputs(
            "AI Research", mock_research_findings, mock_article_output
        )

        # Read review interface
        review_html = result.read_text()

        # Check content
        assert "Content Review: AI Research" in review_html
        assert str(mock_article_output.word_count) in review_html
        assert f"{mock_article_output.keyword_density:.1%}" in review_html
        assert "View Full Article" in review_html
        assert "View Research Data" in review_html

        # Check metrics display
        assert "1500" in review_html  # Word count
        assert "6" in review_html  # Reading time
        assert "3" in review_html  # Source count

    @pytest.mark.asyncio
    async def test_save_outputs_failure(
        self, orchestrator, mock_research_findings, mock_article_output
    ):
        """Test handling of save failures."""
        # Set output to unwritable location
        orchestrator.output_dir = Path("/root/forbidden")

        with pytest.raises(Exception):
            await orchestrator.save_outputs(
                "test", mock_research_findings, mock_article_output
            )


class TestStylingFunctions:
    """Test cases for HTML styling functions."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.output_dir = Path("/tmp/test_output")
        config.openai_api_key = "test_key"
        config.tavily_api_key = "test_key"
        config.max_retries = 3
        return config

    @pytest.fixture
    def mock_research_findings(self):
        """Create mock research findings."""
        sources = [
            AcademicSource(
                title="AI Research Paper",
                url="https://journal.edu/paper1",
                authors=["Smith, J."],
                publication_date="2024-01-01",
                excerpt="Important findings about AI",
                domain=".edu",
                credibility_score=0.9,
            ),
            AcademicSource(
                title="ML Study",
                url="https://university.edu/paper2",
                excerpt="Machine learning insights",
                domain=".edu",
                credibility_score=0.85,
            ),
            AcademicSource(
                title="Tech Report",
                url="https://institute.org/report",
                excerpt="Technical analysis",
                domain=".org",
                credibility_score=0.75,
            ),
        ]

        return ResearchFindings(
            keyword="artificial intelligence",
            research_summary="Comprehensive research on AI applications and impacts reveals transformative potential across multiple industries, with significant improvements in efficiency, accuracy, and decision-making capabilities.",
            academic_sources=sources,
            key_statistics=["85% improvement", "2x faster processing"],
            research_gaps=["Long-term effects unclear"],
            main_findings=[
                "AI transforms industries",
                "Ethical considerations crucial",
                "Rapid advancement continues",
            ],
            total_sources_analyzed=10,
            search_query_used="artificial intelligence research",
        )

    @pytest.fixture
    def mock_article_output(self):
        """Create mock article output."""
        sections = [
            ArticleSection(
                heading="Introduction to AI",
                content="Artificial intelligence represents a paradigm shift in technology. This comprehensive introduction explores the fundamental concepts of AI, its historical development, and its growing importance in modern society. We'll examine how AI is transforming various industries and shaping our future.",
            ),
            ArticleSection(
                heading="Applications of AI",
                content="AI applications span numerous industries, from healthcare and finance to transportation and entertainment. In healthcare, AI assists with diagnosis and treatment planning. In finance, it powers fraud detection and algorithmic trading. This section explores these diverse applications in detail.",
            ),
            ArticleSection(
                heading="Future of AI Technology",
                content="The future holds exciting possibilities for artificial intelligence. As technology advances, we can expect more sophisticated AI systems capable of complex reasoning and decision-making. This section examines emerging trends, potential breakthroughs, and the challenges that lie ahead.",
            ),
        ]

        return ArticleOutput(
            title="The Complete Guide to Artificial Intelligence",
            meta_description="Explore the world of artificial intelligence, its applications, benefits, and future prospects in this comprehensive guide.",
            focus_keyword="artificial intelligence",
            introduction="Artificial intelligence (AI) is revolutionizing how we live and work. This comprehensive guide explores the latest developments in AI technology, its practical applications across various industries, and its potential to transform our future.",
            main_sections=sections,
            conclusion="In conclusion, artificial intelligence will continue to shape our future in profound ways. As we embrace these technologies, we must ensure responsible development and deployment.",
            word_count=1500,
            reading_time_minutes=6,
            keyword_density=0.015,
            sources_used=[
                "https://journal.edu/paper1",
                "https://university.edu/paper2",
            ],
        )

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create workflow orchestrator with mocked agents."""
        with patch("workflow.create_research_agent") as mock_create_research:
            with patch("workflow.create_writer_agent") as mock_create_writer:
                # Mock agent creation
                mock_create_research.return_value = Mock()
                mock_create_writer.return_value = Mock()

                return WorkflowOrchestrator(mock_config)

    def test_add_styling_to_html(self, orchestrator):
        """Test CSS styling addition to HTML."""
        basic_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test</title>
        </head>
        <body>
            <h1>Test Article</h1>
        </body>
        </html>
        """

        styled_html = orchestrator._add_styling_to_html(basic_html)

        # Check CSS was added
        assert "<style>" in styled_html
        assert "body {" in styled_html
        assert "font-family:" in styled_html
        assert "max-width: 800px" in styled_html

        # Check CSS is in the right place
        assert styled_html.index("<style>") < styled_html.index("</head>")

    def test_create_review_interface(
        self, orchestrator, mock_research_findings, mock_article_output
    ):
        """Test review interface creation."""
        html = orchestrator._create_review_interface(
            "test keyword", mock_article_output, mock_research_findings
        )

        # Check structure
        assert "<!DOCTYPE html>" in html
        assert "Content Review: test keyword" in html

        # Check metrics
        assert "1500" in html  # Word count
        assert "6" in html  # Reading time
        assert "1.5%" in html  # Keyword density

        # Check sources
        assert "AI Research Paper" in html
        assert "0.90" in html  # Credibility score

        # Check links
        assert 'href="article.html"' in html
        assert 'href="research.json"' in html


# Integration tests
class TestWorkflowIntegration:
    """Integration tests for the complete workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, mock_config, tmp_path):
        """Test the complete workflow end-to-end."""
        # Use real temp directory
        mock_config.output_dir = tmp_path

        # Create test data
        test_research = ResearchFindings(
            keyword="blockchain",
            research_summary="Blockchain technology overview reveals revolutionary potential in distributed ledger systems, offering unprecedented security and transparency for digital transactions across various industries.",
            academic_sources=[
                AcademicSource(
                    title="Blockchain Study",
                    url="https://test.edu/blockchain",
                    excerpt="Distributed ledger technology",
                    domain=".edu",
                    credibility_score=0.85,
                )
            ],
            main_findings=["Decentralized", "Secure", "Transparent"],
            total_sources_analyzed=5,
            search_query_used="blockchain technology",
        )

        test_article = ArticleOutput(
            title="Understanding Blockchain",
            meta_description="A comprehensive guide to blockchain technology and its applications in modern digital systems, cryptocurrencies, and decentralized finance.",
            focus_keyword="blockchain",
            introduction="Blockchain is revolutionizing digital transactions and data management. This comprehensive guide explores the fundamental concepts of blockchain technology, its practical applications, and its potential to transform various industries through decentralization.",
            main_sections=[
                ArticleSection(
                    heading="What is Blockchain?",
                    content="Blockchain is a distributed ledger technology that enables secure, transparent, and tamper-proof record-keeping. At its core, blockchain consists of a chain of blocks, each containing transaction data, timestamps, and cryptographic hashes that link to previous blocks.",
                ),
                ArticleSection(
                    heading="How Blockchain Works",
                    content="Understanding how blockchain works requires examining its key components: nodes, miners, consensus mechanisms, and cryptographic security. Each transaction is verified by multiple nodes in the network, ensuring integrity and preventing double-spending without central authority.",
                ),
                ArticleSection(
                    heading="Blockchain Applications",
                    content="Beyond cryptocurrencies, blockchain technology finds applications in supply chain management, healthcare records, voting systems, and smart contracts. These implementations leverage blockchain's inherent security and transparency to solve real-world problems efficiently.",
                ),
            ],
            conclusion="Blockchain will continue to evolve and reshape how we think about trust, security, and decentralization in digital systems. Its impact extends far beyond cryptocurrency.",
            word_count=1000,
            reading_time_minutes=4,
            keyword_density=0.018,
            sources_used=["https://test.edu/blockchain"],
        )

        # Mock agent functions
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch(
                    "workflow.run_research_agent", AsyncMock(return_value=test_research)
                ):
                    with patch(
                        "writer_agent.agent.run_writer_agent",
                        AsyncMock(return_value=test_article),
                    ):

                        orchestrator = WorkflowOrchestrator(mock_config)
                        result = await orchestrator.run_full_workflow("blockchain")

                        # Verify output
                        assert result.exists()
                        assert result.name == "index.html"

                        # Check all files exist
                        output_dir = result.parent
                        assert (output_dir / "article.html").exists()
                        assert (output_dir / "research.json").exists()

                        # Verify content
                        article_content = (output_dir / "article.html").read_text()
                        assert "Understanding Blockchain" in article_content
                        assert "blockchain" in article_content.lower()

    @pytest.mark.asyncio
    async def test_workflow_with_retries(self, mock_config):
        """Test workflow with retry mechanism."""
        # Create orchestrator
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                orchestrator = WorkflowOrchestrator(mock_config)

                # Mock research to fail twice then succeed
                call_count = 0
                test_research = Mock(spec=ResearchFindings)
                test_research.academic_sources = [Mock()]
                test_research.main_findings = ["Finding 1", "Finding 2"]
                test_research.key_statistics = ["Stat 1", "Stat 2"]
                test_research.research_gaps = ["Gap 1"]

                async def flaky_research(agent, keyword):
                    nonlocal call_count
                    call_count += 1
                    if call_count < 3:
                        raise Exception("Temporary failure")
                    return test_research

                with patch("workflow.run_research_agent", flaky_research):
                    # Should eventually succeed
                    result = await orchestrator.run_research("test")
                    assert result == test_research
                    assert call_count == 3

    @pytest.mark.asyncio
    async def test_workflow_with_unicode_keyword(self, mock_config, tmp_path):
        """Test workflow handles unicode and special characters in keywords."""
        mock_config.output_dir = tmp_path
        
        # Test various unicode keywords
        unicode_keywords = [
            "健康管理",  # Japanese
            "santé",  # French with accent
            "α-β testing",  # Greek letters
            "emoji 🚀 test",  # Emoji
            "test/slash",  # Path separator
            "test\\backslash",  # Backslash
        ]
        
        test_research = ResearchFindings(
            keyword="test",
            research_summary="Test summary for unicode handling.",
            academic_sources=[
                AcademicSource(
                    title="Unicode Test Study",
                    url="https://test.edu/unicode",
                    excerpt="Testing unicode handling",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["Unicode works"],
            total_sources_analyzed=1,
            search_query_used="test",
        )
        
        # Use helper to create valid article
        test_article = create_valid_article_output(
            keyword="test",
            title="Unicode Article Test: Special Characters Support",
            sources_count=1
        )
        # Add unicode content to test unicode handling
        test_article.main_sections[0].content = ("Content with unicode: 测试 santé α-β 🚀. " +
                                                test_article.main_sections[0].content)
        
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch("workflow.run_research_agent", AsyncMock(return_value=test_research)):
                    with patch("writer_agent.agent.run_writer_agent", AsyncMock(return_value=test_article)):
                        orchestrator = WorkflowOrchestrator(mock_config)
                        
                        for keyword in unicode_keywords:
                            # Should not raise any exceptions
                            result = await orchestrator.run_full_workflow(keyword)
                            assert result.exists()
                            
                            # Verify safe filename was created
                            output_dir = result.parent
                            assert output_dir.exists()

    @pytest.mark.asyncio
    async def test_workflow_performance_benchmark(self, mock_config, tmp_path):
        """Test workflow performance meets expectations."""
        import time
        
        mock_config.output_dir = tmp_path
        
        # Create minimal test data for speed
        test_research = ResearchFindings(
            keyword="performance test",
            research_summary="Quick performance test.",
            academic_sources=[
                AcademicSource(
                    title="Perf Test",
                    url="https://test.edu/perf",
                    excerpt="Performance testing",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["Fast"],
            total_sources_analyzed=1,
            search_query_used="performance test",
        )
        
        # Use helper to create valid article
        test_article = create_valid_article_output(
            keyword="performance test",
            title="Performance Test Article: Benchmarking Results",
            sources_count=1
        )
        
        # Mock agents with instant responses
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch("workflow.run_research_agent", AsyncMock(return_value=test_research)):
                    with patch("writer_agent.agent.run_writer_agent", AsyncMock(return_value=test_article)):
                        orchestrator = WorkflowOrchestrator(mock_config)
                        
                        start_time = time.time()
                        result = await orchestrator.run_full_workflow("performance test")
                        end_time = time.time()
                        
                        # Workflow should complete quickly when agents are mocked
                        execution_time = end_time - start_time
                        assert execution_time < 1.0  # Should complete in under 1 second
                        assert result.exists()

    @pytest.mark.asyncio
    async def test_workflow_with_minimal_research(self, mock_config, tmp_path):
        """Test workflow handles cases with minimal research findings."""
        mock_config.output_dir = tmp_path
        
        # Create research with minimal data
        minimal_research = ResearchFindings(
            keyword="obscure topic",
            research_summary="Very limited information available.",
            academic_sources=[],  # No sources found
            main_findings=[],  # No findings
            key_statistics=[],  # No statistics
            research_gaps=["Everything needs more research"],
            total_sources_analyzed=0,
            search_query_used="obscure topic",
        )
        
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch("workflow.run_research_agent", AsyncMock(return_value=minimal_research)):
                    orchestrator = WorkflowOrchestrator(mock_config)
                    
                    # Should raise ValueError for no sources
                    with pytest.raises(ValueError, match="No academic sources found"):
                        await orchestrator.run_research("obscure topic")

    @pytest.mark.asyncio
    async def test_workflow_large_content_handling(self, mock_config, tmp_path):
        """Test workflow handles large articles properly."""
        mock_config.output_dir = tmp_path
        
        # Create large content
        large_content = "This is a test paragraph. " * 200  # ~2000 words
        
        test_research = ResearchFindings(
            keyword="large content",
            research_summary="Testing large content handling.",
            academic_sources=[
                AcademicSource(
                    title="Large Content Study",
                    url="https://test.edu/large",
                    excerpt="Study on large content",
                    domain=".edu",
                    credibility_score=0.9,
                )
            ],
            main_findings=["Large content works"],
            total_sources_analyzed=1,
            search_query_used="large content",
        )
        
        test_article = ArticleOutput(
            title="Large Content Article",
            meta_description="Testing system handling of large articles and content generation with comprehensive validation of performance and reliability for extensive content volumes.",
            focus_keyword="large content",
            introduction=large_content[:500],
            main_sections=[
                ArticleSection(
                    heading="Section 1",
                    content=large_content,
                ),
                ArticleSection(
                    heading="Section 2",
                    content=large_content,
                ),
                ArticleSection(
                    heading="Section 3",
                    content=large_content,
                ),
            ],
            conclusion="Large article conclusion. This comprehensive test demonstrates the system's ability to handle substantial content volumes while maintaining performance and quality standards.",
            word_count=6000,  # Large word count
            reading_time_minutes=24,
            keyword_density=0.015,
            sources_used=["https://test.edu/large"],
        )
        
        with patch("workflow.create_research_agent", return_value=Mock()):
            with patch("workflow.create_writer_agent", return_value=Mock()):
                with patch("workflow.run_research_agent", AsyncMock(return_value=test_research)):
                    with patch("writer_agent.agent.run_writer_agent", AsyncMock(return_value=test_article)):
                        orchestrator = WorkflowOrchestrator(mock_config)
                        result = await orchestrator.run_full_workflow("large content")
                        
                        # Verify large content was saved properly
                        assert result.exists()
                        output_dir = result.parent
                        article_content = (output_dir / "article.html").read_text()
                        
                        # Should contain the large content
                        assert len(article_content) > 10000  # Should be a large file
                        assert "Large Content Article" in article_content
