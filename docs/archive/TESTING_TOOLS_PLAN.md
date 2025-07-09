# Comprehensive Test Plan for tools.py

## Current Coverage Analysis

**Current Coverage**: 84.33% (146/173 statements covered)

### Currently Tested Functions
1. **TavilyClient class**
   - ✅ Initialization and context manager
   - ✅ Successful search operations
   - ✅ Error handling (401, 429, timeout)
   - ✅ Retry logic with backoff
   - ✅ Rate limiting
   - ✅ Credibility scoring
   - ✅ Domain extraction
   - ✅ Malformed response handling

2. **Utility Functions**
   - ✅ `extract_key_statistics()` - all branches
   - ✅ `search_academic_sources()` wrapper

### Untested Code (Missing Lines)
1. Line 116: Rate limit cleanup logic (while loop)
2. Line 126-136: Rate limit wait time calculation
3. Line 178-181: Domain filtering logic
4. Line 195: Coroutine handling for mocked responses
5. Line 223: Generic exception handling in ClientResponseError
6. Line 314: Journal/pubmed URL scoring
7. Lines 363-364: Domain extraction error handling
8. Lines 450-453: `calculate_reading_time()` function
9. Lines 467-478: `clean_text_for_seo()` function
10. Lines 491-519: `generate_slug()` function

## Test Plan by Function

### 1. Rate Limiting Enhancement Tests

#### Test: Rate Limit Window Cleanup
```python
async def test_rate_limit_window_cleanup():
    """Test that old requests are properly cleaned from rate limit tracking."""
    # Goal: Cover line 116 - while loop that removes old requests
    # Setup: Add old timestamps to _request_times
    # Action: Call _check_rate_limit()
    # Assert: Old timestamps are removed
```

#### Test: Rate Limit Wait Time Calculation
```python
async def test_rate_limit_wait_time_calculation():
    """Test accurate wait time calculation when rate limited."""
    # Goal: Cover lines 126-136 - wait time calculation and sleep
    # Setup: Fill rate limit queue to capacity
    # Action: Make another request
    # Assert: Correct wait time is calculated and applied
```

### 2. Search Configuration Tests

#### Test: Domain Filtering
```python
async def test_search_with_domain_filtering():
    """Test that include_domains is properly added to payload."""
    # Goal: Cover lines 178-181
    # Setup: Configure client with include_domains
    # Action: Perform search
    # Assert: Payload includes domain filter
```

#### Test: No Domain Filtering
```python
async def test_search_without_domain_filtering():
    """Test search when include_domains is empty."""
    # Goal: Cover the false branch of domain filtering
    # Setup: Configure client with empty include_domains
    # Action: Perform search
    # Assert: Payload doesn't include domain filter
```

### 3. Error Handling Enhancement Tests

#### Test: Generic API Error
```python
async def test_generic_api_error():
    """Test handling of non-401/429 API errors."""
    # Goal: Cover line 223 - generic ClientResponseError
    # Setup: Mock 500 error response
    # Action: Perform search
    # Assert: TavilyAPIError raised with correct message
```

#### Test: Async Mock Response Handling
```python
async def test_async_mock_response_handling():
    """Test handling of async mock responses in tests."""
    # Goal: Cover line 195 - coroutine check
    # Setup: Create AsyncMock that returns coroutine
    # Action: Perform search
    # Assert: Coroutine is properly awaited
```

### 4. Credibility Scoring Edge Cases

#### Test: Journal/PubMed URL Scoring
```python
def test_credibility_journal_pubmed_urls():
    """Test credibility scoring for journal and pubmed URLs."""
    # Goal: Cover line 314
    # Test URLs containing 'journal' or 'pubmed'
    # Assert: Additional score bonus applied
```

### 5. Domain Extraction Edge Cases

#### Test: Malformed URL Handling
```python
def test_extract_domain_error_handling():
    """Test domain extraction with malformed URLs."""
    # Goal: Cover lines 363-364 - exception handling
    # Test various malformed URLs
    # Assert: Returns default .com domain
```

### 6. Utility Functions Tests

#### Test: Reading Time Calculation
```python
def test_calculate_reading_time():
    """Test reading time calculation for various word counts."""
    # Goal: Cover lines 450-453
    # Test cases:
    # - 0 words → 1 minute (minimum)
    # - 100 words → 1 minute
    # - 225 words → 1 minute
    # - 450 words → 2 minutes
    # - 2250 words → 10 minutes
```

#### Test: SEO Text Cleaning
```python
def test_clean_text_for_seo():
    """Test text cleaning for SEO optimization."""
    # Goal: Cover lines 467-478
    # Test cases:
    # - Extra whitespace removal
    # - Quote replacement
    # - HTML tag removal
    # - Sentence ending addition
    # - Already properly formatted text
```

#### Test: Slug Generation
```python
def test_generate_slug():
    """Test URL slug generation from titles."""
    # Goal: Cover lines 491-519
    # Test cases:
    # - Basic title conversion
    # - Multiple spaces handling
    # - Ampersand (&) conversion to double hyphen
    # - Special character removal
    # - Multiple hyphen collapse
    # - Leading/trailing hyphen removal
```

## Mock Strategy

### 1. Tavily API Response Mocking
```python
@pytest.fixture
def mock_tavily_response():
    """Fixture for standard Tavily API response."""
    return {
        "answer": "Summary text",
        "results": [
            {
                "title": "Academic Paper",
                "url": "https://journal.edu/paper",
                "content": "Research findings...",
                "score": 0.95
            }
        ]
    }
```

### 2. aiohttp Session Mocking
```python
@pytest.fixture
async def mock_session():
    """Properly configured async mock session."""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.raise_for_status = AsyncMock()
    response.json = AsyncMock()
    
    # Proper context manager setup
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=None)
    session.post.return_value = context
    
    return session
```

### 3. Rate Limit Testing Mock
```python
@pytest.fixture
def mock_datetime(monkeypatch):
    """Mock datetime for controlled rate limit testing."""
    from datetime import datetime, timedelta
    
    class MockDatetime:
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        
        @classmethod
        def now(cls):
            return cls.current_time
        
        @classmethod
        def advance(cls, seconds):
            cls.current_time += timedelta(seconds=seconds)
    
    monkeypatch.setattr('tools.datetime', MockDatetime)
    return MockDatetime
```

## Error Scenarios to Test

1. **Network Errors**
   - Connection timeout
   - DNS resolution failure
   - SSL certificate errors

2. **API Response Errors**
   - Empty response body
   - Invalid JSON
   - Missing required fields
   - Null values in results

3. **Rate Limiting Edge Cases**
   - Burst requests
   - Requests spanning window boundary
   - Clock drift handling

4. **Concurrent Request Handling**
   - Multiple simultaneous searches
   - Rate limit lock contention

## Integration Test Cases

1. **End-to-End Search Flow**
   ```python
   async def test_full_search_flow():
       """Test complete search with real-like responses."""
       # Configure client
       # Perform search
       # Verify all processing steps
       # Check final response structure
   ```

2. **Error Recovery Flow**
   ```python
   async def test_error_recovery_flow():
       """Test search recovery after transient errors."""
       # First attempt fails
       # Retry succeeds
       # Verify final result
   ```

## Performance Test Cases

1. **Large Response Handling**
   - Test with maximum allowed results
   - Verify memory efficiency

2. **Rate Limit Performance**
   - Measure overhead of rate limiting
   - Verify no unnecessary delays

## Test Implementation Priority

1. **High Priority** (Missing coverage)
   - `calculate_reading_time()`
   - `clean_text_for_seo()`
   - `generate_slug()`
   - Rate limit edge cases

2. **Medium Priority** (Error paths)
   - Generic API errors
   - Domain extraction errors
   - Journal URL scoring

3. **Low Priority** (Already well covered)
   - Additional credibility scenarios
   - More malformed response cases

## Success Metrics

- Achieve 95%+ code coverage for tools.py
- All edge cases documented and tested
- Mock strategies reusable for other tests
- Clear error messages for debugging
- Fast test execution (< 1 second per test)