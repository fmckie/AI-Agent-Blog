#!/usr/bin/env python
"""
Test runner script for SEO Content Automation System.

This script runs all tests and generates coverage reports.
It can be used for local development and CI/CD pipelines.
"""

import os

# Import required libraries
import subprocess
import sys
from pathlib import Path


# Colors for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{message.center(60)}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")


def print_status(message: str, status: str = "info") -> None:
    """Print a status message with color."""
    colors = {
        "info": Colors.CYAN,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED,
    }
    color = colors.get(status, Colors.RESET)
    print(f"{color}► {message}{Colors.RESET}")


def run_command(command: list[str], description: str) -> bool:
    """
    Run a command and return success status.

    Args:
        command: Command and arguments to run
        description: Description of what the command does

    Returns:
        True if command succeeded, False otherwise
    """
    print_status(f"Running: {description}", "info")
    print_status(f"Command: {' '.join(command)}", "info")

    try:
        # Run the command with inherited environment variables
        result = subprocess.run(command, capture_output=True, text=True, check=True, env=os.environ)

        # Print output if any
        if result.stdout:
            print(result.stdout)

        print_status(f"✓ {description} completed successfully", "success")
        return True

    except subprocess.CalledProcessError as e:
        print_status(f"✗ {description} failed", "error")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(f"{Colors.RED}Error output:{Colors.RESET}")
            print(e.stderr)
        return False


def main():
    """Run all tests and generate reports."""
    print_header("SEO Content Automation Test Suite")

    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Add project directory to Python path so tests can import modules
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    # Also set PYTHONPATH environment variable for subprocess calls
    os.environ["PYTHONPATH"] = str(project_dir)

    # Check if virtual environment is activated
    if not hasattr(sys, "real_prefix") and not (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print_status("Warning: Virtual environment not activated", "warning")
        print_status("Run 'source venv/bin/activate' first", "warning")
        print()

    # Track overall success
    all_passed = True

    # 1. Run unit tests
    print_header("Running Unit Tests")
    if not run_command(
        ["pytest", "tests/", "-v", "-m", "not integration", "--no-cov"], "Unit tests"
    ):
        all_passed = False

    # 2. Run integration tests (if any)
    print_header("Running Integration Tests")
    if not run_command(
        ["pytest", "tests/", "-v", "-m", "integration", "--no-cov"], "Integration tests"
    ):
        # Integration test failures are warnings for now
        print_status("Integration tests failed (non-blocking)", "warning")

    # 3. Run all tests with coverage
    print_header("Running All Tests with Coverage")
    if not run_command(
        [
            "pytest",
            "tests/",
            "-v",
            "--cov",
            "--cov-report=term-missing",
            "--cov-report=html",
        ],
        "Full test suite with coverage",
    ):
        all_passed = False

    # 4. Run type checking (if mypy is installed)
    print_header("Running Type Checking")
    try:
        if not run_command(
            ["mypy", ".", "--ignore-missing-imports"], "Type checking with mypy"
        ):
            print_status("Type checking failed (non-blocking)", "warning")
    except FileNotFoundError:
        print_status("mypy not installed, skipping type checking", "warning")

    # 5. Run linting (if available)
    print_header("Running Code Quality Checks")

    # Try black
    try:
        run_command(["black", ".", "--check"], "Code formatting check (black)")
    except FileNotFoundError:
        print_status("black not installed, skipping formatting check", "warning")

    # Try isort
    try:
        run_command(["isort", ".", "--check-only"], "Import sorting check (isort)")
    except FileNotFoundError:
        print_status("isort not installed, skipping import check", "warning")

    # 6. Generate test report
    print_header("Test Summary")

    # Check coverage report
    coverage_file = project_dir / "htmlcov" / "index.html"
    if coverage_file.exists():
        print_status(f"Coverage report generated: {coverage_file}", "success")
        print_status("Open the file in a browser to view detailed coverage", "info")

    # Final status
    print()
    if all_passed:
        print_status("All required tests passed! ✨", "success")
        print_status("The codebase is ready for deployment", "success")
        return 0
    else:
        print_status("Some tests failed. Please fix the issues and run again.", "error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
