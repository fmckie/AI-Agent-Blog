"""
Output formatting utilities for the CLI.

This module provides formatting helpers for various output types
used throughout the command-line interface.
"""

from typing import Any, Dict, List


def format_file_size(bytes_size: int) -> str:
    """
    Format bytes into human-readable size.

    Args:
        bytes_size: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_percentage(value: float, precision: int = 1) -> str:
    """
    Format a decimal value as percentage.

    Args:
        value: Decimal value between 0 and 1
        precision: Number of decimal places

    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{precision}f}%"


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_metrics_for_export(metrics: Dict[str, Any], format_type: str) -> str:
    """
    Format metrics dictionary for export in various formats.

    Args:
        metrics: Dictionary of metrics
        format_type: Output format ('json', 'csv', 'prometheus')

    Returns:
        Formatted string ready for export
    """
    if format_type == "csv":
        # Simple CSV format
        lines = ["metric,value"]
        for key, value in metrics.items():
            if isinstance(value, (int, float, str)):
                lines.append(f"{key},{value}")
        return "\n".join(lines)

    elif format_type == "prometheus":
        # Prometheus exposition format
        lines = []
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                metric_name = f"seo_cache_{key}"
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(f"{metric_name} {value}")
        return "\n".join(lines)

    # Default to JSON (handled elsewhere)
    return ""
