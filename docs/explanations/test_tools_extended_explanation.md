# Understanding test_tools_extended.py

## Purpose
This test file extends the coverage of tools.py by focusing on edge cases, concurrent operations, and advanced error scenarios that complement the existing test_tools_comprehensive.py.

## Architecture

### Test Organization
- `TestTavilyClientAdvanced` - Tests for complex client scenarios (concurrency, recovery)
- `TestSearchAcademicSourcesAdvanced` - Edge cases for the search function
- `TestExtractKeyStatisticsAdvanced` - Complex pattern matching scenarios
- `TestURLContentExtraction` - Web scraping edge cases
- `TestErrorPropagation` - How errors flow through the system
- `TestPerformanceOptimizations` - Performance-related testing
- `TestToolsIntegration` - End-to-end workflow tests

### Key Testing Concepts

#### 1. Concurrent Operations Testing
```python
tasks = []
for i in range(5):
    task = asyncio.create_task(client.search("test query"))
    tasks.append(task)
results = await asyncio.gather(*tasks, return_exceptions=True)
```
Tests how the system handles multiple simultaneous requests.

#### 2. Rate Limiting Simulation
```python
for i in range(58):  # Fill up most of the rate limit
    client._request_times.append(current_time - timedelta(seconds=i))
```
Simulates a nearly-full rate limit window to test edge conditions.

#### 3. Network Recovery Testing
```python
# First request fails
client.session.post = AsyncMock(side_effect=aiohttp.ClientError("Network error"))
# Later request succeeds
client.session.post = AsyncMock(return_value=mock_response)
```
Tests the client's ability to recover from transient failures.

#### 4. Malformed Response Handling
```python
mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid", "", 0))
```
Tests graceful handling of unexpected API responses.

## Decision Rationale

### Why These Specific Tests?

1. **Concurrency**: Modern applications often make parallel API calls
2. **Rate Limiting**: Critical for respecting API limits and avoiding bans
3. **Error Recovery**: Production systems must handle transient failures
4. **Data Validation**: APIs can return unexpected data formats
5. **Performance**: Ensures the system scales efficiently

## Learning Path

### For Beginners
1. Start with `test_statistics_with_various_formats` - simple pattern matching
2. Study `test_search_empty_results_handling` - basic error handling
3. Look at `test_malformed_json_response` - API response validation

### For Intermediate Developers
1. Examine concurrent testing patterns
2. Study rate limiting implementation
3. Understand error propagation through async code

### For Advanced Developers
1. Analyze the performance testing strategies
2. Consider race condition handling
3. Think about distributed system failures

## Real-World Applications

### 1. API Client Design
These patterns apply to any external API integration:
- Rate limiting prevents API bans
- Retry logic handles network issues
- Concurrent requests improve performance

### 2. Web Scraping
The URL extraction tests demonstrate:
- Handling various HTML structures
- Managing crawl depth
- Preventing infinite loops

### 3. Data Processing
Statistics extraction shows:
- Pattern matching complexity
- Handling various data formats
- Filtering false positives

## Common Pitfalls

### 1. Not Testing Concurrency
```python
# WRONG: Only testing sequential operations
result1 = await client.search("query1")
result2 = await client.search("query2")

# CORRECT: Testing concurrent operations
results = await asyncio.gather(
    client.search("query1"),
    client.search("query2")
)
```

### 2. Ignoring Rate Limits in Tests
```python
# WRONG: Making unlimited requests
for i in range(100):
    await client.search(f"query{i}")

# CORRECT: Respecting rate limits
for i in range(100):
    await client.search(f"query{i}")
    if i % 10 == 0:
        await asyncio.sleep(1)  # Pause to avoid rate limits
```

### 3. Not Testing Error Recovery
```python
# WRONG: Only testing happy path
response = await client.search("query")
assert response.results

# CORRECT: Testing error and recovery
with pytest.raises(NetworkError):
    await client.search("query")
# Verify client can still work after error
response = await client.search("query2")
```

## Best Practices Demonstrated

### 1. Realistic Test Data
```python
queries = [
    "COVID-19 & mental health",
    "type 2 diabetes (T2D)",
    "omega-3/omega-6 ratio",
]
```
Uses real-world query formats that users might enter.

### 2. Comprehensive Error Testing
```python
errors = [
    (TavilyAuthError("Invalid API key"), TavilyAuthError),
    (TavilyRateLimitError("Rate limit exceeded"), TavilyRateLimitError),
    (TavilyTimeoutError("Request timeout"), TavilyTimeoutError),
]
```
Tests each error type separately for precise handling.

### 3. Performance Measurement
```python
start_time = asyncio.get_event_loop().time()
# ... operations ...
end_time = asyncio.get_event_loop().time()
assert (end_time - start_time) < expected_duration
```
Ensures operations complete within acceptable time limits.

### 4. Edge Case Coverage
```python
# Empty results
mock_client.search.return_value = TavilySearchResponse(results=[])
# Partial results
{"title": "Test"},  # Missing url and content
# Circular references
"http://site.com/pageC": "<html><a href='/'>Home</a></html>"
```

## Interactive Exercises

### Exercise 1: Add Retry Backoff Testing
Implement tests for exponential backoff:
```python
def test_exponential_backoff_timing():
    # Test that retries follow exponential backoff pattern
    # 1st retry: 1s, 2nd: 2s, 3rd: 4s, etc.
    pass
```

### Exercise 2: Test Connection Pool Limits
Add tests for connection pool exhaustion:
```python
async def test_connection_pool_exhaustion():
    # Test behavior when all connections are in use
    # Should queue requests or fail gracefully
    pass
```

### Exercise 3: Add Chaos Testing
Implement random failure injection:
```python
async def test_random_failures():
    # Randomly fail 30% of requests
    # System should still complete successfully
    pass
```

## Debugging Tips

### 1. Async Debugging
```python
# Use asyncio.create_task() with names for better debugging
task = asyncio.create_task(client.search("test"), name="search_task_1")
```

### 2. Mock Verification
```python
# Verify mock was called with expected arguments
mock_client.search.assert_called_with("expected query")
# Check all calls made
print(mock_client.search.call_args_list)
```

### 3. Timing Issues
```python
# Add small delays to avoid race conditions in tests
await asyncio.sleep(0.01)  # Let other tasks run
```

## Advanced Topics

### 1. Testing Rate Limit Headers
Real APIs often return rate limit info in headers:
```python
mock_response.headers = {
    "X-RateLimit-Remaining": "42",
    "X-RateLimit-Reset": "1642598400"
}
```

### 2. Testing Circuit Breakers
If the client implements circuit breakers:
```python
# After multiple failures, circuit should open
for _ in range(5):
    with pytest.raises(TavilyAPIError):
        await client.search("test")
# Circuit open - should fail fast
with pytest.raises(CircuitOpenError):
    await client.search("test")
```

### 3. Testing Distributed Tracing
If the system supports tracing:
```python
with patch("tools.tracer") as mock_tracer:
    await client.search("test")
    mock_tracer.start_span.assert_called_with("tavily_search")
```

What questions do you have about testing async operations, Finn?
Would you like me to explain any concurrency pattern in more detail?
Try this exercise: Add tests for WebSocket connections if the API supports real-time updates!