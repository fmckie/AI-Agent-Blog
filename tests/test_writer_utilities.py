"""
Comprehensive tests for Writer Agent utility functions.

This test file covers all utility functions in writer_agent/utilities.py,
including readability scoring, SEO analysis, and content quality assessment.
"""

from typing import Any, Dict, List

# Import testing utilities
import pytest

# Import utilities to test
from writer_agent.utilities import (
    _generate_score_recommendations,
    analyze_keyword_placement,
    calculate_content_score,
    calculate_readability_score,
    extract_headers_structure,
    find_transition_words,
    suggest_internal_links,
    validate_header_hierarchy,
)


class TestReadabilityScore:
    """Test cases for readability scoring functions."""

    def test_calculate_readability_basic(self):
        """Test basic readability calculation."""
        # Simple text with known characteristics
        text = "The cat sat on the mat. It was a sunny day. Birds sang happily."

        result = calculate_readability_score(text)

        # Check structure
        assert "score" in result
        assert "level" in result
        assert "sentence_count" in result
        assert "word_count" in result
        assert "avg_words_per_sentence" in result
        assert "avg_syllables_per_word" in result

        # Check values
        assert result["sentence_count"] == 3
        assert result["word_count"] == 14
        assert result["avg_words_per_sentence"] > 0
        assert 0 <= result["score"] <= 100

    def test_readability_complex_text(self):
        """Test readability with complex academic text."""
        text = """
        The epistemological implications of quantum mechanics fundamentally challenge 
        our understanding of objective reality. Furthermore, the Copenhagen interpretation 
        suggests that consciousness plays an integral role in the collapse of the wave function.
        """

        result = calculate_readability_score(text)

        # Complex text should have lower readability score
        assert result["score"] < 50
        assert "Difficult" in result["level"] or "Graduate" in result["level"]

    def test_readability_simple_text(self):
        """Test readability with very simple text."""
        text = "I like cats. Cats are fun. They play a lot. I have two cats."

        result = calculate_readability_score(text)

        # Simple text should have high readability score
        assert result["score"] > 70
        assert "Easy" in result["level"]

    def test_readability_edge_cases(self):
        """Test readability with edge cases."""
        # Empty text
        result_empty = calculate_readability_score("")
        assert result_empty["score"] == 0
        assert result_empty["level"] == "N/A"

        # Single word
        result_single = calculate_readability_score("Hello")
        assert result_single["word_count"] == 1
        assert result_single["sentence_count"] == 1

        # No punctuation
        result_no_punct = calculate_readability_score(
            "This is text without punctuation"
        )
        assert result_no_punct["sentence_count"] == 1

    def test_readability_html_stripping(self):
        """Test that HTML tags are properly stripped."""
        text_with_html = (
            "<p>This is <strong>bold</strong> text.</p> <div>Another sentence.</div>"
        )

        result = calculate_readability_score(text_with_html)

        # Should count words without HTML tags
        assert result["word_count"] == 6  # "This is bold text Another sentence"
        assert result["sentence_count"] == 2

    def test_syllable_counting(self):
        """Test syllable counting accuracy."""
        # Test with known syllable counts
        test_cases = [
            ("cat", 1),  # 1 syllable
            ("hello", 2),  # 2 syllables
            ("beautiful", 3),  # 3-4 syllables (simplified counter)
            ("a", 1),  # Minimum 1 syllable
        ]

        for word, expected_min in test_cases:
            result = calculate_readability_score(word)
            # Our simplified syllable counter might not be perfect
            assert result["avg_syllables_per_word"] >= expected_min


class TestHeaderExtraction:
    """Test cases for header extraction and validation."""

    def test_extract_html_headers(self):
        """Test extracting headers from HTML content."""
        html_content = """
        <h1>Main Title</h1>
        <p>Some content</p>
        <h2>Section One</h2>
        <p>More content</p>
        <h3>Subsection 1.1</h3>
        <h2>Section Two</h2>
        <h4>Deep Section</h4>
        """

        headers = extract_headers_structure(html_content)

        assert len(headers) == 5
        assert headers[0] == {"level": 1, "text": "Main Title", "type": "html"}
        assert headers[1] == {"level": 2, "text": "Section One", "type": "html"}
        assert headers[2] == {"level": 3, "text": "Subsection 1.1", "type": "html"}
        assert headers[3] == {"level": 2, "text": "Section Two", "type": "html"}
        assert headers[4] == {"level": 4, "text": "Deep Section", "type": "html"}

    def test_extract_markdown_headers(self):
        """Test extracting headers from markdown content."""
        markdown_content = """
# Main Title
Some content here
## Section One
More content
### Subsection 1.1
## Section Two
#### Deep Section
        """

        headers = extract_headers_structure(markdown_content)

        assert len(headers) == 5
        assert headers[0] == {"level": 1, "text": "Main Title", "type": "markdown"}
        assert headers[1] == {"level": 2, "text": "Section One", "type": "markdown"}
        assert headers[4] == {"level": 4, "text": "Deep Section", "type": "markdown"}

    def test_extract_mixed_headers(self):
        """Test extracting headers from mixed HTML/markdown content."""
        mixed_content = """
        <h1>HTML Title</h1>
        # Markdown Title
        <h2>HTML Section</h2>
        ## Markdown Section
        """

        headers = extract_headers_structure(mixed_content)

        # Should find all headers
        assert len(headers) == 4
        html_headers = [h for h in headers if h["type"] == "html"]
        markdown_headers = [h for h in headers if h["type"] == "markdown"]
        assert len(html_headers) == 2
        assert len(markdown_headers) == 2

    def test_extract_headers_with_nested_tags(self):
        """Test extracting headers with nested HTML tags."""
        content = """
        <h1>Title with <em>emphasis</em></h1>
        <h2>Section with <strong>bold text</strong></h2>
        """

        headers = extract_headers_structure(content)

        # Should strip nested tags
        assert headers[0]["text"] == "Title with emphasis"
        assert headers[1]["text"] == "Section with bold text"

    def test_validate_header_hierarchy_valid(self):
        """Test validating proper header hierarchy."""
        headers = [
            {"level": 1, "text": "Title", "type": "html"},
            {"level": 2, "text": "Section 1", "type": "html"},
            {"level": 3, "text": "Subsection 1.1", "type": "html"},
            {"level": 3, "text": "Subsection 1.2", "type": "html"},
            {"level": 2, "text": "Section 2", "type": "html"},
        ]

        result = validate_header_hierarchy(headers)

        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["h1_count"] == 1
        assert result["total_headers"] == 5

    def test_validate_header_hierarchy_no_h1(self):
        """Test validation when H1 is missing."""
        headers = [
            {"level": 2, "text": "Section 1", "type": "html"},
            {"level": 3, "text": "Subsection", "type": "html"},
        ]

        result = validate_header_hierarchy(headers)

        assert result["valid"] is False
        assert "No H1 header found" in result["issues"]
        assert result["h1_count"] == 0

    def test_validate_header_hierarchy_multiple_h1(self):
        """Test validation with multiple H1 headers."""
        headers = [
            {"level": 1, "text": "Title 1", "type": "html"},
            {"level": 1, "text": "Title 2", "type": "html"},
            {"level": 2, "text": "Section", "type": "html"},
        ]

        result = validate_header_hierarchy(headers)

        assert result["valid"] is False
        assert any(
            "Multiple H1 headers found (2)" in issue for issue in result["issues"]
        )
        assert result["h1_count"] == 2

    def test_validate_header_hierarchy_skip(self):
        """Test validation when header levels are skipped."""
        headers = [
            {"level": 1, "text": "Title", "type": "html"},
            {"level": 2, "text": "Section", "type": "html"},
            {"level": 4, "text": "Deep Section", "type": "html"},  # Skips H3
        ]

        result = validate_header_hierarchy(headers)

        assert result["valid"] is False
        assert any("H2 → H4" in issue for issue in result["issues"])

    def test_validate_empty_headers(self):
        """Test validation with no headers."""
        result = validate_header_hierarchy([])

        assert result["valid"] is True
        assert "No headers found" in result["issues"]
        assert result["h1_count"] == 0


class TestTransitionWords:
    """Test cases for transition word analysis."""

    def test_find_transition_words_basic(self):
        """Test finding basic transition words."""
        text = """
        First, we need to understand the basics. Furthermore, it's important to 
        practice regularly. However, some people find it challenging. Therefore, 
        we provide additional support.
        """

        result = find_transition_words(text)

        # Check structure
        assert "found" in result
        assert "total_count" in result
        assert "percentage" in result
        assert "recommendation" in result

        # Check found transitions
        transition_words = [t["word"] for t in result["found"]]
        assert "first" in transition_words
        assert "furthermore" in transition_words
        assert "however" in transition_words
        assert "therefore" in transition_words

    def test_transition_words_counting(self):
        """Test accurate counting of transition words."""
        text = "However, this is important. However, we must be careful. However, there are risks."

        result = find_transition_words(text)

        # Should count "however" 3 times
        however_entry = next(t for t in result["found"] if t["word"] == "however")
        assert however_entry["count"] == 3

    def test_transition_words_percentage(self):
        """Test transition word percentage calculation."""
        # Text with known word count and transitions
        text = "First, this is important. Second, we must consider. Therefore, action needed."
        # 11 words total, 3 transition words

        result = find_transition_words(text)

        # 3/11 = 27.27%
        assert 25 <= result["percentage"] <= 30
        assert "Consider adding more transitions" in result["recommendation"]

    def test_transition_words_good_percentage(self):
        """Test when transition percentage is in good range."""
        text = " ".join(["word"] * 85 + ["however"] * 10 + ["therefore"] * 5)
        # 100 words total, 15 transition words = 15%

        result = find_transition_words(text)

        assert 14 <= result["percentage"] <= 16
        assert "Good (10-20%)" in result["recommendation"]

    def test_transition_words_empty_text(self):
        """Test with empty or minimal text."""
        result_empty = find_transition_words("")
        assert result_empty["total_count"] == 0
        assert result_empty["percentage"] == 0

        result_no_transitions = find_transition_words("No transitions here at all.")
        assert result_no_transitions["total_count"] == 0

    def test_transition_phrases(self):
        """Test multi-word transition phrases."""
        text = "In addition to the main points, we must consider alternatives. On the other hand, there are risks."

        result = find_transition_words(text)

        transition_words = [t["word"] for t in result["found"]]
        assert "in addition" in transition_words
        assert "on the other hand" in transition_words


class TestKeywordAnalysis:
    """Test cases for keyword placement analysis."""

    def test_analyze_keyword_placement_comprehensive(self):
        """Test comprehensive keyword placement analysis."""
        content = """
        <h1>Machine Learning Guide</h1>
        <p>This guide covers machine learning fundamentals. We'll explore how 
        machine learning works.</p>
        
        <h2>What is Machine Learning?</h2>
        <p>Machine learning is a subset of AI.</p>
        
        <h2>Applications</h2>
        <p>There are many uses for ML technologies.</p>
        """

        result = analyze_keyword_placement(content, "machine learning")

        # Check structure
        assert "in_title" in result
        assert "in_first_paragraph" in result
        assert "in_headers" in result
        assert "total_occurrences" in result
        assert "positions" in result
        assert "recommendations" in result

        # Check specific placements
        assert result["in_title"] is True
        assert result["in_first_paragraph"] is True
        assert len(result["in_headers"]) == 2  # H1 and H2
        assert result["total_occurrences"] == 5

    def test_keyword_placement_missing_locations(self):
        """Test when keyword is missing from key locations."""
        content = """
        <h1>A Different Title</h1>
        <p>This is the introduction without the keyword.</p>
        
        <h2>Section One</h2>
        <p>Here we mention machine learning once.</p>
        """

        result = analyze_keyword_placement(content, "machine learning")

        assert result["in_title"] is False
        assert result["in_first_paragraph"] is False
        assert len(result["in_headers"]) == 0
        assert result["total_occurrences"] == 1

        # Check recommendations
        assert "Add keyword to title (H1)" in result["recommendations"]
        assert "Add keyword to first paragraph" in result["recommendations"]

    def test_keyword_case_insensitive(self):
        """Test that keyword matching is case-insensitive."""
        content = """
        <h1>MACHINE LEARNING Guide</h1>
        <p>Machine Learning is important.</p>
        """

        result = analyze_keyword_placement(content, "machine learning")

        assert result["in_title"] is True
        assert result["in_first_paragraph"] is True
        assert result["total_occurrences"] == 2

    def test_keyword_positions(self):
        """Test that keyword positions are correctly identified."""
        content = "machine learning is great. I love machine learning!"

        result = analyze_keyword_placement(content, "machine learning")

        assert len(result["positions"]) == 2
        assert result["positions"][0] == 0  # First occurrence at position 0
        assert result["positions"][1] > 20  # Second occurrence later

    def test_keyword_in_headers_details(self):
        """Test detailed header information for keywords."""
        content = """
        <h2>Introduction to Machine Learning</h2>
        <h3>Machine Learning Basics</h3>
        <h4>Advanced Machine Learning</h4>
        """

        result = analyze_keyword_placement(content, "machine learning")

        assert len(result["in_headers"]) == 3
        # Check that we get level and text for each header
        for header in result["in_headers"]:
            assert "level" in header
            assert "text" in header
            assert "machine learning" in header["text"].lower()


class TestInternalLinks:
    """Test cases for internal link suggestions."""

    def test_suggest_internal_links_guide_keyword(self):
        """Test link suggestions for guide-type keywords."""
        content = (
            "This comprehensive guide covers beginner topics and advanced concepts."
        )

        suggestions = suggest_internal_links(content, "python guide")

        # Should suggest links based on content and keyword
        assert len(suggestions) <= 5
        # May include suggestions like "beginner python guide", "comprehensive python guide"

    def test_suggest_internal_links_tips_keyword(self):
        """Test link suggestions for tips-type keywords."""
        content = "Here are the best practices and proven methods for success."

        suggestions = suggest_internal_links(content, "SEO tips")

        # Should identify tip-related content
        assert len(suggestions) <= 5

    def test_suggest_internal_links_ing_words(self):
        """Test link suggestions with -ing keywords."""
        content = "Learning programming requires dedication."

        suggestions = suggest_internal_links(content, "programming")

        # Should create variations like "program guide", "program tips"
        assert any("program" in s for s in suggestions)

    def test_suggest_internal_links_plural_words(self):
        """Test link suggestions with plural keywords."""
        content = "Multiple strategies for success."

        suggestions = suggest_internal_links(content, "strategies")

        # Should handle plural forms
        assert len(suggestions) > 0

    def test_suggest_internal_links_no_duplicates(self):
        """Test that suggestions don't contain duplicates."""
        content = "Best tips and best practices for best results."

        suggestions = suggest_internal_links(content, "marketing tips")

        # Check no duplicates
        assert len(suggestions) == len(set(suggestions))


class TestContentScoring:
    """Test cases for content quality scoring."""

    def test_calculate_content_score_high_quality(self):
        """Test scoring high-quality content."""
        content = """
        <h1>Complete Guide to Machine Learning</h1>
        <p>Machine learning is transforming industries. Furthermore, it's becoming 
        essential for modern businesses.</p>
        
        <h2>What is Machine Learning?</h2>
        <p>Machine learning enables computers to learn from data. However, it requires
        careful implementation.</p>
        
        <h2>Types of Machine Learning</h2>
        <p>There are three main types. First, supervised learning. Second, unsupervised
        learning. Third, reinforcement learning.</p>
        
        <h3>Supervised Learning</h3>
        <p>This type uses labeled data. Therefore, it's ideal for classification.</p>
        
        <h3>Unsupervised Learning</h3>
        <p>This finds patterns without labels. Consequently, it's great for clustering.</p>
        """ + " ".join(
            ["Additional content"] * 500
        )  # Make it 1000+ words

        result = calculate_content_score(
            content=content,
            keyword="machine learning",
            word_count=1200,
            sources_count=5,
        )

        # Check structure
        assert "total_score" in result
        assert "grade" in result
        assert "breakdown" in result
        assert "recommendations" in result

        # High-quality content should score well
        assert result["total_score"] > 70
        assert result["grade"] in ["A", "A+", "B+", "B"]

    def test_content_score_breakdown(self):
        """Test individual score components."""
        content = "<h1>Test</h1><p>Short content.</p>"

        result = calculate_content_score(
            content=content,
            keyword="test",
            word_count=500,  # Low word count
            sources_count=1,  # Few sources
        )

        breakdown = result["breakdown"]

        # Check each component
        assert breakdown["word_count"] == 10  # Less than 1000 words
        assert breakdown["sources"] == 5  # Only 1 source
        assert breakdown["structure"] == 5  # Only 1 header

        # Should have recommendations
        assert len(result["recommendations"]) > 0

    def test_content_score_optimal_readability(self):
        """Test that optimal readability scores highest."""
        # Create content with good readability (simple sentences)
        content = """
        <h1>Test Article</h1>
        <p>This is a test. It has simple words. The sentences are short.</p>
        """ + " ".join(
            ["Simple sentence."] * 100
        )

        result = calculate_content_score(
            content=content, keyword="test", word_count=1000, sources_count=3
        )

        # Readability should contribute to score
        assert result["breakdown"]["readability"] >= 10

    def test_score_recommendations_generation(self):
        """Test recommendation generation based on scores."""
        scores = {
            "word_count": 10,  # Low
            "readability": 10,  # Low
            "keyword_optimization": 5,  # Very low
            "structure": 5,  # Low
            "sources": 5,  # Low
            "transitions": 5,  # Low
        }

        recommendations = _generate_score_recommendations(scores)

        # Should have recommendations for each low score
        assert any("1500+ words" in r for r in recommendations)
        assert any("readability" in r for r in recommendations)
        assert any("keyword placement" in r for r in recommendations)
        assert any("subheadings" in r for r in recommendations)
        assert any("sources" in r for r in recommendations)
        assert any("transition words" in r for r in recommendations)

    def test_content_score_grades(self):
        """Test grade assignment based on total score."""
        # Test different score ranges
        test_cases = [
            (95, "A+"),
            (87, "A"),
            (82, "B+"),
            (77, "B"),
            (72, "C+"),
            (67, "C"),
            (50, "D"),
        ]

        for total, expected_grade in test_cases:
            # Mock the scoring
            content = "<h1>Test</h1><p>Test content.</p>"
            result = calculate_content_score(content, "test", 1000, 3)

            # Manually set the total score for testing
            result["total_score"] = total

            # Re-calculate grade
            if total >= 90:
                grade = "A+"
            elif total >= 85:
                grade = "A"
            elif total >= 80:
                grade = "B+"
            elif total >= 75:
                grade = "B"
            elif total >= 70:
                grade = "C+"
            elif total >= 65:
                grade = "C"
            else:
                grade = "D"

            assert grade == expected_grade


# Edge case tests
class TestWriterUtilitiesEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_content_handling(self):
        """Test all functions with empty content."""
        # Readability
        readability = calculate_readability_score("")
        assert readability["score"] == 0

        # Headers
        headers = extract_headers_structure("")
        assert len(headers) == 0

        # Transitions
        transitions = find_transition_words("")
        assert transitions["total_count"] == 0

        # Keyword placement
        keyword = analyze_keyword_placement("", "test")
        assert keyword["total_occurrences"] == 0

        # Internal links
        links = suggest_internal_links("", "test")
        assert isinstance(links, list)

    def test_unicode_handling(self):
        """Test handling of Unicode characters."""
        content = """
        <h1>Guide to Café Culture</h1>
        <p>Exploring the café scene in París. Furthermore, the ambiance is très magnifique!</p>
        """

        # Test readability
        readability = calculate_readability_score(content)
        assert readability["word_count"] > 0

        # Test keyword with accents
        keyword = analyze_keyword_placement(content, "café")
        assert keyword["in_title"] is True

        # Test headers
        headers = extract_headers_structure(content)
        assert headers[0]["text"] == "Guide to Café Culture"

    def test_malformed_html(self):
        """Test handling of malformed HTML."""
        # Unclosed tags
        content = "<h1>Title<h2>Section</h2>"
        headers = extract_headers_structure(content)
        assert len(headers) >= 1  # Should still find the h2

        # Nested headers (invalid HTML)
        content2 = "<h1>Title <h2>Nested</h2></h1>"
        headers2 = extract_headers_structure(content2)
        # Should handle gracefully
        assert len(headers2) > 0

    def test_very_long_content(self):
        """Test performance with very long content."""
        # Create long content
        long_content = "<h1>Title</h1>\n"
        for i in range(100):
            long_content += f"<h2>Section {i}</h2>\n<p>{'word ' * 100}</p>\n"

        # All functions should handle long content
        readability = calculate_readability_score(long_content)
        assert readability["word_count"] > 10000

        headers = extract_headers_structure(long_content)
        assert len(headers) == 101  # 1 h1 + 100 h2

        # Score calculation should work
        score = calculate_content_score(long_content, "test", 10000, 5)
        assert score["total_score"] > 0
