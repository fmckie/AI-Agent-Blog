# Generated Articles Table Explanation

## Purpose
The `generated_articles` table serves as a comprehensive registry of all content created by the system, tracking quality metrics, performance data, and enabling content analytics and improvement over time.

## Architecture Overview
This table implements:
- Complete article lifecycle tracking
- Multi-dimensional quality scoring
- Performance analytics
- SEO metric tracking
- Future-ready Google Drive integration

## Key Concepts

### 1. Table Structure

#### Article Identification
```sql
keyword TEXT NOT NULL
title TEXT NOT NULL
meta_description TEXT NOT NULL CHECK (char_length(meta_description) BETWEEN 120 AND 160)
```
- **keyword**: Links to research trigger
- **title**: SEO-optimized headline
- **meta_description**: Length-validated for SEO

#### Content Metrics
```sql
word_count INTEGER NOT NULL
reading_time_minutes INTEGER GENERATED ALWAYS AS (CEIL(word_count / 200.0)) STORED
```
- **word_count**: Raw content length
- **reading_time**: Auto-calculated at 200 words/minute
- **Generated column**: PostgreSQL computes automatically

#### Quality Tracking
```sql
quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 100)
seo_score FLOAT
keyword_density FLOAT
```
- **Multi-factor scoring**: Comprehensive quality assessment
- **SEO metrics**: Track optimization effectiveness
- **Keyword density**: 1-2% optimal range

### 2. Quality Scoring Algorithm

#### Scoring Components
```sql
CREATE FUNCTION calculate_article_quality_score
```

The algorithm evaluates:
1. **Word Count (20 points)**
   - Optimal: 1200-2000 words
   - Good: 800-1200 or 2000-2500
   - Fair: 500-800

2. **SEO Score (30 points)**
   - Direct percentage conversion
   - Weighted most heavily

3. **Keyword Density (15 points)**
   - Optimal: 1-2%
   - Acceptable: 0.5-1% or 2-3%

4. **Readability (15 points)**
   - Optimal: 60-70 Flesch Reading Ease
   - Target: General audience comprehension

5. **Structure (10 points)**
   - All sections present
   - Proper heading hierarchy

6. **Links (10 points)**
   - Internal links ≥ 3
   - External links 5-15

### 3. Content Analytics

#### Structured Metrics
```sql
content_metrics JSONB DEFAULT '{}'
```
Stores detailed metrics:
```json
{
  "headings_count": {"h1": 1, "h2": 4, "h3": 6},
  "internal_links": 5,
  "external_links": 10,
  "images_count": 3,
  "readability_score": 65.5,
  "sections": ["introduction", "main_content", "conclusion"]
}
```

#### Performance Tracking
```sql
generation_time_seconds FLOAT
total_api_calls INTEGER DEFAULT 0
```
- **generation_time**: Optimization metric
- **api_calls**: Cost tracking

### 4. Status Management

#### Article Lifecycle
```sql
status article_status DEFAULT 'draft'
```
States from custom type:
- **draft**: Initial generation
- **published**: Live content
- **archived**: Historical record

#### Publishing Workflow
```sql
reviewed BOOLEAN DEFAULT FALSE
published_at TIMESTAMP WITH TIME ZONE
```
- **Review gate**: Quality control step
- **Publication tracking**: When went live

### 5. Smart Functions

#### Article Recording
```sql
CREATE FUNCTION record_article_generation
```
**Features**:
- Automatic quality scoring
- Atomic operation
- Returns computed metrics
- Links to research cache

#### Statistics Dashboard
```sql
CREATE FUNCTION get_article_statistics
```
**Provides**:
- Generation trends
- Quality distribution
- Popular keywords
- Daily production rates

#### Duplicate Detection
```sql
CREATE FUNCTION find_similar_articles
```
- **Uses**: PostgreSQL's similarity function
- **Prevents**: Near-duplicate content
- **Threshold**: 80% title similarity

### 6. Indexing Strategy

#### Performance Indexes
```sql
-- Keyword lookups
CREATE INDEX idx_generated_articles_keyword

-- Status filtering
CREATE INDEX idx_generated_articles_status

-- Quality sorting
CREATE INDEX idx_generated_articles_quality ... WHERE quality_score IS NOT NULL
```

#### Partial Indexes
```sql
-- Articles needing review
WHERE reviewed = FALSE AND status = 'draft'

-- Published articles only
WHERE status = 'published'
```
- **Efficiency**: Smaller indexes for specific queries
- **Use case**: Dashboard views

## Decision Rationale

### Why Track Quality Score?
1. **Continuous improvement**: Identify what works
2. **A/B testing**: Compare approaches
3. **ROI measurement**: Quality vs. performance
4. **Training data**: For future ML models

### Why Generated Columns?
1. **Consistency**: Always accurate calculations
2. **Performance**: Pre-computed at write time
3. **Simplicity**: No application logic needed
4. **Atomicity**: Can't forget to update

### Why JSONB for Metrics?
1. **Flexibility**: Add new metrics without schema change
2. **Queryability**: PostgreSQL JSON operators
3. **Performance**: Binary format is fast
4. **Future-proof**: Evolving requirements

## Learning Path

### Content Quality Metrics
1. **Flesch Reading Ease**: 0-100 scale (higher = easier)
2. **Keyword Density**: (keyword count / total words) * 100
3. **Heading Structure**: Proper H1→H2→H3 hierarchy
4. **Link Ratio**: Balance internal/external links

### PostgreSQL Advanced Features
1. **Generated columns**: Computed fields
2. **Custom types**: ENUMs for status
3. **Similarity functions**: Fuzzy text matching
4. **Partial indexes**: Conditional indexing

## Real-World Applications

### Similar Systems
1. **WordPress**: Post tracking with metadata
2. **HubSpot**: Content performance analytics
3. **Contentful**: Headless CMS with metrics
4. **Google Analytics**: Content scoring

### Industry Standards
- **Core Web Vitals**: Page experience signals
- **E-A-T**: Expertise, Authority, Trust
- **YMYL**: Your Money Your Life content standards
- **Schema.org**: Structured data for articles

## Common Pitfalls

1. **Over-optimization**: Keyword stuffing hurts quality
2. **Ignoring readability**: Complex text loses readers
3. **Missing structure**: Poor heading hierarchy
4. **Link farms**: Too many low-quality links

## Best Practices Demonstrated

1. **Comprehensive tracking**: Every aspect measured
2. **Automatic calculations**: Reduce manual work
3. **Quality gates**: Review before publishing
4. **Historical data**: Learn from past content

## Query Examples

### Record New Article
```sql
SELECT * FROM record_article_generation(
    'diabetes management',
    'Ultimate Guide to Diabetes Management in 2024',
    'Discover evidence-based strategies for effective diabetes management, including diet, exercise, and medication options backed by latest research.',
    1847,
    '/drafts/diabetes-management_2024-01-15/article.html',
    '{"headings_count": {"h1": 1, "h2": 5, "h3": 8}, "readability_score": 65.2}'::jsonb,
    85.5,  -- SEO score
    1.8    -- Keyword density
);
```

### Get Performance Dashboard
```sql
SELECT * FROM get_article_statistics(30);
-- Returns last 30 days of metrics
```

### Check for Duplicates
```sql
SELECT * FROM find_similar_articles(
    'keto diet',
    'Complete Keto Diet Guide for Beginners'
);
```

### Update Article Status
```sql
SELECT update_article_status(
    123,  -- article_id
    'published',
    'drive_file_id_here',
    'https://docs.google.com/...'
);
```

## Advanced Concepts

### Quality Score Interpretation
- **80-100**: Excellent, ready to publish
- **60-79**: Good, minor improvements needed
- **40-59**: Fair, significant edits required
- **0-39**: Poor, consider regeneration

### Performance Optimization Tips
1. **Batch operations**: Record multiple articles together
2. **Async processing**: Don't block on quality calculation
3. **Cache statistics**: Don't recalculate frequently
4. **Archive old data**: Move to cold storage

What questions do you have about article tracking and quality metrics, Finn?
Would you like me to explain how readability scores are calculated?
Try this exercise: Design a query to find your best-performing articles by quality score and generation time.