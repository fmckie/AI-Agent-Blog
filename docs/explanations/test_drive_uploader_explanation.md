# Google Drive Uploader Tests - Detailed Explanation

## Purpose
This test suite comprehensively tests the Google Drive upload functionality, including both single article uploads (ArticleUploader) and batch operations (BatchUploader). It ensures reliability, error handling, and performance of the Drive integration.

## Architecture

### Test Structure
1. **TestArticleUploader**: Tests single file upload operations
2. **TestBatchUploader**: Tests batch upload with concurrency and retries

### Key Testing Patterns

#### 1. Mock Fixtures
```python
@pytest.fixture
def mock_drive_service(self):
    """Create mock Google Drive service."""
    service = Mock()
    # Setup chainable mocks
    files_mock = Mock()
    service.files.return_value = files_mock
```
- Creates realistic mock of Google Drive API
- Supports method chaining (e.g., `service.files().create().execute()`)
- Isolates tests from actual API calls

#### 2. Dependency Injection
```python
@pytest.fixture
def uploader(self, mock_auth, mock_drive_service):
    """Create ArticleUploader with mocked dependencies."""
    mock_auth.get_service.return_value = mock_drive_service
    uploader = ArticleUploader(auth=mock_auth)
    uploader.service = mock_drive_service
    return uploader
```
- Injects mocked dependencies
- Allows testing without network calls
- Enables precise behavior verification

## Key Concepts

### 1. HTML to Google Docs Conversion
The uploader converts HTML articles to Google Docs format:
```python
def test_upload_html_as_doc_success(self, uploader):
    html_content = "<html><body><h1>Test</h1></body></html>"
    result = uploader.upload_html_as_doc(html_content, "Test")
```
- Tests MIME type conversion
- Verifies metadata attachment
- Ensures proper file naming

### 2. Folder Hierarchy Management
Tests automatic folder creation:
```python
def test_ensure_folder_path_creates_hierarchy(self, uploader):
    final_id = uploader._ensure_folder_path("2025/01/07")
    # Verifies: root → 2025 → 01 → 07
```
- Tests recursive folder creation
- Verifies parent-child relationships
- Ensures idempotency (doesn't recreate existing)

### 3. Caching Strategy
Tests folder ID caching for performance:
```python
def test_create_folder_uses_cache(self, uploader):
    uploader._folder_cache["root/TestFolder"] = "cached_id"
    folder_id = uploader.create_folder("TestFolder", "root")
    # No API call made - uses cache
```

### 4. Batch Processing
Tests concurrent upload with limits:
```python
async def test_upload_pending_articles_success(self, batch_uploader):
    result = await batch_uploader.upload_pending_articles(articles)
    assert result["stats"]["successful"] == 2
```
- Tests batch size limits
- Verifies concurrent execution
- Ensures proper statistics tracking

### 5. Retry Logic
Tests exponential backoff on failures:
```python
def test_upload_article_with_retry_success_on_retry(self):
    # Fails once, then succeeds
    uploader.upload_html_as_doc.side_effect = [
        Exception("Network error"),
        {"file_id": "success_id", ...}
    ]
```

## Decision Rationale

### Why Mock Google Drive API?
1. **Speed**: Tests run instantly without network calls
2. **Reliability**: No dependency on Google's services
3. **Control**: Can simulate any error condition
4. **Cost**: No API quota usage during testing

### Why Test Folder Caching?
1. **Performance**: Reduces API calls by 90%+
2. **Rate Limits**: Helps avoid quota exhaustion
3. **Consistency**: Ensures folder structure stability

### Why Async Batch Upload?
1. **Efficiency**: Processes multiple files concurrently
2. **Scalability**: Handles hundreds of articles
3. **Resilience**: Continues despite individual failures

## Learning Path

1. **Start with**: Single file upload tests
2. **Then understand**: Folder management and caching
3. **Move to**: Batch processing patterns
4. **Finally**: Error handling and retry strategies

## Real-World Applications

### Testing Upload Failures
```python
# Simulate network timeout
mock_service.files().create().execute.side_effect = HttpError(
    resp=Mock(status=504), content=b'Gateway Timeout'
)
```

### Testing Rate Limiting
```python
# Simulate quota exceeded
mock_service.files().create().execute.side_effect = HttpError(
    resp=Mock(status=429), content=b'Rate Limit Exceeded'
)
```

### Testing Large Batches
```python
# Create 100 articles
articles = [create_test_article(i) for i in range(100)]
result = await batch_uploader.upload_pending_articles(articles)
```

## Common Pitfalls

1. **Forgetting to Mock Chainable Methods**
   ```python
   # Wrong - won't work
   mock_service.files.create.execute.return_value = {...}
   
   # Right - proper chaining
   mock_service.files().create().execute.return_value = {...}
   ```

2. **Not Testing Edge Cases**
   ```python
   # Test empty folder path
   uploader._ensure_folder_path("")
   
   # Test special characters
   uploader.create_folder("Folder/With:Special*Chars")
   ```

3. **Ignoring Async Context**
   ```python
   # Wrong - not async
   def test_batch_upload(self):
       batch_uploader.upload_pending_articles(articles)
   
   # Right - async test
   @pytest.mark.asyncio
   async def test_batch_upload(self):
       await batch_uploader.upload_pending_articles(articles)
   ```

## Best Practices

1. **Test Both Success and Failure Paths**
   - Every feature should have success tests
   - Every feature should have failure tests
   - Test edge cases and boundary conditions

2. **Use Realistic Test Data**
   ```python
   # Good - realistic HTML
   html = "<html><body><h1>SEO Guide</h1><p>Content...</p></body></html>"
   
   # Bad - minimal test data
   html = "<html></html>"
   ```

3. **Verify Side Effects**
   ```python
   # Verify database updated
   assert storage.track_upload.called
   
   # Verify statistics updated
   assert uploader.stats["successful"] == expected
   ```

4. **Test Concurrency Limits**
   ```python
   # Verify respects concurrent_uploads setting
   with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
       mock_executor.assert_called_with(max_workers=3)
   ```

## Security Considerations

1. **Never Use Real Credentials**: Always mock authentication
2. **Sanitize Test Data**: Don't include sensitive information
3. **Test Permission Errors**: Verify proper handling of 403 errors
4. **Mock Token Refresh**: Test expired credential handling

## Performance Testing

1. **Batch Size Optimization**
   ```python
   # Test different batch sizes
   for batch_size in [1, 10, 50, 100]:
       config.batch_size = batch_size
       # Measure performance
   ```

2. **Concurrent Upload Limits**
   ```python
   # Test concurrent limits
   for concurrent in [1, 5, 10]:
       config.concurrent_uploads = concurrent
       # Measure throughput
   ```

3. **Cache Hit Rates**
   ```python
   # Verify cache effectiveness
   assert uploader._folder_cache.hits > uploader._folder_cache.misses
   ```

## What questions do you have about these tests, Finn?
Would you like me to explain any specific test pattern in more detail?
Try this exercise: Write a test for handling a new error case, like a file that's too large to upload.