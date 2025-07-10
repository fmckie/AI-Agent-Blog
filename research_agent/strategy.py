"""
Research strategy implementation for dynamic tool selection.

This module implements intelligent strategies for selecting appropriate
research tools based on topic analysis and research goals.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from models import AcademicSource

# Set up logging for strategy decisions
logger = logging.getLogger(__name__)


class TopicType(Enum):
    """Classification of research topics."""

    ACADEMIC = "academic"  # Peer-reviewed, scholarly topics
    TECHNICAL = "technical"  # Programming, engineering, technical docs
    MEDICAL = "medical"  # Health, medical research
    BUSINESS = "business"  # Business, finance, economics
    NEWS = "news"  # Current events, recent developments
    GENERAL = "general"  # General knowledge topics
    EMERGING = "emerging"  # New, cutting-edge topics with limited research


class ResearchDepth(Enum):
    """Depth of research required."""

    SURFACE = "surface"  # Quick overview
    STANDARD = "standard"  # Balanced research
    DEEP = "deep"  # Comprehensive investigation
    EXHAUSTIVE = "exhaustive"  # Maximum depth with all tools


class ToolType(Enum):
    """Available research tools."""

    SEARCH = "search"  # Basic web search
    EXTRACT = "extract"  # Full content extraction
    CRAWL = "crawl"  # Website crawling
    MAP = "map"  # Site structure mapping
    MULTI_STEP = "multi_step"  # Orchestrated multi-tool research


@dataclass
class ToolRecommendation:
    """Recommendation for tool usage."""

    tool: ToolType
    priority: int  # 1-10, higher is more important
    reasoning: str
    parameters: Dict[str, Any]


@dataclass
class ResearchPlan:
    """Complete research plan with tool recommendations."""

    topic_type: TopicType
    research_depth: ResearchDepth
    primary_tools: List[ToolRecommendation]
    optional_tools: List[ToolRecommendation]
    search_queries: List[str]
    target_domains: List[str]
    time_constraints: Optional[str] = None
    special_instructions: Optional[str] = None


class ResearchStrategy:
    """
    Intelligent research strategy selection based on topic analysis.

    This class analyzes research topics and initial results to determine
    the most effective tools and approaches for comprehensive research.
    """

    def __init__(self):
        """Initialize the research strategy analyzer."""
        # Topic indicators for classification
        self.topic_indicators = {
            TopicType.ACADEMIC: [
                "research",
                "study",
                "theory",
                "hypothesis",
                "methodology",
                "peer-reviewed",
                "journal",
                "academic",
                "scholar",
                "university",
                "dissertation",
                "thesis",
                "literature review",
                "meta-analysis",
            ],
            TopicType.TECHNICAL: [
                "programming",
                "coding",
                "software",
                "algorithm",
                "framework",
                "api",
                "documentation",
                "tutorial",
                "implementation",
                "debug",
                "architecture",
                "design pattern",
                "best practices",
                "optimization",
            ],
            TopicType.MEDICAL: [
                "health",
                "medical",
                "disease",
                "treatment",
                "clinical",
                "patient",
                "diagnosis",
                "therapy",
                "drug",
                "medication",
                "symptom",
                "condition",
                "healthcare",
                "epidemiology",
            ],
            TopicType.BUSINESS: [
                "business",
                "market",
                "finance",
                "economics",
                "strategy",
                "revenue",
                "profit",
                "investment",
                "startup",
                "enterprise",
                "management",
                "leadership",
                "marketing",
                "sales",
            ],
            TopicType.NEWS: [
                "latest",
                "recent",
                "breaking",
                "current",
                "today",
                "yesterday",
                "update",
                "announcement",
                "news",
                "trending",
                "happening",
                "development",
                "event",
            ],
            TopicType.EMERGING: [
                "new",
                "emerging",
                "cutting-edge",
                "breakthrough",
                "novel",
                "innovative",
                "future",
                "next-generation",
                "experimental",
                "beta",
                "preview",
                "upcoming",
            ],
        }

        # Domain preferences by topic type
        self.domain_preferences = {
            TopicType.ACADEMIC: [
                ".edu",
                ".gov",
                "scholar.google.com",
                "pubmed.ncbi.nlm.nih.gov",
            ],
            TopicType.TECHNICAL: [
                ".io",
                "github.com",
                "stackoverflow.com",
                ".dev",
                "docs.",
            ],
            TopicType.MEDICAL: [".gov", ".edu", "nih.gov", "who.int", ".org"],
            TopicType.BUSINESS: [".com", "bloomberg.com", "forbes.com", "wsj.com"],
            TopicType.NEWS: [".com", ".org", "reuters.com", "apnews.com"],
            TopicType.GENERAL: [".org", ".com", ".edu", ".gov"],
        }

    def analyze_topic(
        self, keyword: str, initial_context: Optional[str] = None
    ) -> TopicType:
        """
        Analyze a research topic to determine its type.

        Args:
            keyword: The research keyword/topic
            initial_context: Optional context about the research

        Returns:
            The classified topic type
        """
        keyword_lower = keyword.lower()
        context_lower = initial_context.lower() if initial_context else ""
        combined_text = f"{keyword_lower} {context_lower}"

        # Score each topic type
        scores: Dict[TopicType, int] = {}

        for topic_type, indicators in self.topic_indicators.items():
            score = sum(1 for indicator in indicators if indicator in combined_text)
            # Weight keyword matches higher than context matches
            keyword_score = sum(
                2 for indicator in indicators if indicator in keyword_lower
            )
            scores[topic_type] = score + keyword_score

        # Check for explicit emerging topics
        if any(
            indicator in keyword_lower
            for indicator in ["2024", "2025", "latest", "new"]
        ):
            scores[TopicType.EMERGING] = scores.get(TopicType.EMERGING, 0) + 3

        # Return the highest scoring type, defaulting to GENERAL
        if max(scores.values()) == 0:
            return TopicType.GENERAL

        return max(scores.items(), key=lambda x: x[1])[0]

    def determine_research_depth(
        self, keyword: str, requirements: Optional[Dict[str, Any]] = None
    ) -> ResearchDepth:
        """
        Determine the appropriate research depth.

        Args:
            keyword: The research topic
            requirements: Optional requirements (e.g., time constraints, quality needs)

        Returns:
            The recommended research depth
        """
        # Default to standard depth
        depth = ResearchDepth.STANDARD

        if requirements:
            # Check for explicit depth requirements
            if requirements.get("quick") or requirements.get("overview"):
                depth = ResearchDepth.SURFACE
            elif requirements.get("comprehensive") or requirements.get("thorough"):
                depth = ResearchDepth.DEEP
            elif requirements.get("exhaustive") or requirements.get("complete"):
                depth = ResearchDepth.EXHAUSTIVE

            # Check for time constraints
            time_limit = requirements.get("time_limit_minutes", 0)
            if time_limit > 0 and time_limit < 5:
                depth = ResearchDepth.SURFACE
            elif time_limit > 30:
                depth = ResearchDepth.DEEP

        # Complex topics need deeper research
        if len(keyword.split()) > 3 or "and" in keyword or "vs" in keyword:
            if depth == ResearchDepth.SURFACE:
                depth = ResearchDepth.STANDARD
            elif depth == ResearchDepth.STANDARD:
                depth = ResearchDepth.DEEP

        return depth

    def select_tools(
        self,
        topic_type: TopicType,
        research_depth: ResearchDepth,
        available_domains: Optional[List[str]] = None,
    ) -> Tuple[List[ToolRecommendation], List[ToolRecommendation]]:
        """
        Select appropriate tools based on topic and depth.

        Args:
            topic_type: The classified topic type
            research_depth: The required research depth
            available_domains: Optional list of domains found in initial search

        Returns:
            Tuple of (primary_tools, optional_tools)
        """
        primary_tools = []
        optional_tools = []

        # Always start with search for discovery
        primary_tools.append(
            ToolRecommendation(
                tool=ToolType.SEARCH,
                priority=10,
                reasoning="Initial discovery and source identification",
                parameters={
                    "max_results": 10 if research_depth == ResearchDepth.SURFACE else 20
                },
            )
        )

        # Depth-based tool selection
        if research_depth in [ResearchDepth.DEEP, ResearchDepth.EXHAUSTIVE]:
            # Deep research needs extraction
            primary_tools.append(
                ToolRecommendation(
                    tool=ToolType.EXTRACT,
                    priority=9,
                    reasoning="Full content needed for comprehensive analysis",
                    parameters={
                        "top_n_sources": (
                            5 if research_depth == ResearchDepth.DEEP else 10
                        )
                    },
                )
            )
        elif research_depth == ResearchDepth.STANDARD:
            # Standard research uses extraction as optional
            optional_tools.append(
                ToolRecommendation(
                    tool=ToolType.EXTRACT,
                    priority=7,
                    reasoning="Extract if high-value sources found",
                    parameters={"top_n_sources": 3},
                )
            )

        # Topic-specific tool selection
        if topic_type == TopicType.ACADEMIC:
            # Academic topics benefit from crawling .edu domains
            primary_tools.append(
                ToolRecommendation(
                    tool=ToolType.CRAWL,
                    priority=8,
                    reasoning="Academic sites often have related papers and datasets",
                    parameters={
                        "target_domains": [".edu", ".gov"],
                        "max_depth": 2,
                        "focus": "publications, research, papers",
                    },
                )
            )

        elif topic_type == TopicType.TECHNICAL:
            # Technical topics need documentation crawling
            optional_tools.append(
                ToolRecommendation(
                    tool=ToolType.CRAWL,
                    priority=8,
                    reasoning="Technical documentation sites have comprehensive guides",
                    parameters={
                        "target_domains": ["docs.", "github.com", ".io"],
                        "max_depth": 3,
                        "focus": "documentation, tutorials, examples",
                    },
                )
            )

            # Map documentation sites for structure
            optional_tools.append(
                ToolRecommendation(
                    tool=ToolType.MAP,
                    priority=6,
                    reasoning="Understand documentation organization",
                    parameters={"focus": "api, guides, tutorials"},
                )
            )

        elif topic_type == TopicType.MEDICAL:
            # Medical research needs authoritative sources
            primary_tools.append(
                ToolRecommendation(
                    tool=ToolType.EXTRACT,
                    priority=9,
                    reasoning="Medical information requires full context",
                    parameters={"credibility_threshold": 0.8},
                )
            )

            # Crawl government health sites
            optional_tools.append(
                ToolRecommendation(
                    tool=ToolType.CRAWL,
                    priority=7,
                    reasoning="Government health sites have comprehensive data",
                    parameters={
                        "target_domains": ["nih.gov", "cdc.gov", "who.int"],
                        "max_depth": 2,
                        "focus": "studies, statistics, guidelines",
                    },
                )
            )

        elif topic_type == TopicType.EMERGING:
            # Emerging topics need broad coverage
            primary_tools.append(
                ToolRecommendation(
                    tool=ToolType.MULTI_STEP,
                    priority=9,
                    reasoning="Emerging topics require comprehensive multi-angle research",
                    parameters={"include_news": True, "time_range": "3months"},
                )
            )

        # Exhaustive research uses all tools
        if research_depth == ResearchDepth.EXHAUSTIVE:
            # Upgrade all optional tools to primary
            primary_tools.extend(optional_tools)
            optional_tools = []

            # Add comprehensive crawling
            primary_tools.append(
                ToolRecommendation(
                    tool=ToolType.CRAWL,
                    priority=8,
                    reasoning="Exhaustive research requires deep domain exploration",
                    parameters={"max_depth": 3, "comprehensive": True},
                )
            )

        # Sort by priority
        primary_tools.sort(key=lambda x: x.priority, reverse=True)
        optional_tools.sort(key=lambda x: x.priority, reverse=True)

        return primary_tools, optional_tools

    def create_research_plan(
        self,
        keyword: str,
        requirements: Optional[Dict[str, Any]] = None,
        initial_results: Optional[List[AcademicSource]] = None,
    ) -> ResearchPlan:
        """
        Create a comprehensive research plan.

        Args:
            keyword: The research topic
            requirements: Optional requirements and constraints
            initial_results: Optional initial search results for analysis

        Returns:
            Complete research plan with recommendations
        """
        # Analyze the topic
        topic_type = self.analyze_topic(
            keyword, requirements.get("context") if requirements else None
        )

        # Determine depth
        research_depth = self.determine_research_depth(keyword, requirements)

        # Analyze available domains if we have initial results
        available_domains = []
        if initial_results:
            available_domains = self._extract_domains(initial_results)

        # Select tools
        primary_tools, optional_tools = self.select_tools(
            topic_type, research_depth, available_domains
        )

        # Generate search queries
        search_queries = self._generate_search_queries(keyword, topic_type)

        # Identify target domains
        target_domains = self._identify_target_domains(topic_type, available_domains)

        # Time constraints
        time_constraints = None
        if requirements and requirements.get("time_limit_minutes"):
            time_constraints = f"{requirements['time_limit_minutes']} minutes"

        # Special instructions based on topic
        special_instructions = self._generate_special_instructions(
            topic_type, research_depth
        )

        return ResearchPlan(
            topic_type=topic_type,
            research_depth=research_depth,
            primary_tools=primary_tools,
            optional_tools=optional_tools,
            search_queries=search_queries,
            target_domains=target_domains,
            time_constraints=time_constraints,
            special_instructions=special_instructions,
        )

    def adapt_strategy(
        self, current_plan: ResearchPlan, intermediate_results: Dict[str, Any]
    ) -> ResearchPlan:
        """
        Adapt the research strategy based on intermediate results.

        Args:
            current_plan: The current research plan
            intermediate_results: Results from executed stages

        Returns:
            Updated research plan
        """
        # Analyze what we've found so far
        sources_found = intermediate_results.get("sources_count", 0)
        source_quality = intermediate_results.get("average_credibility", 0)
        domains_covered = intermediate_results.get("domains", [])

        # Make adjustments
        if sources_found < 3 and source_quality < 0.7:
            # Poor initial results - need to broaden search
            logger.info("Adapting strategy: Broadening search due to limited results")

            # Add alternative search queries
            current_plan.search_queries.extend(
                [
                    f"{current_plan.topic_type.value} {keyword}"
                    for keyword in current_plan.search_queries[0].split()[:2]
                ]
            )

            # Upgrade optional tools to primary
            current_plan.primary_tools.extend(current_plan.optional_tools)
            current_plan.optional_tools = []

        elif sources_found > 10 and source_quality > 0.8:
            # Excellent results - can be more selective
            logger.info("Adapting strategy: Focusing on high-quality sources")

            # Remove lower-priority tools
            current_plan.primary_tools = [
                tool for tool in current_plan.primary_tools if tool.priority >= 8
            ]

            # Add extraction for top sources only
            for tool in current_plan.primary_tools:
                if tool.tool == ToolType.EXTRACT:
                    tool.parameters["top_n_sources"] = 3

        # Check if we need domain-specific crawling
        edu_gov_domains = [d for d in domains_covered if ".edu" in d or ".gov" in d]
        if len(edu_gov_domains) >= 2 and current_plan.topic_type == TopicType.ACADEMIC:
            # Good academic domains found - prioritize crawling
            crawl_tool = next(
                (t for t in current_plan.optional_tools if t.tool == ToolType.CRAWL),
                None,
            )
            if crawl_tool:
                current_plan.primary_tools.append(crawl_tool)
                current_plan.optional_tools.remove(crawl_tool)

        return current_plan

    def _extract_domains(self, sources: List[AcademicSource]) -> List[str]:
        """Extract unique domains from sources."""
        domains = set()
        for source in sources:
            # Extract domain from URL
            match = re.search(r"https?://([^/]+)", source.url)
            if match:
                domains.add(match.group(1))
        return list(domains)

    def _generate_search_queries(
        self, keyword: str, topic_type: TopicType
    ) -> List[str]:
        """Generate multiple search queries for comprehensive coverage."""
        queries = [keyword]  # Always include the original

        # Add topic-specific modifiers
        if topic_type == TopicType.ACADEMIC:
            queries.extend(
                [
                    f'"{keyword}" peer-reviewed',
                    f'"{keyword}" research study',
                    f'"{keyword}" systematic review',
                ]
            )
        elif topic_type == TopicType.TECHNICAL:
            queries.extend(
                [
                    f"{keyword} documentation",
                    f"{keyword} implementation guide",
                    f"{keyword} best practices",
                ]
            )
        elif topic_type == TopicType.MEDICAL:
            queries.extend(
                [
                    f'"{keyword}" clinical studies',
                    f'"{keyword}" treatment guidelines',
                    f'"{keyword}" patient outcomes',
                ]
            )
        elif topic_type == TopicType.EMERGING:
            queries.extend(
                [
                    f"{keyword} 2024",
                    f"{keyword} latest developments",
                    f"{keyword} breakthrough",
                ]
            )

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)

        return unique_queries[:5]  # Limit to 5 queries

    def _identify_target_domains(
        self, topic_type: TopicType, available_domains: List[str]
    ) -> List[str]:
        """Identify the best domains to focus on."""
        # Get preferred domains for this topic type
        preferred = self.domain_preferences.get(topic_type, [])

        # Find matches in available domains
        target_domains = []
        for domain in available_domains:
            for pref in preferred:
                if pref in domain:
                    target_domains.append(domain)
                    break

        # Add default recommendations if few matches
        if len(target_domains) < 2:
            target_domains.extend(preferred[:3])

        # Remove duplicates and limit
        return list(dict.fromkeys(target_domains))[:5]

    def _generate_special_instructions(
        self, topic_type: TopicType, research_depth: ResearchDepth
    ) -> str:
        """Generate special instructions based on topic and depth."""
        instructions = []

        # Topic-specific instructions
        if topic_type == TopicType.ACADEMIC:
            instructions.append(
                "Focus on peer-reviewed sources and recent publications"
            )
            instructions.append("Extract methodology sections and statistical data")
        elif topic_type == TopicType.TECHNICAL:
            instructions.append(
                "Prioritize official documentation and implementation examples"
            )
            instructions.append("Look for code samples and API references")
        elif topic_type == TopicType.MEDICAL:
            instructions.append("Verify all health claims with authoritative sources")
            instructions.append("Note study sizes and confidence intervals")
        elif topic_type == TopicType.EMERGING:
            instructions.append("Cross-reference multiple sources for accuracy")
            instructions.append("Identify the most recent developments")

        # Depth-specific instructions
        if research_depth == ResearchDepth.EXHAUSTIVE:
            instructions.append("Leave no stone unturned - explore all related topics")
            instructions.append("Document conflicting viewpoints and controversies")
        elif research_depth == ResearchDepth.SURFACE:
            instructions.append("Focus on key takeaways and summaries")
            instructions.append("Prioritize clarity over comprehensiveness")

        return " | ".join(instructions) if instructions else None
