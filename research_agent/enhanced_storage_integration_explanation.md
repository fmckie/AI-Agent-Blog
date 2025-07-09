# Research Agent Enhanced Storage Integration

This document explains how EnhancedVectorStorage has been integrated into the Research Agent tools, completing Phase 3.3 of the Tavily Enhancement Plan.

## Overview

The Research Agent now automatically stores all research data in the EnhancedVectorStorage system, providing:
- Persistent storage of research sources
- Full content archival with embeddings
- Source relationship mapping
- Crawl hierarchy preservation
- Advanced search capabilities

## Integration Points

### 1. search_academic()
When the Research Agent performs academic searches:
- All found sources are automatically stored in EnhancedVectorStorage
- Each source is saved with metadata but without embeddings initially
- Sources are marked for later embedding generation when full content is available

```python
# Store sources in EnhancedVectorStorage if available
if enhanced_storage_available and findings.academic_sources:
    storage = get_enhanced_storage()
    for source in findings.academic_sources:
        source_id = await storage.store_research_source(
            source=source,
            generate_embedding=False  # Will generate later with full content
        )
```

### 2. extract_full_content()
When extracting full content from URLs:
- Updates existing sources with complete content
- Generates embeddings for the full content
- Enables semantic search on article content

```python
# Update source with full content in EnhancedVectorStorage
source = AcademicSource(
    title=result.get("title", source_data["title"]),
    url=result.get("url"),
    excerpt=result.get("raw_content", "")[:500],
    domain=source_data["domain"],
    credibility_score=source_data["credibility_score"],
    source_type=source_data.get("source_type", "extracted")
)
await storage.store_research_source(
    source=source,
    full_content=result.get("raw_content"),
    generate_embedding=True
)
```

### 3. crawl_domain()
When crawling websites:
- Stores all crawled pages as sources
- Creates hierarchical relationships (crawled_from)
- Links related pages from the same crawl session

```python
# Store crawl results
stored_ids = await storage.store_crawl_results(
    crawl_data={"results": pages},
    parent_url=url,
    keyword=keyword
)

# Create relationships between crawled pages
for i in range(len(stored_ids) - 1):
    await storage.create_source_relationship(
        source_id=stored_ids[i],
        related_id=stored_ids[i + 1],
        relationship_type="related",
        metadata={"crawl_session": url}
    )
```

### 4. analyze_domain_structure()
When analyzing website structure:
- Stores domain analysis as a special source type
- Preserves insights about site organization
- Links to related sources from the domain

### 5. multi_step_research()
At the end of comprehensive research:
- Calculates similarities between all found sources
- Creates "similar" relationships based on content
- Enables discovery of related research

```python
# Calculate similarities between sources
for source_id in source_ids:
    await storage.calculate_source_similarities(
        source_id=source_id,
        threshold=0.7,
        max_relationships=3
    )
```

## Architecture

### Lazy Initialization
The integration uses lazy initialization to avoid import-time database connections:

```python
_enhanced_storage_instance: Optional[EnhancedVectorStorage] = None

def get_enhanced_storage() -> Optional[EnhancedVectorStorage]:
    """Get or create the global enhanced storage instance."""
    global _enhanced_storage_instance
    if enhanced_storage_available and _enhanced_storage_instance is None:
        try:
            _enhanced_storage_instance = EnhancedVectorStorage()
        except Exception as e:
            logger.error(f"Failed to initialize EnhancedVectorStorage: {e}")
            return None
    return _enhanced_storage_instance
```

### Graceful Degradation
If EnhancedVectorStorage is not available:
- The Research Agent continues to function normally
- Only basic RAG caching is used
- A warning is logged but no errors occur

### Error Handling
All storage operations are wrapped in try/except blocks:
- Storage failures don't interrupt research
- Warnings are logged for debugging
- Research results are always returned

## Benefits

1. **Research Persistence**: All research is permanently stored and searchable
2. **Relationship Discovery**: Find related sources automatically
3. **Crawl Tracking**: Understand which pages came from which domains
4. **Content Evolution**: Track how sources are enhanced with full content
5. **Advanced Queries**: Use the EnhancedVectorStorage search methods for complex lookups

## Usage

The integration is automatic - no code changes are needed in the Research Agent itself. Simply having EnhancedVectorStorage available enables all features.

To check if storage is active:
```python
if enhanced_storage_available:
    print("EnhancedVectorStorage is active")
```

## Future Enhancements

With this integration complete, future phases can build on the stored data:
- Research memory system (Phase 4)
- Source quality tracking over time
- Adaptive research strategies based on past results
- Learning from successful research patterns