"""
Utility functions for the Research Agent.

This module provides helper functions for research analysis, including
citation formatting, research synthesis, and data extraction.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from models import AcademicSource, ResearchFindings

# Set up logging
logger = logging.getLogger(__name__)


def format_apa_citation(source: AcademicSource) -> str:
    """
    Format an academic source as an APA citation.

    Args:
        source: AcademicSource to format

    Returns:
        APA-formatted citation string
    """
    # Start with authors if available
    citation_parts = []

    if source.authors:
        # Format authors (Last, F.)
        author_list = []
        for author in source.authors[:3]:  # First 3 authors
            if "," in author:
                # Already in "Last, First" format
                parts = author.strip().split(",")
                if len(parts) >= 2:
                    last_name = parts[0].strip()
                    first_name = parts[1].strip()
                    # Check if first name exists and is not empty
                    if first_name:
                        author_list.append(f"{last_name}, {first_name[0]}.")
                    else:
                        author_list.append(last_name if last_name else author)
                else:
                    author_list.append(author)
            else:
                # In "First Last" format
                parts = author.strip().split()
                if len(parts) >= 2:
                    # Assume last part is surname
                    author_list.append(f"{parts[-1]}, {parts[0][0]}.")
                else:
                    author_list.append(author)

        if len(source.authors) > 3:
            author_list.append("et al.")

        citation_parts.append(", ".join(author_list))
    else:
        # No authors, use organization or website name
        citation_parts.append("Unknown Author")

    # Add year if available
    if source.publication_date:
        # Try to extract year from date string
        year_match = re.search(r"\b(19|20)\d{2}\b", source.publication_date)
        if year_match:
            citation_parts.append(f"({year_match.group()})")
        else:
            citation_parts.append(f"({source.publication_date})")
    else:
        citation_parts.append("(n.d.)")

    # Add title
    citation_parts.append(f"{source.title}.")

    # Add journal if available
    if source.journal_name:
        citation_parts.append(f"*{source.journal_name}*.")

    # Add URL
    citation_parts.append(f"Retrieved from {source.url}")

    return " ".join(citation_parts)


def format_mla_citation(source: AcademicSource) -> str:
    """
    Format an academic source as an MLA citation.

    Args:
        source: AcademicSource to format

    Returns:
        MLA-formatted citation string
    """
    citation_parts = []

    # Authors (Last, First)
    if source.authors:
        if len(source.authors) == 1:
            citation_parts.append(f"{source.authors[0]}.")
        elif len(source.authors) == 2:
            citation_parts.append(f"{source.authors[0]}, and {source.authors[1]}.")
        else:
            citation_parts.append(f"{source.authors[0]}, et al.")

    # Title in quotes
    citation_parts.append(f'"{source.title}."')

    # Journal in italics
    if source.journal_name:
        citation_parts.append(f"*{source.journal_name}*,")

    # Date
    if source.publication_date:
        citation_parts.append(f"{source.publication_date},")

    # URL
    citation_parts.append(f"{source.url}.")

    return " ".join(citation_parts)


def extract_research_themes(findings: ResearchFindings) -> List[str]:
    """
    Extract main themes from research findings.

    Args:
        findings: ResearchFindings to analyze

    Returns:
        List of identified themes
    """
    # Combine all text for analysis
    all_text = findings.research_summary + " ".join(findings.main_findings)

    # Common theme indicators
    theme_patterns = [
        r"\b(trend|pattern|theme|finding|result|outcome|impact|effect|benefit|challenge|risk|opportunity)\b[^.]{0,50}",
        r"\b(shows?|indicates?|suggests?|reveals?|demonstrates?)\s+[^.]{0,50}",
        r"\b(significant|important|critical|key|major|primary|main)\s+\w+",
    ]

    themes = set()

    # Extract themes using patterns
    for pattern in theme_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        for match in matches:
            # Clean and add theme
            theme = match.strip()
            if len(theme) > 10 and len(theme) < 100:
                themes.add(theme.lower())

    # Convert to list and limit
    theme_list = list(themes)[:10]

    # Log themes found
    logger.debug(f"Extracted {len(theme_list)} themes from research")

    return theme_list


def calculate_source_diversity(sources: List[AcademicSource]) -> Dict[str, Any]:
    """
    Calculate diversity metrics for academic sources.

    Args:
        sources: List of academic sources

    Returns:
        Dictionary with diversity metrics
    """
    diversity_metrics: Dict[str, Any] = {
        "total_sources": len(sources),
        "domain_distribution": {},
        "year_distribution": {},
        "credibility_distribution": {
            "high": 0,  # >= 0.8
            "medium": 0,  # 0.6 - 0.8
            "low": 0,  # < 0.6
        },
        "diversity_score": 0.0,
    }

    # Analyze domain distribution
    for source in sources:
        domain = source.domain
        domain_dist = diversity_metrics["domain_distribution"]
        if isinstance(domain_dist, dict):
            domain_dist[domain] = domain_dist.get(domain, 0) + 1

    # Analyze year distribution
    current_year = datetime.now().year
    for source in sources:
        if source.publication_date:
            # Try to extract year
            year_match = re.search(r"\b(19|20)\d{2}\b", source.publication_date)
            if year_match:
                year = int(year_match.group())
                age = current_year - year
                if age <= 2:
                    year_category = "very_recent"
                elif age <= 5:
                    year_category = "recent"
                else:
                    year_category = "older"

                year_dist = diversity_metrics["year_distribution"]
                if isinstance(year_dist, dict):
                    year_dist[year_category] = year_dist.get(year_category, 0) + 1

    # Analyze credibility distribution
    for source in sources:
        cred_dist = diversity_metrics["credibility_distribution"]
        if isinstance(cred_dist, dict):
            if source.credibility_score >= 0.8:
                cred_dist["high"] += 1
            elif source.credibility_score >= 0.6:
                cred_dist["medium"] += 1
            else:
                cred_dist["low"] += 1

    # Calculate overall diversity score (0-1)
    if len(sources) > 0:
        # Domain diversity (more domains = higher score)
        domain_dist = diversity_metrics["domain_distribution"]
        domain_score = (
            len(domain_dist) / min(len(sources), 5)
            if isinstance(domain_dist, dict)
            else 0
        )

        # Year diversity (mix of recent and established = higher score)
        year_dist = diversity_metrics["year_distribution"]
        year_score = len(year_dist) / 3 if isinstance(year_dist, dict) else 0

        # Credibility balance (mostly high = good)
        cred_dist = diversity_metrics["credibility_distribution"]
        cred_score = (
            cred_dist["high"] / len(sources) if isinstance(cred_dist, dict) else 0
        )

        # Combined score
        diversity_metrics["diversity_score"] = (
            domain_score + year_score + cred_score
        ) / 3

    return diversity_metrics


def identify_conflicting_findings(findings: ResearchFindings) -> List[Dict[str, str]]:
    """
    Identify potential conflicts or contradictions in research findings.

    Args:
        findings: ResearchFindings to analyze

    Returns:
        List of identified conflicts with descriptions
    """
    conflicts = []

    # Words that suggest contradiction
    conflict_indicators = [
        "however",
        "contrary",
        "despite",
        "although",
        "whereas",
        "in contrast",
        "on the other hand",
        "conflicting",
        "disputed",
        "controversial",
        "debate",
        "disagreement",
    ]

    # Analyze main findings for conflicts
    all_text = " ".join(findings.main_findings)

    for indicator in conflict_indicators:
        if indicator in all_text.lower():
            # Find sentences with conflict indicators
            sentences = all_text.split(".")
            for sentence in sentences:
                if indicator in sentence.lower() and len(sentence) > 20:
                    conflicts.append(
                        {"indicator": indicator, "description": sentence.strip()}
                    )

    # Check for numerical contradictions
    numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", all_text)
    if (
        len(set(numbers)) > len(numbers) * 0.7
    ):  # Many different numbers might indicate conflicts
        logger.debug("Detected potential numerical variations in findings")

    return conflicts[:5]  # Return top 5 conflicts


def generate_research_questions(findings: ResearchFindings) -> List[str]:
    """
    Generate follow-up research questions based on findings and gaps.

    Args:
        findings: ResearchFindings to analyze

    Returns:
        List of research questions
    """
    questions = []

    # Based on research gaps
    for gap in findings.research_gaps:
        # Transform gap into question
        if "further research" in gap.lower():
            question = gap.replace(
                "further research is needed", "What research is needed"
            )
            question = question.replace(
                "further research needed", "What research is needed"
            )
            questions.append(f"{question}?")
        elif "unclear" in gap.lower():
            questions.append(
                f"What factors contribute to the unclear aspects of {findings.keyword}?"
            )
        elif "limited" in gap.lower():
            questions.append(
                f"How can we address the limited data on {findings.keyword}?"
            )

    # Based on findings
    if findings.main_findings:
        questions.append(
            f"What are the long-term implications of {findings.main_findings[0]}?"
        )
        questions.append(
            f"How can practitioners apply {findings.keyword} research in real-world settings?"
        )

    # General questions
    questions.extend(
        [
            f"What are the ethical considerations in {findings.keyword} research?",
            f"How does {findings.keyword} vary across different populations or contexts?",
            f"What emerging technologies might impact {findings.keyword} in the future?",
        ]
    )

    # Remove duplicates and limit
    unique_questions = list(dict.fromkeys(questions))
    return unique_questions[:8]


def assess_research_quality(findings: ResearchFindings) -> Dict[str, Any]:
    """
    Assess the overall quality of research findings.

    Args:
        findings: ResearchFindings to assess

    Returns:
        Dictionary with quality metrics and recommendations
    """
    quality_assessment: Dict[str, Any] = {
        "overall_score": 0.0,
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "metrics": {
            "source_quality": 0.0,
            "source_quantity": 0.0,
            "content_depth": 0.0,
            "recency": 0.0,
            "diversity": 0.0,
        },
    }

    # Assess source quality
    if findings.academic_sources:
        avg_credibility = sum(
            s.credibility_score for s in findings.academic_sources
        ) / len(findings.academic_sources)
        metrics = quality_assessment["metrics"]
        if isinstance(metrics, dict):
            metrics["source_quality"] = avg_credibility

        if avg_credibility >= 0.8:
            strengths = quality_assessment["strengths"]
            if isinstance(strengths, list):
                strengths.append("High-quality academic sources")
        elif avg_credibility < 0.6:
            weaknesses = quality_assessment["weaknesses"]
            recommendations = quality_assessment["recommendations"]
            if isinstance(weaknesses, list):
                weaknesses.append("Low average source credibility")
            if isinstance(recommendations, list):
                recommendations.append("Seek more peer-reviewed sources")

    # Assess source quantity
    source_count = len(findings.academic_sources)
    metrics = quality_assessment["metrics"]
    strengths = quality_assessment["strengths"]
    weaknesses = quality_assessment["weaknesses"]
    recommendations = quality_assessment["recommendations"]

    if isinstance(metrics, dict):
        if source_count >= 5:
            metrics["source_quantity"] = 1.0
            if isinstance(strengths, list):
                strengths.append(f"Comprehensive coverage with {source_count} sources")
        elif source_count >= 3:
            metrics["source_quantity"] = 0.7
        else:
            metrics["source_quantity"] = 0.4
            if isinstance(weaknesses, list):
                weaknesses.append("Limited number of sources")
            if isinstance(recommendations, list):
                recommendations.append("Expand search to find more sources")

    # Assess content depth
    metrics = quality_assessment["metrics"]
    strengths = quality_assessment["strengths"]
    recommendations = quality_assessment["recommendations"]

    if isinstance(metrics, dict):
        if findings.key_statistics and len(findings.key_statistics) >= 3:
            metrics["content_depth"] = 0.8
            if isinstance(strengths, list):
                strengths.append("Rich statistical evidence")
        else:
            metrics["content_depth"] = 0.5
            if isinstance(recommendations, list):
                recommendations.append("Extract more quantitative data")

    # Assess recency
    recent_sources = 0
    for source in findings.academic_sources:
        if source.publication_date and "202" in source.publication_date:
            recent_sources += 1

    recency_ratio = (
        recent_sources / len(findings.academic_sources)
        if findings.academic_sources
        else 0
    )
    metrics = quality_assessment["metrics"]
    strengths = quality_assessment["strengths"]
    weaknesses = quality_assessment["weaknesses"]
    recommendations = quality_assessment["recommendations"]

    if isinstance(metrics, dict):
        metrics["recency"] = recency_ratio

    if recency_ratio >= 0.7:
        if isinstance(strengths, list):
            strengths.append("Mostly recent sources")
    elif recency_ratio < 0.3:
        if isinstance(weaknesses, list):
            weaknesses.append("Many outdated sources")
        if isinstance(recommendations, list):
            recommendations.append("Prioritize more recent research")

    # Get diversity score
    diversity = calculate_source_diversity(findings.academic_sources)
    metrics = quality_assessment["metrics"]
    if isinstance(metrics, dict):
        metrics["diversity"] = diversity["diversity_score"]

    # Calculate overall score
    if isinstance(metrics, dict):
        quality_assessment["overall_score"] = sum(metrics.values()) / len(metrics)

    # Overall recommendations
    overall_score = quality_assessment["overall_score"]
    recommendations = quality_assessment["recommendations"]
    strengths = quality_assessment["strengths"]

    if overall_score < 0.6:
        if isinstance(recommendations, list):
            recommendations.insert(0, "Consider conducting additional research")
    elif overall_score > 0.8:
        if isinstance(strengths, list):
            strengths.insert(0, "Excellent research quality overall")

    return quality_assessment


# Export utilities
__all__ = [
    "format_apa_citation",
    "format_mla_citation",
    "extract_research_themes",
    "calculate_source_diversity",
    "identify_conflicting_findings",
    "generate_research_questions",
    "assess_research_quality",
]
