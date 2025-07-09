# Enhanced Storage Tests Explanation

## Purpose

This test suite comprehensively validates the `EnhancedVectorStorage` class, ensuring all methods work correctly with proper error handling, edge cases, and integration points.

## Test Architecture

```
test_enhanced_storage.py
├── Fixtures
│   ├── mock_config - Configuration setup
│   ├── mock_supabase - Database client mock
│   ├── sample_academic_source - Test data
│   └── storage - Instance with all mocks
├── Test Classes
│   ├── TestResearchSourceManagement
│   ├── TestCrawlResultStorage
│   ├── TestSourceRelationshipMapping
│   ├── TestAdvancedSearchMethods
│   ├── TestBatchOperations
│   └── TestHelperMethods
└── Integration Tests
    └── test_error_handling
```

## Key Testing Concepts

### 1. Mock Strategy

**Supabase Client Mocking:**
```python
table_mock.insert = Mock(return_value=table_mock)  # Chaining
table_mock.execute = Mock()  # Terminal method
```

**Why This Pattern?**
- Supabase uses method chaining: `client.table().select().eq().execute()`
- Each method returns self until `execute()`
- Allows testing the exact API calls made

### 2. Async Testing

```python
@pytest.mark.asyncio
async def test_method(self, storage):
```

**Why Async Tests?**
- All storage methods are async
- Tests must await results
- Fixtures can be async too

### 3. Patching Strategy

```python
with patch.object(storage, '_process_and_store_chunks', return_value=["chunk1"]):
```

**Why Patch Helper Methods?**
- Isolates unit under test
- Avoids complex setup for internal methods
- Tests one thing at a time

## Test Categories Explained

### Research Source Management Tests

**What They Test:**
- Storing sources with/without content
- Credibility updates with history
- URL-based retrieval with relationships

**Key Test Case:**
```python
async def test_store_research_source_with_content():
    # Tests the full pipeline:
    # 1. Store metadata
    # 2. Queue for embeddings
    # 3. Process chunks
```

**Edge Cases Covered:**
- Missing authors
- No full content
- Duplicate URLs (upsert behavior)

### Crawl Result Storage Tests

**What They Test:**
- Converting crawl data to sources
- Maintaining parent-child relationships
- Building hierarchical structures

**Key Insight:**
Tests verify that crawled pages get lower credibility scores (capped at 0.8) than academic sources.

### Relationship Mapping Tests

**What They Test:**
- Creating explicit relationships
- Automatic similarity calculation
- Bidirectional relationship queries

**Important Pattern:**
```python
# Mock RPC call for SQL functions
mock_supabase.rpc.return_value.execute.return_value = Mock(data=[...])
```

### Advanced Search Tests

**What They Test:**
- Multi-criteria filtering
- Hybrid search scoring
- Relationship-aware results

**Hybrid Search Logic:**
```python
weights = {"keyword": 0.4, "vector": 0.6}
# Tests that sources matching both get highest scores
```

### Batch Operation Tests

**What They Test:**
- Efficient multi-source storage
- Queue processing with failures
- Batch size limits

**Key Test:**
```python
async def test_batch_process_embeddings():
    # Verifies status transitions:
    # pending -> processing -> completed/failed
```

## Common Testing Pitfalls

### 1. Forgetting Mock Chaining
```python
# Wrong - Won't work
mock_supabase.table.return_value = {"data": [...]}

# Right - Proper chaining
mock_supabase.table().select().execute.return_value = Mock(data=[...])
```

### 2. Not Mocking Internal Methods
```python
# Wrong - Will try to actually process chunks
await storage.store_research_source(source, full_content="...")

# Right - Mock the internal method
with patch.object(storage, '_process_and_store_chunks'):
    await storage.store_research_source(source, full_content="...")
```

### 3. Incorrect Async Testing
```python
# Wrong - Not awaited
def test_async_method(self, storage):
    result = storage.async_method()  # Returns coroutine!

# Right - Properly awaited
@pytest.mark.asyncio
async def test_async_method(self, storage):
    result = await storage.async_method()
```

## Test Data Patterns

### UUID Generation
```python
source_id = str(uuid4())  # Realistic IDs
```

### Realistic Academic Sources
```python
AcademicSource(
    title="Understanding Deep Learning",
    url="https://example.edu/deep-learning",
    credibility_score=0.95  # High for .edu
)
```

### Mock Embeddings
```python
query_embedding = [0.1] * 1536  # Correct dimensions
```

## Assertions Strategy

### Verify API Calls
```python
mock_supabase.table.assert_called_with("research_sources")
assert mock_supabase.table().update.call_count >= 2
```

### Check Data Integrity
```python
call_args = mock_supabase.table().upsert.call_args[0][0]
assert call_args["url"] == sample_academic_source.url
```

### Validate Business Logic
```python
assert result[0]["combined_score"] > result[1]["combined_score"]
```

## Error Handling Tests

### Database Errors
```python
mock_supabase.table().execute.side_effect = Exception("Database error")
```

### Graceful Failures
```python
result = await storage.get_source_by_url("https://test.com")
assert result is None  # Should handle error gracefully
```

## Performance Considerations

### Batch Size Testing
- Default: 100 for inserts
- Embedding queue: 10 (API limits)
- Tests verify batching works correctly

### Mock Performance
- Mocks are instant - no actual DB calls
- Can test with large datasets efficiently

## Integration Points

### With Base VectorStorage
- Tests inheritance works correctly
- Verifies parent methods still accessible

### With Models
- Uses actual Pydantic models
- Tests serialization/deserialization

### With Embeddings
- Mocks embedding generation
- Tests queue processing logic

## Running the Tests

### Individual Test Class
```bash
pytest tests/test_rag/test_enhanced_storage.py::TestResearchSourceManagement -v
```

### Specific Test
```bash
pytest tests/test_rag/test_enhanced_storage.py::test_hybrid_search -v
```

### With Coverage
```bash
pytest tests/test_rag/test_enhanced_storage.py --cov=rag.enhanced_storage
```

## Debugging Failed Tests

### 1. Check Mock Calls
```python
print(mock_supabase.table.mock_calls)  # See all calls made
```

### 2. Verify Data Flow
```python
print(f"Args passed: {mock_supabase.table().upsert.call_args}")
```

### 3. Async Issues
```python
# Add await where needed
# Check @pytest.mark.asyncio decorator
```

## Next Steps for Testing

### Additional Tests Needed:
1. **Concurrent Operations**: Test parallel source storage
2. **Large Datasets**: Test with 1000+ sources
3. **Network Failures**: Test retry logic
4. **Memory Usage**: Test with large content

### Integration Tests:
1. With real Supabase (test environment)
2. With actual embeddings
3. End-to-end research workflow

## What Questions Do You Have, Finn?

These tests ensure our enhanced storage is rock-solid. Would you like me to:
1. Show how to debug a specific failing test?
2. Add more edge case tests?
3. Create integration tests with the research agent?

Try this exercise: Add a test for what happens when you try to create a circular relationship (A->B->C->A). How should the system handle this?