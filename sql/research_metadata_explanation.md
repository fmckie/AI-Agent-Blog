# Research Metadata Table Explanation

## Purpose
The `research_metadata` table acts as a source registry and credibility tracker, maintaining information about every source referenced in our research to ensure quality and enable intelligent source selection.

## Architecture Overview
This table implements a sophisticated source evaluation system:
- Automatic credibility scoring based on domain patterns
- Source type categorization for filtering
- Usage tracking for popularity metrics
- Quality indicators for academic rigor

## Key Concepts

### 1. Table Structure

#### Source Identification
```sql
source_url TEXT NOT NULL UNIQUE
domain TEXT NOT NULL
```
- **source_url**: Complete URL (unique constraint prevents duplicates)
- **domain**: Extracted for pattern matching (e.g., "nature.com")
- **Design choice**: Separate domain field enables efficient pattern matching

#### Credibility System
```sql
credibility_score FLOAT NOT NULL CHECK (credibility_score >= 0 AND credibility_score <= 1)
is_academic BOOLEAN NOT NULL DEFAULT FALSE
```
- **Score ranges**:
  - 0.0-0.3: Low (personal blogs, forums)
  - 0.3-0.6: Medium (news sites, established blogs)
  - 0.6-0.8: High (research institutions, government)
  - 0.8-1.0: Academic (peer-reviewed, .edu domains)

#### Source Classification
```sql
source_type TEXT CHECK (source_type IN (...))
```
- **Categories**: journal, government, education, organization, news, blog, other
- **Purpose**: Enable filtering by source type
- **Example**: "Show me only journal articles"

### 2. Credibility Algorithm

#### Automatic Scoring Function
```sql
CREATE FUNCTION calculate_credibility_score
```

The algorithm considers:
1. **Domain patterns**: .edu gets 0.8 base score
2. **Known publishers**: nature.com gets 0.85
3. **Quality indicators**: +0.1 for citations
4. **Source type**: +0.1 for journals

#### Domain Recognition Patterns
```sql
-- Academic domains
'%\.(edu|ac\.uk|edu\.au|edu\.ca)$'

-- Journal publishers
'%(nature\.com|science\.org|nejm\.org|bmj\.com)$'

-- Preprint servers
'%(arxiv\.org|biorxiv\.org|medrxiv\.org)$'
```

### 3. Smart Functions

#### Upsert Pattern
```sql
CREATE FUNCTION upsert_research_metadata
```
- **What it does**: Insert new source or update existing
- **Smart feature**: Increments reference count on duplicates
- **Returns**: Whether source is new or existing
- **Use case**: Called whenever we encounter a source

#### Top Sources Analysis
```sql
CREATE FUNCTION get_top_sources_for_research
```
- **Purpose**: Find best sources for a keyword
- **Ranking**: By credibility, then usage frequency
- **Insight**: Shows which sources provide most value

#### Diversity Analysis
```sql
CREATE FUNCTION analyze_source_diversity
```
- **Metrics provided**:
  - Total unique sources
  - Academic vs. general split
  - Source type distribution
  - Credibility spread
- **Use case**: Ensure balanced research

### 4. Quality Indicators

#### Boolean Flags
```sql
has_citations BOOLEAN DEFAULT FALSE
has_methodology BOOLEAN DEFAULT FALSE
```
- **has_citations**: Source references other work
- **has_methodology**: Explains research methods
- **Impact**: Boosts credibility score

#### Usage Tracking
```sql
times_referenced INTEGER DEFAULT 1
first_seen TIMESTAMP
last_updated TIMESTAMP
```
- **Purpose**: Track source popularity and freshness
- **Analytics**: Identify most-used sources
- **Maintenance**: Find stale sources

## Decision Rationale

### Why Track Sources Separately?
1. **Deduplication**: One source entry, many research chunks
2. **Consistency**: Uniform credibility scoring
3. **Performance**: Fast source-based filtering
4. **Analytics**: Source quality insights

### Why Automatic Credibility Scoring?
1. **Objectivity**: Consistent evaluation criteria
2. **Scalability**: No manual review needed
3. **Transparency**: Clear scoring rules
4. **Adaptability**: Easy to adjust algorithm

### Why Domain-Based Patterns?
1. **Reliability**: Domains indicate source type
2. **Efficiency**: Fast pattern matching
3. **Maintenance**: Easy to add new patterns
4. **Coverage**: Handles international domains

## Learning Path

### Understanding Credibility
1. **Domain authority**: Why .edu/.gov are trusted
2. **Peer review**: Academic publishing process
3. **Impact factors**: Journal quality metrics
4. **Preprints**: Faster but less vetted research

### Database Patterns
1. **UPSERT**: Insert or update in one operation
2. **CHECK constraints**: Enforce business rules
3. **Computed columns**: Derive values automatically
4. **Aggregate functions**: Analyze data patterns

## Real-World Applications

### Similar Systems
1. **Google Scholar**: Ranks academic sources
2. **PubMed**: Medical literature database
3. **Web of Science**: Citation tracking
4. **News aggregators**: Source credibility scoring

### Industry Standards
- **CRAAP Test**: Currency, Relevance, Authority, Accuracy, Purpose
- **RADAR Method**: Relevance, Authority, Date, Appearance, Reason
- **Impact Factor**: Journal citation metrics

## Common Pitfalls

1. **Over-trusting domains**: Not all .org sites are credible
2. **Ignoring recency**: Old research may be outdated
3. **Single source bias**: Need diverse perspectives
4. **Missing context**: Credibility varies by topic

## Best Practices Demonstrated

1. **Defensive programming**: Domain constraint validation
2. **Incremental updates**: Reference counting
3. **Audit trail**: Timestamp tracking
4. **Extensibility**: JSONB for future metadata

## Query Examples

### Add New Source
```sql
SELECT * FROM upsert_research_metadata(
    'https://www.nature.com/articles/s41586-021-03819-2',
    'nature.com',
    'journal',
    true,  -- has_citations
    true   -- has_methodology
);
```

### Find Best Sources
```sql
SELECT * FROM get_top_sources_for_research('machine learning', 5);
```

### Analyze Research Quality
```sql
SELECT * FROM analyze_source_diversity('ketogenic diet');
```

## Advanced Features

### Metadata JSONB
Stores additional information:
```json
{
  "publication_name": "Nature Medicine",
  "impact_factor": 87.241,
  "peer_reviewed": true,
  "open_access": false,
  "last_verified": "2024-01-15"
}
```

### Automatic Timestamp Updates
```sql
CREATE TRIGGER update_research_metadata_timestamp_trigger
```
- Ensures last_updated always current
- No manual timestamp management needed

What questions do you have about source credibility assessment, Finn?
Would you like me to explain how impact factors work in academic publishing?
Try this exercise: What other quality indicators could we track for sources?