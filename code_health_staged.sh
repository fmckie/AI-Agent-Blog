#!/bin/bash
# code_health_staged.sh - Staged code health analysis with early stopping
# Runs health checks in stages from most to least critical

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
STAGE_FAILED=false
CONTINUE_ON_FAIL=false

# Store detailed findings
declare -a CRITICAL_FINDINGS
declare -a WARNING_FINDINGS
declare -a SUGGESTION_FINDINGS

# Stage tracking
COMPLETED_STAGES=0
TOTAL_STAGES=7

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --continue|-c)
            CONTINUE_ON_FAIL=true
            shift
            ;;
        --quick|-q)
            QUICK_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --continue, -c    Continue even if critical issues found"
            echo "  --quick, -q       Quick mode (skip slow checks)"
            echo "  --verbose, -v     Verbose output"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Stages:"
            echo "  1. Critical Checks (syntax, test failures)"
            echo "  2. Security Analysis"
            echo "  3. Code Quality"
            echo "  4. Bug Patterns"
            echo "  5. Complexity Analysis"
            echo "  6. Dependencies"
            echo "  7. Documentation"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print colored headers
print_header() {
    echo -e "\n${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  Stage $1: $2${NC}"
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
        "stage")
            echo -e "${MAGENTA}▶ ${message}${NC}"
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
            SUGGESTION_FINDINGS+=("[$category] $message")
            SUGGESTIONS=$((SUGGESTIONS + 1))
            TOTAL_SCORE=$((TOTAL_SCORE - penalty))
            ;;
    esac
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

# Function to check if we should continue
should_continue() {
    if [ $CRITICAL_ISSUES -gt 0 ] && [ "$CONTINUE_ON_FAIL" = false ]; then
        echo -e "\n${RED}${BOLD}⛔ Critical issues found! Stopping analysis.${NC}"
        echo -e "${YELLOW}Use --continue to run all stages regardless of critical issues.${NC}"
        return 1
    fi
    return 0
}

# Function to show stage progress
show_progress() {
    local percent=$((COMPLETED_STAGES * 100 / TOTAL_STAGES))
    echo -e "\n${CYAN}Progress: [$COMPLETED_STAGES/$TOTAL_STAGES] ${percent}% complete${NC}"
}

# Start health check
clear
echo -e "${BLUE}${BOLD}🏥 Staged Code Health Check - SEO Content Automation System${NC}"
echo -e "${CYAN}Running analysis in stages with early stopping...${NC}\n"

# Track start time
START_TIME=$(date +%s)

# Check if we're in the right directory
if [ ! -f "pytest.ini" ] || [ ! -d "tests" ]; then
    print_status "error" "Not in project root directory!"
    exit 1
fi

# ============================================================================
# STAGE 1: Critical Checks (Must Pass)
# ============================================================================
print_header "1/7" "Critical Checks (Syntax & Tests)"
print_status "stage" "Checking for critical issues that block execution..."

# Python syntax check
print_status "info" "Checking Python syntax..."
SYNTAX_OUTPUT=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -print0 | xargs -0 -n1 python -m py_compile 2>&1)
SYNTAX_ERRORS=$(echo "$SYNTAX_OUTPUT" | grep -c "SyntaxError" || echo "0")

if [ $SYNTAX_ERRORS -gt 0 ]; then
    add_finding "critical" "Syntax" "$SYNTAX_ERRORS file(s) with syntax errors" 20
    print_status "critical" "$SYNTAX_ERRORS syntax errors found!"
    if [ "$VERBOSE" = true ]; then
        echo -e "${RED}Syntax errors in:${NC}"
        echo "$SYNTAX_OUTPUT" | grep -B1 "SyntaxError" | head -10
    fi
else
    print_status "success" "No syntax errors found"
fi

# Basic import check
print_status "info" "Checking critical imports..."
IMPORT_ERRORS=$(python -c "import sys; sys.path.insert(0, '.'); import main" 2>&1 | grep -c "Error" || echo "0")
if [ $IMPORT_ERRORS -gt 0 ]; then
    add_finding "critical" "Imports" "Main module has import errors" 15
    print_status "critical" "Critical import errors detected"
else
    print_status "success" "Core imports working"
fi

# Quick test check (only critical tests)
if [ "$QUICK_MODE" != true ]; then
    print_status "info" "Running critical tests..."
    TEST_OUTPUT=$(pytest tests/test_basic.py -x -q 2>&1)
    TEST_EXIT=$?
    
    if [ $TEST_EXIT -ne 0 ]; then
        add_finding "critical" "Tests" "Basic tests failing" 15
        print_status "critical" "Critical test failures!"
    else
        print_status "success" "Basic tests passing"
    fi
fi

COMPLETED_STAGES=$((COMPLETED_STAGES + 1))
show_progress

# Check if we should continue
if ! should_continue; then
    STAGE_FAILED=true
    # Jump to final report
    exec 3>&1
    exec 1>&3
    exec 2>&3
else
    print_status "success" "Stage 1 complete - No blocking issues"
fi

# ============================================================================
# STAGE 2: Security Analysis (High Priority)
# ============================================================================
if [ "$STAGE_FAILED" = false ]; then
    print_header "2/7" "Security Analysis"
    print_status "stage" "Scanning for security vulnerabilities..."
    
    # Hardcoded secrets check
    print_status "info" "Scanning for hardcoded secrets..."
    SECRET_PATTERNS="(password|api_key|secret|token|apikey|api-key).*=.*['\"][^'\"]+['\"]"
    SECRETS_FOUND=$(grep -r -i -E "$SECRET_PATTERNS" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests 2>/dev/null | grep -v -E "(example|test|dummy|fake|mock)" | wc -l | tr -d ' ')
    
    if [ "$SECRETS_FOUND" -gt 0 ]; then
        add_finding "critical" "Security" "$SECRETS_FOUND potential hardcoded secret(s)" 10
        print_status "critical" "$SECRETS_FOUND potential secrets exposed!"
        if [ "$VERBOSE" = true ]; then
            echo -e "${RED}Found in files:${NC}"
            grep -r -i -E "$SECRET_PATTERNS" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv | grep -v -E "(example|test|dummy)" | cut -d: -f1 | sort -u | head -5
        fi
    else
        print_status "success" "No hardcoded secrets detected"
    fi
    
    # SQL injection check
    print_status "info" "Checking for SQL injection vulnerabilities..."
    SQL_RISKS=$(grep -r -E "(execute|executemany|executescript)\s*\([^)]*%" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$SQL_RISKS" -gt 0 ]; then
        add_finding "critical" "Security" "$SQL_RISKS potential SQL injection risk(s)" 8
        print_status "critical" "$SQL_RISKS SQL injection vulnerabilities!"
    else
        print_status "success" "No SQL injection risks found"
    fi
    
    # eval/exec usage
    EVAL_USAGE=$(grep -r -E "eval\s*\(|exec\s*\(" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests 2>/dev/null | wc -l | tr -d ' ')
    if [ "$EVAL_USAGE" -gt 0 ]; then
        add_finding "warning" "Security" "$EVAL_USAGE use(s) of eval/exec" 5
        print_status "warning" "$EVAL_USAGE potentially unsafe eval/exec calls"
    fi
    
    COMPLETED_STAGES=$((COMPLETED_STAGES + 1))
    show_progress
    
    if ! should_continue; then
        STAGE_FAILED=true
    else
        print_status "success" "Stage 2 complete - Security check passed"
    fi
fi

# ============================================================================
# STAGE 3: Code Quality Analysis
# ============================================================================
if [ "$STAGE_FAILED" = false ]; then
    print_header "3/7" "Code Quality Analysis"
    print_status "stage" "Analyzing code quality metrics..."
    
    # Linting with flake8
    if command -v flake8 &> /dev/null; then
        print_status "info" "Running flake8 linter..."
        FLAKE8_OUTPUT=$(flake8 . --count --exit-zero --max-line-length=88 --extend-ignore=E203,W503 --exclude=venv,.venv,__pycache__ 2>/dev/null)
        FLAKE8_ISSUES=$(echo "$FLAKE8_OUTPUT" | tail -1 | grep -oE '^[0-9]+' || echo "0")
        
        if [ "$FLAKE8_ISSUES" -gt 100 ]; then
            add_finding "warning" "Quality" "$FLAKE8_ISSUES linting issues (needs cleanup)" 10
            print_status "warning" "$FLAKE8_ISSUES linting issues found"
        elif [ "$FLAKE8_ISSUES" -gt 50 ]; then
            add_finding "warning" "Quality" "$FLAKE8_ISSUES linting issues" 5
            print_status "warning" "$FLAKE8_ISSUES linting issues"
        elif [ "$FLAKE8_ISSUES" -gt 0 ]; then
            add_finding "suggestion" "Quality" "$FLAKE8_ISSUES minor linting issues" 2
            print_status "info" "$FLAKE8_ISSUES minor issues"
        else
            print_status "success" "No linting issues"
        fi
    else
        print_status "info" "Skipping flake8 (not installed)"
    fi
    
    # Type checking with mypy
    if command -v mypy &> /dev/null && [ "$QUICK_MODE" != true ]; then
        print_status "info" "Running type checker..."
        MYPY_ERRORS=$(mypy . --ignore-missing-imports --no-error-summary 2>&1 | grep -c "error:" || echo "0")
        
        if [ "$MYPY_ERRORS" -gt 20 ]; then
            add_finding "warning" "Types" "$MYPY_ERRORS type errors" 8
            print_status "warning" "$MYPY_ERRORS type errors"
        elif [ "$MYPY_ERRORS" -gt 0 ]; then
            add_finding "suggestion" "Types" "$MYPY_ERRORS type errors" 3
            print_status "info" "$MYPY_ERRORS type errors"
        else
            print_status "success" "Type checking passed"
        fi
    fi
    
    COMPLETED_STAGES=$((COMPLETED_STAGES + 1))
    show_progress
    print_status "success" "Stage 3 complete"
fi

# ============================================================================
# STAGE 4: Bug Pattern Detection
# ============================================================================
if [ "$STAGE_FAILED" = false ]; then
    print_header "4/7" "Bug Pattern Detection"
    print_status "stage" "Scanning for common bug patterns..."
    
    # Mutable default arguments
    print_status "info" "Checking for mutable default arguments..."
    MUTABLE_DEFAULTS=$(grep -r "def.*=\[\]\|def.*={}" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MUTABLE_DEFAULTS" -gt 0 ]; then
        add_finding "warning" "Bugs" "$MUTABLE_DEFAULTS mutable default argument(s)" 3
        print_status "warning" "$MUTABLE_DEFAULTS mutable defaults found"
    else
        print_status "success" "No mutable defaults"
    fi
    
    # Bare except clauses
    print_status "info" "Checking for bare except clauses..."
    BARE_EXCEPT=$(grep -r "except:" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
    if [ "$BARE_EXCEPT" -gt 0 ]; then
        add_finding "warning" "Bugs" "$BARE_EXCEPT bare except clause(s)" 2
        print_status "warning" "$BARE_EXCEPT bare excepts found"
    else
        print_status "success" "No bare except clauses"
    fi
    
    # Unused imports
    print_status "info" "Checking for unused code..."
    if command -v autoflake &> /dev/null; then
        UNUSED=$(autoflake --check -r . --exclude=venv,__pycache__ 2>/dev/null | grep -c "would remove" || echo "0")
        if [ "$UNUSED" -gt 10 ]; then
            add_finding "suggestion" "Bugs" "$UNUSED unused imports/variables" 2
            print_status "info" "$UNUSED unused items found"
        fi
    fi
    
    COMPLETED_STAGES=$((COMPLETED_STAGES + 1))
    show_progress
    print_status "success" "Stage 4 complete"
fi

# ============================================================================
# STAGE 5: Complexity Analysis
# ============================================================================
if [ "$STAGE_FAILED" = false ] && [ "$QUICK_MODE" != true ]; then
    print_header "5/7" "Complexity Analysis"
    print_status "stage" "Analyzing code complexity..."
    
    # File length check
    print_status "info" "Checking file sizes..."
    LONG_FILES=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -exec wc -l {} \; | awk '$1 > 500 {count++} END {print count+0}')
    
    if [ "$LONG_FILES" -gt 0 ]; then
        add_finding "warning" "Complexity" "$LONG_FILES file(s) over 500 lines" 3
        print_status "warning" "$LONG_FILES large files found"
        if [ "$VERBOSE" = true ]; then
            echo -e "${YELLOW}Large files:${NC}"
            find . -name "*.py" -not -path "./venv/*" -exec wc -l {} \; | awk '$1 > 500 {print $2}' | head -5
        fi
    else
        print_status "success" "All files within size limits"
    fi
    
    # Cyclomatic complexity with radon
    if command -v radon &> /dev/null; then
        print_status "info" "Measuring cyclomatic complexity..."
        COMPLEX_FUNCTIONS=$(radon cc . -s -j --exclude="venv/*,.venv/*" 2>/dev/null | python -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for f in data.values() for func in f if func['complexity'] > 10))" 2>/dev/null || echo "0")
        
        if [ "$COMPLEX_FUNCTIONS" -gt 5 ]; then
            add_finding "warning" "Complexity" "$COMPLEX_FUNCTIONS highly complex functions" 5
            print_status "warning" "$COMPLEX_FUNCTIONS complex functions"
        elif [ "$COMPLEX_FUNCTIONS" -gt 0 ]; then
            add_finding "suggestion" "Complexity" "$COMPLEX_FUNCTIONS complex functions" 2
            print_status "info" "$COMPLEX_FUNCTIONS complex functions"
        else
            print_status "success" "Low complexity maintained"
        fi
    fi
    
    COMPLETED_STAGES=$((COMPLETED_STAGES + 1))
    show_progress
    print_status "success" "Stage 5 complete"
fi

# ============================================================================
# STAGE 6: Dependencies Check
# ============================================================================
if [ "$STAGE_FAILED" = false ]; then
    print_header "6/7" "Dependencies Analysis"
    print_status "stage" "Checking project dependencies..."
    
    # Requirements file check
    if [ -f "requirements.txt" ]; then
        print_status "info" "Analyzing requirements.txt..."
        TOTAL_DEPS=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l | tr -d ' ')
        print_status "info" "Total dependencies: $TOTAL_DEPS"
        
        if [ "$TOTAL_DEPS" -gt 50 ]; then
            add_finding "warning" "Dependencies" "High dependency count: $TOTAL_DEPS" 3
            print_status "warning" "Consider reducing dependencies"
        fi
        
        # Check for version pinning
        UNPINNED=$(grep -v "^#" requirements.txt | grep -v "^$" | grep -v "==" | wc -l | tr -d ' ')
        if [ "$UNPINNED" -gt 5 ]; then
            add_finding "warning" "Dependencies" "$UNPINNED unpinned dependencies" 4
            print_status "warning" "$UNPINNED dependencies without version pins"
        fi
    else
        add_finding "critical" "Dependencies" "Missing requirements.txt" 10
        print_status "critical" "No requirements.txt found!"
    fi
    
    # Check for security vulnerabilities
    if command -v safety &> /dev/null && [ "$QUICK_MODE" != true ]; then
        print_status "info" "Checking for known vulnerabilities..."
        VULNS=$(safety check --json 2>/dev/null | python -c "import sys, json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo "0")
        
        if [ "$VULNS" -gt 0 ]; then
            add_finding "critical" "Dependencies" "$VULNS known vulnerabilities" 15
            print_status "critical" "$VULNS security vulnerabilities in dependencies!"
        else
            print_status "success" "No known vulnerabilities"
        fi
    fi
    
    COMPLETED_STAGES=$((COMPLETED_STAGES + 1))
    show_progress
    print_status "success" "Stage 6 complete"
fi

# ============================================================================
# STAGE 7: Documentation Check
# ============================================================================
if [ "$STAGE_FAILED" = false ] && [ "$QUICK_MODE" != true ]; then
    print_header "7/7" "Documentation Analysis"
    print_status "stage" "Checking documentation quality..."
    
    # Docstring coverage
    print_status "info" "Analyzing docstring coverage..."
    TOTAL_FUNCTIONS=$(grep -r "^def " . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests | wc -l | tr -d ' ')
    DOCUMENTED=$(grep -r -A1 "^def " . --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests | grep -c '"""' || echo "0")
    
    if [ "$TOTAL_FUNCTIONS" -gt 0 ]; then
        DOC_PERCENT=$((DOCUMENTED * 100 / TOTAL_FUNCTIONS))
        print_status "info" "Docstring coverage: ${DOC_PERCENT}%"
        
        if [ "$DOC_PERCENT" -lt 50 ]; then
            add_finding "warning" "Documentation" "Poor docstring coverage: ${DOC_PERCENT}%" 5
            print_status "warning" "Low documentation coverage"
        elif [ "$DOC_PERCENT" -lt 80 ]; then
            add_finding "suggestion" "Documentation" "Docstring coverage: ${DOC_PERCENT}%" 2
            print_status "info" "Documentation could be improved"
        else
            print_status "success" "Good documentation coverage"
        fi
    fi
    
    # TODO/FIXME comments
    print_status "info" "Checking for TODO/FIXME comments..."
    TODOS=$(grep -r -i "TODO\|FIXME\|HACK\|XXX" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
    if [ "$TODOS" -gt 10 ]; then
        add_finding "warning" "Documentation" "$TODOS TODO/FIXME comments" 3
        print_status "warning" "$TODOS unresolved TODOs"
    elif [ "$TODOS" -gt 0 ]; then
        add_finding "suggestion" "Documentation" "$TODOS TODO/FIXME comments" 1
        print_status "info" "$TODOS TODOs found"
    else
        print_status "success" "No TODO comments"
    fi
    
    COMPLETED_STAGES=$((COMPLETED_STAGES + 1))
    show_progress
    print_status "success" "Stage 7 complete"
fi

# ============================================================================
# Final Report Generation
# ============================================================================

# Ensure score doesn't go below 0
if [ $TOTAL_SCORE -lt 0 ]; then
    TOTAL_SCORE=0
fi

# Calculate execution time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Generate grade
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

# Display final report
echo -e "\n${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  📊 Health Check Summary${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Display score
echo -e "${BOLD}Overall Health Score: ${GRADE_COLOR}${TOTAL_SCORE}/100 (${GRADE})${NC}"
echo -e "${BOLD}Health Status: ${GRADE_COLOR}${HEALTH_STATUS}${NC}"
echo -e "${BOLD}Analysis Time: ${DURATION}s${NC}\n"

# Display issue summary
echo -e "${BOLD}Issues Found:${NC}"
echo -e "  ${RED}● Critical Issues: ${CRITICAL_ISSUES}${NC}"
echo -e "  ${YELLOW}● Warnings: ${WARNINGS}${NC}"
echo -e "  ${CYAN}● Suggestions: ${SUGGESTIONS}${NC}"
echo -e "  ${BOLD}━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}Total: ${ISSUES_FOUND}${NC}\n"

# Show what was skipped
if [ "$STAGE_FAILED" = true ]; then
    SKIPPED=$((TOTAL_STAGES - COMPLETED_STAGES))
    echo -e "${YELLOW}${BOLD}⚠ Analysis stopped early due to critical issues${NC}"
    echo -e "${YELLOW}Skipped $SKIPPED stages. Use --continue to run all stages.${NC}\n"
fi

# Display critical findings
if [ ${#CRITICAL_FINDINGS[@]} -gt 0 ]; then
    echo -e "${RED}${BOLD}Critical Issues (Fix Immediately):${NC}"
    for finding in "${CRITICAL_FINDINGS[@]}"; do
        echo -e "  ${RED}⛔ $finding${NC}"
    done
    echo
fi

# Display warnings (only first 5 if many)
if [ ${#WARNING_FINDINGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}Warnings:${NC}"
    count=0
    for finding in "${WARNING_FINDINGS[@]}"; do
        if [ $count -lt 5 ] || [ "$VERBOSE" = true ]; then
            echo -e "  ${YELLOW}⚠ $finding${NC}"
        fi
        count=$((count + 1))
    done
    if [ $count -gt 5 ] && [ "$VERBOSE" != true ]; then
        echo -e "  ${YELLOW}... and $((count - 5)) more warnings (use -v to see all)${NC}"
    fi
    echo
fi

# Display suggestions (only in verbose mode)
if [ ${#SUGGESTION_FINDINGS[@]} -gt 0 ] && [ "$VERBOSE" = true ]; then
    echo -e "${CYAN}${BOLD}Suggestions:${NC}"
    for finding in "${SUGGESTION_FINDINGS[@]}"; do
        echo -e "  ${CYAN}💡 $finding${NC}"
    done
    echo
fi

# Quick fix commands
if [ $CRITICAL_ISSUES -gt 0 ] || [ $WARNINGS -gt 5 ]; then
    echo -e "${BOLD}🔧 Quick Fix Commands:${NC}"
    
    if grep -q "syntax errors" <<< "${CRITICAL_FINDINGS[@]}"; then
        echo -e "  ${CYAN}python -m py_compile \$(find . -name '*.py')${NC}  # Find syntax errors"
    fi
    
    if grep -q "import errors" <<< "${CRITICAL_FINDINGS[@]}"; then
        echo -e "  ${CYAN}python -c 'import main'${NC}  # Debug import issues"
    fi
    
    if grep -q "hardcoded secret" <<< "${CRITICAL_FINDINGS[@]}"; then
        echo -e "  ${CYAN}grep -r \"password.*=\" . --include=\"*.py\"${NC}  # Find secrets"
    fi
    
    if [ $WARNINGS -gt 0 ]; then
        echo -e "  ${CYAN}flake8 . --max-line-length=88${NC}  # Check code style"
        echo -e "  ${CYAN}black .${NC}  # Auto-format code"
    fi
    echo
fi

# Recommendations based on score
echo -e "${BOLD}📋 Recommendation:${NC}"
if [ $TOTAL_SCORE -lt 60 ]; then
    echo -e "${RED}${BOLD}⚠️  URGENT: This codebase needs immediate debugging!${NC}"
    echo -e "Estimated time needed: ${BOLD}2-3 days${NC}"
    echo -e "1. Fix all syntax errors and import issues"
    echo -e "2. Address security vulnerabilities"
    echo -e "3. Fix failing tests"
elif [ $TOTAL_SCORE -lt 80 ]; then
    echo -e "${YELLOW}${BOLD}This codebase needs attention.${NC}"
    echo -e "Estimated time needed: ${BOLD}1 day${NC}"
    echo -e "1. Address critical warnings"
    echo -e "2. Improve code quality"
    echo -e "3. Update documentation"
else
    echo -e "${GREEN}${BOLD}✨ Codebase is healthy!${NC}"
    echo -e "Continue with regular maintenance."
fi

# Save report
REPORT_FILE="health_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "Code Health Report - $(date)"
    echo "Score: $TOTAL_SCORE/100 ($GRADE)"
    echo "Critical: $CRITICAL_ISSUES, Warnings: $WARNINGS, Suggestions: $SUGGESTIONS"
    echo ""
    echo "Findings:"
    for finding in "${CRITICAL_FINDINGS[@]}" "${WARNING_FINDINGS[@]}" "${SUGGESTION_FINDINGS[@]}"; do
        echo "- $finding"
    done
} > "$REPORT_FILE"

echo -e "\n${GREEN}Report saved to: $REPORT_FILE${NC}"

# Exit with appropriate code
if [ $CRITICAL_ISSUES -gt 0 ]; then
    exit 2  # Critical issues
elif [ $WARNINGS -gt 0 ]; then
    exit 1  # Warnings
else
    exit 0  # All good
fi