#!/bin/bash
# run_tests_staged.sh - Run tests in stages with combined coverage
# This script runs different test categories separately and combines coverage

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored headers
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

# Function to print status messages
print_status() {
    local status=$1
    local message=$2
    case $status in
        "info")
            echo -e "${BLUE}► ${message}${NC}"
            ;;
        "success")
            echo -e "${GREEN}✓ ${message}${NC}"
            ;;
        "error")
            echo -e "${RED}✗ ${message}${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠ ${message}${NC}"
            ;;
    esac
}

# Track start time
start_time=$(date +%s)

# Parse command line arguments
SKIP_SLOW=false
SKIP_INTEGRATION=false
PARALLEL=true
VERBOSE=false
HTML_REPORT=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-slow)
            SKIP_SLOW=true
            shift
            ;;
        --skip-integration)
            SKIP_INTEGRATION=true
            shift
            ;;
        --no-parallel)
            PARALLEL=false
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --no-html)
            HTML_REPORT=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --skip-slow          Skip slow tests"
            echo "  --skip-integration   Skip integration tests"
            echo "  --no-parallel        Disable parallel execution"
            echo "  --verbose, -v        Verbose output"
            echo "  --no-html            Skip HTML report generation"
            echo "  --help, -h           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_header "SEO Content Automation - Staged Test Runner"

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_status "warning" "Virtual environment not activated"
    print_status "info" "Consider running: source venv/bin/activate"
fi

# Check for required dependencies
print_status "info" "Checking dependencies..."

# Check for pytest-xdist if parallel execution is requested
if $PARALLEL; then
    if ! python -c "import xdist" 2>/dev/null; then
        print_status "warning" "pytest-xdist not installed, disabling parallel execution"
        print_status "info" "Install with: pip install pytest-xdist"
        PARALLEL=false
    fi
fi

# Clean up previous coverage data
print_status "info" "Cleaning up previous coverage data..."
rm -f .coverage*
rm -rf htmlcov/

# Set up pytest base command
PYTEST_BASE="pytest"
if $VERBOSE; then
    PYTEST_BASE="$PYTEST_BASE -v"
else
    PYTEST_BASE="$PYTEST_BASE -q"
fi

# Add parallel execution if available
if $PARALLEL; then
    # Get CPU count (leave one free)
    CPU_COUNT=$(python -c "import os; print(max(1, os.cpu_count() - 1))")
    PYTEST_BASE="$PYTEST_BASE -n $CPU_COUNT"
    print_status "info" "Using $CPU_COUNT parallel workers"
fi

# Common pytest options
PYTEST_OPTS="--tb=short -r fEsxX"

# Track overall test status
ALL_PASSED=true

# Stage 1: Fast Unit Tests
print_header "Stage 1: Fast Unit Tests"
print_status "info" "Running fast unit tests (no external dependencies)..."

if $PYTEST_BASE tests/ -m "unit and not slow" $PYTEST_OPTS \
    --cov=. --cov-report= --cov-branch; then
    print_status "success" "Fast unit tests passed"
else
    print_status "error" "Fast unit tests failed"
    ALL_PASSED=false
fi

# Stage 2: All Unit Tests (including slower ones)
if ! $SKIP_SLOW; then
    print_header "Stage 2: All Unit Tests"
    print_status "info" "Running all unit tests (including slower ones)..."
    
    if $PYTEST_BASE tests/ -m "unit" $PYTEST_OPTS \
        --cov=. --cov-append --cov-report=; then
        print_status "success" "All unit tests passed"
    else
        print_status "error" "Some unit tests failed"
        ALL_PASSED=false
    fi
fi

# Stage 3: Integration Tests
if ! $SKIP_INTEGRATION; then
    print_header "Stage 3: Integration Tests"
    print_status "info" "Running integration tests (may use external resources)..."
    
    # Integration tests might take longer, so reduce parallelism
    if $PARALLEL; then
        INTEGRATION_WORKERS=$(python -c "import os; print(max(1, (os.cpu_count() - 1) // 2))")
        INTEGRATION_CMD="pytest -n $INTEGRATION_WORKERS"
    else
        INTEGRATION_CMD="pytest"
    fi
    
    if $VERBOSE; then
        INTEGRATION_CMD="$INTEGRATION_CMD -v"
    else
        INTEGRATION_CMD="$INTEGRATION_CMD -q"
    fi
    
    if $INTEGRATION_CMD tests/ -m "integration" $PYTEST_OPTS \
        --cov=. --cov-append --cov-report=; then
        print_status "success" "Integration tests passed"
    else
        print_status "error" "Some integration tests failed"
        ALL_PASSED=false
    fi
fi

# Stage 4: End-to-End Tests
print_header "Stage 4: End-to-End Tests"
print_status "info" "Checking for e2e tests..."

# Count e2e tests
E2E_COUNT=$(pytest tests/ -m "e2e" --collect-only -q 2>/dev/null | grep -c "test_" || echo "0")
# Remove any whitespace/newlines from the count
E2E_COUNT=$(echo "$E2E_COUNT" | tr -d '\n\r ')

if [ "$E2E_COUNT" -gt 0 ]; then
    print_status "info" "Running $E2E_COUNT end-to-end tests..."
    
    if $PYTEST_BASE tests/ -m "e2e" $PYTEST_OPTS \
        --cov=. --cov-append --cov-report=; then
        print_status "success" "End-to-end tests passed"
    else
        print_status "error" "Some end-to-end tests failed"
        ALL_PASSED=false
    fi
else
    print_status "info" "No e2e tests found, skipping"
fi

# Combine coverage data
print_header "Coverage Report Generation"

# Check if we have coverage data
if ls .coverage* 1> /dev/null 2>&1; then
    print_status "info" "Combining coverage data..."
    
    # Combine coverage files if using parallel mode
    if $PARALLEL; then
        coverage combine
    fi
    
    # Generate terminal report
    print_status "info" "Generating coverage report..."
    echo ""
    coverage report --skip-covered --precision=2
    
    # Generate HTML report if requested
    if $HTML_REPORT; then
        print_status "info" "Generating HTML coverage report..."
        coverage html
        print_status "success" "HTML report generated at: htmlcov/index.html"
        
        # Try to open in browser on macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "info" "Opening coverage report in browser..."
            open htmlcov/index.html 2>/dev/null || true
        fi
    fi
    
    # Generate XML report for CI/CD
    coverage xml -o coverage.xml
    print_status "success" "XML report generated at: coverage.xml"
else
    print_status "error" "No coverage data found!"
fi

# Final summary
print_header "Test Summary"

# Calculate execution time
end_time=$(date +%s)
duration=$((end_time - start_time))
minutes=$((duration / 60))
seconds=$((duration % 60))

print_status "info" "Total execution time: ${minutes}m ${seconds}s"

# Show test statistics
echo ""
print_status "info" "Test statistics:"

# Count tests by marker
for marker in unit integration slow e2e; do
    count=$(pytest tests/ -m "$marker" --collect-only -q 2>/dev/null | grep -c "test_" || echo "0")
    # Remove any whitespace/newlines from the count
    count=$(echo "$count" | tr -d '\n\r ')
    if [ "$count" -gt 0 ]; then
        echo "  • $marker tests: $count"
    fi
done

# Final status
echo ""
if $ALL_PASSED; then
    print_status "success" "All test stages passed! 🎉"
    exit 0
else
    print_status "error" "Some tests failed. Please review the output above."
    print_status "info" "Tips:"
    echo "  • Run with -v for verbose output"
    echo "  • Use --skip-integration for faster local testing"
    echo "  • Check htmlcov/index.html for detailed coverage"
    exit 1
fi