"""
Comprehensive tests for ResearchStrategy class.

This module tests topic classification, research depth determination,
tool selection, and adaptive strategy functionality.
"""

import pytest
from typing import Dict, List

from models import AcademicSource
from research_agent.strategy import (
    ResearchStrategy,
    TopicType,
    ResearchDepth,
    ToolType,
    ToolRecommendation,
    ResearchPlan
)


class TestTopicClassification:
    """Test topic type classification functionality."""
    
    @pytest.fixture
    def strategy(self):
        """Create a ResearchStrategy instance for testing."""
        return ResearchStrategy()
    
    def test_academic_topic_classification(self, strategy):
        """Test classification of academic topics."""
        # Test clear academic keywords
        assert strategy.analyze_topic("quantum computing research") == TopicType.ACADEMIC
        assert strategy.analyze_topic("peer-reviewed study on climate change") == TopicType.ACADEMIC
        assert strategy.analyze_topic("meta-analysis of educational methods") == TopicType.ACADEMIC
        assert strategy.analyze_topic("dissertation on machine learning") == TopicType.ACADEMIC
        
        # Test with context
        assert strategy.analyze_topic(
            "AI ethics",
            "looking for academic papers and research studies"
        ) == TopicType.ACADEMIC
    
    def test_technical_topic_classification(self, strategy):
        """Test classification of technical topics."""
        assert strategy.analyze_topic("Python programming tutorial") == TopicType.TECHNICAL
        assert strategy.analyze_topic("API documentation for REST services") == TopicType.TECHNICAL
        assert strategy.analyze_topic("debugging JavaScript frameworks") == TopicType.TECHNICAL
        assert strategy.analyze_topic("software architecture patterns") == TopicType.TECHNICAL
        assert strategy.analyze_topic("algorithm optimization techniques") == TopicType.TECHNICAL
    
    def test_medical_topic_classification(self, strategy):
        """Test classification of medical topics."""
        assert strategy.analyze_topic("diabetes treatment options") == TopicType.MEDICAL
        assert strategy.analyze_topic("COVID-19 vaccine efficacy") == TopicType.MEDICAL
        assert strategy.analyze_topic("clinical trials for cancer therapy") == TopicType.MEDICAL
        assert strategy.analyze_topic("patient outcomes in healthcare") == TopicType.MEDICAL
        
        # Test with medical context
        assert strategy.analyze_topic(
            "blood pressure",
            "looking for medical research and treatment guidelines"
        ) == TopicType.MEDICAL
    
    def test_business_topic_classification(self, strategy):
        """Test classification of business topics."""
        assert strategy.analyze_topic("startup investment strategies") == TopicType.BUSINESS
        assert strategy.analyze_topic("market analysis for e-commerce") == TopicType.BUSINESS
        assert strategy.analyze_topic("revenue optimization techniques") == TopicType.BUSINESS
        assert strategy.analyze_topic("business leadership principles") == TopicType.BUSINESS
    
    def test_news_topic_classification(self, strategy):
        """Test classification of news/current events topics."""
        assert strategy.analyze_topic("latest AI developments") == TopicType.NEWS
        assert strategy.analyze_topic("breaking news on technology") == TopicType.NEWS
        assert strategy.analyze_topic("recent updates in quantum computing") == TopicType.NEWS
        assert strategy.analyze_topic("today's market trends") == TopicType.NEWS
    
    def test_emerging_topic_classification(self, strategy):
        """Test classification of emerging topics."""
        assert strategy.analyze_topic("new breakthrough in quantum computing") == TopicType.EMERGING
        assert strategy.analyze_topic("cutting-edge AI research 2024") == TopicType.EMERGING
        assert strategy.analyze_topic("novel coronavirus variant") == TopicType.EMERGING
        assert strategy.analyze_topic("next-generation battery technology") == TopicType.EMERGING
    
    def test_general_topic_classification(self, strategy):
        """Test fallback to general classification."""
        assert strategy.analyze_topic("random topic") == TopicType.GENERAL
        assert strategy.analyze_topic("something interesting") == TopicType.GENERAL
        assert strategy.analyze_topic("tell me about stuff") == TopicType.GENERAL
    
    def test_mixed_indicator_classification(self, strategy):
        """Test topics with mixed indicators."""
        # Academic wins due to keyword weighting
        topic = strategy.analyze_topic("research on latest business trends")
        assert topic in [TopicType.ACADEMIC, TopicType.BUSINESS, TopicType.NEWS]
        
        # Medical should win with strong indicators
        assert strategy.analyze_topic(
            "clinical research on new treatment methods"
        ) == TopicType.MEDICAL


class TestResearchDepthDetermination:
    """Test research depth determination logic."""
    
    @pytest.fixture
    def strategy(self):
        return ResearchStrategy()
    
    def test_default_depth(self, strategy):
        """Test default depth is standard."""
        depth = strategy.determine_research_depth("test topic")
        assert depth == ResearchDepth.STANDARD
    
    def test_quick_research_depth(self, strategy):
        """Test surface depth for quick research."""
        depth = strategy.determine_research_depth(
            "AI basics",
            {"quick": True}
        )
        assert depth == ResearchDepth.SURFACE
        
        depth = strategy.determine_research_depth(
            "Python overview",
            {"overview": True}
        )
        assert depth == ResearchDepth.SURFACE
    
    def test_comprehensive_research_depth(self, strategy):
        """Test deep depth for comprehensive research."""
        depth = strategy.determine_research_depth(
            "quantum computing",
            {"comprehensive": True}
        )
        assert depth == ResearchDepth.DEEP
        
        depth = strategy.determine_research_depth(
            "machine learning",
            {"thorough": True}
        )
        assert depth == ResearchDepth.DEEP
    
    def test_exhaustive_research_depth(self, strategy):
        """Test exhaustive depth for complete research."""
        depth = strategy.determine_research_depth(
            "climate change",
            {"exhaustive": True}
        )
        assert depth == ResearchDepth.EXHAUSTIVE
        
        depth = strategy.determine_research_depth(
            "medical research",
            {"complete": True}
        )
        assert depth == ResearchDepth.EXHAUSTIVE
    
    def test_time_constraint_depth(self, strategy):
        """Test depth based on time constraints."""
        # Very short time = surface
        depth = strategy.determine_research_depth(
            "test topic",
            {"time_limit_minutes": 3}
        )
        assert depth == ResearchDepth.SURFACE
        
        # Long time = deep
        depth = strategy.determine_research_depth(
            "test topic",
            {"time_limit_minutes": 45}
        )
        assert depth == ResearchDepth.DEEP
        
        # Medium time = standard (default)
        depth = strategy.determine_research_depth(
            "test topic",
            {"time_limit_minutes": 15}
        )
        assert depth == ResearchDepth.STANDARD
    
    def test_complex_topic_depth_upgrade(self, strategy):
        """Test that complex topics get upgraded depth."""
        # Simple topic
        simple_depth = strategy.determine_research_depth("AI")
        
        # Complex topic with multiple parts
        complex_depth = strategy.determine_research_depth(
            "machine learning and deep learning algorithms"
        )
        
        # Complex topic with comparison
        comparison_depth = strategy.determine_research_depth(
            "TensorFlow vs PyTorch for production systems"
        )
        
        # Complex topics should have deeper research
        assert simple_depth == ResearchDepth.STANDARD
        assert complex_depth in [ResearchDepth.STANDARD, ResearchDepth.DEEP]
        
        # Surface should be upgraded to standard for complex topics
        surface_complex = strategy.determine_research_depth(
            "quantum computing vs classical computing performance",
            {"quick": True}
        )
        assert surface_complex == ResearchDepth.STANDARD


class TestToolSelection:
    """Test tool selection based on topic and depth."""
    
    @pytest.fixture
    def strategy(self):
        return ResearchStrategy()
    
    def test_basic_tool_selection(self, strategy):
        """Test that search is always included as primary tool."""
        primary, optional = strategy.select_tools(
            TopicType.GENERAL,
            ResearchDepth.SURFACE,
            []
        )
        
        # Search should always be first
        assert len(primary) > 0
        assert primary[0].tool == ToolType.SEARCH
        assert primary[0].priority == 10
    
    def test_deep_research_tool_selection(self, strategy):
        """Test tool selection for deep research."""
        primary, optional = strategy.select_tools(
            TopicType.ACADEMIC,
            ResearchDepth.DEEP,
            []
        )
        
        # Should include search and extract as primary
        tool_types = [t.tool for t in primary]
        assert ToolType.SEARCH in tool_types
        assert ToolType.EXTRACT in tool_types
        
        # Extract should be high priority for deep research
        extract_tool = next(t for t in primary if t.tool == ToolType.EXTRACT)
        assert extract_tool.priority >= 9
    
    def test_academic_topic_tool_selection(self, strategy):
        """Test tool selection for academic topics."""
        primary, optional = strategy.select_tools(
            TopicType.ACADEMIC,
            ResearchDepth.STANDARD,
            []
        )
        
        # Academic topics should include crawl for .edu domains
        tool_types = [t.tool for t in primary]
        assert ToolType.CRAWL in tool_types
        
        # Check crawl parameters
        crawl_tool = next(t for t in primary if t.tool == ToolType.CRAWL)
        assert ".edu" in crawl_tool.parameters["target_domains"]
        assert ".gov" in crawl_tool.parameters["target_domains"]
    
    def test_technical_topic_tool_selection(self, strategy):
        """Test tool selection for technical topics."""
        primary, optional = strategy.select_tools(
            TopicType.TECHNICAL,
            ResearchDepth.STANDARD,
            []
        )
        
        # Extract should be optional for standard depth
        optional_types = [t.tool for t in optional]
        assert ToolType.CRAWL in optional_types
        
        # Check for documentation-focused parameters
        crawl_tool = next(t for t in optional if t.tool == ToolType.CRAWL)
        assert "documentation" in crawl_tool.parameters["focus"]
    
    def test_medical_topic_tool_selection(self, strategy):
        """Test tool selection for medical topics."""
        primary, optional = strategy.select_tools(
            TopicType.MEDICAL,
            ResearchDepth.STANDARD,
            []
        )
        
        # Medical topics need high credibility extraction
        tool_types = [t.tool for t in primary]
        assert ToolType.EXTRACT in tool_types
        
        extract_tool = next(t for t in primary if t.tool == ToolType.EXTRACT)
        assert extract_tool.parameters.get("credibility_threshold", 0) >= 0.8
    
    def test_emerging_topic_tool_selection(self, strategy):
        """Test tool selection for emerging topics."""
        primary, optional = strategy.select_tools(
            TopicType.EMERGING,
            ResearchDepth.STANDARD,
            []
        )
        
        # Emerging topics should use multi-step research
        tool_types = [t.tool for t in primary]
        assert ToolType.MULTI_STEP in tool_types
        
        multi_tool = next(t for t in primary if t.tool == ToolType.MULTI_STEP)
        assert multi_tool.parameters.get("include_news") is True
    
    def test_exhaustive_research_tool_selection(self, strategy):
        """Test tool selection for exhaustive research."""
        primary, optional = strategy.select_tools(
            TopicType.ACADEMIC,
            ResearchDepth.EXHAUSTIVE,
            []
        )
        
        # All optional tools should become primary
        assert len(optional) == 0
        
        # Should have all major tools
        tool_types = [t.tool for t in primary]
        assert ToolType.SEARCH in tool_types
        assert ToolType.EXTRACT in tool_types
        assert ToolType.CRAWL in tool_types
        
        # Crawl should be comprehensive
        crawl_tool = next(t for t in primary if t.tool == ToolType.CRAWL)
        assert crawl_tool.parameters.get("comprehensive") is True
        assert crawl_tool.parameters.get("max_depth") >= 3


class TestResearchPlanCreation:
    """Test complete research plan creation."""
    
    @pytest.fixture
    def strategy(self):
        return ResearchStrategy()
    
    def test_basic_research_plan(self, strategy):
        """Test creation of basic research plan."""
        plan = strategy.create_research_plan("artificial intelligence")
        
        assert plan.topic_type in [TopicType.TECHNICAL, TopicType.ACADEMIC]
        assert plan.research_depth == ResearchDepth.STANDARD
        assert len(plan.primary_tools) > 0
        assert len(plan.search_queries) > 0
        assert len(plan.target_domains) > 0
    
    def test_research_plan_with_requirements(self, strategy):
        """Test plan creation with specific requirements."""
        plan = strategy.create_research_plan(
            "machine learning",
            {
                "comprehensive": True,
                "time_limit_minutes": 60,
                "context": "for production systems"
            }
        )
        
        assert plan.research_depth == ResearchDepth.DEEP
        assert plan.time_constraints == "60 minutes"
        assert "production" in plan.special_instructions.lower()
    
    def test_research_plan_with_initial_results(self, strategy):
        """Test plan creation with initial search results."""
        initial_results = [
            AcademicSource(
                title="ML Paper 1",
                url="https://arxiv.org/paper1",
                authors=["Author"],
                publication_date="2024",
                credibility_score=0.9,
                relevance_score=0.8,
                key_findings=["Finding"],
                methodology="Method",
                citations=10
            ),
            AcademicSource(
                title="ML Tutorial",
                url="https://ml.university.edu/tutorial",
                authors=["Professor"],
                publication_date="2024",
                credibility_score=0.95,
                relevance_score=0.9,
                key_findings=["Tutorial"],
                methodology="Educational",
                citations=50
            )
        ]
        
        plan = strategy.create_research_plan(
            "machine learning optimization",
            initial_results=initial_results
        )
        
        # Should identify available domains
        assert "arxiv.org" in [d for d in plan.target_domains]
        assert any(".edu" in d for d in plan.target_domains)
    
    def test_search_query_generation(self, strategy):
        """Test search query generation for different topics."""
        # Academic topic
        academic_plan = strategy.create_research_plan("quantum computing research")
        assert any("peer-reviewed" in q for q in academic_plan.search_queries)
        assert any("research study" in q for q in academic_plan.search_queries)
        
        # Technical topic
        technical_plan = strategy.create_research_plan("Python async programming")
        assert any("documentation" in q for q in technical_plan.search_queries)
        assert any("implementation" in q for q in technical_plan.search_queries)
        
        # Medical topic
        medical_plan = strategy.create_research_plan("diabetes treatment")
        assert any("clinical" in q for q in medical_plan.search_queries)
        assert any("treatment guidelines" in q for q in medical_plan.search_queries)
    
    def test_domain_targeting(self, strategy):
        """Test domain targeting for different topic types."""
        # Academic should prefer .edu/.gov
        academic_plan = strategy.create_research_plan("academic research methods")
        assert ".edu" in academic_plan.target_domains
        assert ".gov" in academic_plan.target_domains
        
        # Technical should include documentation sites
        technical_plan = strategy.create_research_plan("React hooks tutorial")
        assert any("github.com" in d or ".io" in d for d in technical_plan.target_domains)
        
        # Medical should include health organizations
        medical_plan = strategy.create_research_plan("COVID-19 vaccines")
        assert any("nih.gov" in d or "who.int" in d for d in medical_plan.target_domains)
    
    def test_special_instructions_generation(self, strategy):
        """Test special instructions based on topic and depth."""
        # Academic topic
        academic_plan = strategy.create_research_plan(
            "climate change research",
            {"research_depth": "exhaustive"}
        )
        assert "peer-reviewed" in academic_plan.special_instructions
        assert "methodology" in academic_plan.special_instructions
        
        # Technical topic
        technical_plan = strategy.create_research_plan("Docker containers")
        assert "documentation" in technical_plan.special_instructions
        assert "code samples" in technical_plan.special_instructions
        
        # Medical topic
        medical_plan = strategy.create_research_plan("heart disease prevention")
        assert "authoritative sources" in medical_plan.special_instructions
        assert "study sizes" in medical_plan.special_instructions


class TestAdaptiveStrategy:
    """Test adaptive strategy functionality."""
    
    @pytest.fixture
    def strategy(self):
        return ResearchStrategy()
    
    @pytest.fixture
    def initial_plan(self, strategy):
        """Create an initial research plan."""
        return strategy.create_research_plan("machine learning algorithms")
    
    def test_adapt_strategy_poor_results(self, strategy, initial_plan):
        """Test adaptation when initial results are poor."""
        # Simulate poor results
        intermediate_results = {
            "sources_count": 2,
            "average_credibility": 0.4,
            "domains": ["blog.example.com", "medium.com"]
        }
        
        adapted_plan = strategy.adapt_strategy(initial_plan, intermediate_results)
        
        # Should broaden search
        assert len(adapted_plan.search_queries) > len(initial_plan.search_queries)
        # Should upgrade optional tools to primary
        assert len(adapted_plan.primary_tools) >= len(initial_plan.primary_tools)
    
    def test_adapt_strategy_excellent_results(self, strategy, initial_plan):
        """Test adaptation when results are excellent."""
        # Simulate excellent results
        intermediate_results = {
            "sources_count": 15,
            "average_credibility": 0.85,
            "domains": ["mit.edu", "stanford.edu", "arxiv.org", "nature.com"]
        }
        
        adapted_plan = strategy.adapt_strategy(initial_plan, intermediate_results)
        
        # Should focus on high-priority tools only
        high_priority_tools = [t for t in adapted_plan.primary_tools if t.priority >= 8]
        assert len(high_priority_tools) <= len(initial_plan.primary_tools)
        
        # Should reduce extraction targets
        extract_tool = next(
            (t for t in adapted_plan.primary_tools if t.tool == ToolType.EXTRACT),
            None
        )
        if extract_tool:
            assert extract_tool.parameters.get("top_n_sources", 10) <= 3
    
    def test_adapt_strategy_academic_domains(self, strategy):
        """Test adaptation when good academic domains are found."""
        initial_plan = strategy.create_research_plan(
            "quantum physics research",
            {"strategy": "standard"}
        )
        
        # Simulate finding good academic domains
        intermediate_results = {
            "sources_count": 8,
            "average_credibility": 0.75,
            "domains": ["physics.mit.edu", "quantum.stanford.edu", "physics.harvard.edu"]
        }
        
        adapted_plan = strategy.adapt_strategy(initial_plan, intermediate_results)
        
        # Should prioritize crawling for academic topics with good domains
        if initial_plan.topic_type == TopicType.ACADEMIC:
            # Check if crawl was promoted from optional to primary
            primary_tools = [t.tool for t in adapted_plan.primary_tools]
            assert ToolType.CRAWL in primary_tools
    
    def test_adapt_strategy_no_change_needed(self, strategy, initial_plan):
        """Test when no adaptation is needed."""
        # Simulate adequate results
        intermediate_results = {
            "sources_count": 6,
            "average_credibility": 0.72,
            "domains": ["example.edu", "research.com", "journal.org"]
        }
        
        adapted_plan = strategy.adapt_strategy(initial_plan, intermediate_results)
        
        # Plan should remain similar
        assert len(adapted_plan.primary_tools) == len(initial_plan.primary_tools)
        assert adapted_plan.search_queries == initial_plan.search_queries


class TestDomainExtraction:
    """Test domain extraction utilities."""
    
    @pytest.fixture
    def strategy(self):
        return ResearchStrategy()
    
    def test_extract_domains_from_sources(self, strategy):
        """Test extracting domains from academic sources."""
        sources = [
            AcademicSource(
                title="Paper 1",
                url="https://www.example.edu/paper1",
                authors=["Author"],
                publication_date="2024",
                credibility_score=0.8,
                relevance_score=0.9,
                key_findings=["Finding"],
                methodology="Method",
                citations=5
            ),
            AcademicSource(
                title="Paper 2",
                url="https://research.university.edu/study",
                authors=["Author"],
                publication_date="2024",
                credibility_score=0.8,
                relevance_score=0.9,
                key_findings=["Finding"],
                methodology="Method",
                citations=5
            ),
            AcademicSource(
                title="Paper 3",
                url="https://www.example.edu/paper2",  # Duplicate domain
                authors=["Author"],
                publication_date="2024",
                credibility_score=0.8,
                relevance_score=0.9,
                key_findings=["Finding"],
                methodology="Method",
                citations=5
            )
        ]
        
        domains = strategy._extract_domains(sources)
        
        assert "www.example.edu" in domains
        assert "research.university.edu" in domains
        assert len(domains) == 2  # Should deduplicate


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def strategy(self):
        return ResearchStrategy()
    
    def test_empty_keyword(self, strategy):
        """Test handling of empty keyword."""
        plan = strategy.create_research_plan("")
        assert plan.topic_type == TopicType.GENERAL
        assert len(plan.search_queries) > 0
    
    def test_very_long_keyword(self, strategy):
        """Test handling of very long keyword."""
        long_keyword = " ".join(["word"] * 50)
        plan = strategy.create_research_plan(long_keyword)
        
        # Should still create valid plan
        assert plan.topic_type is not None
        assert len(plan.primary_tools) > 0
    
    def test_special_characters_in_keyword(self, strategy):
        """Test handling of special characters."""
        plan = strategy.create_research_plan("C++ vs C# performance @2024")
        
        assert plan.topic_type == TopicType.TECHNICAL
        assert len(plan.search_queries) > 0
    
    def test_adapt_with_no_sources(self, strategy):
        """Test adaptation with no sources found."""
        plan = strategy.create_research_plan("test topic")
        
        intermediate_results = {
            "sources_count": 0,
            "average_credibility": 0,
            "domains": []
        }
        
        adapted_plan = strategy.adapt_strategy(plan, intermediate_results)
        
        # Should broaden search significantly
        assert len(adapted_plan.search_queries) > len(plan.search_queries)
        assert len(adapted_plan.primary_tools) >= len(plan.primary_tools)