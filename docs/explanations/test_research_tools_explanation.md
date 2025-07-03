# Test Research Tools Explanation

## Purpose
This test file ensures the Research Agent's tool functions and Tavily API integration work correctly. It covers API mocking, error handling, rate limiting, and utility functions that support the research process.

## Architecture

### Test Class Structure
- `TestResearchAgentTools` - Tests the agent's search_academic tool
- `TestTavilyClient` - Tests the Tavily API client implementation
- `TestUtilityFunctions` - Tests helper functions (statistics, slugs, etc.)
- `TestIntegration` - Tests the complete search flow
- `TestContextManager` - Tests async context manager behavior
- `TestEdgeCases` - Tests boundary conditions and errors

### Key Testing Concepts

#### 1. Async Testing with pytest
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

The `@pytest.mark.asyncio` decorator tells pytest to run the test in an event loop.

#### 2. Mocking Async Functions
```python
mock_session = AsyncMock()
mock_response = AsyncMock()
mock_response.json = AsyncMock(return_value=data)
```

`AsyncMock` creates mocks that can be awaited, essential for testing async code.

#### 3. API Response Mocking
We mock at different levels:
- **HTTP Level**: Mock aiohttp responses
- **Function Level**: Mock the search function
- **Client Level**: Mock the entire client

## Decision Rationale

### Why Mock the Tavily API?
1. **Cost** - Real API calls cost money
2. **Speed** - Tests run instantly without network delays
3. **Reliability** - Tests don't fail due to network issues
4. **Control** - Can test specific scenarios (errors, edge cases)

### Why Test Rate Limiting?
1. **API Compliance** - Avoid getting banned
2. **Cost Control** - Prevent excessive charges
3. **System Stability** - Prevent overwhelming the API
4. **User Experience** - Graceful handling of limits

### Why Test Error Scenarios?
1. **Resilience** - System should handle API failures
2. **User Feedback** - Clear error messages
3. **Debugging** - Easier to diagnose issues
4. **Recovery** - Automatic retry logic

## Learning Path

### Beginner Concepts
1. **Basic Mocking** - Replace functions with test doubles
2. **Assertions** - Verify expected behavior
3. **Fixtures** - Reusable test setup

### Intermediate Concepts
1. **Async/Await** - Testing asynchronous code
2. **Context Managers** - Testing resource cleanup
3. **Exception Testing** - Verifying error handling

### Advanced Concepts
1. **Rate Limiting** - Time-based testing
2. **Backoff Strategies** - Exponential retry testing
3. **Integration Testing** - Testing component interactions

## Real-world Applications

### 1. API Client Development
These patterns apply to any API client:
- Authentication handling
- Rate limit compliance
- Error recovery
- Response parsing

### 2. Web Scraping Tools
Similar testing needs:
- Request throttling
- Error handling
- Content extraction
- Data validation

### 3. Microservice Communication
Testing service interactions:
- Circuit breakers
- Retry logic
- Timeout handling
- Fallback strategies

## Common Pitfalls

### 1. Not Mocking Time-Dependent Code
**Mistake**: Testing rate limiting with real time
```python
# Bad - Test takes actual seconds
await client.search("query1")
time.sleep(1)  # Real delay!
await client.search("query2")

# Good - Mock time progression
with patch('datetime.datetime.now') as mock_now:
    mock_now.return_value = start_time
    await client.search("query1")
    mock_now.return_value = start_time + timedelta(seconds=1)
    await client.search("query2")
```

### 2. Incomplete Async Mocking
**Mistake**: Forgetting to make mocks awaitable
```python
# Bad - Will fail with "object is not awaitable"
mock_func = Mock(return_value=result)

# Good - Use AsyncMock
mock_func = AsyncMock(return_value=result)
```

### 3. Not Testing Error Propagation
**Mistake**: Only testing happy paths
```python
# Bad - No error testing
async def test_search():
    result = await search("query")
    assert result is not None

# Good - Test error scenarios
async def test_search_error():
    with pytest.raises(TavilyAPIError):
        await search("query")
```

### 4. Forgetting Cleanup
**Mistake**: Not closing async resources
```python
# Bad - Session leak
client = TavilyClient(config)
await client.search("query")
# Session never closed!

# Good - Use context manager
async with TavilyClient(config) as client:
    await client.search("query")
# Session automatically closed
```

## Best Practices

### 1. Structured Test Data
Create realistic test data:
```python
def create_tavily_response(**kwargs):
    defaults = {
        "title": "Test Article",
        "url": "https://test.edu/article",
        "content": "Test content",
        "score": 0.8
    }
    defaults.update(kwargs)
    return TavilySearchResult(**defaults)
```

### 2. Test Isolation
Each test should be independent:
```python
@pytest.fixture
def fresh_client():
    # New client for each test
    config = create_test_config()
    return TavilyClient(config)
```

### 3. Meaningful Assertions
Make failures clear:
```python
# Bad
assert len(results) > 0

# Good
assert len(results) > 0, f"Expected results but got empty list for query: {query}"
```

### 4. Edge Case Coverage
Test boundaries:
```python
@pytest.mark.parametrize("word_count,expected_time", [
    (0, 1),      # Minimum
    (225, 1),    # Exactly 1 minute
    (226, 1),    # Just over 1 minute
    (10000, 44), # Large document
])
def test_reading_time(word_count, expected_time):
    assert calculate_reading_time(word_count) == expected_time
```

## Interactive Exercises

### Exercise 1: Add Retry Testing
Enhance the tests to verify retry behavior:
1. Mock a failing request that succeeds on retry
2. Verify the number of retry attempts
3. Test exponential backoff timing
4. Test max retry limit

### Exercise 2: Add Response Caching
Implement and test response caching:
1. Add a simple cache to TavilyClient
2. Test cache hits and misses
3. Test cache expiration
4. Test cache size limits

### Exercise 3: Add Request Validation
Add input validation to the client:
1. Validate query length limits
2. Test with invalid characters
3. Test with empty queries
4. Add appropriate error messages

## Debugging Tips

### When Async Tests Hang
1. **Check Awaits** - Ensure all async calls are awaited
2. **Check Mocks** - Verify AsyncMock is used for async functions
3. **Add Timeouts** - Use pytest-timeout to catch hanging tests
4. **Debug Logs** - Add logging to see where it hangs

### When Mocks Don't Work
1. **Check Import Path** - Mock where the function is used, not defined
2. **Check Mock Type** - Use AsyncMock for async, Mock for sync
3. **Check Call Count** - Verify the mock was actually called
4. **Print Arguments** - See what arguments were passed

### Common Error Messages
- `RuntimeError: This event loop is already running` - Async test setup issue
- `TypeError: object Mock can't be used in await expression` - Need AsyncMock
- `AssertionError: Expected call not found` - Mock wasn't called as expected
- `TimeoutError` - Async operation took too long

### Testing Strategies
1. **Start Simple** - Test basic functionality first
2. **Add Complexity** - Layer in error cases and edge cases
3. **Test Interfaces** - Focus on public APIs, not internals
4. **Mock External** - Only mock external dependencies

What questions do you have about this code, Finn?
Would you like me to explain any specific part in more detail?
Try this exercise: Add a test for concurrent API requests to verify thread safety!