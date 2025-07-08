# RAG Module Test Coverage Analysis

## Overview
This document provides a comprehensive analysis of the RAG module files with low test coverage, identifying untested functions, required mocks, and specific test scenarios.

## 1. rag/drive/storage.py (12.96% Coverage)

### Classes and Methods to Test

#### DriveStorageHandler Class
- `__init__(self, client: Optional[Client] = None)` - Constructor with optional Supabase client
- `track_upload(self, article_id: UUID, drive_file_id: str, drive_url: str, folder_path: str) -> bool`
- `track_drive_document(self, file_id: str, file_name: str, mime_type: str, drive_url: str, folder_path: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[UUID]`
- `get_uploaded_articles(self, limit: int = 50, offset: int = 0, include_metadata: bool = True) -> List[Dict[str, Any]]`
- `get_sync_status(self, file_id: str) -> Optional[Dict[str, Any]]`
- `_update_sync_status(self, file_id: str, local_path: str, drive_url: str, status: str, error_message: Optional[str] = None) -> bool`
- `get_pending_uploads(self, limit: int = 10) -> List[Dict[str, Any]]`
- `mark_upload_error(self, article_id: UUID, error_message: str) -> bool`
- `get_drive_documents(self, source_type: str = "drive", limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]`
- `cleanup_orphaned_sync_records(self, dry_run: bool = True) -> Tuple[int, List[str]]`

### External Dependencies to Mock
- `supabase.Client` - Main database client
- `config.get_config()` - Configuration getter
- `rag.config.get_rag_config()` - RAG configuration getter
- Database table operations: `generated_articles`, `drive_sync_status`, `research_documents`

### Test Scenarios

#### Positive Test Cases
1. **Constructor Tests**
   - Test with provided client
   - Test without client (creates new one)
   - Verify configuration loading

2. **track_upload Tests**
   - Successful article upload tracking
   - Update of sync status after upload
   - Return true on success

3. **track_drive_document Tests**
   - Successful document tracking with metadata
   - Proper JSON serialization of metadata
   - UUID return on success

4. **get_uploaded_articles Tests**
   - Retrieve articles with Drive info
   - Pagination (limit/offset)
   - Include/exclude metadata
   - Empty result handling

5. **get_sync_status Tests**
   - Retrieve existing sync status
   - Handle non-existent file ID

6. **_update_sync_status Tests**
   - Create new sync status
   - Update existing sync status
   - Handle upsert operation

7. **get_pending_uploads Tests**
   - Find articles without drive_file_id
   - Respect limit parameter
   - Order by creation date

8. **get_drive_documents Tests**
   - Filter by source type
   - Parse JSON metadata
   - Handle pagination

9. **cleanup_orphaned_sync_records Tests**
   - Dry run mode (report only)
   - Actual deletion mode
   - Identify orphaned article references
   - Identify orphaned document references

#### Negative Test Cases
1. **Database Connection Failures**
   - Mock Supabase client errors
   - Test error logging

2. **Invalid Data Handling**
   - Invalid UUIDs
   - Malformed metadata
   - Database constraint violations

3. **Exception Handling**
   - Network timeouts
   - JSON parsing errors
   - Database query failures

#### Edge Cases
1. **Empty Results**
   - No uploaded articles
   - No pending uploads
   - No orphaned records

2. **Data Integrity**
   - Concurrent updates
   - Partial failures in multi-step operations

## 2. rag/drive/uploader.py (13.46% Coverage)

### Classes and Methods to Test

#### ArticleUploader Class
- `__init__(self, auth: Optional[GoogleDriveAuth] = None, upload_folder_id: Optional[str] = None)`
- `upload_html_as_doc(self, html_content: str, title: str, metadata: Optional[Dict[str, Any]] = None, folder_path: Optional[str] = None) -> Dict[str, Any]`
- `upload_file(self, file_path: Path, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, folder_path: Optional[str] = None, convert_to_docs: bool = True) -> Dict[str, Any]`
- `create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str`
- `_ensure_folder_path(self, folder_path: str) -> str`
- `_find_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]`
- `_prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, str]`
- `update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool`
- `get_upload_folder_structure(self) -> Dict[str, Any]`
- `_get_folder_tree(self, folder_id: str, level: int = 0, max_level: int = 3) -> Dict[str, Any]`

### External Dependencies to Mock
- `googleapiclient.discovery.build` - Google API client builder
- `GoogleDriveAuth` - Authentication handler
- `config.get_config()` - Configuration
- Google Drive API service methods: `files().create()`, `files().list()`, `files().get()`, `files().update()`
- `MediaIoBaseUpload`, `MediaFileUpload` - File upload handlers

### Test Scenarios

#### Positive Test Cases
1. **Constructor Tests**
   - With custom auth instance
   - Without auth (creates new)
   - With custom upload folder ID
   - Default folder from config

2. **upload_html_as_doc Tests**
   - Simple HTML upload
   - Upload with metadata
   - Upload to specific folder path
   - Folder creation if needed
   - Return proper response dict

3. **upload_file Tests**
   - Upload various file types
   - Custom title vs filename
   - Convert to Google Docs
   - Skip conversion
   - Handle different MIME types

4. **create_folder Tests**
   - Create new folder
   - Use cached folder ID
   - Find existing folder
   - Create with parent
   - Create in root

5. **_ensure_folder_path Tests**
   - Create nested folder structure
   - Handle existing paths
   - Parse path components

6. **_find_folder Tests**
   - Find existing folder
   - Search with parent constraint
   - Handle not found

7. **_prepare_metadata Tests**
   - Convert various data types to strings
   - Handle lists/dicts as JSON
   - Boolean conversion
   - None value handling

8. **update_file_metadata Tests**
   - Successful metadata update
   - Handle API response

9. **get_upload_folder_structure Tests**
   - Retrieve folder tree
   - Handle missing upload folder
   - Recursive structure building

#### Negative Test Cases
1. **API Errors**
   - HttpError handling
   - Network failures
   - Rate limiting
   - Authentication failures

2. **File System Errors**
   - FileNotFoundError for uploads
   - Invalid file paths
   - Permission errors

3. **Invalid Input**
   - Empty HTML content
   - Invalid folder paths
   - Malformed metadata

#### Edge Cases
1. **Large Files**
   - Resumable upload behavior
   - Memory efficiency

2. **Special Characters**
   - File names with special chars
   - Folder names with unicode

3. **Concurrency**
   - Folder cache consistency
   - Race conditions in folder creation

## 3. rag/processor.py (13.66% Coverage)

### Classes and Methods to Test

#### TextChunk Class
- `to_dict(self) -> Dict[str, Any]`

#### TextProcessor Class
- `__init__(self, config: RAGConfig)`
- `chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]`
- `_normalize_text(self, text: str) -> str`
- `_split_sentences(self, text: str) -> List[str]`
- `_create_chunks_from_sentences(self, sentences: List[str]) -> List[str]`
- `process_research_findings(self, findings: ResearchFindings) -> List[TextChunk]`
- `_process_academic_source(self, source: AcademicSource, keyword: str) -> List[TextChunk]`
- `extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]`
- `estimate_token_count(self, text: str) -> int`

### External Dependencies to Mock
- `RAGConfig` - Configuration object
- `ResearchFindings` - Model class
- `AcademicSource` - Model class

### Test Scenarios

#### Positive Test Cases
1. **TextChunk Tests**
   - Convert to dictionary with all fields
   - Handle optional source_id

2. **Constructor Tests**
   - Initialize with config
   - Compile regex patterns

3. **chunk_text Tests**
   - Normal text chunking
   - Respect chunk size
   - Handle overlap correctly
   - Add metadata to chunks
   - Generate chunk indices

4. **_normalize_text Tests**
   - Replace multiple whitespaces
   - Remove control characters
   - Normalize line breaks
   - Collapse multiple newlines

5. **_split_sentences Tests**
   - Handle common abbreviations
   - Split on sentence endings
   - Preserve abbreviation dots
   - Filter empty sentences

6. **_create_chunks_from_sentences Tests**
   - Create chunks within size limit
   - Handle overlap between chunks
   - Split oversized sentences
   - Process final chunk

7. **process_research_findings Tests**
   - Process all finding components
   - Handle academic sources
   - Process main findings
   - Process statistics
   - Combine all chunks

8. **_process_academic_source Tests**
   - Create chunks with metadata
   - Set source URLs
   - Calculate credibility flags
   - Include all source fields

9. **extract_key_phrases Tests**
   - Find capitalized sequences
   - Remove URLs first
   - Limit phrase length
   - Return unique phrases

10. **estimate_token_count Tests**
    - Basic character-based estimation

#### Negative Test Cases
1. **Empty/Invalid Input**
   - Empty text
   - Text below minimum size
   - None text input
   - Whitespace-only text

2. **Edge Cases in Chunking**
   - Single word exceeding chunk size
   - Text with no sentence endings
   - Only abbreviations

3. **Malformed Research Data**
   - Missing required fields
   - Invalid academic sources
   - Empty findings lists

#### Edge Cases
1. **Unicode and Special Characters**
   - Emoji handling
   - Non-ASCII characters
   - Mixed scripts

2. **Performance Cases**
   - Very long texts
   - Many small sentences
   - Deeply nested data

## 4. rag/retriever.py (12.32% Coverage)

### Classes and Methods to Test

#### RetrievalStatistics Class
- `__init__(self)`
- `record_exact_hit(self, response_time: float)`
- `record_semantic_hit(self, response_time: float)`
- `record_cache_miss(self, response_time: float)`
- `record_error(self)`
- Properties: `cache_hit_rate`, `average_cache_response_time`, `average_api_response_time`
- `get_summary(self) -> Dict[str, Any]`

#### ResearchRetriever Class
- `__init__(self)`
- `_ensure_pool_warmed(self)`
- `retrieve_or_research(self, keyword: str, research_function: Callable[[], Any]) -> ResearchFindings`
- `_check_exact_cache(self, keyword: str) -> Optional[Dict[str, Any]]`
- `_semantic_search(self, keyword: str) -> Optional[ResearchFindings]`
- `_reconstruct_findings_from_cache(self, cache_entry: Dict[str, Any]) -> ResearchFindings`
- `_reconstruct_findings_from_chunks(self, chunks: List[tuple], original_keyword: str) -> ResearchFindings`
- `_dict_to_findings(self, result_dict: Dict[str, Any], keyword: str) -> ResearchFindings`
- `_extract_domain(self, url: str) -> str`
- `_calculate_credibility(self, domain: str, result: Dict[str, Any]) -> float`
- `_store_research(self, findings: ResearchFindings) -> None`
- `warm_cache(self, keywords: List[str], research_function: Callable) -> Dict[str, Any]`
- `get_instance_statistics(self) -> Dict[str, Any]`
- `get_statistics(cls) -> Optional[Dict[str, Any]]` (class method)
- `cleanup(self) -> None`

### External Dependencies to Mock
- `get_rag_config()` - Configuration
- `TextProcessor` - Text processing
- `EmbeddingGenerator` - Embedding generation
- `VectorStorage` - Storage operations
- `ResearchFindings`, `AcademicSource` - Model classes

### Test Scenarios

#### Positive Test Cases
1. **Statistics Tests**
   - Record different hit types
   - Calculate correct rates
   - Track response times
   - Generate summary

2. **Retriever Constructor Tests**
   - Initialize components
   - Track instance for statistics
   - Set pool warming flag

3. **Pool Warming Tests**
   - Warm on first use only
   - Handle warming failures gracefully

4. **retrieve_or_research Tests**
   - Exact cache hit flow
   - Semantic cache hit flow
   - Cache miss with research
   - Store new research
   - Track statistics correctly

5. **Cache Check Tests**
   - Find exact matches
   - Handle missing entries
   - Handle storage errors

6. **Semantic Search Tests**
   - Generate embeddings
   - Find similar chunks
   - Group by keyword
   - Calculate similarities
   - Reconstruct findings

7. **Reconstruction Tests**
   - From cache entry
   - From semantic chunks
   - Handle all content types
   - Preserve metadata

8. **Conversion Tests**
   - Dict to findings
   - Extract domains
   - Calculate credibility
   - Process Tavily results

9. **Storage Tests**
   - Process findings to chunks
   - Generate embeddings
   - Store with metadata
   - Handle storage failures

10. **Cache Warming Tests**
    - Process keyword list
    - Skip cached keywords
    - Handle failures
    - Return summary

11. **Statistics and Cleanup Tests**
    - Get instance stats
    - Combine class stats
    - Clean up resources

#### Negative Test Cases
1. **Error Handling**
   - Research function failures
   - Storage errors
   - Embedding errors
   - Network failures

2. **Invalid Input**
   - Empty keywords
   - Invalid research results
   - Malformed cache data

3. **Edge Cases**
   - No similar chunks found
   - Below similarity threshold
   - Empty research findings
   - Concurrent access

## Testing Strategy Recommendations

### 1. Mock Strategy
- Use `unittest.mock` for all external dependencies
- Create reusable fixtures for common mocks
- Mock at the boundary (external APIs, database)

### 2. Test Organization
- Group tests by class/functionality
- Use descriptive test names
- Include docstrings explaining test purpose

### 3. Coverage Goals
- Aim for 80%+ coverage per file
- Focus on critical paths first
- Test error handling thoroughly

### 4. Performance Testing
- Add tests for chunking large texts
- Test connection pool efficiency
- Measure embedding generation speed

### 5. Integration Testing
- Test component interactions
- Verify end-to-end flows
- Test with real-like data

## Implementation Priority

1. **High Priority** (Core functionality)
   - ResearchRetriever.retrieve_or_research
   - DriveStorageHandler.track_upload
   - TextProcessor.chunk_text
   - ArticleUploader.upload_html_as_doc

2. **Medium Priority** (Supporting features)
   - Semantic search functionality
   - Folder management
   - Statistics tracking
   - Cache warming

3. **Low Priority** (Utilities)
   - Metadata preparation
   - Key phrase extraction
   - Folder tree visualization