# Understanding test_formatters.py

## Purpose
This test file provides comprehensive coverage for the CLI formatting utilities in `cli/formatters.py`. These formatters are essential for presenting data in a user-friendly way in command-line interfaces.

## Architecture

### Test Class Organization
The tests are organized into classes, with each class testing a specific formatter function:
- `TestFormatFileSize` - Tests file size formatting (bytes to human-readable)
- `TestFormatPercentage` - Tests percentage formatting with precision
- `TestTruncateText` - Tests text truncation for display
- `TestFormatMetricsForExport` - Tests metric export formatting (CSV, Prometheus)
- `TestFormattersIntegration` - Tests formatters working together

### Key Testing Concepts

#### 1. Boundary Testing
```python
def test_kilobytes_formatting(self):
    assert format_file_size(1023) == "1023.00 B"  # Just under 1 KB
    assert format_file_size(1024) == "1.00 KB"    # Exactly 1 KB
```
We test the exact boundaries where units change (1024 bytes = 1 KB).

#### 2. Precision Testing
```python
def test_precision_control(self):
    assert format_percentage(0.1234, precision=0) == "12%"
    assert format_percentage(0.1234, precision=2) == "12.34%"
```
Tests ensure formatting respects precision parameters.

#### 3. Edge Case Testing
```python
def test_edge_cases(self):
    assert truncate_text("") == ""  # Empty input
    assert format_percentage(-0.25) == "-25.0%"  # Negative values
```
Edge cases prevent unexpected failures in production.

#### 4. Parametrized Testing
```python
@pytest.mark.parametrize("format_type,expected_header", [
    ("csv", "metric,value"),
    ("prometheus", "# TYPE"),
])
```
Parametrized tests reduce code duplication when testing similar scenarios.

## Decision Rationale

### Why These Test Patterns?

1. **Comprehensive Coverage**: Each function is tested with normal cases, edge cases, and error conditions.

2. **Clear Test Names**: Test names like `test_megabytes_formatting` immediately tell you what's being tested.

3. **Grouped Assertions**: Related assertions are grouped in single tests for better organization.

4. **Real-World Values**: Tests use realistic values (50 MB, 75% hit rate) that developers will encounter.

## Learning Path

### For Beginners
1. Start with `TestFormatFileSize` - it's the simplest formatter
2. Study how boundary values are tested (1023 vs 1024 bytes)
3. Look at edge case handling in `TestTruncateText`

### For Intermediate Developers
1. Examine the parametrized test example
2. Study the integration tests that combine multiple formatters
3. Notice how fixtures provide reusable test data

### For Advanced Developers
1. Analyze the test organization strategy
2. Consider how these tests ensure backward compatibility
3. Think about performance implications of the formatting functions

## Real-World Applications

### 1. CLI Tools
These formatters are essential for any CLI tool that displays:
- File sizes (backup tools, file managers)
- Progress percentages (download managers, data processors)
- Long text previews (log viewers, content managers)

### 2. Monitoring Systems
The Prometheus format export is used in:
- System monitoring dashboards
- Application performance monitoring
- Infrastructure metrics collection

### 3. Data Export
The CSV formatter enables:
- Excel-compatible exports
- Data pipeline integrations
- Report generation

## Common Pitfalls

### 1. Forgetting Unit Boundaries
```python
# WRONG: Assuming 1000 bytes = 1 KB
assert format_file_size(1000) == "1.00 KB"  # This will fail!

# CORRECT: Using 1024 bytes = 1 KB
assert format_file_size(1024) == "1.00 KB"
```

### 2. Not Testing Precision
```python
# WRONG: Only testing integer percentages
assert format_percentage(0.5) == "50%"

# CORRECT: Testing decimal precision
assert format_percentage(0.5) == "50.0%"  # Note the .0
```

### 3. Ignoring Edge Cases
```python
# WRONG: Only testing positive values
def test_percentage(self):
    assert format_percentage(0.5) == "50.0%"

# CORRECT: Including negative and edge values
def test_percentage(self):
    assert format_percentage(0.5) == "50.0%"
    assert format_percentage(-0.5) == "-50.0%"
    assert format_percentage(1.5) == "150.0%"
```

## Best Practices Demonstrated

### 1. Test Independence
Each test method is completely independent and can run in any order.

### 2. Clear Assertions
```python
assert result == "50.00 MB"  # Clear expected value
assert len(result) <= 200    # Clear constraint
assert result.endswith("...") # Clear behavior
```

### 3. Descriptive Variable Names
```python
short_text = "This is a short text"
long_text = "This is a very long text that needs..."
```

### 4. Comprehensive Coverage
- Normal cases ✓
- Boundary cases ✓
- Error cases ✓
- Integration cases ✓

## Interactive Exercises

### Exercise 1: Add a New Formatter
Try adding a test for a new formatter that converts seconds to human-readable time:
```python
def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    # Your implementation here
    pass
```

### Exercise 2: Test Unicode Handling
Extend the truncate_text tests to handle more complex Unicode scenarios:
- Emoji truncation
- Right-to-left text
- Combining characters

### Exercise 3: Performance Testing
Add a performance test that ensures formatting functions are fast:
```python
def test_format_file_size_performance():
    import time
    start = time.time()
    for _ in range(10000):
        format_file_size(1234567890)
    duration = time.time() - start
    assert duration < 0.1  # Should format 10k times in < 0.1s
```

What questions do you have about this test file, Finn?
Would you like me to explain any specific testing pattern in more detail?
Try this exercise: Add a test for formatting very large numbers (petabytes and beyond)!