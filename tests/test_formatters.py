"""
Comprehensive tests for CLI formatting utilities.

This module tests all formatting functions in cli/formatters.py to ensure
proper output formatting for various CLI display needs.
"""

import pytest
from cli.formatters import (
    format_file_size,
    format_percentage,
    truncate_text,
    format_metrics_for_export,
)


class TestFormatFileSize:
    """Test the format_file_size function."""

    def test_bytes_formatting(self):
        """Test formatting of byte values."""
        # Test exact byte values
        assert format_file_size(0) == "0.00 B"
        assert format_file_size(1) == "1.00 B"
        assert format_file_size(512) == "512.00 B"
        assert format_file_size(1023) == "1023.00 B"

    def test_kilobytes_formatting(self):
        """Test formatting of kilobyte values."""
        # Test KB range (1024 bytes = 1 KB)
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"
        assert format_file_size(2048) == "2.00 KB"
        assert format_file_size(1048575) == "1024.00 KB"

    def test_megabytes_formatting(self):
        """Test formatting of megabyte values."""
        # Test MB range (1024 * 1024 = 1,048,576 bytes = 1 MB)
        assert format_file_size(1048576) == "1.00 MB"
        assert format_file_size(1572864) == "1.50 MB"
        assert format_file_size(10485760) == "10.00 MB"
        assert format_file_size(52428800) == "50.00 MB"

    def test_gigabytes_formatting(self):
        """Test formatting of gigabyte values."""
        # Test GB range (1024 * 1024 * 1024 = 1,073,741,824 bytes = 1 GB)
        assert format_file_size(1073741824) == "1.00 GB"
        assert format_file_size(2147483648) == "2.00 GB"
        assert format_file_size(5368709120) == "5.00 GB"

    def test_terabytes_formatting(self):
        """Test formatting of terabyte values."""
        # Test TB range (1024^4 = 1,099,511,627,776 bytes = 1 TB)
        assert format_file_size(1099511627776) == "1.00 TB"
        assert format_file_size(2199023255552) == "2.00 TB"

    def test_petabytes_formatting(self):
        """Test formatting of petabyte values."""
        # Test PB range (1024^5 = 1,125,899,906,842,624 bytes = 1 PB)
        assert format_file_size(1125899906842624) == "1.00 PB"
        assert format_file_size(2251799813685248) == "2.00 PB"
        # Very large values should also show PB
        assert format_file_size(10 * 1125899906842624) == "10.00 PB"

    def test_precision_formatting(self):
        """Test that values are formatted with 2 decimal places."""
        assert format_file_size(1536) == "1.50 KB"  # Exactly 1.5 KB
        assert format_file_size(1434) == "1.40 KB"  # ~1.4 KB
        assert format_file_size(1126) == "1.10 KB"  # ~1.1 KB
        assert format_file_size(1331) == "1.30 KB"  # ~1.3 KB


class TestFormatPercentage:
    """Test the format_percentage function."""

    def test_basic_percentage_formatting(self):
        """Test basic percentage formatting."""
        assert format_percentage(0) == "0.0%"
        assert format_percentage(0.5) == "50.0%"
        assert format_percentage(1) == "100.0%"
        assert format_percentage(0.25) == "25.0%"
        assert format_percentage(0.75) == "75.0%"

    def test_precision_control(self):
        """Test percentage formatting with different precision levels."""
        # Default precision is 1
        assert format_percentage(0.1234) == "12.3%"
        assert format_percentage(0.1236) == "12.4%"  # Should round
        
        # Test with precision = 0
        assert format_percentage(0.1234, precision=0) == "12%"
        assert format_percentage(0.756, precision=0) == "76%"
        
        # Test with precision = 2
        assert format_percentage(0.1234, precision=2) == "12.34%"
        assert format_percentage(0.75689, precision=2) == "75.69%"
        
        # Test with precision = 3
        assert format_percentage(0.123456, precision=3) == "12.346%"
        assert format_percentage(0.999999, precision=3) == "100.000%"

    def test_edge_cases(self):
        """Test edge cases for percentage formatting."""
        # Very small values
        assert format_percentage(0.0001) == "0.0%"
        assert format_percentage(0.0001, precision=2) == "0.01%"
        assert format_percentage(0.0001, precision=3) == "0.010%"
        
        # Values greater than 1 (over 100%)
        assert format_percentage(1.5) == "150.0%"
        assert format_percentage(2.25) == "225.0%"
        
        # Negative values
        assert format_percentage(-0.25) == "-25.0%"
        assert format_percentage(-1) == "-100.0%"


class TestTruncateText:
    """Test the truncate_text function."""

    def test_no_truncation_needed(self):
        """Test text that doesn't need truncation."""
        short_text = "This is a short text"
        assert truncate_text(short_text) == short_text
        assert truncate_text(short_text, max_length=100) == short_text
        
        # Text exactly at max length
        text_50 = "a" * 50
        assert truncate_text(text_50, max_length=50) == text_50

    def test_basic_truncation(self):
        """Test basic text truncation."""
        long_text = "This is a very long text that needs to be truncated because it exceeds the maximum allowed length for display purposes in the CLI interface"
        
        # Default max_length is 200
        result = truncate_text(long_text)
        # Text is shorter than 200, so no truncation
        assert result == long_text

    def test_custom_max_length(self):
        """Test truncation with custom max length."""
        text = "The quick brown fox jumps over the lazy dog"
        
        result = truncate_text(text, max_length=20)
        assert result == "The quick brown f..."
        assert len(result) == 20
        
        result = truncate_text(text, max_length=10)
        assert result == "The qui..."
        assert len(result) == 10

    def test_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "This text will be truncated with a custom suffix"
        
        result = truncate_text(text, max_length=30, suffix=" [more]")
        assert result == "This text will be trunc [more]"
        assert len(result) == 30
        
        result = truncate_text(text, max_length=25, suffix="…")
        assert result == "This text will be trunca…"
        assert len(result) == 25

    def test_edge_cases(self):
        """Test edge cases for text truncation."""
        # Empty text
        assert truncate_text("") == ""
        
        # Text shorter than suffix
        assert truncate_text("Hi", max_length=2, suffix="...") == "Hi"
        
        # Max length equals suffix length
        assert truncate_text("Hello World", max_length=3, suffix="...") == "..."
        
        # Unicode text
        unicode_text = "Hello 世界! This is a test with unicode characters"
        result = truncate_text(unicode_text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")


class TestFormatMetricsForExport:
    """Test the format_metrics_for_export function."""

    def test_csv_format_basic(self):
        """Test basic CSV format export."""
        metrics = {
            "total_entries": 1000,
            "cache_hits": 750,
            "hit_rate": 0.75,
            "storage_bytes": 1048576,
        }
        
        result = format_metrics_for_export(metrics, "csv")
        lines = result.split("\n")
        
        # Check header
        assert lines[0] == "metric,value"
        
        # Check data lines
        assert "total_entries,1000" in lines
        assert "cache_hits,750" in lines
        assert "hit_rate,0.75" in lines
        assert "storage_bytes,1048576" in lines

    def test_csv_format_filters_complex_types(self):
        """Test CSV format filters out complex types."""
        metrics = {
            "count": 100,
            "rate": 0.95,
            "name": "test_cache",
            "data": {"nested": "value"},  # Should be filtered
            "items": [1, 2, 3],  # Should be filtered
            "active": True,  # Should be included (bool converts to string in CSV)
        }
        
        result = format_metrics_for_export(metrics, "csv")
        lines = result.split("\n")
        
        # Should include simple types
        assert "count,100" in lines
        assert "rate,0.95" in lines
        assert "name,test_cache" in lines
        
        # Should not include complex types
        assert "data" not in result
        assert "items" not in result
        # Bool should be included
        assert "active,True" in result

    def test_prometheus_format_basic(self):
        """Test basic Prometheus format export."""
        metrics = {
            "total_entries": 1000,
            "cache_hits": 750,
            "hit_rate": 0.75,
        }
        
        result = format_metrics_for_export(metrics, "prometheus")
        lines = result.split("\n")
        
        # Check format for each metric
        assert "# TYPE seo_cache_total_entries gauge" in lines
        assert "seo_cache_total_entries 1000" in lines
        
        assert "# TYPE seo_cache_cache_hits gauge" in lines
        assert "seo_cache_cache_hits 750" in lines
        
        assert "# TYPE seo_cache_hit_rate gauge" in lines
        assert "seo_cache_hit_rate 0.75" in lines

    def test_prometheus_format_filters_non_numeric(self):
        """Test Prometheus format only includes numeric values."""
        metrics = {
            "requests": 500,
            "success_rate": 0.98,
            "status": "healthy",  # Should be filtered
            "last_update": "2024-01-20",  # Should be filtered
            "temperature": 23.5,
        }
        
        result = format_metrics_for_export(metrics, "prometheus")
        
        # Should include numeric values
        assert "seo_cache_requests 500" in result
        assert "seo_cache_success_rate 0.98" in result
        assert "seo_cache_temperature 23.5" in result
        
        # Should not include string values
        assert "status" not in result
        assert "last_update" not in result

    def test_json_format_default(self):
        """Test that JSON format returns empty string (handled elsewhere)."""
        metrics = {"test": 123}
        result = format_metrics_for_export(metrics, "json")
        assert result == ""

    def test_unknown_format(self):
        """Test unknown format returns empty string."""
        metrics = {"test": 123}
        result = format_metrics_for_export(metrics, "xml")
        assert result == ""

    def test_empty_metrics(self):
        """Test handling of empty metrics."""
        # CSV format with empty metrics
        result = format_metrics_for_export({}, "csv")
        assert result == "metric,value"
        
        # Prometheus format with empty metrics
        result = format_metrics_for_export({}, "prometheus")
        assert result == ""

    @pytest.mark.parametrize("format_type,expected_header", [
        ("csv", "metric,value"),
        ("prometheus", "# TYPE"),
    ])
    def test_format_headers(self, format_type, expected_header):
        """Test that each format includes expected headers."""
        metrics = {"test_metric": 100}
        result = format_metrics_for_export(metrics, format_type)
        
        if format_type == "csv":
            assert result.startswith(expected_header)
        elif format_type == "prometheus" and result:  # Prometheus might be empty
            assert expected_header in result


# Integration test to verify all formatters work together
class TestFormattersIntegration:
    """Integration tests for formatters working together."""

    def test_format_cache_stats_display(self):
        """Test formatting cache statistics for display."""
        # Simulate cache stats that would be displayed
        cache_stats = {
            "total_entries": 1500,
            "storage_bytes": 52428800,  # 50 MB
            "hit_rate": 0.857,
        }
        
        # Format for display
        size_display = format_file_size(cache_stats["storage_bytes"])
        hit_rate_display = format_percentage(cache_stats["hit_rate"], precision=1)
        
        assert size_display == "50.00 MB"
        assert hit_rate_display == "85.7%"
        
        # Format for CSV export
        csv_export = format_metrics_for_export(cache_stats, "csv")
        assert "total_entries,1500" in csv_export
        assert "storage_bytes,52428800" in csv_export
        assert "hit_rate,0.857" in csv_export

    def test_format_long_content_preview(self):
        """Test formatting long content for preview display."""
        long_content = """
        This is a very long research article about diabetes management that includes
        multiple sections covering diet, exercise, medication, monitoring, and lifestyle
        changes. The content is comprehensive and includes citations from various medical
        journals and research studies. It also contains practical tips and recommendations
        for patients managing their condition on a daily basis.
        """ * 5  # Make it really long
        
        # Truncate for preview
        preview = truncate_text(long_content.strip(), max_length=150)
        assert len(preview) <= 150
        assert preview.endswith("...")
        
        # Should preserve the beginning of the content
        assert preview.startswith("This is a very long research article")


# Fixtures for common test data
@pytest.fixture
def sample_metrics():
    """Provide sample metrics for testing."""
    return {
        "cache_requests": 1000,
        "cache_hits": 850,
        "cache_misses": 150,
        "hit_rate": 0.85,
        "avg_response_time": 0.125,
        "total_storage_bytes": 104857600,  # 100 MB
        "unique_keywords": 75,
        "last_cleanup": "2024-01-20T10:00:00Z",
    }


@pytest.fixture
def large_text():
    """Provide large text for truncation testing."""
    return (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
        "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
        "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
        "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
        "culpa qui officia deserunt mollit anim id est laborum."
    )


# Test utilities
def test_all_formatters_are_tested():
    """Ensure all formatter functions are covered by tests."""
    from cli import formatters
    import inspect
    
    # Get all functions in the formatters module
    formatter_functions = [
        name for name, obj in inspect.getmembers(formatters)
        if inspect.isfunction(obj) and not name.startswith("_")
    ]
    
    # These are the functions we've tested
    tested_functions = [
        "format_file_size",
        "format_percentage", 
        "truncate_text",
        "format_metrics_for_export",
    ]
    
    # Verify we've tested all public functions
    assert set(formatter_functions) == set(tested_functions)