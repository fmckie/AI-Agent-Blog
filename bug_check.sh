#!/bin/bash
# bug_check.sh - Focused bug and error detection for Python codebase

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Initialize counters
TOTAL_ISSUES=0
SYNTAX_ERRORS=0
IMPORT_ERRORS=0
TYPE_ERRORS=0
LOGIC_BUGS=0

echo -e "${BLUE}${BOLD}🐛 Bug Detection Scan - SEO Content Automation${NC}"
echo -e "${CYAN}Scanning for bugs, errors, and potential issues...${NC}\n"

# Function to print status messages
print_status() {
    local status=$1
    local message=$2
    case $status in
        "info") echo -e "${CYAN}ℹ ${message}${NC}" ;;
        "success") echo -e "${GREEN}✓ ${message}${NC}" ;;
        "error") echo -e "${RED}✗ ${message}${NC}" ;;
        "warning") echo -e "${YELLOW}⚠ ${message}${NC}" ;;
    esac
}

# ============================================================================
# 1. SYNTAX ERRORS CHECK
# ============================================================================
echo -e "${BLUE}${BOLD}[1/7] Checking for Syntax Errors...${NC}"
SYNTAX_OUTPUT=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -print0 | xargs -0 -n1 python -m py_compile 2>&1)
SYNTAX_ERRORS=$(echo "$SYNTAX_OUTPUT" | grep -c "SyntaxError" || echo "0")

if [ $SYNTAX_ERRORS -gt 0 ]; then
    print_status "error" "$SYNTAX_ERRORS syntax error(s) found!"
    echo "$SYNTAX_OUTPUT" | grep -B2 "SyntaxError"
    TOTAL_ISSUES=$((TOTAL_ISSUES + SYNTAX_ERRORS))
else
    print_status "success" "No syntax errors"
fi
echo

# ============================================================================
# 2. IMPORT ERRORS CHECK
# ============================================================================
echo -e "${BLUE}${BOLD}[2/7] Checking for Import Errors...${NC}"
# Check main imports
for module in main config workflow agents tools; do
    if python -c "import $module" 2>&1 | grep -q "Error"; then
        print_status "error" "Import error in $module.py"
        python -c "import $module" 2>&1 | grep "Error" | head -5
        IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
        TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
    else
        print_status "success" "$module.py imports correctly"
    fi
done
echo

# ============================================================================
# 3. TYPE ERRORS CHECK (if mypy is available)
# ============================================================================
echo -e "${BLUE}${BOLD}[3/7] Checking for Type Errors...${NC}"
if command -v mypy &> /dev/null; then
    TYPE_OUTPUT=$(mypy . --ignore-missing-imports --no-error-summary 2>&1)
    TYPE_ERRORS=$(echo "$TYPE_OUTPUT" | grep -c "error:" || echo "0")
    
    if [ $TYPE_ERRORS -gt 0 ]; then
        print_status "warning" "$TYPE_ERRORS type error(s) found"
        echo -e "${YELLOW}Top type errors:${NC}"
        echo "$TYPE_OUTPUT" | grep "error:" | head -10
        TOTAL_ISSUES=$((TOTAL_ISSUES + TYPE_ERRORS))
    else
        print_status "success" "No type errors"
    fi
else
    print_status "info" "Skipping (mypy not installed)"
fi
echo

# ============================================================================
# 4. COMMON BUG PATTERNS
# ============================================================================
echo -e "${BLUE}${BOLD}[4/7] Checking for Common Bug Patterns...${NC}"

# Mutable default arguments
MUTABLE_DEFAULTS=$(grep -r "def.*=\[\]\|def.*={}" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
if [ "$MUTABLE_DEFAULTS" -gt 0 ]; then
    print_status "warning" "$MUTABLE_DEFAULTS mutable default argument(s)"
    echo -e "${YELLOW}Files with mutable defaults:${NC}"
    grep -r "def.*=\[\]\|def.*={}" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv -l | head -5
    LOGIC_BUGS=$((LOGIC_BUGS + MUTABLE_DEFAULTS))
    TOTAL_ISSUES=$((TOTAL_ISSUES + MUTABLE_DEFAULTS))
fi

# Bare except clauses
BARE_EXCEPT=$(grep -r "except:" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv 2>/dev/null | wc -l | tr -d ' ')
if [ "$BARE_EXCEPT" -gt 0 ]; then
    print_status "warning" "$BARE_EXCEPT bare except clause(s)"
    echo -e "${YELLOW}Files with bare excepts:${NC}"
    grep -r "except:" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv -l | head -5
    LOGIC_BUGS=$((LOGIC_BUGS + BARE_EXCEPT))
    TOTAL_ISSUES=$((TOTAL_ISSUES + BARE_EXCEPT))
fi

# Missing error handling in async functions
UNHANDLED_ASYNC=$(grep -r "async def" . --include="*.py" --exclude-dir=venv --exclude-dir=.venv -A 10 | grep -B 10 "await" | grep -v "try:" | grep -c "async def" || echo "0")
if [ "$UNHANDLED_ASYNC" -gt 5 ]; then
    print_status "info" "Many async functions without explicit error handling"
fi
echo

# ============================================================================
# 5. MISSING DEPENDENCIES CHECK
# ============================================================================
echo -e "${BLUE}${BOLD}[5/7] Checking for Missing Dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    # Check if all imports in code are in requirements
    MISSING_DEPS=0
    for import_name in $(grep -h "^import\|^from" *.py | awk '{print $2}' | cut -d. -f1 | sort -u); do
        if [[ ! "$import_name" =~ ^(os|sys|json|pathlib|typing|datetime|time|re|asyncio|functools|dataclasses)$ ]]; then
            if ! grep -q "$import_name" requirements.txt 2>/dev/null; then
                if [ -f "$import_name.py" ] || [ -d "$import_name" ]; then
                    continue  # It's a local module
                fi
                print_status "warning" "Import '$import_name' not found in requirements.txt"
                MISSING_DEPS=$((MISSING_DEPS + 1))
            fi
        fi
    done
    
    if [ $MISSING_DEPS -eq 0 ]; then
        print_status "success" "All imports accounted for"
    else
        TOTAL_ISSUES=$((TOTAL_ISSUES + MISSING_DEPS))
    fi
else
    print_status "error" "requirements.txt not found!"
    TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
fi
echo

# ============================================================================
# 6. PYTEST CHECK
# ============================================================================
echo -e "${BLUE}${BOLD}[6/7] Running Tests...${NC}"
if command -v pytest &> /dev/null; then
    # Run tests with minimal output
    TEST_OUTPUT=$(pytest -x --tb=short -q 2>&1)
    TEST_EXIT=$?
    
    if [ $TEST_EXIT -ne 0 ]; then
        FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || echo "1")
        print_status "error" "$FAILED_TESTS test(s) failing"
        echo -e "${RED}Test failures:${NC}"
        echo "$TEST_OUTPUT" | grep -E "FAILED|ERROR|AssertionError" | head -10
        TOTAL_ISSUES=$((TOTAL_ISSUES + FAILED_TESTS))
    else
        print_status "success" "All tests passing"
    fi
else
    print_status "info" "Skipping (pytest not installed)"
fi
echo

# ============================================================================
# 7. CODE ANALYSIS WITH FLAKE8
# ============================================================================
echo -e "${BLUE}${BOLD}[7/7] Running Code Analysis...${NC}"
if command -v flake8 &> /dev/null; then
    # Focus on actual errors, not style issues
    FLAKE8_ERRORS=$(flake8 . --select=E9,F63,F7,F82 --exclude=venv,.venv,__pycache__ --count 2>/dev/null || echo "0")
    
    if [ "$FLAKE8_ERRORS" -gt 0 ]; then
        print_status "error" "$FLAKE8_ERRORS critical code error(s)"
        flake8 . --select=E9,F63,F7,F82 --exclude=venv,.venv,__pycache__ | head -10
        TOTAL_ISSUES=$((TOTAL_ISSUES + FLAKE8_ERRORS))
    else
        print_status "success" "No critical code errors"
    fi
else
    print_status "info" "Skipping (flake8 not installed)"
fi
echo

# ============================================================================
# SUMMARY REPORT
# ============================================================================
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}📊 Bug Check Summary${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

if [ $TOTAL_ISSUES -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✨ No bugs or errors found! Code is clean.${NC}"
else
    echo -e "${BOLD}Issues Found: ${RED}$TOTAL_ISSUES${NC}"
    echo -e "  ${RED}● Syntax Errors: $SYNTAX_ERRORS${NC}"
    echo -e "  ${RED}● Import Errors: $IMPORT_ERRORS${NC}"
    echo -e "  ${YELLOW}● Type Errors: $TYPE_ERRORS${NC}"
    echo -e "  ${YELLOW}● Logic Issues: $LOGIC_BUGS${NC}"
fi

echo -e "\n${BOLD}Quick Fix Commands:${NC}"
if [ $TYPE_ERRORS -gt 0 ]; then
    echo -e "  ${CYAN}mypy . --ignore-missing-imports${NC}  # See all type errors"
fi
if [ $LOGIC_BUGS -gt 0 ]; then
    echo -e "  ${CYAN}grep -r \"def.*=\[\]\" . --include=\"*.py\"${NC}  # Find mutable defaults"
    echo -e "  ${CYAN}grep -r \"except:\" . --include=\"*.py\"${NC}  # Find bare excepts"
fi

# Exit with appropriate code
if [ $SYNTAX_ERRORS -gt 0 ] || [ $IMPORT_ERRORS -gt 0 ]; then
    exit 2  # Critical errors
elif [ $TOTAL_ISSUES -gt 0 ]; then
    exit 1  # Warnings
else
    exit 0  # All good
fi