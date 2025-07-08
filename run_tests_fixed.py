#!/usr/bin/env python
"""
Fixed test runner script for SEO Content Automation System.

This script runs tests with proper timeouts and error handling.
"""

import os
import subprocess
import sys
from pathlib import Path
import time
import argparse


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


def get_cpu_count() -> int:
    """Get the number of CPUs to use for parallel testing."""
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count - 1)


def check_xdist_installed() -> bool:
    """Check if pytest-xdist is installed."""
    try:
        import xdist
        return True
    except ImportError:
        return False


def main():
    """Run all tests and generate reports."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run test suite with various options")
    parser.add_argument("--full", action="store_true", 
                       help="Run full test suite including integration tests")
    parser.add_argument("--unit-only", action="store_true", 
                       help="Run only unit tests (fast)")
    parser.add_argument("--no-cov", action="store_true", 
                       help="Skip coverage reporting for faster execution")
    parser.add_argument("--parallel", dest="parallel", action="store_true",
                       help="Run tests in parallel (requires pytest-xdist)")
    parser.add_argument("--no-parallel", dest="parallel", action="store_false",
                       help="Disable parallel execution")
    parser.set_defaults(parallel=True)
    parser.add_argument("--profile", action="store_true",
                       help="Show test duration profiling")
    parser.add_argument("--failed-first", action="store_true",
                       help="Run previously failed tests first")
    args = parser.parse_args()
    
    start_time = time.time()
    
    print_header("SEO Content Automation Test Suite")

    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Set Python path
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    os.environ["PYTHONPATH"] = str(project_dir)

    # Check if virtual environment is activated
    if not hasattr(sys, "real_prefix") and not (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print_status("Warning: Virtual environment may not be activated", "warning")

    # Build pytest command
    pytest_cmd = ["pytest", "tests/", "-v"]
    
    # Add markers based on mode
    if args.unit_only:
        pytest_cmd.extend(["-m", "not integration and not slow"])
        print_header("Running Unit Tests Only (Fast Mode)")
    elif not args.full:
        pytest_cmd.extend(["-m", "not slow"])
        print_header("Running Standard Test Suite (No Slow Tests)")
    else:
        print_header("Running Full Test Suite (Including Integration)")
    
    # Add parallel execution if requested and available
    has_xdist = check_xdist_installed()
    if args.parallel and has_xdist:
        cpu_count = get_cpu_count()
        pytest_cmd.extend(["-n", str(cpu_count)])
        print_status(f"Using {cpu_count} parallel workers", "info")
    elif args.parallel and not has_xdist:
        print_status("pytest-xdist not installed, running sequentially", "warning")
        print_status("Install with: pip install pytest-xdist", "info")
    
    # Add coverage unless disabled
    if not args.no_cov:
        pytest_cmd.extend([
            "--cov=.",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html",
        ])
    
    # Add test profiling if requested
    if args.profile:
        pytest_cmd.extend(["--durations=10"])
    
    # Add failed-first if requested
    if args.failed_first:
        pytest_cmd.extend(["--lf", "--ff"])
    
    # Add some performance optimizations
    pytest_cmd.extend([
        "--tb=short",
        "-r", "fEsxX",  # Show extra test summary info
    ])
    
    # Run the tests
    print_status(f"Running command: {' '.join(pytest_cmd)}", "info")
    print()
    
    try:
        result = subprocess.run(pytest_cmd, check=False)
        all_passed = (result.returncode == 0)
    except KeyboardInterrupt:
        print_status("\nTest run interrupted by user", "warning")
        return 130
    except Exception as e:
        print_status(f"Error running tests: {e}", "error")
        return 1
    
    # Final report
    print_header("Final Summary")

    # Check coverage report
    if not args.no_cov:
        coverage_file = project_dir / "htmlcov" / "index.html"
        if coverage_file.exists():
            print_status(f"Coverage report: {coverage_file}", "success")

    # Calculate total time
    total_time = time.time() - start_time
    minutes = int(total_time // 60)
    seconds = total_time % 60
    
    print_status(f"Total execution time: {minutes}m {seconds:.1f}s", "info")
    
    # Provide optimization tips
    if total_time > 300:  # More than 5 minutes
        print()
        print_status("💡 Speed up tips:", "info")
        print_status("  • Use --unit-only for quick feedback", "info")
        print_status("  • Use --no-cov to skip coverage", "info")
        print_status("  • Use --failed-first to run failed tests first", "info")
        if not has_xdist:
            print_status("  • Install pytest-xdist for parallel execution", "info")
    
    if all_passed:
        print_status("All tests passed! ✨", "success")
        return 0
    else:
        print_status("Some tests failed. Please fix and run again.", "error")
        return 1


if __name__ == "__main__":
    sys.exit(main())