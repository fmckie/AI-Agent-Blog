# Connection Pooling Explanation

## Purpose
This document explains connection pooling concepts, why it's crucial for our SEO Content Automation System, and how to implement it correctly with Supabase and PgBouncer.

## What is Connection Pooling?

Connection pooling is a technique where database connections are reused rather than created new for each request. Think of it like a car rental service:
- **Without pooling**: Buy a new car for each trip, then sell it
- **With pooling**: Rent a car when needed, return it for others to use

## Why We Need Connection Pooling

### The Problem
PostgreSQL databases have connection limits:
- **Supabase Free**: ~60 connections
- **Each connection**: ~10MB RAM
- **Overhead**: Connection setup/teardown time

### Our Architecture Challenges
```
Multiple Agents → Concurrent Queries → Connection Exhaustion
```

Our system makes many database calls:
1. **Cache checks**: Quick lookups for every search
2. **Research storage**: Bulk inserts of documents
3. **Analytics queries**: Aggregations and stats
4. **Concurrent users**: Multiple articles generating

Without pooling, we'd quickly hit: `FATAL: too many connections`

## How PgBouncer Works

PgBouncer is a lightweight connection pooler that sits between your application and PostgreSQL:

```
Application → PgBouncer → PostgreSQL
     ↓            ↓             ↓
Many connections  Pool of     Limited
(100s)           connections  connections
                 (10-20)      (60 max)
```

### Pool Modes

1. **Session Mode**: Connection assigned for entire session
   - ❌ Not suitable for us (wastes connections)

2. **Transaction Mode**: Connection held only during transaction
   - ✅ Perfect for our use case
   - ✅ Maximum efficiency
   - ⚠️ Some limitations (see below)

3. **Statement Mode**: Connection per statement
   - ❌ Too restrictive for complex queries

## Transaction Mode Limitations

### What Works ✅
```sql
-- Single queries
SELECT * FROM research_cache WHERE keyword = $1;

-- Transactions
BEGIN;
INSERT INTO research_documents ...;
UPDATE research_metadata ...;
COMMIT;

-- Our RPC functions
SELECT * FROM rpc_get_cached_research('diabetes');
```

### What Doesn't Work ❌
```sql
-- Prepared statements
PREPARE myplan AS SELECT ...;
EXECUTE myplan;

-- Session-level settings
SET work_mem = '256MB';

-- Temporary tables
CREATE TEMP TABLE analysis_temp AS ...;

-- LISTEN/NOTIFY
LISTEN channel_name;
```

## Configuration Deep Dive

### Connection Strings

#### Direct Connection (Port 5432)
```
postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
```
**Use for**:
- Database migrations
- Schema changes
- Administrative tasks
- Development/debugging

#### Pooled Connection (Port 6543)
```
postgresql://postgres:[password]@db.[project].supabase.co:6543/postgres?pgbouncer=true
```
**Use for**:
- Application queries
- API endpoints
- Agent operations
- Production traffic

### Pooler Settings

```env
# Pool Configuration
POOL_SIZE=10        # Connections in pool
POOL_TIMEOUT=60     # Wait time for connection
POOL_MODE=transaction  # PgBouncer mode
```

#### Sizing Your Pool
```
Pool Size = (Number of Workers × Average Connections per Worker)

Example:
- 2 agents running concurrently
- Each makes ~5 concurrent queries
- Pool Size = 2 × 5 = 10
```

## Implementation Patterns

### Python with asyncpg
```python
import asyncpg
import asyncio
from contextlib import asynccontextmanager

class DatabasePool:
    def __init__(self, pool_url: str, pool_size: int = 10):
        self.pool_url = pool_url
        self.pool_size = pool_size
        self._pool = None
    
    async def init(self):
        """Initialize connection pool"""
        self._pool = await asyncpg.create_pool(
            self.pool_url,
            min_size=2,
            max_size=self.pool_size,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )
    
    @asynccontextmanager
    async def acquire(self):
        """Get connection from pool"""
        async with self._pool.acquire() as conn:
            yield conn
    
    async def close(self):
        """Close all connections"""
        await self._pool.close()

# Usage
db = DatabasePool(POOL_URL)
await db.init()

async with db.acquire() as conn:
    result = await conn.fetch("SELECT * FROM rpc_check_cache_exists($1)", keyword)
```

### Connection Pool Monitoring
```python
async def get_pool_stats(pool):
    """Monitor pool health"""
    return {
        "size": pool.get_size(),
        "free": pool.get_idle_size(),
        "used": pool.get_size() - pool.get_idle_size(),
        "waiting": pool.get_pending_size()
    }
```

## Best Practices

### 1. Keep Connections Short
```python
# ❌ Bad: Holding connection during I/O
async with db.acquire() as conn:
    data = await conn.fetch("SELECT...")
    processed = await external_api_call(data)  # Don't hold connection!
    await conn.execute("INSERT...")

# ✅ Good: Release during I/O
async with db.acquire() as conn:
    data = await conn.fetch("SELECT...")

processed = await external_api_call(data)

async with db.acquire() as conn:
    await conn.execute("INSERT...")
```

### 2. Use Transactions Wisely
```python
# ✅ Good: Batch operations in transaction
async with db.acquire() as conn:
    async with conn.transaction():
        await conn.execute("INSERT INTO research_documents...")
        await conn.execute("UPDATE research_metadata...")
```

### 3. Handle Pool Exhaustion
```python
try:
    async with asyncio.timeout(5):  # 5 second timeout
        async with db.acquire() as conn:
            result = await conn.fetch(...)
except asyncio.TimeoutError:
    logger.error("Connection pool exhausted")
    # Implement backoff/retry logic
```

## Monitoring and Debugging

### Check Active Connections
```sql
-- Total connections
SELECT count(*) FROM pg_stat_activity;

-- By state
SELECT state, count(*) 
FROM pg_stat_activity 
GROUP BY state;

-- Long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

### PgBouncer Statistics
```sql
-- In PgBouncer admin console
SHOW POOLS;
SHOW CLIENTS;
SHOW SERVERS;
```

## Common Issues and Solutions

### 1. "Too many connections"
**Symptoms**: Error under load
**Solutions**:
- Switch to pooled connection
- Reduce POOL_SIZE
- Check for connection leaks
- Scale up database

### 2. "Prepared statement does not exist"
**Symptoms**: Error with certain ORMs
**Solutions**:
- Disable prepared statements
- Use simple protocol
- Switch to parameterized queries

### 3. "Connection pool timeout"
**Symptoms**: Timeout acquiring connection
**Solutions**:
- Increase pool size
- Reduce query time
- Add circuit breaker
- Check for deadlocks

### 4. "Cannot use LISTEN/NOTIFY"
**Symptoms**: Real-time features fail
**Solutions**:
- Use direct connection for LISTEN
- Implement polling alternative
- Use Supabase Realtime

## Performance Optimization

### 1. Connection Overhead
Without pooling:
```
Connect: 20-50ms
Query: 5ms
Disconnect: 10ms
Total: 35-65ms per query
```

With pooling:
```
Acquire: 0.1ms
Query: 5ms
Release: 0.1ms
Total: 5.2ms per query (10x faster!)
```

### 2. Memory Usage
```
Without pooling: Connections × 10MB
With pooling: Pool Size × 10MB

Example:
100 requests = 1000MB (without) vs 100MB (with 10-connection pool)
```

## Testing Connection Pooling

### Load Test Script
```python
async def load_test(pool_url, concurrent_requests=50):
    """Test pool under load"""
    db = DatabasePool(pool_url)
    await db.init()
    
    async def single_request(i):
        try:
            async with db.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM research_cache"
                )
            return True
        except Exception as e:
            print(f"Request {i} failed: {e}")
            return False
    
    # Run concurrent requests
    tasks = [single_request(i) for i in range(concurrent_requests)]
    results = await asyncio.gather(*tasks)
    
    success_rate = sum(results) / len(results) * 100
    print(f"Success rate: {success_rate}%")
    
    await db.close()
```

## Migration Guide

### Step 1: Update Connection Strings
```python
# Before
DATABASE_URL = "postgresql://...supabase.co:5432/postgres"

# After
DATABASE_URL = "postgresql://...supabase.co:5432/postgres"  # Migrations only
DATABASE_POOL_URL = "postgresql://...supabase.co:6543/postgres?pgbouncer=true"
```

### Step 2: Update Database Client
```python
# Before
conn = await asyncpg.connect(DATABASE_URL)

# After
pool = await asyncpg.create_pool(DATABASE_POOL_URL)
async with pool.acquire() as conn:
    ...
```

### Step 3: Test Thoroughly
1. Run load tests
2. Monitor connections
3. Check error logs
4. Verify performance

## Conclusion

Connection pooling is not optional for production—it's essential. Our implementation using PgBouncer in transaction mode provides:
- **10x performance improvement** for connection-heavy workloads
- **90% reduction** in memory usage
- **Seamless scaling** for concurrent users
- **Protection** against connection exhaustion

By following these patterns and best practices, our SEO Content Automation System can handle high loads efficiently while staying within Supabase's connection limits.

What questions do you have about connection pooling, Finn?
Would you like me to explain PgBouncer's internals in more detail?
Try this exercise: Calculate the optimal pool size for 100 concurrent users, each making 3 queries.