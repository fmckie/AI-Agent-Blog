# Google Drive Configuration Module - Detailed Explanation

## Purpose
The `rag/drive/config.py` module provides a centralized configuration system for all Google Drive integration features in the SEO Content Automation System. It uses Pydantic for validation and supports both file-based and environment variable configuration.

## Architecture

### Core Components

1. **DriveConfig Class**
   - Pydantic model that defines all Drive-related settings
   - Provides validation, type checking, and default values
   - Supports environment variable overrides with `GOOGLE_DRIVE_` prefix

2. **Configuration Categories**
   - **Upload Settings**: Controls automatic uploads and folder organization
   - **Batch Settings**: Manages batch upload operations and concurrency
   - **Error Handling**: Defines retry logic and failure management
   - **MIME Type Support**: Specifies supported file types and conversions
   - **Sync Settings**: Controls document synchronization intervals
   - **Metadata Settings**: Manages document properties and tags
   - **Rate Limiting**: Prevents API quota exhaustion

3. **Helper Functions**
   - `load_drive_config()`: Loads configuration from JSON or environment
   - `save_drive_config()`: Persists configuration to JSON file
   - `get_drive_config()`: Returns singleton configuration instance
   - `set_drive_config()`: Updates the global configuration

## Key Concepts

### 1. Folder Structure Patterns
The `folder_structure` field supports dynamic patterns:
- `YYYY`: Current year (e.g., 2025)
- `MM`: Current month (e.g., 01)
- `DD`: Current day (e.g., 07)
- `keyword`: Article's target keyword
- `title`: Article title (sanitized)

Example: `"YYYY/MM/keyword"` → `"2025/01/seo-optimization"`

### 2. MIME Type Mapping
Converts source file types to Google Drive formats:
```python
"text/html" → "application/vnd.google-apps.document"
"text/markdown" → "application/vnd.google-apps.document"
```

### 3. Retry Strategy
Implements exponential backoff:
- Initial delay: `retry_delay` seconds
- Backoff multiplier: 2x
- Maximum attempts: `max_retries`

### 4. Batch Upload Logic
- Processes `batch_size` articles at once
- Runs `concurrent_uploads` operations in parallel
- Quarantines articles after `quarantine_after_retries` total attempts

## Decision Rationale

### Why Pydantic?
1. **Type Safety**: Ensures configuration values are correct types
2. **Validation**: Built-in validators prevent invalid configurations
3. **Environment Support**: Automatic loading from environment variables
4. **Serialization**: Easy JSON export/import

### Why Singleton Pattern?
1. **Consistency**: Single configuration instance across the application
2. **Performance**: Avoid repeated file I/O
3. **Simplicity**: Easy access via `get_drive_config()`

### Default Values Reasoning
- **batch_size=10**: Balance between efficiency and memory usage
- **concurrent_uploads=3**: Prevent overwhelming the API
- **retry_delay=60**: Give temporary issues time to resolve
- **sync_interval=300**: 5 minutes balances freshness vs API usage

## Learning Path

1. **Start Here**: Understand Pydantic models and validation
2. **Next**: Learn about environment variable configuration
3. **Then**: Study retry patterns and exponential backoff
4. **Advanced**: Explore concurrent upload strategies

## Real-World Applications

### Enterprise Integration
```python
# Configure for high-volume production use
config = DriveConfig(
    batch_size=50,
    concurrent_uploads=10,
    max_retries=5,
    notify_on_error=True,
    custom_properties={"department": "content", "project": "seo"}
)
```

### Development Setup
```python
# Configure for testing
config = DriveConfig(
    auto_upload=False,  # Manual control
    batch_size=1,       # Process one at a time
    log_failures=True,  # Detailed debugging
    retry_delay=5       # Fast retries for testing
)
```

### Rate-Limited Environment
```python
# Configure for API quota constraints
config = DriveConfig(
    requests_per_minute=30,  # Half the default
    concurrent_uploads=1,    # Sequential processing
    sync_interval=600       # 10-minute intervals
)
```

## Common Pitfalls

1. **Invalid Folder Patterns**
   ```python
   # Wrong: Uses unsupported pattern
   folder_structure = "YYYY/MONTH/DAY"  # 'MONTH' not supported
   
   # Right: Use supported patterns
   folder_structure = "YYYY/MM/DD"
   ```

2. **Excessive Retries**
   ```python
   # Wrong: Too aggressive
   max_retries = 20
   retry_delay = 1
   
   # Right: Reasonable limits
   max_retries = 3
   retry_delay = 60
   ```

3. **Missing Environment Variables**
   ```python
   # Wrong: Assumes env vars exist
   config = DriveConfig()  # May use defaults
   
   # Right: Provide explicit values
   config = load_drive_config(Path("drive_config.json"))
   ```

## Best Practices

1. **Configuration Validation**
   Always validate configuration on startup:
   ```python
   try:
       config = get_drive_config()
       # Validate critical settings
       assert config.default_folder_id, "Drive folder ID required"
   except Exception as e:
       logger.error(f"Invalid Drive configuration: {e}")
       sys.exit(1)
   ```

2. **Environment-Specific Configs**
   Use different config files per environment:
   ```python
   env = os.getenv("ENVIRONMENT", "development")
   config_path = Path(f"configs/drive_config.{env}.json")
   config = load_drive_config(config_path)
   ```

3. **Configuration Updates**
   Update configuration dynamically:
   ```python
   config = get_drive_config()
   if high_error_rate:
       config.retry_delay *= 2  # Increase delay
       config.concurrent_uploads = 1  # Reduce load
   ```

## Security Considerations

1. **Never Include Credentials**: Configuration should not contain API keys or tokens
2. **Validate User Input**: Custom properties should be sanitized
3. **Limit Retry Attempts**: Prevent infinite retry loops
4. **Monitor Rate Limits**: Respect API quotas to avoid suspension

## Performance Implications

- **Batch Size**: Larger batches = fewer API calls but more memory
- **Concurrent Uploads**: More parallelism = faster but higher load
- **Sync Interval**: Shorter = more responsive but more API usage
- **Retry Delay**: Longer = more resilient but slower recovery

## What questions do you have about this configuration system, Finn?
Would you like me to explain any specific configuration option in more detail?
Try this exercise: Create a configuration optimized for uploading 1000 articles per day with minimal API usage.