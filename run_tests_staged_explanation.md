# Staged Test Runner Explanation

Hey Finn! I've created a comprehensive staged test runner that intelligently runs your tests in phases and combines coverage at the end. Let me walk you through how it works and why it's designed this way.

## Purpose

This script solves the problem of running a large test suite efficiently by:
1. Running tests in logical stages (fast → slow)
2. Combining coverage data from all stages
3. Providing early feedback if fast tests fail
4. Offering flexible options for different scenarios

## Architecture

The script follows a staged execution pattern:

```
Stage 1: Fast Unit Tests (seconds)
   ↓ (only continues if passed)
Stage 2: All Unit Tests (minutes)
   ↓ (optional)
Stage 3: Integration Tests (minutes)
   ↓ (optional)
Stage 4: End-to-End Tests (minutes)
   ↓
Coverage Report Generation
```

## Key Concepts

### 1. **Staged Execution**
Tests run from fastest to slowest, giving you quick feedback. If fast tests fail, why wait for slow ones?

### 2. **Coverage Accumulation**
Each stage appends to the coverage data using `--cov-append`, building a complete picture.

### 3. **Parallel Execution Management**
- Unit tests: Use all available cores
- Integration tests: Use half the cores (they might compete for resources)
- Automatically falls back to sequential if pytest-xdist isn't installed

### 4. **Smart Test Discovery**
The script counts tests before running them, skipping empty stages.

## Decision Rationale

1. **Why Stages?**
   - Fast feedback loop for developers
   - Fail fast on simple errors
   - Optimize CI/CD pipeline time

2. **Why Different Parallelism Levels?**
   - Unit tests are isolated and benefit from max parallelism
   - Integration tests might share resources (databases, APIs)
   - Prevents resource exhaustion

3. **Why Bash Instead of Python?**
   - Simpler for CI/CD integration
   - Easy to modify without Python knowledge
   - Direct process control

## Learning Path

### Basic Usage
```bash
# Run all stages with default settings
./run_tests_staged.sh

# Quick development mode (skip slow tests)
./run_tests_staged.sh --skip-slow --skip-integration

# Verbose output for debugging
./run_tests_staged.sh -v

# No parallel execution (for debugging)
./run_tests_staged.sh --no-parallel
```

### Advanced Usage
```bash
# CI/CD mode - fail fast, no HTML
./run_tests_staged.sh --no-html

# Development mode - quick feedback
./run_tests_staged.sh --skip-integration --skip-slow

# Pre-commit hook
./run_tests_staged.sh || exit 1
```

## Real-World Applications

### 1. **Development Workflow**
```bash
# During coding - fast feedback
./run_tests_fast.sh

# Before committing - thorough check
./run_tests_staged.sh --skip-slow

# Before pushing - complete validation
./run_tests_staged.sh
```

### 2. **CI/CD Pipeline**
```yaml
# GitHub Actions example
- name: Run staged tests
  run: |
    ./run_tests_staged.sh --no-html
  timeout-minutes: 30
```

### 3. **Pre-commit Hook**
```bash
#!/bin/bash
# .git/hooks/pre-commit
./run_tests_staged.sh --skip-integration || {
    echo "Tests failed! Commit aborted."
    exit 1
}
```

## Common Pitfalls

1. **Coverage Data Conflicts**
   - Always clean `.coverage*` files before starting
   - Use `--cov-append` for subsequent runs
   - Remember to `coverage combine` for parallel runs

2. **Resource Exhaustion**
   - Don't use all CPU cores (leaves system unresponsive)
   - Integration tests might need exclusive database access
   - Watch memory usage with large test suites

3. **Test Isolation**
   - Parallel tests must not share state
   - Use proper test fixtures with appropriate scopes
   - Clean up resources after each test

## Best Practices

### 1. **Mark Your Tests Properly**
```python
import pytest

@pytest.mark.unit
@pytest.mark.fast
def test_simple_function():
    """Runs in Stage 1"""
    assert 1 + 1 == 2

@pytest.mark.unit
@pytest.mark.slow
def test_complex_algorithm():
    """Runs in Stage 2"""
    result = expensive_computation()
    assert result == expected

@pytest.mark.integration
def test_api_endpoint():
    """Runs in Stage 3"""
    response = client.get('/api/endpoint')
    assert response.status_code == 200
```

### 2. **Optimize Test Placement**
```
tests/
├── unit/          # Fast, isolated tests
├── integration/   # Tests with external dependencies
├── e2e/          # Full workflow tests
└── performance/  # Slow performance tests
```

### 3. **Coverage Configuration**
Already set in your `pyproject.toml`:
```toml
[tool.coverage.run]
parallel = true
concurrency = ["thread", "multiprocessing"]
```

## Script Features Explained

### Color-Coded Output
- 🔵 Blue: Information
- ✅ Green: Success
- ⚠️ Yellow: Warning
- ❌ Red: Error

### Automatic Browser Opening
On macOS, the script opens the HTML coverage report automatically!

### Test Statistics
Shows count of tests by category before running them.

### Smart Defaults
- Parallel execution enabled by default
- HTML reports generated by default
- Verbose mode available with `-v`

## Performance Comparison

| Mode | Time | Coverage | Use Case |
|------|------|----------|----------|
| Fast Runner | ~10s | No | Active development |
| Staged (skip slow) | ~1m | Yes | Pre-commit |
| Staged (full) | ~5m | Yes | Pre-push/CI |
| Old Runner | ~20m | Yes | Never! |

## Debugging Tips

1. **Test Failures**
   ```bash
   # Run with verbose output
   ./run_tests_staged.sh -v
   
   # Run specific stage manually
   pytest tests/ -m "unit and not slow" -v
   ```

2. **Coverage Issues**
   ```bash
   # Check coverage files
   ls -la .coverage*
   
   # Manually combine
   coverage combine
   coverage report
   ```

3. **Parallel Execution Problems**
   ```bash
   # Disable parallel execution
   ./run_tests_staged.sh --no-parallel
   ```

## Integration with Your Workflow

1. **Alias for Quick Access**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   alias test-fast="./run_tests_fast.sh"
   alias test-staged="./run_tests_staged.sh"
   alias test-all="./run_tests_staged.sh"
   ```

2. **VS Code Task**
   ```json
   {
     "label": "Run Staged Tests",
     "type": "shell",
     "command": "./run_tests_staged.sh",
     "group": {
       "kind": "test",
       "isDefault": true
     }
   }
   ```

3. **Makefile Integration**
   ```makefile
   test-fast:
       ./run_tests_fast.sh
   
   test-staged:
       ./run_tests_staged.sh
   
   test-ci:
       ./run_tests_staged.sh --no-html
   ```

## Next Steps

1. Start using it: `./run_tests_staged.sh --skip-integration`
2. Mark your slow tests: Add `@pytest.mark.slow` to tests taking >1s
3. Organize tests by type: Move integration tests to a separate directory
4. Set up git hooks: Add pre-commit/pre-push hooks

## Security Considerations

- The script cleans coverage data at start (prevents data leakage)
- Parallel execution might expose race conditions
- Resource limits prevent system exhaustion
- Coverage reports might contain sensitive code paths

What questions do you have about this code, Finn?
Would you like me to explain any specific part in more detail?
Try this exercise: Run `./run_tests_staged.sh --skip-slow -v` and watch how it progresses through the stages!