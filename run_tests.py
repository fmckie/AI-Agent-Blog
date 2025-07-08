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
import shutil


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
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, env=os.environ
        )

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


def get_cpu_count() -> int:
    """Get the number of CPUs to use for parallel testing."""
    # Use all CPUs minus 1 to keep system responsive
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count - 1)


def check_dependencies() -> dict[str, bool]:
    """Check if optional dependencies are installed."""
    deps = {}
    
    # Check for pytest-xdist (parallel execution)
    try:
        subprocess.run(["pytest", "--version", "-n", "auto"], 
                      capture_output=True, check=True)
        deps["pytest-xdist"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        deps["pytest-xdist"] = False
    
    # Check for pytest-timeout
    try:
        subprocess.run(["pytest", "--version", "--timeout=1"], 
                      capture_output=True, check=True)
        deps["pytest-timeout"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        deps["pytest-timeout"] = False
    
    return deps


def main():
    """Run all tests and generate reports."""
    import time
    import argparse
    
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

    # Check optional dependencies
    deps = check_dependencies()
    if not deps["pytest-xdist"] and args.parallel:
        print_status("pytest-xdist not installed, parallel execution disabled", "warning")
        print_status("Install with: pip install pytest-xdist", "info")
        args.parallel = False
    
    if not deps["pytest-timeout"]:
        print_status("pytest-timeout not installed, no test timeouts", "warning")
        print_status("Install with: pip install pytest-timeout", "info")

    # Track overall success
    all_passed = True

    # Build pytest command
    pytest_cmd = ["pytest", "tests/"]
    
    # Add verbosity
    pytest_cmd.append("-v")
    
    # Add markers based on mode
    if args.unit_only:
        pytest_cmd.extend(["-m", "not integration and not slow"])
        print_header("Running Unit Tests Only (Fast Mode)")
    elif not args.full:
        pytest_cmd.extend(["-m", "not slow"])
        print_header("Running Standard Test Suite (No Slow Tests)")
    else:
        print_header("Running Full Test Suite (Including Integration)")
    
    # Add parallel execution if available and requested
    if args.parallel and deps["pytest-xdist"]:
        cpu_count = get_cpu_count()
        pytest_cmd.extend(["-n", str(cpu_count)])
        print_status(f"Using {cpu_count} parallel workers", "info")
    
    # Add coverage unless disabled
    if not args.no_cov:
        pytest_cmd.extend([
            "--cov=.",  # Specify source directory
            "--cov-report=term-missing:skip-covered",  # More concise output
            "--cov-report=html",
            "--cov-report=xml",
        ])
        # Only add parallel mode flag if using xdist
        if args.parallel and deps["pytest-xdist"]:
            pytest_cmd.append("--cov-append")
    
    # Add test profiling if requested
    if args.profile:
        pytest_cmd.extend(["--durations=10"])
    
    # Add failed-first if requested
    if args.failed_first:
        pytest_cmd.extend(["--lf", "--ff"])
    
    # Add timeout if available
    if deps["pytest-timeout"]:
        # 5 minutes for integration tests, 30s for unit tests
        timeout = "300" if args.full else "30"
        pytest_cmd.extend([f"--timeout={timeout}"])
    
    # Run the tests
    test_type = "Unit tests" if args.unit_only else "Test suite"
    if not run_command(pytest_cmd, test_type):
        all_passed = False
    
    # Combine coverage if parallel mode was used
    if not args.no_cov and args.parallel and deps["pytest-xdist"]:
        print_header("Combining Parallel Coverage Results")
        run_command(["coverage", "combine"], "Combining coverage data")
        run_command(["coverage", "report", "--skip-covered"], "Coverage report")
        run_command(["coverage", "html"], "HTML coverage report")
    
    # Show test statistics
    print_header("Test Statistics")
    
    # Get test counts by marker
    markers = ["unit", "integration", "slow", "fast"]
    for marker in markers:
        result = subprocess.run(
            ["pytest", "tests/", "-m", marker, "--collect-only", "-q"],
            capture_output=True,
            text=True
        )
        count = len([l for l in result.stdout.splitlines() if "test_" in l])
        if count > 0:
            print_status(f"{marker.capitalize()} tests: {count}", "info")
    
    # Quick code quality checks (only in full mode)
    if args.full:
        print_header("Quick Code Quality Checks")
        
        # Try black
        try:
            run_command(["black", ".", "--check", "--quiet"], "Code formatting (black)")
        except FileNotFoundError:
            print_status("black not installed", "warning")
        
        # Try isort
        try:
            run_command(["isort", ".", "--check-only", "--quiet"], "Import sorting (isort)")
        except FileNotFoundError:
            print_status("isort not installed", "warning")

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
    
    # Provide optimization tips based on execution time
    if total_time > 300:  # More than 5 minutes
        print()
        print_status("💡 Speed up tips:", "info")
        print_status("  • Use --unit-only for quick feedback during development", "info")
        print_status("  • Use --no-cov to skip coverage calculation", "info")
        print_status("  • Use --failed-first to run failed tests first", "info")
        if not deps["pytest-xdist"]:
            print_status("  • Install pytest-xdist for parallel execution", "info")
    
    if all_passed:
        print_status("All tests passed! ✨", "success")
        return 0
    else:
        print_status("Some tests failed. Please fix and run again.", "error")
        print_status("Tip: Use --failed-first to run failed tests first", "info")
        return 1


if __name__ == "__main__":
    sys.exit(main())