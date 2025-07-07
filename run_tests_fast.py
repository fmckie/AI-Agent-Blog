#!/usr/bin/env python
"""
Fast test runner for development - runs tests once without coverage.

This script provides quick feedback during development by:
- Running tests only once (not multiple times)
- Skipping coverage analysis
- Skipping type checking and code formatting
- Optionally running tests in parallel
"""

import os
import subprocess
import sys
from pathlib import Path
import argparse
import time


# ANSI color codes for terminal output
class Colors:
    """Terminal color codes for pretty output."""
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
    """Print a colored status message."""
    # Map status types to colors
    colors = {
        "info": Colors.CYAN,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED,
    }
    # Get the appropriate color
    color = colors.get(status, Colors.RESET)
    print(f"{color}► {message}{Colors.RESET}")


def check_pytest_xdist() -> bool:
    """Check if pytest-xdist is installed for parallel execution."""
    try:
        import pytest_xdist
        return True
    except ImportError:
        return False


def main():
    """Run fast test suite for quick development feedback."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fast test runner for development")
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    parser.add_argument(
        "-k", "--keyword",
        help="Only run tests matching this keyword expression"
    )
    parser.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Include integration tests (normally skipped)"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="tests/",
        help="Specific test file or directory to run"
    )
    
    args = parser.parse_args()
    
    # Print header
    print_header("Fast Test Runner")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Set up Python path for imports
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    os.environ["PYTHONPATH"] = str(project_dir)
    
    # Build pytest command
    cmd = ["pytest", args.path]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    # Add other options
    cmd.extend(["--tb=short", "--no-cov"])  # Short traceback, no coverage
    
    # Add test selection
    if not args.integration:
        cmd.extend(["-m", "not integration and not slow"])
    
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    if args.fail_fast:
        cmd.append("-x")
    
    # Add parallel execution if requested and available
    if args.parallel:
        if check_pytest_xdist():
            cmd.extend(["-n", "auto"])
            print_status("Running tests in parallel mode", "info")
        else:
            print_status(
                "pytest-xdist not installed, running sequentially", 
                "warning"
            )
            print_status(
                "Install with: pip install pytest-xdist", 
                "warning"
            )
    
    # Record start time
    start_time = time.time()
    
    # Run the tests
    print_status(f"Running: {' '.join(cmd)}", "info")
    print()
    
    try:
        # Execute pytest with real-time output
        result = subprocess.run(cmd, check=False)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Print summary
        print()
        print_header("Test Summary")
        
        # Format duration nicely
        if duration < 60:
            duration_str = f"{duration:.1f} seconds"
        else:
            minutes = int(duration // 60)
            seconds = duration % 60
            duration_str = f"{minutes}m {seconds:.1f}s"
        
        print_status(f"Total time: {duration_str}", "info")
        
        # Print result
        if result.returncode == 0:
            print_status("All tests passed! ✨", "success")
            return 0
        else:
            print_status("Some tests failed", "error")
            print_status(
                "Run ./run_tests.py for full test suite with coverage", 
                "info"
            )
            return result.returncode
            
    except KeyboardInterrupt:
        print()
        print_status("Test run interrupted by user", "warning")
        return 130
    except Exception as e:
        print_status(f"Error running tests: {e}", "error")
        return 1


if __name__ == "__main__":
    sys.exit(main())