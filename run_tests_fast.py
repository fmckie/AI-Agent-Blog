#!/usr/bin/env python
"""
Fast test runner for quick development feedback.

This script runs only the most essential tests for rapid iteration.
Use this during development for immediate feedback on changes.
"""

import os
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


def main():
    """Run fast test suite for development."""
    import time
    import argparse

    parser = argparse.ArgumentParser(description="Fast test runner for development")
    parser.add_argument(
        "path", nargs="?", default="tests/", help="Specific test path or file to run"
    )
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword expression")
    parser.add_argument(
        "-x", "--exitfirst", action="store_true", help="Exit on first failure"
    )
    parser.add_argument(
        "-l",
        "--lf",
        "--last-failed",
        action="store_true",
        help="Run only last failed tests",
    )
    parser.add_argument(
        "-f",
        "--ff",
        "--failed-first",
        action="store_true",
        help="Run failed tests first",
    )
    parser.add_argument(
        "--pdb", action="store_true", help="Drop into debugger on failures"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--watch", action="store_true", help="Watch for file changes and re-run tests"
    )
    args = parser.parse_args()

    start_time = time.time()

    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Set Python path
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    os.environ["PYTHONPATH"] = str(project_dir)

    print(f"\n{Colors.BLUE}{Colors.BOLD}⚡ Fast Test Runner{Colors.RESET}")
    print(f"{Colors.CYAN}Running minimal test suite for quick feedback{Colors.RESET}\n")

    # Build pytest command
    cmd = ["pytest"]

    # Add test path
    cmd.append(args.path)

    # Fast mode settings
    cmd.extend(
        [
            "-m",
            "not slow and not integration",  # Skip slow and integration tests
            "--tb=short",  # Short traceback
            "-q",  # Quiet by default
            "--disable-warnings",  # Hide warnings
            "--maxfail=3",  # Stop after 3 failures
        ]
    )

    # Explicitly disable coverage to avoid any automatic coverage collection
    cmd.extend(["-p", "no:cov"])

    # Try to use pytest-xdist for parallel execution
    try:
        subprocess.run(
            ["pytest", "--version", "-n", "auto"], capture_output=True, check=True
        )
        cpu_count = max(1, (os.cpu_count() or 1) - 1)
        cmd.extend(["-n", str(cpu_count)])
        print_status(f"Running with {cpu_count} parallel workers", "info")
    except:
        pass

    # Add optional arguments
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    if args.exitfirst:
        cmd.append("-x")
    if args.lf:
        cmd.append("--lf")
    if args.ff:
        cmd.append("--ff")
    if args.pdb:
        cmd.append("--pdb")
    if args.verbose:
        cmd.remove("-q")
        cmd.append("-v")

    # Watch mode
    if args.watch:
        print_status("Watch mode enabled. Press Ctrl+C to exit.", "info")
        try:
            # Try to use pytest-watch if available
            watch_cmd = ["ptw"] + cmd[1:]  # Remove 'pytest' from command
            subprocess.run(watch_cmd)
        except FileNotFoundError:
            print_status("pytest-watch not installed", "warning")
            print_status("Install with: pip install pytest-watch", "info")
            print_status("Running tests once instead...", "info")
            subprocess.run(cmd)
    else:
        # Run tests
        result = subprocess.run(cmd)

        # Show timing
        total_time = time.time() - start_time
        print(f"\n{Colors.CYAN}Total time: {total_time:.1f}s{Colors.RESET}")

        # Show tips based on result
        if result.returncode == 0:
            print(f"{Colors.GREEN}✨ All tests passed!{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}💡 Quick tips:{Colors.RESET}")
            print(f"  • Use -x to stop on first failure")
            print(f"  • Use -k 'test_name' to run specific tests")
            print(f"  • Use --lf to run only failed tests")
            print(f"  • Use --pdb to debug failures")
            print(f"  • Use --watch for continuous testing")

        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
