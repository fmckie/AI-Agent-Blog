# Staged Code Health Check Explanation

Hey Finn! I've created a staged version of the code health checker that runs analyses in priority order, giving you faster feedback and the ability to stop early when critical issues are found. This is much more efficient than running everything at once!

## Purpose

This staged approach solves several problems:
1. **Fast feedback** - Critical issues are found in seconds, not minutes
2. **Early stopping** - Why continue if syntax is broken?
3. **Priority ordering** - Most important checks run first
4. **Progressive analysis** - Each stage builds on the previous

## Architecture

The script runs 7 stages in order of importance:

```
Stage 1: Critical Checks (Syntax & Basic Tests)
   ↓ (stops here if critical issues found)
Stage 2: Security Analysis
   ↓
Stage 3: Code Quality
   ↓
Stage 4: Bug Patterns
   ↓
Stage 5: Complexity Analysis
   ↓
Stage 6: Dependencies
   ↓
Stage 7: Documentation
```

Each stage can fail independently, and by default, critical issues stop the analysis.

## Key Concepts

### 1. **Stage Priority**
- **Critical stages (1-2)**: Must pass for code to run
- **Quality stages (3-4)**: Should pass for maintainability
- **Health stages (5-7)**: Nice to pass for long-term success

### 2. **Early Stopping Logic**
```bash
# After each stage:
if [ $CRITICAL_ISSUES -gt 0 ] && [ "$CONTINUE_ON_FAIL" = false ]; then
    echo "Critical issues found! Stopping analysis."
    # Jump to final report
fi
```

### 3. **Progressive Scoring**
- Start with 100 points
- Each stage can deduct points
- Critical issues deduct more (10-20 points)
- Score determines if debugging is needed

## Decision Rationale

1. **Why Staged Execution?**
   - No point checking documentation if syntax is broken
   - Security issues are more urgent than style issues
   - Developers get actionable feedback faster

2. **Why This Order?**
   - Syntax must work (Stage 1)
   - Security is critical (Stage 2)
   - Code quality affects everything (Stage 3)
   - Documentation can wait (Stage 7)

3. **Why Allow Continuing?**
   - Sometimes you want the full picture
   - CI/CD might need all results
   - Use `--continue` flag to override

## Learning Path

### Basic Usage

```bash
# Quick health check (stops on critical issues)
./code_health_staged.sh

# Full analysis regardless of issues
./code_health_staged.sh --continue

# Quick mode (skip slow checks)
./code_health_staged.sh --quick

# Verbose output with all details
./code_health_staged.sh --verbose
```

### Understanding Stage Results

Each stage shows:
- What it's checking
- Issues found (with severity)
- Progress indicator
- Success/failure status

Example output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Stage 1/7: Critical Checks (Syntax & Tests)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ Checking for critical issues that block execution...
ℹ Checking Python syntax...
✓ No syntax errors found
✓ Stage 1 complete - No blocking issues

Progress: [1/7] 14% complete
```

## Real-World Applications

### 1. **Pre-Commit Hook**
```bash
#!/bin/bash
# Fast check before commit
./code_health_staged.sh --quick
if [ $? -eq 2 ]; then
    echo "Critical issues! Commit blocked."
    exit 1
fi
```

### 2. **CI/CD Pipeline**
```yaml
# GitHub Actions
- name: Quick Health Check
  run: ./code_health_staged.sh --quick
  
- name: Full Health Analysis
  if: success()
  run: ./code_health_staged.sh --continue --verbose
```

### 3. **Development Workflow**
```bash
# During coding - quick checks
alias health-quick="./code_health_staged.sh --quick"

# Before PR - thorough check
alias health-full="./code_health_staged.sh --continue"

# Debug mode - see everything
alias health-debug="./code_health_staged.sh --continue --verbose"
```

## Common Pitfalls

### 1. **Skipping Important Stages**
- Don't always use `--quick` mode
- Run full analysis before releases
- Some issues only show in later stages

### 2. **Ignoring Early Warnings**
- Fix issues as they appear
- Don't let warnings accumulate
- Critical issues can cascade

### 3. **Over-relying on Score**
- Score is a guideline, not absolute
- Read the specific issues
- Context matters for some warnings

## Best Practices

### 1. **Use Appropriate Mode**
```bash
# Development iteration
./code_health_staged.sh --quick

# Before commit
./code_health_staged.sh

# Before release
./code_health_staged.sh --continue --verbose
```

### 2. **Fix Issues by Stage**
- Complete Stage 1 fixes before moving on
- Security (Stage 2) before style (Stage 3)
- This prevents fix conflicts

### 3. **Monitor Trends**
```bash
# Save scores over time
./code_health_staged.sh | grep "Overall Health Score" >> health_history.log

# See improvement
tail -10 health_history.log
```

## Stage Details

### Stage 1: Critical Checks
- **Python syntax** - Code must be parseable
- **Import verification** - Main module must import
- **Basic tests** - Core functionality works

### Stage 2: Security
- **Hardcoded secrets** - API keys, passwords
- **SQL injection** - Unsafe queries
- **eval/exec usage** - Code execution risks

### Stage 3: Code Quality
- **Linting** - PEP8 compliance
- **Type checking** - Type hints correctness
- **Code formatting** - Consistent style

### Stage 4: Bug Patterns
- **Mutable defaults** - Common Python pitfall
- **Bare excepts** - Hidden errors
- **Unused code** - Dead imports/variables

### Stage 5: Complexity
- **File length** - Over 500 lines
- **Function complexity** - Cyclomatic complexity
- **Nesting depth** - Readability issues

### Stage 6: Dependencies
- **requirements.txt** - Must exist
- **Version pinning** - Reproducible builds
- **Security vulnerabilities** - Known CVEs

### Stage 7: Documentation
- **Docstring coverage** - Function documentation
- **TODO/FIXME** - Unfinished work
- **README quality** - Project documentation

## Customization

### Add Custom Stages
```bash
# Add after Stage 4
print_header "4.5/7" "Custom Business Logic"
# Your custom checks here
```

### Modify Stage Order
```bash
# Move security to Stage 1 for high-security projects
# Reorder the stage blocks in the script
```

### Adjust Penalties
```bash
# Make security issues more severe
add_finding "critical" "Security" "Issue found" 25  # Instead of 10
```

## Performance Comparison

| Mode | Time | Coverage | Use Case |
|------|------|----------|----------|
| Staged (default) | 5-10s | Stops on critical | Development |
| Staged --quick | 2-5s | Skips slow checks | Iteration |
| Staged --continue | 15-30s | Full analysis | Pre-release |
| Original (all at once) | 30-60s | Everything | Comparison |

## Integration with Other Tools

### 1. **With Test Runner**
```bash
# Run health check before tests
./code_health_staged.sh --quick && ./run_tests_fast.sh
```

### 2. **With Git Hooks**
```bash
# pre-push hook
#!/bin/bash
echo "Running health check..."
./code_health_staged.sh
if [ $? -ne 0 ]; then
    echo "Fix issues before pushing!"
    exit 1
fi
```

### 3. **With Make**
```makefile
.PHONY: health health-quick health-full

health-quick:
	./code_health_staged.sh --quick

health:
	./code_health_staged.sh

health-full:
	./code_health_staged.sh --continue --verbose

check: health test
	@echo "All checks passed!"
```

## Debugging Based on Stage Failures

### Stage 1 Failure
```bash
# Find syntax errors
python -m py_compile $(find . -name "*.py")

# Debug imports
python -c "import main; print('OK')"
```

### Stage 2 Failure
```bash
# Find secrets
grep -r "password.*=" . --include="*.py"

# Check SQL
grep -r "execute.*%" . --include="*.py"
```

### Stage 3 Failure
```bash
# Auto-fix formatting
black .
isort .

# Check types
mypy . --ignore-missing-imports
```

## Quick Reference

### Exit Codes
- `0` - All good (might have suggestions)
- `1` - Warnings found
- `2` - Critical issues found

### Flags
- `--continue` - Don't stop on critical issues
- `--quick` - Skip slow analyses
- `--verbose` - Show all details
- `--help` - Show usage

### Speed Tips
1. Use `--quick` during development
2. Run full check before commits
3. Use `--continue` only when needed
4. Cache results between runs

What questions do you have about this code, Finn?
Would you like me to explain any specific part in more detail?
Try this exercise: Run `./code_health_staged.sh` and see which stage finds the most issues in your code!