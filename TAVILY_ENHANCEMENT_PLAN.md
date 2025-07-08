# Tavily Enhancement Plan for SEO Content Automation System

## Executive Summary

This plan details how to enhance our existing PydanticAI research agent with Tavily's advanced web capabilities (search, extract, crawl) while maintaining our current architecture and adding sophisticated Supabase storage for better data persistence and retrieval.

## Current System Analysis

### What We Have
1. **Research Agent** (`research_agent/agent.py`)
   - Uses PydanticAI framework
   - Currently uses basic Tavily search via `search_academic_sources`
   - Implements RAG caching through `ResearchRetriever`
   - Returns structured `ResearchFindings` model

2. **Storage System** (`rag/storage.py`)
   - Supabase integration with pgvector
   - Vector embeddings for semantic search
   - Connection pooling with asyncpg
   - Basic caching mechanism

3. **Tools** (`tools.py`)
   - `TavilyClient` with basic search functionality
   - Rate limiting and retry logic
   - Credibility scoring system

### What We're Missing
1. **Advanced Tavily Features**
   - Extract: Full content extraction from URLs
   - Crawl: Website traversal and deep content gathering
   - Map: Quick link discovery
   - Advanced search parameters (time range, instructions)

2. **Sophisticated Storage**
   - Structured storage for different content types
   - Relationship mapping between sources
   - Advanced querying capabilities
   - Content versioning

## Enhancement Architecture

### Phase 1: Tavily API Enhancement

#### 1.1 Extend TavilyClient with Full API Support

```python
# Enhanced tools.py additions
class EnhancedTavilyClient(TavilyClient):
    """Extended Tavily client with full API capabilities."""
    
    async def extract(self, urls: List[str], extract_depth: str = "advanced") -> Dict:
        """Extract full content from specific URLs."""
        
    async def crawl(self, url: str, max_depth: int = 2, instructions: Optional[str] = None) -> Dict:
        """Crawl website for comprehensive content."""
        
    async def map(self, url: str, instructions: Optional[str] = None) -> Dict:
        """Map website structure quickly."""
```

#### 1.2 Create Specialized Tool Functions for Agent

```python
# research_agent/tools.py additions
async def extract_full_content(ctx: RunContext[None], urls: List[str], config: Config) -> Dict:
    """Extract full content from URLs for deep analysis."""
    
async def crawl_website(ctx: RunContext[None], url: str, instructions: str, config: Config) -> Dict:
    """Crawl website with specific instructions."""
    
async def analyze_domain_authority(ctx: RunContext[None], url: str) -> Dict:
    """Analyze domain for credibility and authority metrics."""
```

### Phase 2: Enhanced Research Agent

#### 2.1 Multi-Step Research Workflow

```python
# research_agent/agent.py enhancements
class ResearchWorkflow:
    """Orchestrates multi-step research process."""
    
    async def execute_research_pipeline(self, keyword: str):
        # Step 1: Initial broad search
        # Step 2: Identify high-value sources
        # Step 3: Extract full content from top sources
        # Step 4: Crawl promising domains for related content
        # Step 5: Synthesize findings
```

#### 2.2 Dynamic Tool Selection

```python
@research_agent.tool
async def smart_research_tool(ctx: RunContext[None], query: str, research_type: str) -> Dict:
    """Dynamically selects appropriate Tavily tool based on research needs."""
    
    if research_type == "broad_survey":
        return await search_with_params(query, time_range="month", max_results=20)
    elif research_type == "deep_dive":
        # Search → Extract → Crawl workflow
    elif research_type == "competitor_analysis":
        # Crawl specific domains
```

### Phase 3: Advanced Supabase Storage

#### 3.1 Enhanced Database Schema

```sql
-- Research sources table with relationships
CREATE TABLE research_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    title TEXT,
    full_content TEXT,
    excerpt TEXT,
    credibility_score FLOAT,
    source_type TEXT,
    authors JSONB,
    publication_date TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Research findings table
CREATE TABLE research_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    research_summary TEXT,
    main_findings JSONB,
    key_statistics JSONB,
    research_gaps JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Source relationships
CREATE TABLE source_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES research_sources(id),
    related_source_id UUID REFERENCES research_sources(id),
    relationship_type TEXT,
    strength FLOAT
);

-- Content chunks with enhanced metadata
CREATE TABLE content_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES research_sources(id),
    chunk_text TEXT,
    chunk_embedding vector(1536),
    chunk_metadata JSONB,
    chunk_type TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.2 Storage Manager Enhancement

```python
# rag/storage.py enhancements
class EnhancedVectorStorage(VectorStorage):
    """Extended storage with structured data management."""
    
    async def store_research_source(self, source: AcademicSource, full_content: Optional[str] = None):
        """Store complete source with relationships."""
        
    async def store_crawl_results(self, crawl_data: Dict, parent_url: str):
        """Store crawled website data with hierarchy."""
        
    async def get_related_sources(self, source_id: str, relationship_type: str = None):
        """Retrieve related sources based on relationships."""
        
    async def search_by_criteria(self, domain: str = None, date_range: tuple = None, 
                                min_credibility: float = None):
        """Advanced search with multiple criteria."""
```

### Phase 4: Intelligent Research Features

#### 4.1 Research Memory System

```python
class ResearchMemory:
    """Maintains context across research sessions."""
    
    def __init__(self, storage: EnhancedVectorStorage):
        self.storage = storage
        self.session_cache = {}
        
    async def remember_source_quality(self, domain: str, quality_metrics: Dict):
        """Track source quality over time."""
        
    async def get_preferred_sources(self, topic: str) -> List[str]:
        """Return historically reliable sources for topic."""
        
    async def avoid_low_quality_domains(self) -> List[str]:
        """Return domains to exclude based on past experience."""
```

#### 4.2 Adaptive Research Strategy

```python
class AdaptiveResearchStrategy:
    """Adapts research approach based on initial findings."""
    
    async def analyze_initial_results(self, results: List[Dict]) -> str:
        """Determine best research strategy."""
        
        if self._is_emerging_topic(results):
            return "crawl_news_sites"
        elif self._is_academic_topic(results):
            return "deep_extract_journals"
        elif self._is_technical_topic(results):
            return "crawl_documentation"
```

### Phase 5: Integration Points

#### 5.1 Enhanced Agent Prompt

```python
ENHANCED_RESEARCH_PROMPT = """
You are an advanced research agent with sophisticated web capabilities:

1. **Search**: Find relevant sources with time filtering and domain preferences
2. **Extract**: Get full content from valuable sources
3. **Crawl**: Explore entire websites for comprehensive coverage
4. **Analyze**: Assess source credibility and extract key insights

Research Strategy:
- Start with broad search to understand the landscape
- Identify 3-5 high-value sources for deep extraction
- Crawl 1-2 authoritative domains for additional context
- Synthesize findings with emphasis on recent, credible sources

Always:
- Prefer .edu, .gov, and peer-reviewed sources
- Extract specific statistics and data points
- Note conflicting information between sources
- Identify gaps in current research
"""
```

#### 5.2 Workflow Integration

```python
async def enhanced_research_workflow(agent: Agent, keyword: str) -> ResearchFindings:
    """Execute enhanced multi-step research process."""
    
    # Step 1: Initial search with time filtering
    recent_results = await agent.run(
        f"Search for recent developments in {keyword} from the last 3 months"
    )
    
    # Step 2: Deep extraction from top sources
    top_sources = recent_results.get_top_sources(3)
    extracted_content = await agent.run(
        f"Extract full content from these sources: {top_sources}"
    )
    
    # Step 3: Targeted crawling
    if needs_deeper_research(extracted_content):
        crawl_results = await agent.run(
            f"Crawl the most authoritative domain for comprehensive {keyword} information"
        )
    
    # Step 4: Synthesis with storage
    return await synthesize_and_store(all_results)
```

## Implementation Timeline

### Week 1: Foundation
- Extend TavilyClient with extract, crawl, map methods
- Create enhanced database schema
- Update models.py with new data structures

### Week 2: Agent Enhancement
- Implement new tool functions for agent
- Create multi-step research workflow
- Add dynamic tool selection logic

### Week 3: Storage Integration
- Implement EnhancedVectorStorage
- Add relationship mapping
- Create research memory system

### Week 4: Advanced Features
- Implement adaptive research strategy
- Add quality tracking
- Create comprehensive testing suite

### Week 5: Optimization & Testing
- Performance optimization
- Integration testing
- Documentation updates

## Key Benefits

1. **Deeper Research**: Full content extraction provides complete context
2. **Comprehensive Coverage**: Crawling ensures no important information is missed
3. **Better Quality**: Enhanced credibility scoring and source relationships
4. **Improved Efficiency**: Intelligent caching and memory reduce redundant API calls
5. **Richer Data**: Structured storage enables advanced querying and analysis

## Success Metrics

- 50% increase in source credibility scores
- 75% reduction in redundant API calls through intelligent caching
- 3x more content extracted per research session
- 90% accuracy in identifying research gaps
- 40% improvement in content generation quality scores

## Next Steps

1. Review and approve this plan
2. Set up enhanced database schema
3. Begin Phase 1 implementation
4. Create comprehensive test suite
5. Document new capabilities

## Code Quality Considerations

- Maintain backward compatibility
- Add comprehensive error handling
- Include detailed logging
- Write extensive tests
- Update documentation

This enhancement will transform our research agent from a basic search tool into a sophisticated research assistant capable of deep, nuanced analysis of any topic.