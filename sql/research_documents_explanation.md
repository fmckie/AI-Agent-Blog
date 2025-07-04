# Research Documents Table Explanation

## Purpose
The `research_documents` table is the heart of our RAG system, storing chunked research content with vector embeddings to enable semantic search across all gathered knowledge.

## Architecture Overview
This table implements a modern approach to information retrieval by combining:
- Traditional database querying (exact matches)
- Vector similarity search (semantic understanding)
- Metadata filtering (credibility, source type)
- Performance optimization (specialized indexes)

## Key Concepts

### 1. Table Structure

#### Core Fields
```sql
id BIGSERIAL PRIMARY KEY
keyword TEXT NOT NULL
content TEXT NOT NULL
```
- **id**: Auto-incrementing unique identifier
- **keyword**: The search term that triggered this research
- **content**: The actual research text (facts, insights, findings)

#### Vector Storage
```sql
embedding vector(1536) NOT NULL
```
- **What it is**: A mathematical representation of the content's meaning
- **Size**: 1536 dimensions (matches text-embedding-3-small model)
- **Purpose**: Enables finding semantically similar content

#### Metadata JSONB
```sql
metadata JSONB NOT NULL DEFAULT '{}'
```
- **Flexibility**: Store varying attributes without schema changes
- **Expected fields**:
  - `source_url`: Where this information came from
  - `credibility_score`: 0.0-1.0 quality rating
  - `is_academic`: Boolean for .edu/.gov sources
  - `key_topics`: Main themes in the chunk

### 2. Indexing Strategy

#### Standard Indexes
```sql
CREATE INDEX idx_research_documents_keyword
CREATE INDEX idx_research_documents_created_at
```
- **Purpose**: Speed up common queries
- **When used**: Filtering by keyword or date

#### JSONB Index
```sql
CREATE INDEX ... USING gin(metadata)
```
- **Type**: Generalized Inverted Index (GIN)
- **Purpose**: Fast queries on JSON fields
- **Example**: Find all academic sources quickly

#### Vector Index
```sql
CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops)
```
- **Algorithm**: IVFFlat (Inverted File with Flat compression)
- **Purpose**: Accelerate similarity searches
- **Trade-off**: Slight accuracy loss for major speed gain

### 3. Search Functions

#### Semantic Search
```sql
CREATE FUNCTION search_similar_research
```
- **How it works**: Finds content similar in meaning, not just keywords
- **Example use case**: Search "diabetes treatment" finds "blood sugar management"
- **Similarity threshold**: Default 0.7 (70% similar)

#### Academic Filter
```sql
CREATE FUNCTION find_academic_research
```
- **Purpose**: Prioritize credible academic sources
- **Sorting**: By credibility score, then recency
- **Use case**: When you need peer-reviewed information

#### Statistics
```sql
CREATE FUNCTION get_research_stats
```
- **Provides**: Overview of research quality
- **Metrics**: Total chunks, academic percentage, average credibility
- **Use case**: Assess research coverage for a topic

### 4. Data Validation

#### Trigger System
```sql
CREATE TRIGGER validate_research_metadata_trigger
```
- **When it runs**: Before any insert or update
- **What it checks**:
  - Required fields exist
  - Credibility score is valid (0-1)
  - Source URL is present
- **Benefit**: Prevents bad data at database level

## Decision Rationale

### Why Chunk Research?
1. **Granular search**: Find specific facts, not just documents
2. **Better embeddings**: Smaller text chunks create more focused vectors
3. **Flexible retrieval**: Combine chunks from multiple sources

### Why JSONB for Metadata?
1. **Schema flexibility**: Add new fields without migrations
2. **Query performance**: GIN indexes make JSON queries fast
3. **Rich querying**: PostgreSQL's JSON operators are powerful

### Why IVFFlat Index?
1. **Scalability**: Handles millions of vectors efficiently
2. **Tunable**: Adjust lists parameter for speed/accuracy trade-off
3. **Proven**: Used by major vector search systems

## Learning Path

### Vector Search Deep Dive
1. **Cosine similarity**: Measures angle between vectors (0=different, 1=identical)
2. **Embedding space**: Similar concepts cluster together
3. **Semantic search**: Understands meaning, not just keywords

### Performance Optimization
1. **Index selection**: Different indexes for different query patterns
2. **Chunk size**: Balance between context and precision
3. **Similarity threshold**: Higher = more precise, lower = more results

## Real-World Applications

### Similar Systems
1. **Elasticsearch**: Uses similar chunking for document search
2. **Pinecone**: Dedicated vector database with similar concepts
3. **ChatGPT Retrieval**: Chunks and embeds documentation

### Scaling Considerations
- **Current**: Handles 100K+ chunks easily
- **Future**: Can partition by date or keyword
- **Optimization**: Adjust IVFFlat lists parameter as data grows

## Common Pitfalls

1. **Chunk size**: Too small loses context, too large dilutes meaning
2. **Missing indexes**: Similarity searches without vector index are slow
3. **Metadata validation**: Not enforcing required fields causes issues
4. **Similarity threshold**: Too high returns nothing, too low returns noise

## Best Practices Demonstrated

1. **Constraints**: Ensure data quality (content not empty)
2. **Defaults**: Sensible defaults for optional parameters
3. **Documentation**: Comments explain each component
4. **Validation**: Trigger ensures data integrity

## Query Examples

### Find Similar Research
```sql
SELECT * FROM search_similar_research(
    query_embedding := (SELECT embedding FROM research_documents WHERE id = 123),
    search_keyword := 'diabetes',
    similarity_threshold := 0.8
);
```

### Get Academic Sources
```sql
SELECT * FROM find_academic_research('insulin resistance', 10);
```

### Research Overview
```sql
SELECT * FROM get_research_stats('ketogenic diet');
```

What questions do you have about vector search and research storage, Finn?
Would you like me to explain how embeddings capture semantic meaning?
Try this exercise: How would you modify this schema to track research quality over time?