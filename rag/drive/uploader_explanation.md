# Google Drive Article Uploader - Detailed Explanation

## Purpose
The `uploader.py` module handles uploading generated SEO articles to Google Drive, converting HTML content to Google Docs format, and organizing files in a structured folder hierarchy.

## Architecture

### Core Components

1. **ArticleUploader Class** - Main uploader with features:
   - HTML to Google Docs conversion
   - Automatic folder creation and organization
   - Metadata attachment
   - Folder caching for performance
   - Multiple upload methods

2. **Key Features**:
   - **Format Conversion**: Automatically converts HTML to Google Docs
   - **Folder Organization**: Creates date-based or custom folder structures
   - **Metadata Support**: Attaches keywords, timestamps, and custom data
   - **Caching**: Reduces API calls by caching folder lookups
   - **Error Handling**: Graceful handling of network issues

### Main Methods

#### `upload_html_as_doc()`
Uploads HTML content directly as a Google Doc:
```python
result = uploader.upload_html_as_doc(
    html_content="<h1>My Article</h1><p>Content...</p>",
    title="SEO Guide for 2025",
    metadata={"keywords": ["seo", "guide"], "author": "AI"},
    folder_path="2025/01/07"
)
```

#### `upload_file()`
Uploads a file from disk:
```python
result = uploader.upload_file(
    file_path=Path("article.html"),
    title="Custom Title",
    convert_to_docs=True  # Convert to Google Doc
)
```

#### `create_folder()`
Creates folders with automatic deduplication:
```python
folder_id = uploader.create_folder("January 2025", parent_id="...")
```

## Folder Organization Strategy

The uploader supports flexible folder organization:

```
Upload Folder (Root)
├── 2025/
│   ├── 01/
│   │   ├── 07/
│   │   │   ├── "SEO Best Practices"
│   │   │   └── "Content Marketing Guide"
│   │   └── 08/
│   │       └── "Keyword Research Tips"
│   └── 02/
│       └── ...
└── By Topic/
    ├── Technical SEO/
    └── Content Strategy/
```

## Metadata Management

Metadata is attached as Google Drive properties:
- **keywords**: List of keywords used
- **generation_date**: When article was created
- **research_sources**: Number of sources used
- **word_count**: Article length
- **seo_score**: Quality metrics

Example:
```python
metadata = {
    "keywords": ["python", "automation"],
    "generation_date": "2025-01-07",
    "word_count": 1500,
    "seo_score": 85
}
```

## Performance Optimizations

1. **Folder Caching**:
   - Caches folder IDs to avoid repeated lookups
   - Significantly reduces API calls

2. **Resumable Uploads**:
   - Large files upload in chunks
   - Can resume if connection drops

3. **Batch Operations**:
   - Methods designed for efficient bulk uploads

## Error Handling

The uploader handles various error scenarios:

1. **Authentication Errors**:
   - Token refresh handled automatically
   - Clear error messages for auth issues

2. **Network Errors**:
   - Resumable uploads for large files
   - Retry logic for transient failures

3. **Quota Errors**:
   - Detects API quota exceeded
   - Provides clear feedback

## Integration with Workflow

The uploader integrates seamlessly with the article generation workflow:

```python
# After article generation
html_content = article.to_html()

# Upload to Drive
uploader = ArticleUploader()
result = uploader.upload_html_as_doc(
    html_content=html_content,
    title=article.title,
    metadata={
        "keywords": research.keywords,
        "sources": len(research.sources),
        "generated_at": datetime.now().isoformat()
    },
    folder_path=f"{datetime.now().year}/{datetime.now().month:02d}"
)

# Save Drive URL for reference
article.drive_url = result['web_link']
```

## Usage Examples

### Basic Upload
```python
from rag.drive.uploader import ArticleUploader

uploader = ArticleUploader()

# Upload HTML content
result = uploader.upload_html_as_doc(
    html_content="<h1>Title</h1><p>Content</p>",
    title="My Article"
)
print(f"Uploaded to: {result['web_link']}")
```

### With Folder Organization
```python
# Create date-based folder structure
from datetime import datetime

date_path = datetime.now().strftime("%Y/%m/%d")
result = uploader.upload_html_as_doc(
    html_content=content,
    title=title,
    folder_path=date_path
)
```

### Batch Upload
```python
# Upload multiple articles
articles = [...]  # List of articles

for article in articles:
    result = uploader.upload_html_as_doc(
        html_content=article.html,
        title=article.title,
        metadata=article.metadata,
        folder_path=article.date_path
    )
    print(f"Uploaded: {article.title}")
```

## Security Considerations

1. **Permissions**:
   - Only creates/modifies files created by the app
   - Cannot delete user's existing files
   - Respects Drive sharing settings

2. **Data Privacy**:
   - Content uploaded remains private by default
   - No automatic sharing unless specified
   - Metadata stored as properties, not public

## Common Issues and Solutions

1. **"Parent folder not found"**
   - Ensure upload_folder_id is set correctly
   - Check folder exists and app has access

2. **"File too large"**
   - Use resumable uploads (automatic)
   - Check Drive storage quota

3. **"Invalid metadata"**
   - Ensure all metadata values are serializable
   - Complex objects converted to JSON strings

## Next Steps

With the uploader ready, we can:
1. Create CLI command for manual uploads
2. Integrate with workflow for automatic uploads
3. Add batch upload functionality
4. Implement version tracking

The uploader provides a robust foundation for managing articles in Google Drive with proper organization and metadata.