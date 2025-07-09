#!/bin/bash
# run_tests_with_real_keys.sh - Run tests using real API keys from .env
# This script loads the .env file and runs tests that require real API authentication

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_msg() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_msg "$RED" "Error: .env file not found!"
    echo "Please create a .env file with your API keys."
    echo "You can copy from .env.example: cp .env.example .env"
    exit 1
fi

# Load environment variables from .env
print_msg "$BLUE" "Loading environment variables from .env..."
export $(grep -v '^#' .env | xargs)

# Verify required API keys are present
if [ -z "$TAVILY_API_KEY" ]; then
    print_msg "$RED" "Error: TAVILY_API_KEY not found in .env!"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    print_msg "$RED" "Error: OPENAI_API_KEY not found in .env!"
    exit 1
fi

print_msg "$GREEN" "API keys loaded successfully"

# Parse command line arguments
COVERAGE=true
VERBOSE=false
MARKERS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --unit)
            MARKERS="-m unit"
            shift
            ;;
        --integration)
            MARKERS="-m integration"
            shift
            ;;
        --all)
            MARKERS=""
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--no-coverage] [--verbose|-v] [--unit|--integration|--all]"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest tests/"

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD $MARKERS"
fi

if $VERBOSE; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if $COVERAGE; then
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=term-missing --cov-report=html"
fi

# Run tests
print_msg "$BLUE" "Running tests with real API keys..."
print_msg "$YELLOW" "Command: $PYTEST_CMD"
echo ""

$PYTEST_CMD

# Check exit code
if [ $? -eq 0 ]; then
    print_msg "$GREEN" "✓ All tests passed!"
    if $COVERAGE; then
        print_msg "$BLUE" "Coverage report available at: htmlcov/index.html"
    fi
else
    print_msg "$RED" "✗ Some tests failed"
    exit 1
fi