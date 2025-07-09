# Supabase AI & pgvector Research Documentation

## Executive Summary

This document compiles comprehensive research on Supabase's AI capabilities, focusing on pgvector implementation for Phase 3 of the SEO Content Automation System enhancement plan. The research reveals that Supabase with pgvector provides a robust, scalable solution for vector storage and retrieval, perfectly suited for our research agent's needs.

## Key Findings

### 1. pgvector Fundamentals

**What is pgvector?**
- PostgreSQL extension for vector similarity search
- Enables storing and querying vector embeddings directly in Postgres
- Supports embeddings from any model (OpenAI, Hugging Face, etc.)
- Production-ready with companies storing millions of embeddings

**Core Philosophy:**
> "The best vector database is the database you already have" - Supabase

### 2. Vector Storage Schema Patterns

#### Basic Vector Table
```sql
-- For general embeddings (adjust dimensions to match your model)
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding vector(384),
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### OpenAI Embeddings Schema
```sql
-- For text-embedding-ada-002 (1536 dimensions)
CREATE TABLE research_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url TEXT UNIQUE NOT NULL,
  title TEXT,
  content TEXT,
  embedding vector(1536),
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### Advanced Schema with Relationships
```sql
-- Sources table with metadata
CREATE TABLE research_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT UNIQUE NOT NULL,
  domain TEXT NOT NULL,
  title TEXT,
  full_content TEXT,
  credibility_score FLOAT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Embeddings table with foreign key
CREATE TABLE source_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES research_sources(id) ON DELETE CASCADE,
  chunk_text TEXT,
  chunk_number INTEGER,
  embedding vector(1536),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Source relationships
CREATE TABLE source_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES research_sources(id),
  related_source_id UUID REFERENCES research_sources(id),
  relationship_type TEXT,
  similarity_score FLOAT,
  UNIQUE(source_id, related_source_id)
);
```

### 3. Distance Operators & Metrics

pgvector supports three distance operators:

1. **`<->` Euclidean Distance (L2)**
   - Best for: General similarity when magnitude matters
   - Use case: Finding similar research papers by content

2. **`<=>` Cosine Distance**
   - Best for: Text similarity (direction matters, not magnitude)
   - Use case: Semantic search for related topics
   - Most common for NLP applications

3. **`<#>` Negative Inner Product**
   - Best for: Maximum inner product search
   - Use case: When vectors are normalized (fastest option)

**Performance Tip:** Dot product (`<#>`) is fastest with normalized vectors.

### 4. Indexing Strategies

#### IVFFlat Index (Inverted File Flat)
```sql
-- For cosine similarity
CREATE INDEX ON source_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- For L2 distance
CREATE INDEX ON source_embeddings 
USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);

-- For inner product
CREATE INDEX ON source_embeddings 
USING ivfflat (embedding vector_ip_ops)
WITH (lists = 100);
```

**Lists Calculation:** `lists = 4 * sqrt(total_rows)`

#### HNSW Index (Hierarchical Navigable Small World)
- Better recall than IVFFlat
- Higher build time but faster queries
- Coming soon to Supabase

### 5. Query Patterns

#### Basic Similarity Search
```sql
-- Find similar content using cosine distance
SELECT 
  source_id,
  chunk_text,
  1 - (embedding <=> query_embedding) as similarity
FROM source_embeddings
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

#### Filtered Similarity Search
```sql
-- Search with metadata filtering
CREATE OR REPLACE FUNCTION search_similar_sources(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
  domain_filter text DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  title TEXT,
  content TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    s.id,
    s.title,
    s.full_content,
    1 - (se.embedding <=> query_embedding) as similarity
  FROM source_embeddings se
  JOIN research_sources s ON s.id = se.source_id
  WHERE 
    1 - (se.embedding <=> query_embedding) > match_threshold
    AND (domain_filter IS NULL OR s.domain = domain_filter)
  ORDER BY se.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

#### Hybrid Search (Semantic + Keyword)
```sql
-- Combine vector similarity with full-text search
WITH semantic_search AS (
  SELECT 
    source_id,
    MAX(1 - (embedding <=> query_embedding)) as semantic_score
  FROM source_embeddings
  GROUP BY source_id
),
keyword_search AS (
  SELECT 
    id as source_id,
    ts_rank(to_tsvector('english', full_content), query) as keyword_score
  FROM research_sources,
    plainto_tsquery('english', search_query) query
  WHERE to_tsvector('english', full_content) @@ query
)
SELECT 
  s.*,
  COALESCE(sem.semantic_score, 0) * 0.5 + 
  COALESCE(key.keyword_score, 0) * 0.5 as combined_score
FROM research_sources s
LEFT JOIN semantic_search sem ON s.id = sem.source_id
LEFT JOIN keyword_search key ON s.id = key.source_id
WHERE sem.semantic_score IS NOT NULL OR key.keyword_score IS NOT NULL
ORDER BY combined_score DESC
LIMIT 20;
```

### 6. Performance Optimization

#### Best Practices
1. **Normalize Vectors**: For fastest dot product operations
2. **Optimize Dimensions**: Fewer dimensions = better performance
3. **Batch Operations**: Insert/update multiple vectors at once
4. **Use Appropriate Index**: IVFFlat for most cases
5. **Pre-filter When Possible**: Apply WHERE clauses before vector operations

#### Dimension Reduction
```python
# Example: Reduce dimensions using PCA
from sklearn.decomposition import PCA

# Reduce from 1536 to 768 dimensions
pca = PCA(n_components=768)
reduced_embeddings = pca.fit_transform(original_embeddings)
```

### 7. Real-World Implementation Examples

#### Storing Research Findings
```python
async def store_research_with_embeddings(
    self, 
    source: AcademicSource, 
    full_content: str,
    embeddings: List[float]
) -> str:
    """Store research source with its embedding."""
    
    async with self.pool.acquire() as conn:
        # Store the source
        source_id = await conn.fetchval("""
            INSERT INTO research_sources 
            (url, domain, title, full_content, credibility_score, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, 
            source.url, 
            source.domain, 
            source.title,
            full_content,
            source.credibility_score,
            json.dumps(source.metadata)
        )
        
        # Store the embedding
        await conn.execute("""
            INSERT INTO source_embeddings
            (source_id, chunk_text, embedding)
            VALUES ($1, $2, $3)
        """,
            source_id,
            full_content[:1000],  # Store preview
            embeddings
        )
        
        return source_id
```

#### Finding Related Sources
```python
async def find_related_sources(
    self, 
    source_id: str, 
    similarity_threshold: float = 0.7
) -> List[Dict]:
    """Find sources related to a given source."""
    
    async with self.pool.acquire() as conn:
        # Get the source's embedding
        embedding = await conn.fetchval("""
            SELECT embedding 
            FROM source_embeddings 
            WHERE source_id = $1
            LIMIT 1
        """, source_id)
        
        if not embedding:
            return []
        
        # Find similar sources
        results = await conn.fetch("""
            SELECT 
                s.id,
                s.title,
                s.url,
                1 - (se.embedding <=> $1::vector) as similarity
            FROM source_embeddings se
            JOIN research_sources s ON s.id = se.source_id
            WHERE 
                se.source_id != $2
                AND 1 - (se.embedding <=> $1::vector) > $3
            ORDER BY se.embedding <=> $1::vector
            LIMIT 10
        """, embedding, source_id, similarity_threshold)
        
        return [dict(r) for r in results]
```

### 8. Migration Considerations

#### From Current System
```sql
-- Add vector column to existing table
ALTER TABLE content_chunks 
ADD COLUMN embedding vector(1536);

-- Create index after populating
CREATE INDEX idx_content_embeddings 
ON content_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### Data Migration Tools
- **vec2pg**: CLI for migrating from Pinecone/Qdrant
- **pgvector-python**: Python client for batch operations

### 9. Security & Access Control

```sql
-- Enable RLS for multi-tenant scenarios
ALTER TABLE research_sources ENABLE ROW LEVEL SECURITY;

-- Create policy for organization-based access
CREATE POLICY "Organizations can view their own sources"
ON research_sources
FOR SELECT
USING (organization_id = auth.jwt() ->> 'org_id');
```

### 10. Cost & Performance Metrics

**Observed Performance:**
- Companies storing 1.6M+ embeddings with sub-second queries
- 10x cost reduction compared to dedicated vector databases
- No additional infrastructure required

**Benchmarks:**
- Query time: <100ms for 1M vectors with proper indexing
- Insert rate: 10K+ vectors/second in batches
- Storage: ~6KB per 1536-dimension vector

## Recommendations for Phase 3

Based on this research, Phase 3 should incorporate:

1. **Use Cosine Distance** (`<=>`) for text similarity (most appropriate for research content)
2. **Implement IVFFlat indexing** with calculated list size
3. **Normalize vectors** before storage for performance
4. **Add hybrid search** combining semantic and keyword search
5. **Implement chunking strategy** for large documents
6. **Use JSONB for flexible metadata** storage
7. **Consider dimension reduction** for performance optimization
8. **Implement relationship scoring** using vector similarity
9. **Add RLS policies** for future multi-tenant support
10. **Use batch operations** for bulk inserts

## Integration with Current System

Our existing `VectorStorage` class can be enhanced to:
- Support multiple distance metrics
- Implement proper indexing
- Add relationship management
- Enable hybrid search
- Optimize chunk size and overlap

## Conclusion

Supabase with pgvector provides all necessary features for Phase 3 implementation. The platform offers:
- Production-ready vector storage
- Flexible schema design
- Multiple search strategies
- Excellent performance at scale
- Unified data architecture

This eliminates the need for separate vector databases while providing superior integration with our existing PostgreSQL infrastructure.