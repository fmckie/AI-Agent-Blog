# Database Setup Guide for SEO Content Automation System

## Overview

This guide walks you through setting up the database infrastructure for the RAG (Retrieval-Augmented Generation) system that powers intelligent caching and semantic search capabilities.

## Prerequisites

1. **Supabase Account**: Free tier is sufficient for development
2. **OpenAI API Key**: For embedding generation
3. **Basic SQL Knowledge**: Helpful but not required

## Step-by-Step Setup

### 1. Create Supabase Project

1. Visit [supabase.com](https://supabase.com) and sign up
2. Click "New Project"
3. Configure your project:
   - **Name**: `seo-content-automation` (or your preference)
   - **Database Password**: Generate a strong password
   - **Region**: Choose closest to your location
   - **Plan**: Free tier is fine for development

4. Once created, navigate to Settings → API and note:
   - **Project URL**: `https://[your-project-id].supabase.co`
   - **Service Role Key**: Under "Project API keys" (keep this secret!)

### 2. Initialize Database Schema

Navigate to your Supabase project's SQL Editor and run each script in order:

#### Step 1: Initialize Database
```sql
-- Run the contents of sql/init_database.sql
-- This enables pgvector and creates helper functions
```

**What this does**:
- Enables pgvector extension for semantic search
- Creates custom types for data consistency
- Sets up utility functions

#### Step 2: Create Research Documents Table
```sql
-- Run the contents of sql/research_documents.sql
-- This creates the main research storage with embeddings
```

**What this does**:
- Stores research chunks with vector embeddings
- Enables semantic similarity search
- Indexes for performance

#### Step 3: Set Up Source Metadata
```sql
-- Run the contents of sql/research_metadata.sql
-- This tracks and scores research sources
```

**What this does**:
- Maintains registry of all sources
- Calculates credibility scores
- Tracks usage statistics

#### Step 4: Create Research Cache
```sql
-- Run the contents of sql/research_cache.sql
-- This caches complete API responses
```

**What this does**:
- Stores Tavily API responses
- Reduces API costs
- Implements TTL-based expiration

#### Step 5: Track Generated Articles
```sql
-- Run the contents of sql/generated_articles.sql
-- This records all generated content
```

**What this does**:
- Tracks article generation history
- Calculates quality scores
- Links research to outputs

#### Step 6: Future Drive Integration
```sql
-- Run the contents of sql/drive_documents.sql
-- Placeholder for Google Drive features
```

**What this does**:
- Prepares structure for Phase 7.4
- No immediate functionality

#### Step 7: Create RPC Functions
```sql
-- Run the contents of sql/rpc_functions.sql
-- Creates safe database access functions
```

**What this does**:
- Provides secure API for queries
- Replaces dangerous arbitrary SQL execution
- Optimized for connection pooling
- Includes analytics and maintenance functions

### 3. Verify Installation

Run this verification query in SQL Editor:

```sql
-- Check all tables were created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'research_documents',
    'research_metadata', 
    'research_cache',
    'generated_articles',
    'drive_documents'
)
ORDER BY table_name;

-- Should return 5 rows
```

### 4. Configure Application

Update your `.env` file with Supabase credentials:

```env
# Supabase Configuration
SUPABASE_URL=https://[your-project-id].supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # Your service role key

# Embedding Configuration
EMBEDDING_MODEL_NAME=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_BATCH_SIZE=100
EMBEDDING_MAX_RETRIES=3

# Cache Configuration
CACHE_SIMILARITY_THRESHOLD=0.8
CACHE_TTL_DAYS=7
CACHE_MAX_AGE_DAYS=30
```

## Transaction Pooler Configuration

### Why Use Transaction Pooler?

Transaction pooling is **essential** for production deployments because:

1. **Connection Limits**: Free tier databases have connection limits (typically 60)
2. **Serverless Compatibility**: Required for Vercel, Netlify, AWS Lambda
3. **Performance**: Reuses connections efficiently
4. **Cost Optimization**: Prevents connection exhaustion errors

### When to Use Transaction Pooler

Use the transaction pooler when:
- ✅ Running in serverless environments
- ✅ Making many short-lived queries (cache checks)
- ✅ Multiple concurrent users/agents
- ✅ Using connection-heavy frameworks

Use direct connection when:
- ❌ Using LISTEN/NOTIFY
- ❌ Creating temporary tables
- ❌ Using prepared statements
- ❌ Running database migrations

### Setting Up Transaction Pooler

1. **Get Pooler Connection String**
   - Go to Supabase Dashboard → Settings → Database
   - Under "Connection String", select "Transaction Mode"
   - Note the different port: `6543` (instead of `5432`)

2. **Connection String Format**
   ```env
   # Direct connection (for migrations, admin tasks)
   DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
   
   # Pooled connection (for application use)
   DATABASE_POOL_URL=postgresql://postgres:[password]@[host]:6543/postgres?pgbouncer=true
   ```

3. **Update Your .env File**
   ```env
   # Add both connection strings
   SUPABASE_URL=https://[your-project-id].supabase.co
   SUPABASE_SERVICE_KEY=eyJ...
   
   # Direct connection (migrations only)
   DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
   
   # Pooled connection (application use)
   DATABASE_POOL_URL=postgresql://postgres:[password]@[host]:6543/postgres?pgbouncer=true
   
   # Connection settings
   POOL_SIZE=10  # Number of connections in pool
   POOL_TIMEOUT=60  # Seconds to wait for connection
   ```

### Code Compatibility

Our SQL functions are already pooler-compatible because they:
- ✅ Use atomic operations
- ✅ Don't rely on session state
- ✅ Complete within single transactions
- ✅ Don't use temporary tables

### Best Practices

1. **Keep Transactions Short**
   ```python
   # Good: Quick query
   result = await db.fetch_one("SELECT * FROM research_cache WHERE keyword = $1", keyword)
   
   # Bad: Long-running transaction
   # Don't hold connections for file I/O or API calls
   ```

2. **Use Connection Wisely**
   ```python
   # For most queries (use pooled)
   async with get_pooled_connection() as conn:
       await conn.fetch("SELECT...")
   
   # For migrations (use direct)
   async with get_direct_connection() as conn:
       await conn.execute("CREATE TABLE...")
   ```

3. **Monitor Connection Usage**
   ```sql
   -- Check active connections
   SELECT count(*) FROM pg_stat_activity;
   
   -- See connection details
   SELECT pid, usename, application_name, state 
   FROM pg_stat_activity 
   WHERE datname = 'postgres';
   ```

### Troubleshooting

**Error: "too many connections"**
- Switch to pooled connection string
- Reduce POOL_SIZE
- Check for connection leaks

**Error: "prepared statement does not exist"**
- Prepared statements don't work with pooler
- Use regular parameterized queries instead

**Error: "cannot use LISTEN/NOTIFY"**
- Use direct connection for real-time features
- Consider alternatives like polling

## Testing Your Setup

### 1. Test Vector Extension
```sql
-- Test pgvector is working
SELECT vector_dims(ARRAY[1,2,3]::vector);
-- Should return: 3
```

### 2. Test Functions
```sql
-- Test credibility scoring
SELECT calculate_credibility_score(
    'nature.com',
    true,  -- has_citations
    true,  -- has_methodology
    'journal'
);
-- Should return ~0.95-1.0
```

### 3. Test Cache Function
```sql
-- Test cache storage (with dummy data)
SELECT * FROM store_research_cache(
    'test keyword',
    '{"results": [{"url": "test.com", "content": "test"}]}'::jsonb,
    168  -- 7 days TTL
);
-- Should return ID and expiration
```

## Common Issues & Solutions

### Issue: "extension 'vector' does not exist"
**Solution**: Ensure you're using Supabase (includes pgvector) or install pgvector manually

### Issue: "permission denied for schema public"
**Solution**: Use the service role key, not the anon key

### Issue: Functions not found
**Solution**: Run init_database.sql first - it creates required functions

### Issue: Very slow vector searches
**Solution**: Ensure indexes were created, especially the IVFFlat index

## Maintenance Tasks

### Daily/Weekly
```sql
-- Clean expired cache entries
SELECT cleanup_expired_research_cache(30);

-- Check cache performance
SELECT * FROM get_cache_statistics();
```

### Monthly
```sql
-- Analyze source quality trends
SELECT 
    DATE_TRUNC('month', created_at) as month,
    AVG(credibility_score) as avg_credibility,
    COUNT(DISTINCT source_url) as unique_sources
FROM research_metadata
GROUP BY month
ORDER BY month DESC;
```

## Performance Optimization

### 1. Index Maintenance
```sql
-- Rebuild indexes if queries slow down
REINDEX TABLE research_documents;
REINDEX TABLE research_cache;
```

### 2. Vacuum Tables
```sql
-- Clean up dead rows
VACUUM ANALYZE research_documents;
VACUUM ANALYZE research_cache;
```

### 3. Monitor Table Sizes
```sql
-- Check storage usage
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Security Best Practices

1. **Never commit service keys**: Use environment variables
2. **Use Row Level Security**: Enable RLS for production
3. **Regular backups**: Supabase handles this automatically
4. **Monitor usage**: Check Supabase dashboard for anomalies

## Next Steps

Once your database is set up:

1. Test with a simple keyword search
2. Monitor cache hit rates
3. Adjust similarity thresholds based on results
4. Set up periodic maintenance scripts

## Troubleshooting

If you encounter issues:

1. Check Supabase logs (Project → Logs → Postgres)
2. Verify API keys are correct
3. Ensure all SQL scripts ran without errors
4. Join Supabase Discord for community help

## Additional Resources

- [Supabase Docs](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- Project SQL explanations in `sql/*_explanation.md` files

Questions? Check the explanation files for each SQL script for detailed understanding of the database design.