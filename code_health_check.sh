#!/bin/bash
# code_health_check.sh - Analyze code health and identify potential bugs
# This script runs various checks and generates a health score

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Initialize scoring variables
TOTAL_SCORE=100
ISSUES_FOUND=0
CRITICAL_ISSUES=0
WARNINGS=0
SUGGESTIONS=0

# Categories and their weights
declare -A CATEGORY_WEIGHTS=(
    ["test_failures"]=30
    ["code_quality"]=20
    ["security"]=15
    ["complexity"]=15
    ["documentation"]=10
    ["dependencies"]=10
)

# Store detailed findings
declare -a FINDINGS
declare -a CRITICAL_FINDINGS
declare -a WARNING_FINDINGS

# Function to print colored headers
print_header() {
    echo -e "\n${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Function to print status messages
print_status() {
    local status=$1
    local message=$2
    case $status in
        "info")
            echo -e "${CYAN}ℹ ${message}${NC}"
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
        "critical")
            echo -e "${RED}${BOLD}⛔ ${message}${NC}"
            ;;
    esac
}

# Function to add finding
add_finding() {
    local severity=$1
    local category=$2
    local message=$3
    local penalty=$4
    
    case $severity in
        "critical")
            CRITICAL_FINDINGS+=("[$category] $message")
            CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
            TOTAL_SCORE=$((TOTAL_SCORE - penalty))
            ;;
        "warning")
            WARNING_FINDINGS+=("[$category] $message")
            WARNINGS=$((WARNINGS + 1))
            TOTAL_SCORE=$((TOTAL_SCORE - penalty))
            ;;
        "suggestion")
            FINDINGS+=("[$category] $message")
            SUGGESTIONS=$((SUGGESTIONS + 1))
            TOTAL_SCORE=$((TOTAL_SCORE - penalty))
            ;;
    esac
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

# Start health check
clear
print_header "🏥 Code Health Check - SEO Content Automation System"
echo -e "${CYAN}Starting comprehensive code analysis...${NC}\n"

# Check if we're in the right directory
if [ ! -f "pytest.ini" ] || [ ! -d "tests" ]; then
    print_status "error" "Not in project root directory!"
    exit 1
fi

# 1. Test Suite Analysis
print_header "1. Test Suite Analysis"
print_status "info" "Running test analysis..."

# Count total tests
TOTAL_TESTS=$(pytest --collect-only -q 2>/dev/null | grep -c "test_" || echo "0")
print_status "info" "Total tests found: $TOTAL_TESTS"

# Run tests and capture results
TEST_OUTPUT=$(pytest tests/ -v --tb=short -q 2>&1)
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_status "success" "All tests passing!"
else
    # Parse test failures
    FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || echo "0")
    ERROR_TESTS=$(echo "$TEST_OUTPUT" | grep -c "ERROR" || echo "0")
    
    if [ $FAILED_TESTS -gt 0 ]; then
        add_finding "critical" "Tests" "$FAILED_TESTS test(s) failing" $((FAILED_TESTS * 5))
        print_status "critical" "$FAILED_TESTS test failures found"
    fi
    
    if [ $ERROR_TESTS -gt 0 ]; then
        add_finding "critical" "Tests" "$ERROR_TESTS test(s) with errors" $((ERROR_TESTS * 7))
        print_status "critical" "$ERROR_TESTS test errors found"
    fi
fi

# Check test coverage
if command -v coverage &> /dev/null; then
    print_status "info" "Checking test coverage..."
    COVERAGE_OUTPUT=$(coverage run -m pytest tests/ -q 2>/dev/null && coverage report --skip-covered | tail -n 1)
    COVERAGE_PERCENT=$(echo "$COVERAGE_OUTPUT" | grep -oE '[0-9]+%' | tr -d '%' | head -1)
    
    if [ -n "$COVERAGE_PERCENT" ]; then
        print_status "info" "Test coverage: ${COVERAGE_PERCENT}%"
        if [ "$COVERAGE_PERCENT" -lt 60 ]; then
            add_finding "critical" "Coverage" "Low test coverage: ${COVERAGE_PERCENT}%" 15
        elif [ "$COVERAGE_PERCENT" -lt 80 ]; then
            add_finding "warning" "Coverage" "Test coverage below target: ${COVERAGE_PERCENT}%" 8
        else
            print_status "success" "Good test coverage!"
        fi
    fi
fi

# 2. Code Quality Analysis
print_header "2. Code Quality Analysis"

# Python syntax errors
print_status "info" "Checking for syntax errors..."
SYNTAX_ERRORS=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -exec python -m py_compile {} \; 2>&1 | grep -c "SyntaxError" || echo "0")
if [ $SYNTAX_ERRORS -gt 0 ]; then
    add_finding "critical" "Syntax" "$SYNTAX_ERRORS Python syntax error(s)" $((SYNTAX_ERRORS * 10))
    print_status "critical" "$SYNTAX_ERRORS syntax errors found"
else
    print_status "success" "No syntax errors found"
fi

# Check with flake8 if available
if command -v flake8 &> /dev/null; then
    print_status "info" "Running flake8 linting..."
    FLAKE8_OUTPUT=$(flake8 . --count --exit-zero --max-line-length=88 --extend-ignore=E203,W503 --exclude=venv,.venv,__pycache__ 2>/dev/null)
    FLAKE8_ISSUES=$(echo "$FLAKE8_OUTPUT" | tail -1 | grep -oE '^[0-9]+' || echo "0")
    
    if [ "$FLAKE8_ISSUES" -gt 100 ]; then
        add_finding "critical" "Linting" "$FLAKE8_ISSUES linting issues" 10
        print_status "critical" "$FLAKE8_ISSUES linting issues (needs cleanup)"
    elif [ "$FLAKE8_ISSUES" -gt 50 ]; then
        add_finding "warning" "Linting" "$FLAKE8_ISSUES linting issues" 5
        print_status "warning" "$FLAKE8_ISSUES linting issues"
    elif [ "$FLAKE8_ISSUES" -gt 0 ]; then
        add_finding "suggestion" "Linting" "$FLAKE8_ISSUES minor linting issues" 2
        print_status "info" "$FLAKE8_ISSUES minor linting issues"
    else
        print_status "success" "No linting issues"
    fi
fi

# Check for type hints with mypy
if command -v mypy &> /dev/null; then
    print_status "info" "Running type checking..."
    MYPY_OUTPUT=$(mypy . --ignore-missing-imports --no-error-summary 2>&1 | grep -c "error:" || echo "0")
    
    if [ "$MYPY_OUTPUT" -gt 20 ]; then
        add_finding "warning" "Types" "$MYPY_OUTPUT type errors" 8
        print_status "warning" "$MYPY_OUTPUT type errors found"
    elif [ "$MYPY_OUTPUT" -gt 0 ]; then
        add_finding "suggestion" "Types" "$MYPY_OUTPUT type errors" 3
        print_status "info" "$MYPY_OUTPUT type errors found"
    else
        print_status "success" "Type checking passed"
    fi
fi

# 3. Security Analysis
print_header "3. Security Analysis"

# Check for hardcoded secrets
print_status "info" "Scanning for potential secrets..."
SECRET_PATTERNS="(password|api_key|secret|token|apikey|api-key).*=.*['\"][^'\"]+['\"]"
POTENTIAL_SECRETS=$(grep -r -i -E "$SECRET_PATTERNS" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests 2>/dev/null | grep -v -E "(example|test|dummy|fake|mock)" | wc -l | tr -d ' ')

if [ "$POTENTIAL_SECRETS" -gt 0 ]; then
    add_finding "critical" "Security" "$POTENTIAL_SECRETS potential hardcoded secret(s)" $((POTENTIAL_SECRETS * 10))
    print_status "critical" "$POTENTIAL_SECRETS potential hardcoded secrets found"
else
    print_status "success" "No hardcoded secrets detected"
fi

# Check for SQL injection vulnerabilities
print_status "info" "Checking for SQL injection risks..."
SQL_RISKS=$(grep -r -E "(execute|executemany|executescript)\s*\([^)]*%" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')

if [ "$SQL_RISKS" -gt 0 ]; then
    add_finding "critical" "Security" "$SQL_RISKS potential SQL injection risk(s)" $((SQL_RISKS * 8))
    print_status "critical" "$SQL_RISKS potential SQL injection vulnerabilities"
else
    print_status "success" "No SQL injection risks detected"
fi

# Check for use of eval/exec
EVAL_USAGE=$(grep -r -E "(eval|exec)\s*\(" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests 2>/dev/null | wc -l | tr -d ' ')
if [ "$EVAL_USAGE" -gt 0 ]; then
    add_finding "warning" "Security" "$EVAL_USAGE use(s) of eval/exec" $((EVAL_USAGE * 5))
    print_status "warning" "$EVAL_USAGE potentially unsafe eval/exec calls"
fi

# 4. Code Complexity Analysis
print_header "4. Code Complexity Analysis"

# Check for long files
print_status "info" "Checking file lengths..."
LONG_FILES=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -exec wc -l {} \; | awk '$1 > 500 {count++} END {print count+0}')

if [ "$LONG_FILES" -gt 0 ]; then
    add_finding "warning" "Complexity" "$LONG_FILES file(s) over 500 lines" $((LONG_FILES * 3))
    print_status "warning" "$LONG_FILES files exceed 500 lines"
else
    print_status "success" "All files within size limits"
fi

# Check for long functions (simple heuristic)
print_status "info" "Checking function complexity..."
LONG_FUNCTIONS=$(grep -r "^def " . --include="*.py" --exclude-dir=venv --exclude-dir=.venv -A 50 | grep -E "^--$" | wc -l | tr -d ' ')
ESTIMATED_LONG_FUNCS=$((LONG_FUNCTIONS / 10)) # Rough estimate

if [ "$ESTIMATED_LONG_FUNCS" -gt 10 ]; then
    add_finding "warning" "Complexity" "Many potentially complex functions" 5
    print_status "warning" "Several complex functions detected"
elif [ "$ESTIMATED_LONG_FUNCS" -gt 5 ]; then
    add_finding "suggestion" "Complexity" "Some complex functions" 2
    print_status "info" "Some complex functions detected"
else
    print_status "success" "Functions appear well-structured"
fi

# 5. Documentation Check
print_header "5. Documentation Analysis"

# Check for missing docstrings
print_status "info" "Checking documentation coverage..."
TOTAL_FUNCTIONS=$(grep -r "^def " . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests | wc -l | tr -d ' ')
DOCUMENTED_FUNCTIONS=$(grep -r -A1 "^def " . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests | grep -c '"""' || echo "0")

if [ "$TOTAL_FUNCTIONS" -gt 0 ]; then
    DOC_PERCENTAGE=$((DOCUMENTED_FUNCTIONS * 100 / TOTAL_FUNCTIONS))
    print_status "info" "Function documentation: ${DOC_PERCENTAGE}%"
    
    if [ "$DOC_PERCENTAGE" -lt 50 ]; then
        add_finding "warning" "Documentation" "Low documentation coverage: ${DOC_PERCENTAGE}%" 5
        print_status "warning" "Poor documentation coverage"
    elif [ "$DOC_PERCENTAGE" -lt 80 ]; then
        add_finding "suggestion" "Documentation" "Documentation coverage: ${DOC_PERCENTAGE}%" 2
        print_status "info" "Documentation could be improved"
    else
        print_status "success" "Good documentation coverage"
    fi
fi

# Check README
if [ ! -f "README.md" ]; then
    add_finding "warning" "Documentation" "Missing README.md" 3
    print_status "warning" "No README.md found"
else
    README_LINES=$(wc -l < README.md)
    if [ "$README_LINES" -lt 50 ]; then
        add_finding "suggestion" "Documentation" "README.md seems minimal" 1
        print_status "info" "README.md could be more comprehensive"
    else
        print_status "success" "README.md present"
    fi
fi

# 6. Dependencies Check
print_header "6. Dependencies Analysis"

# Check for requirements.txt
if [ -f "requirements.txt" ]; then
    print_status "info" "Checking dependencies..."
    
    # Count total dependencies
    TOTAL_DEPS=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l | tr -d ' ')
    print_status "info" "Total dependencies: $TOTAL_DEPS"
    
    if [ "$TOTAL_DEPS" -gt 50 ]; then
        add_finding "warning" "Dependencies" "High number of dependencies: $TOTAL_DEPS" 3
        print_status "warning" "Consider reducing dependencies"
    fi
    
    # Check for outdated packages (if pip-outdated is available)
    if command -v pip &> /dev/null; then
        OUTDATED=$(pip list --outdated 2>/dev/null | tail -n +3 | wc -l | tr -d ' ')
        if [ "$OUTDATED" -gt 10 ]; then
            add_finding "warning" "Dependencies" "$OUTDATED outdated packages" 5
            print_status "warning" "$OUTDATED packages need updating"
        elif [ "$OUTDATED" -gt 0 ]; then
            add_finding "suggestion" "Dependencies" "$OUTDATED outdated packages" 2
            print_status "info" "$OUTDATED packages could be updated"
        fi
    fi
else
    add_finding "critical" "Dependencies" "Missing requirements.txt" 10
    print_status "critical" "No requirements.txt found"
fi

# 7. Common Bug Patterns
print_header "7. Common Bug Pattern Detection"

# Check for common Python pitfalls
print_status "info" "Scanning for common bug patterns..."

# Mutable default arguments
MUTABLE_DEFAULTS=$(grep -r "def.*=\[\]" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
if [ "$MUTABLE_DEFAULTS" -gt 0 ]; then
    add_finding "warning" "Bugs" "$MUTABLE_DEFAULTS mutable default argument(s)" $((MUTABLE_DEFAULTS * 3))
    print_status "warning" "$MUTABLE_DEFAULTS mutable default arguments found"
fi

# Bare except clauses
BARE_EXCEPT=$(grep -r "except:" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
if [ "$BARE_EXCEPT" -gt 0 ]; then
    add_finding "warning" "Bugs" "$BARE_EXCEPT bare except clause(s)" $((BARE_EXCEPT * 2))
    print_status "warning" "$BARE_EXCEPT bare except clauses found"
fi

# TODO/FIXME comments
TODOS=$(grep -r -i "TODO\|FIXME\|HACK\|BUG" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
if [ "$TODOS" -gt 10 ]; then
    add_finding "warning" "Bugs" "$TODOS TODO/FIXME comments" 3
    print_status "warning" "$TODOS unresolved TODO/FIXME comments"
elif [ "$TODOS" -gt 0 ]; then
    add_finding "suggestion" "Bugs" "$TODOS TODO/FIXME comments" 1
    print_status "info" "$TODOS TODO/FIXME comments found"
else
    print_status "success" "No TODO/FIXME comments"
fi

# Ensure score doesn't go below 0
if [ $TOTAL_SCORE -lt 0 ]; then
    TOTAL_SCORE=0
fi

# Generate final report
print_header "📊 Health Check Summary"

# Calculate grade
if [ $TOTAL_SCORE -ge 90 ]; then
    GRADE="A"
    GRADE_COLOR=$GREEN
    HEALTH_STATUS="Excellent"
elif [ $TOTAL_SCORE -ge 80 ]; then
    GRADE="B"
    GRADE_COLOR=$GREEN
    HEALTH_STATUS="Good"
elif [ $TOTAL_SCORE -ge 70 ]; then
    GRADE="C"
    GRADE_COLOR=$YELLOW
    HEALTH_STATUS="Fair"
elif [ $TOTAL_SCORE -ge 60 ]; then
    GRADE="D"
    GRADE_COLOR=$YELLOW
    HEALTH_STATUS="Poor"
else
    GRADE="F"
    GRADE_COLOR=$RED
    HEALTH_STATUS="Critical"
fi

# Display score
echo -e "${BOLD}Overall Health Score: ${GRADE_COLOR}${TOTAL_SCORE}/100 (${GRADE})${NC}"
echo -e "${BOLD}Health Status: ${GRADE_COLOR}${HEALTH_STATUS}${NC}\n"

# Display issue summary
echo -e "${BOLD}Issues Found:${NC}"
echo -e "  ${RED}● Critical Issues: ${CRITICAL_ISSUES}${NC}"
echo -e "  ${YELLOW}● Warnings: ${WARNINGS}${NC}"
echo -e "  ${CYAN}● Suggestions: ${SUGGESTIONS}${NC}"
echo -e "  ${BOLD}━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}Total: ${ISSUES_FOUND}${NC}\n"

# Display critical findings
if [ ${#CRITICAL_FINDINGS[@]} -gt 0 ]; then
    echo -e "${RED}${BOLD}Critical Issues Requiring Immediate Attention:${NC}"
    for finding in "${CRITICAL_FINDINGS[@]}"; do
        echo -e "  ${RED}⛔ $finding${NC}"
    done
    echo
fi

# Display warnings
if [ ${#WARNING_FINDINGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}Warnings to Address:${NC}"
    for finding in "${WARNING_FINDINGS[@]}"; do
        echo -e "  ${YELLOW}⚠ $finding${NC}"
    done
    echo
fi

# Display suggestions
if [ ${#FINDINGS[@]} -gt 0 ]; then
    echo -e "${CYAN}${BOLD}Suggestions for Improvement:${NC}"
    for finding in "${FINDINGS[@]}"; do
        echo -e "  ${CYAN}💡 $finding${NC}"
    done
    echo
fi

# Recommendations
print_header "🔧 Recommendations"

if [ $TOTAL_SCORE -lt 60 ]; then
    echo -e "${RED}${BOLD}⚠️  URGENT: This codebase needs immediate attention!${NC}\n"
    echo -e "${BOLD}Priority Actions:${NC}"
    echo -e "1. ${RED}Fix all failing tests immediately${NC}"
    echo -e "2. ${RED}Address security vulnerabilities${NC}"
    echo -e "3. ${YELLOW}Resolve critical bugs${NC}"
    echo -e "4. ${YELLOW}Improve test coverage${NC}"
    echo -e "5. ${CYAN}Refactor complex code${NC}"
    echo
    echo -e "${BOLD}Recommended: Allocate 2-3 days for thorough debugging${NC}"
elif [ $TOTAL_SCORE -lt 80 ]; then
    echo -e "${YELLOW}${BOLD}This codebase needs some attention.${NC}\n"
    echo -e "${BOLD}Recommended Actions:${NC}"
    echo -e "1. ${YELLOW}Address warning-level issues${NC}"
    echo -e "2. ${YELLOW}Improve test coverage to 80%+${NC}"
    echo -e "3. ${CYAN}Update documentation${NC}"
    echo -e "4. ${CYAN}Refactor complex functions${NC}"
    echo
    echo -e "${BOLD}Recommended: Schedule 1 day for improvements${NC}"
else
    echo -e "${GREEN}${BOLD}✨ Codebase is in good health!${NC}\n"
    echo -e "${BOLD}Maintenance Tasks:${NC}"
    echo -e "1. ${GREEN}Keep dependencies updated${NC}"
    echo -e "2. ${GREEN}Maintain test coverage${NC}"
    echo -e "3. ${CYAN}Address any TODO comments${NC}"
    echo
    echo -e "${BOLD}Keep up the excellent work!${NC}"
fi

# Generate detailed report file
REPORT_FILE="code_health_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "Code Health Report - $(date)"
    echo "================================"
    echo "Overall Score: $TOTAL_SCORE/100 ($GRADE)"
    echo "Health Status: $HEALTH_STATUS"
    echo ""
    echo "Issues Summary:"
    echo "- Critical: $CRITICAL_ISSUES"
    echo "- Warnings: $WARNINGS"
    echo "- Suggestions: $SUGGESTIONS"
    echo ""
    echo "Detailed Findings:"
    for finding in "${CRITICAL_FINDINGS[@]}" "${WARNING_FINDINGS[@]}" "${FINDINGS[@]}"; do
        echo "- $finding"
    done
} > "$REPORT_FILE"

echo
print_status "success" "Detailed report saved to: $REPORT_FILE"

# Exit with appropriate code
if [ $CRITICAL_ISSUES -gt 0 ]; then
    exit 2  # Critical issues found
elif [ $WARNINGS -gt 0 ]; then
    exit 1  # Warnings found
else
    exit 0  # All good
fi