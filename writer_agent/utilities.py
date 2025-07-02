"""
Utility functions for the Writer Agent.

This module contains helper functions for content analysis,
SEO optimization, and readability scoring.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Set, Tuple


def calculate_readability_score(text: str) -> Dict[str, Any]:
    """
    Calculate readability metrics for the given text.

    Uses simplified Flesch Reading Ease formula to determine
    how easy the text is to read.

    Args:
        text: The text to analyze

    Returns:
        Dictionary with readability metrics
    """
    # Remove HTML tags if present
    clean_text = re.sub(r"<[^>]+>", "", text)

    # Count sentences (rough approximation)
    sentences = re.split(r"[.!?]+", clean_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)

    # Count words
    words = clean_text.split()
    word_count = len(words)

    # Count syllables (simplified - count vowel groups)
    syllable_count = 0
    for word in words:
        word_lower = word.lower()
        # Remove non-alphabetic characters
        word_clean = re.sub(r"[^a-z]", "", word_lower)
        # Count vowel groups as syllables (simplified)
        vowel_groups = re.findall(r"[aeiou]+", word_clean)
        syllables = len(vowel_groups)
        # Ensure at least 1 syllable per word
        syllable_count += max(1, syllables)

    # Calculate averages
    if sentence_count == 0 or word_count == 0:
        return {
            "score": 0,
            "level": "N/A",
            "sentence_count": sentence_count,
            "word_count": word_count,
            "avg_words_per_sentence": 0,
            "avg_syllables_per_word": 0,
        }

    avg_words_per_sentence = word_count / sentence_count
    avg_syllables_per_word = syllable_count / word_count

    # Flesch Reading Ease Score
    # Score = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
    score = max(0, min(100, score))  # Clamp between 0-100

    # Determine reading level
    if score >= 90:
        level = "Very Easy (5th grade)"
    elif score >= 80:
        level = "Easy (6th grade)"
    elif score >= 70:
        level = "Fairly Easy (7th grade)"
    elif score >= 60:
        level = "Standard (8th-9th grade)"
    elif score >= 50:
        level = "Fairly Difficult (10th-12th grade)"
    elif score >= 30:
        level = "Difficult (College)"
    else:
        level = "Very Difficult (Graduate)"

    return {
        "score": round(score, 1),
        "level": level,
        "sentence_count": sentence_count,
        "word_count": word_count,
        "avg_words_per_sentence": round(avg_words_per_sentence, 1),
        "avg_syllables_per_word": round(avg_syllables_per_word, 1),
    }


def extract_headers_structure(content: str) -> List[Dict[str, Any]]:
    """
    Extract the header structure from HTML or markdown content.

    Args:
        content: HTML or markdown content

    Returns:
        List of headers with their level and text
    """
    headers = []

    # Extract HTML headers (case-insensitive, multiline)
    html_headers = re.findall(
        r"<h([1-6])>(.*?)</h\1>", content, re.IGNORECASE | re.DOTALL
    )
    for level, text in html_headers:
        # Clean the header text
        clean_text = re.sub(r"<[^>]+>", "", text).strip()
        headers.append({"level": int(level), "text": clean_text, "type": "html"})

    # Extract markdown headers
    # First try to find headers at start of lines
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        # Match markdown headers
        md_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if md_match:
            level = len(md_match.group(1))
            text = md_match.group(2).strip()
            headers.append({"level": level, "text": text, "type": "markdown"})

    return headers


def validate_header_hierarchy(headers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that headers follow proper hierarchy.

    Args:
        headers: List of headers from extract_headers_structure

    Returns:
        Validation results
    """
    issues = []

    if not headers:
        return {"valid": True, "issues": ["No headers found"], "h1_count": 0}

    # Check for H1
    h1_count = sum(1 for h in headers if h["level"] == 1)
    if h1_count == 0:
        issues.append("No H1 header found")
    elif h1_count > 1:
        issues.append(f"Multiple H1 headers found ({h1_count})")

    # Check hierarchy
    for i in range(1, len(headers)):
        current_level = headers[i]["level"]
        prev_level = headers[i - 1]["level"]

        # Headers should not skip levels (e.g., H2 -> H4)
        if current_level > prev_level + 1:
            issues.append(
                f"Header hierarchy skip: H{prev_level} → H{current_level} "
                f"('{headers[i-1]['text'][:30]}...' → '{headers[i]['text'][:30]}...')"
            )

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "h1_count": h1_count,
        "total_headers": len(headers),
    }


def find_transition_words(text: str) -> Dict[str, Any]:
    """
    Find and count transition words in the text.

    Transition words improve content flow and readability.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with transition word analysis
    """
    # Common transition words and phrases
    transition_words: List[str] = [
        # Addition
        "furthermore",
        "moreover",
        "additionally",
        "also",
        "besides",
        "in addition",
        "as well as",
        "not only",
        "but also",
        # Contrast
        "however",
        "nevertheless",
        "nonetheless",
        "on the other hand",
        "in contrast",
        "whereas",
        "while",
        "although",
        "despite",
        # Cause/Effect
        "therefore",
        "consequently",
        "as a result",
        "thus",
        "hence",
        "accordingly",
        "for this reason",
        "because",
        "since",
        # Example
        "for example",
        "for instance",
        "such as",
        "specifically",
        "to illustrate",
        "namely",
        "in particular",
        # Sequence
        "first",
        "second",
        "third",
        "finally",
        "next",
        "then",
        "subsequently",
        "meanwhile",
        "afterward",
        # Conclusion
        "in conclusion",
        "to summarize",
        "in summary",
        "overall",
        "ultimately",
        "in short",
        "to conclude",
    ]

    # Convert text to lowercase for matching
    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)

    # Count transition words
    found_transitions: List[Dict[str, Any]] = []
    for transition in transition_words:
        if transition in text_lower:
            count = text_lower.count(transition)
            found_transitions.append({"word": transition, "count": count})

    # Calculate percentage
    total_transition_count = sum(t["count"] for t in found_transitions)
    transition_percentage = (
        (total_transition_count / word_count * 100) if word_count > 0 else 0
    )

    return {
        "found": found_transitions,
        "total_count": total_transition_count,
        "percentage": round(transition_percentage, 2),
        "recommendation": (
            "Good (10-20%)"
            if 10 <= transition_percentage <= 20
            else "Consider adding more transitions"
        ),
    }


def analyze_keyword_placement(content: str, keyword: str) -> Dict[str, Any]:
    """
    Analyze where the keyword appears in the content.

    Args:
        content: The content to analyze
        keyword: The target keyword

    Returns:
        Dictionary with keyword placement analysis
    """
    keyword_lower = keyword.lower()
    content_lower = content.lower()

    # Split content into sections
    # Try to identify introduction (first paragraph)
    paragraphs = re.split(r"\n\s*\n", content)

    placement: Dict[str, Any] = {
        "in_title": False,
        "in_first_paragraph": False,
        "in_headers": [],
        "total_occurrences": content_lower.count(keyword_lower),
        "positions": [],
    }

    # Check title (H1)
    h1_match = re.search(r"<h1>(.*?)</h1>", content, re.IGNORECASE)
    if h1_match and keyword_lower in h1_match.group(1).lower():
        placement["in_title"] = True

    # Check first paragraph
    if paragraphs and keyword_lower in paragraphs[0].lower():
        placement["in_first_paragraph"] = True

    # Check headers
    headers = extract_headers_structure(content)
    for header in headers:
        if keyword_lower in header["text"].lower():
            in_headers_list = placement["in_headers"]
            if isinstance(in_headers_list, list):
                in_headers_list.append(
                    {"level": header["level"], "text": header["text"]}
                )

    # Find all positions (character indices)
    start = 0
    while True:
        pos = content_lower.find(keyword_lower, start)
        if pos == -1:
            break
        positions_list = placement["positions"]
        if isinstance(positions_list, list):
            positions_list.append(pos)
        start = pos + 1

    # SEO recommendations
    recommendations: List[str] = []
    if not placement["in_title"]:
        recommendations.append("Add keyword to title (H1)")
    if not placement["in_first_paragraph"]:
        recommendations.append("Add keyword to first paragraph")
    in_headers = placement["in_headers"]
    if isinstance(in_headers, list) and len(in_headers) < 2:
        recommendations.append("Consider adding keyword to more subheadings")

    placement["recommendations"] = recommendations

    return placement




def calculate_content_score(
    content: str, keyword: str, word_count: int, sources_count: int
) -> Dict[str, Any]:
    """
    Calculate an overall content quality score.

    Args:
        content: The article content
        keyword: Target keyword
        word_count: Total word count
        sources_count: Number of sources cited

    Returns:
        Dictionary with scoring breakdown
    """
    scores = {}

    # Word count score (max 25 points)
    if word_count >= 2000:
        scores["word_count"] = 25
    elif word_count >= 1500:
        scores["word_count"] = 20
    elif word_count >= 1000:
        scores["word_count"] = 15
    else:
        scores["word_count"] = 10

    # Readability score (max 20 points)
    readability = calculate_readability_score(content)
    if 60 <= readability["score"] <= 70:  # Optimal range
        scores["readability"] = 20
    elif 50 <= readability["score"] <= 79:
        scores["readability"] = 15
    else:
        scores["readability"] = 10

    # Keyword optimization (max 20 points)
    keyword_analysis = analyze_keyword_placement(content, keyword)
    keyword_score = 0
    if keyword_analysis["in_title"]:
        keyword_score += 8
    if keyword_analysis["in_first_paragraph"]:
        keyword_score += 7
    if len(keyword_analysis["in_headers"]) >= 2:
        keyword_score += 5
    scores["keyword_optimization"] = keyword_score

    # Structure score (max 15 points)
    headers = extract_headers_structure(content)
    if len(headers) >= 5:
        scores["structure"] = 15
    elif len(headers) >= 3:
        scores["structure"] = 10
    else:
        scores["structure"] = 5

    # Sources score (max 10 points)
    if sources_count >= 5:
        scores["sources"] = 10
    elif sources_count >= 3:
        scores["sources"] = 7
    else:
        scores["sources"] = 5

    # Transition words score (max 10 points)
    transitions = find_transition_words(content)
    if 10 <= transitions["percentage"] <= 20:
        scores["transitions"] = 10
    elif 5 <= transitions["percentage"] <= 25:
        scores["transitions"] = 7
    else:
        scores["transitions"] = 5

    # Calculate total
    total_score = sum(scores.values())

    # Determine grade
    if total_score >= 90:
        grade = "A+"
    elif total_score >= 85:
        grade = "A"
    elif total_score >= 80:
        grade = "B+"
    elif total_score >= 75:
        grade = "B"
    elif total_score >= 70:
        grade = "C+"
    elif total_score >= 65:
        grade = "C"
    else:
        grade = "D"

    return {
        "total_score": total_score,
        "grade": grade,
        "breakdown": scores,
        "max_possible": 100,
        "recommendations": _generate_score_recommendations(scores),
    }


def _generate_score_recommendations(scores: Dict[str, int]) -> List[str]:
    """
    Generate recommendations based on score breakdown.

    Args:
        scores: Score breakdown dictionary

    Returns:
        List of recommendations
    """
    recommendations: List[str] = []

    # Check each category and suggest improvements
    if scores.get("word_count", 0) < 20:
        recommendations.append("Consider expanding content to 1500+ words")

    if scores.get("readability", 0) < 15:
        recommendations.append("Simplify sentences for better readability")

    if scores.get("keyword_optimization", 0) < 15:
        recommendations.append("Improve keyword placement in title and headers")

    if scores.get("structure", 0) < 10:
        recommendations.append("Add more subheadings for better structure")

    if scores.get("sources", 0) < 7:
        recommendations.append("Include more credible sources")

    if scores.get("transitions", 0) < 7:
        recommendations.append("Add more transition words for better flow")

    return recommendations
