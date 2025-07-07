# Performance Tuning Guide - Learning Documentation

## Purpose

This guide teaches you how to optimize system performance through measurement, analysis, and targeted improvements. Performance tuning is both an art and a science - it requires understanding the system's behavior and making data-driven decisions.

## Architecture

### Performance Stack
```
Application Layer
    ↓
Caching Layer (RAG)
    ↓
Database Layer (Supabase)
    ↓
External APIs (Tavily, OpenAI)
```

Each layer has different optimization opportunities and constraints.

## Key Concepts

### Amdahl's Law
The speedup from optimization is limited by the fraction of time that improvement affects:
```
Speedup = 1 / ((1 - P) + P/S)
```
Where P = parallel portion, S = speedup of that portion

This means: **Optimize the bottlenecks first!**

### Cache Hit Rate Economics
```
Cost per request = (1 - hit_rate) × api_cost
Time per request = hit_rate × cache_time + (1 - hit_rate) × api_time
```

Example:
- 70% hit rate: $0.012 per request (vs $0.04 without cache)
- 90% hit rate: $0.004 per request

### Connection Pooling
Like a restaurant with reserved tables:
- **Min connections**: Always ready tables
- **Max connections**: Restaurant capacity
- **Pool warming**: Pre-set tables before opening

Without pooling: 150ms per connection setup
With pooling: 0ms (reuse existing)

## Decision Rationale

### Why These Default Values?

1. **Cache Similarity 0.8**
   - Balances precision vs recall
   - 0.9 = too strict (misses related content)
   - 0.7 = too loose (irrelevant matches)

2. **Connection Pool 2-10**
   - Min 2: Handles concurrent requests
   - Max 10: Prevents database overload
   - Most apps need 3-5 connections

3. **Chunk Size 1000**
   - Semantic coherence maintained
   - Fits in single embedding
   - Efficient storage/retrieval

4. **Parallel Limit 3**
   - Respects API rate limits
   - Balances speed vs stability
   - Works on most systems

### Trade-offs

**Speed vs Cost**
- More parallel = faster but costlier
- Larger cache = faster but more storage
- Lower threshold = more hits but less accurate

**Memory vs Performance**
- Larger batches = faster but more RAM
- More connections = faster but more resources
- Bigger cache = faster but memory hungry

## Learning Path

### Beginner: Measure First
1. Run baseline benchmarks
2. Check cache statistics
3. Monitor resource usage
4. Identify bottlenecks

### Intermediate: Targeted Optimization
1. Tune cache thresholds
2. Adjust parallel processing
3. Optimize batch sizes
4. Implement monitoring

### Advanced: System-wide Tuning
1. Database query optimization
2. Custom indexing strategies
3. Load balancing
4. Auto-scaling implementation

## Real-World Scenarios

### Scenario 1: Startup on a Budget
**Challenge**: Minimize API costs
**Solution**:
```env
CACHE_SIMILARITY_THRESHOLD=0.7
CACHE_TTL_DAYS=30
TAVILY_SEARCH_DEPTH=basic
PARALLEL_WORKERS=1
```
**Result**: 80% cost reduction, slightly slower

### Scenario 2: Content Agency
**Challenge**: Process 100+ articles daily
**Solution**:
```env
CONNECTION_POOL_MAX=50
PARALLEL_WORKERS=5
EMBEDDING_BATCH_SIZE=200
CACHE_SIMILARITY_THRESHOLD=0.75
```
**Result**: 5x throughput increase

### Scenario 3: Real-time Generation
**Challenge**: <5s response time
**Solution**:
```env
CONNECTION_POOL_MIN=10
CACHE_SIMILARITY_THRESHOLD=0.6
EMBEDDING_CACHE_SIZE=5000
```
**Result**: 95% requests under 5s

## Common Pitfalls

### 1. Premature Optimization
**Problem**: Optimizing without data
**Solution**: Always measure first
**Example**: Don't add caching before knowing hit patterns

### 2. Over-Parallelization
**Problem**: Rate limits and resource exhaustion
**Solution**: Start conservative, increase gradually
**Example**: Parallel=10 might hit API limits

### 3. Ignoring Cache Maintenance
**Problem**: Degraded performance over time
**Solution**: Regular cleanup and monitoring
**Example**: 6-month old cache with 50% stale entries

### 4. One-Size-Fits-All Config
**Problem**: Different workloads need different settings
**Solution**: Environment-specific configurations
**Example**: Dev vs Production settings

## Performance Patterns

### Pattern 1: Cache-First Architecture
```python
async def get_data(key):
    # Check cache first
    if cached := await cache.get(key):
        return cached
    
    # Fall back to API
    data = await api.fetch(key)
    await cache.set(key, data)
    return data
```

### Pattern 2: Circuit Breaker
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5):
        self.failures = 0
        self.threshold = failure_threshold
        self.is_open = False
    
    async def call(self, func):
        if self.is_open:
            raise Exception("Circuit breaker is open")
        
        try:
            result = await func()
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.is_open = True
            raise
```

### Pattern 3: Adaptive Batching
```python
class AdaptiveBatcher:
    def __init__(self):
        self.batch_size = 10
        self.success_rate = 1.0
    
    def adjust_batch_size(self, success):
        if success and self.batch_size < 100:
            self.batch_size += 5
        elif not success and self.batch_size > 5:
            self.batch_size = max(5, self.batch_size // 2)
```

## Monitoring Strategy

### Key Metrics to Track

1. **Response Time Percentiles**
   - P50: Median (typical case)
   - P95: Most requests
   - P99: Worst case

2. **Error Rates**
   - API failures
   - Timeout errors
   - Cache misses

3. **Resource Utilization**
   - CPU usage patterns
   - Memory growth
   - Connection pool saturation

4. **Business Metrics**
   - Cost per article
   - Articles per hour
   - Cache savings

### Alerting Thresholds

- Cache hit rate < 50%: Investigation needed
- P95 response time > 5s: Performance degradation
- Error rate > 5%: System unhealthy
- Memory > 80%: Resource pressure

## Cost Optimization Math

### API Cost Model
```
Daily cost = (requests × (1 - cache_hit_rate) × api_cost) + storage_cost

Example (100 requests/day):
- No cache: 100 × $0.04 = $4.00/day
- 70% cache: 100 × 0.3 × $0.04 = $1.20/day
- 90% cache: 100 × 0.1 × $0.04 = $0.40/day
```

### ROI Calculation
```
ROI = (Savings - Cache_Infrastructure_Cost) / Cache_Infrastructure_Cost

Example:
- Savings: $90/month (from cache)
- Supabase cost: $25/month
- ROI: ($90 - $25) / $25 = 260%
```

## Advanced Techniques

### 1. Predictive Caching
Analyze patterns to pre-cache likely requests:
```python
# Track request patterns
request_history = defaultdict(list)

# Predict next likely requests
def predict_next_keywords(current_keyword):
    related = request_history[current_keyword]
    return most_common(related, n=5)
```

### 2. Dynamic Threshold Adjustment
Adjust similarity threshold based on hit rate:
```python
if hit_rate < 0.5:
    threshold *= 0.95  # Lower threshold
elif hit_rate > 0.9:
    threshold *= 1.05  # Raise threshold
```

### 3. Load-Based Scaling
Adjust parallelism based on system load:
```python
cpu_percent = psutil.cpu_percent()
if cpu_percent < 50:
    workers = min(workers + 1, max_workers)
elif cpu_percent > 80:
    workers = max(workers - 1, 1)
```

## What Questions Do You Have?

Performance tuning is an iterative process. The key is to:
1. Measure everything
2. Change one thing at a time
3. Validate improvements
4. Document what works

Try this exercise: Run `python main.py cache stats` before and after lowering CACHE_SIMILARITY_THRESHOLD by 0.1. What changes do you observe?

Would you like me to explain any specific optimization technique in more detail, Finn?