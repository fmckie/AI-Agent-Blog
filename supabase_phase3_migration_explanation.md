# Supabase Phase 3 Migration Explanation

## Purpose

This migration script creates the database infrastructure for storing and searching research content from scraped articles using vector embeddings. It's specifically designed for the SEO Content Automation System's research storage needs.

## What This Migration Does

### 1. Enables pgvector
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
- Adds vector data type support to PostgreSQL
- Enables similarity search on embeddings
- Required for AI-powered semantic search

### 2. Core Tables Structure

**research_sources**
- Stores article metadata (URL, title, domain)
- Holds full content from scraped articles
- Tracks credibility scores and publication dates
- No embeddings here - just source data

**content_chunks**
- Breaks articles into searchable chunks
- Stores OpenAI embeddings (1536 dimensions)
- Enables semantic search across research
- Tracks which embedding model was used

**source_relationships**
- Maps connections between articles
- Stores similarity scores
- Helps find related research

**research_findings**
- Aggregates insights by keyword
- Stores summaries and key statistics
- Links research sessions to outcomes

### 3. Performance Features

**Vector Index**
```sql
CREATE INDEX idx_chunks_embedding_cosine 
ON content_chunks 
USING ivfflat (chunk_embedding vector_cosine_ops)
WITH (lists = 100);
```
- Uses cosine distance (best for text)
- IVFFlat algorithm for fast searches
- Auto-adjustable based on data size

**Helper Functions**
- `search_similar_chunks()`: Find semantically similar content
- `find_related_sources()`: Discover connected articles
- `calculate_optimal_lists()`: Auto-tune index performance

### 4. Operational Tables

**embedding_queue**
- Tracks which articles need embeddings
- Monitors processing status
- Handles retry logic for failures

**search_history**
- Logs all vector searches
- Tracks performance metrics
- Helps optimize search parameters

## Key Design Decisions

### Why These Specific Tables?

1. **Separation of Concerns**
   - Sources: Raw article data
   - Chunks: Searchable segments with embeddings
   - Findings: Processed insights

2. **Chunk-Based Storage**
   - Articles are too long for single embeddings
   - Chunks allow precise semantic search
   - Overlap prevents context loss

3. **Tracking Everything**
   - Queue for embedding generation
   - History for search optimization
   - Relationships for discovery

### Why Cosine Distance?

For text embeddings, cosine distance is ideal because:
- It measures semantic similarity (angle between vectors)
- Ignores magnitude differences
- Perfect for comparing meaning, not length

### Why 1536 Dimensions?

- Matches OpenAI's text-embedding-ada-002 model
- Industry standard for text embeddings
- Good balance of accuracy and performance

## How It Works in Practice

### 1. Storing Research
```python
# 1. Scrape article
article = scrape_url("https://example.com/ai-article")

# 2. Store in research_sources
source_id = store_source(article)

# 3. Break into chunks
chunks = create_chunks(article.content, overlap=50)

# 4. Generate embeddings
embeddings = openai.embed(chunks)

# 5. Store in content_chunks with embeddings
store_chunks_with_embeddings(source_id, chunks, embeddings)
```

### 2. Searching Research
```python
# 1. Convert query to embedding
query_embedding = openai.embed("machine learning best practices")

# 2. Search similar chunks
results = search_similar_chunks(
    query_embedding,
    threshold=0.7,  # 70% similarity minimum
    limit=10
)

# 3. Retrieve full articles
articles = get_articles_from_chunks(results)
```

## Performance Considerations

### Index Optimization
- Formula: `lists = 4 * sqrt(row_count)`
- Automatically adjusts as data grows
- Re-index periodically for best performance

### Query Speed
- With proper indexing: <100ms for millions of chunks
- Without index: Several seconds
- Index build time: Few minutes for large datasets

## Common Operations

### Find Related Articles
```sql
SELECT * FROM find_related_sources(
    'source-uuid-here',
    similarity_threshold := 0.8,
    max_results := 5
);
```

### Search by Domain
```sql
SELECT * FROM search_similar_chunks(
    query_embedding := '[...]',
    domain_filter := 'arxiv.org'
);
```

### Monitor Performance
```sql
SELECT 
    AVG(execution_time_ms) as avg_time,
    COUNT(*) as search_count
FROM search_history
WHERE created_at > NOW() - INTERVAL '1 day';
```

## Migration Safety

### No Data Loss
- Only creates new tables
- Doesn't modify existing data
- Can be rolled back if needed

### Rollback Script
```sql
DROP TABLE IF EXISTS search_history CASCADE;
DROP TABLE IF EXISTS embedding_queue CASCADE;
DROP TABLE IF EXISTS content_chunks CASCADE;
DROP TABLE IF EXISTS source_relationships CASCADE;
DROP TABLE IF EXISTS research_findings CASCADE;
DROP TABLE IF EXISTS research_sources CASCADE;
DROP EXTENSION IF EXISTS vector;
```

## Next Steps After Migration

1. **Test Vector Operations**
   ```sql
   -- Create a test vector
   SELECT '[1,2,3]'::vector;
   ```

2. **Verify Tables**
   ```sql
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name LIKE 'research_%';
   ```

3. **Check Functions**
   ```sql
   SELECT routine_name 
   FROM information_schema.routines 
   WHERE routine_schema = 'public';
   ```

## What Questions Do You Have, Finn?

This migration creates a robust foundation for AI-powered research storage. Would you like me to:
1. Explain any specific part in more detail?
2. Show how to test the migration?
3. Create examples of using these tables?

Try this exercise: Think about how you'd search for "similar research" - would you search by keywords, concepts, or both? This migration enables both approaches!