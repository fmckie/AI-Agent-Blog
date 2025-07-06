# SEO Content Automation System Planning

This document outlines the high-level design for building an MVP of an automated content generation system using PydanticAI. The system researches keywords using academic sources via Tavily API, generates SEO-optimized articles, and produces HTML drafts for human review. This planning document serves as your architectural blueprint, explaining not just what to build but why each decision makes sense.

## System Architecture

Our system follows a user-initiated pipeline where each component has a single, well-defined responsibility:

```
                    +------------------+
                    |   User Query     |
                    |   (Keyword)      |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Workflow        |
                    |  Orchestrator    |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                                     |
+---------v---------+                 +---------v---------+
|  Research Agent   |                 |   Writer Agent    |
|  (PydanticAI)     |                 |   (PydanticAI)    |
+---------+---------+                 +---------+---------+
          |                                     |
          |                                     |
+---------v---------+                 +---------v---------+
|   RAG Cache       |                 |  Prompt Templates |
|   (Supabase)      |                 |   Management      |
+---------+---------+                 +-------------------+
          |                                     |
          |                                     |
+---------v---------+                 +---------v---------+
|   Tavily API      |                 |  Google Drive     |
|   Integration     |                 |  Integration      |
+-------------------+                 +-------------------+
                             |
                    +--------v---------+
                    |   HTML Output    |
                    |   (Drafts)       |
                    +------------------+
```

### Key Components:

1. **Workflow Orchestrator (`workflow.py`)**
   - Receives user keyword queries
   - Coordinates agent execution
   - Manages data flow between agents
   - Handles error recovery
   - Saves output drafts

2. **Research Agent (`agents.py`)**
   - Uses PydanticAI for structured research
   - Integrates Tavily API as a tool
   - Focuses on academic sources
   - Returns structured ResearchFindings model
   - Implements credibility scoring

3. **Writer Agent (`agents.py`)**
   - Uses PydanticAI for content generation
   - Consumes ResearchFindings from Research Agent
   - Applies SEO optimization
   - Outputs structured ArticleOutput model
   - Formats content as HTML

4. **Tavily Integration (`tools.py`)**
   - Async HTTP client wrapper
   - Academic source filtering
   - Rate limit handling
   - Error recovery with retries

5. **Configuration Management (`config.py`)**
   - Environment variable loading
   - API key management
   - Output directory configuration
   - Validation of required settings

6. **Entry Point (`main.py`)**
   - CLI interface using Click
   - User query collection
   - Workflow initialization
   - Result presentation

7. **RAG Cache System (`rag/`)**
   - Vector storage using Supabase with pgvector
   - Semantic search for cached research
   - Embedding generation with OpenAI
   - Automatic cache warming and management
   - Hybrid search combining exact and semantic matches

8. **Google Drive Integration (`rag/drive/`)**
   - OAuth 2.0 authentication
   - Automatic article upload to Drive
   - Document folder monitoring
   - File format conversion (HTML to Google Docs)
   - Version tracking and metadata management

## Development Phases

The project is organized into manageable phases that build upon each other:

### Phase 1: Foundation Setup
Establish project structure, configuration management, and understand async patterns.

### Phase 2: API Integration
Build the Tavily API wrapper with proper async handling and error recovery.

### Phase 3: Research Agent
Implement the PydanticAI-based research agent that analyzes academic sources.

### Phase 4: Writer Agent
Create the content generation agent that transforms research into articles.

### Phase 5: Workflow Orchestration
Connect all components into a cohesive workflow with proper error handling.

### Phase 6: User Interface
Build the CLI interface for easy interaction with the system.

### Phase 7: RAG System & Knowledge Management
Implement vector storage for research caching and Google Drive integration for knowledge persistence.

## Environment Configuration

The system uses environment variables for secure configuration:

```bash
# API Keys
TAVILY_API_KEY=              # Your Tavily API key for web search
OPENAI_API_KEY=              # Your OpenAI API key for content generation

# Output Configuration
OUTPUT_DIR=./drafts          # Directory for saving article drafts

# Optional Settings
LOG_LEVEL=INFO               # Logging verbosity (DEBUG, INFO, WARNING, ERROR)
MAX_RETRIES=3                # Maximum retry attempts for API calls
REQUEST_TIMEOUT=30           # API request timeout in seconds

# RAG System Configuration
SUPABASE_URL=                # Your Supabase project URL
SUPABASE_SERVICE_KEY=        # Your Supabase service key
EMBEDDING_MODEL_NAME=text-embedding-3-small  # OpenAI embedding model
EMBEDDING_BASE_URL=https://api.openai.com/v1  # Embedding API base URL

# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=      # Folder ID for monitoring documents
GOOGLE_DRIVE_UPLOAD_FOLDER_ID= # Folder ID for uploading articles
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json  # Path to Google credentials
```

## File Structure

```
seo_content_automation/
├── .env                     # Environment variables (not in git)
├── .env.example            # Example environment configuration
├── .gitignore              # Git ignore file
├── requirements.txt        # Python dependencies
├── README.md              # Project documentation
├── PLANNING.md            # This planning document
├── TASKS.md               # Detailed implementation tasks
├── main.py                # CLI entry point
├── config.py              # Configuration management
├── workflow.py            # Workflow orchestration
├── agents.py              # Research and Writer agents
├── tools.py               # API integrations and utilities
├── prompts/               # Prompt template directory
│   └── article_template.txt    # Article generation prompt
├── rag/                   # RAG system module
│   ├── __init__.py       # Module initialization
│   ├── embeddings.py     # OpenAI embedding generation
│   ├── storage.py        # Supabase vector operations
│   ├── retriever.py      # Semantic search logic
│   ├── processor.py      # Text chunking and processing
│   ├── config.py         # RAG-specific configuration
│   └── drive/            # Google Drive integration
│       ├── __init__.py   # Drive module init
│       ├── uploader.py   # Article upload to Drive
│       ├── watcher.py    # Folder monitoring
│       └── auth.py       # OAuth authentication
├── sql/                   # Database schemas
│   ├── research_documents.sql   # Research chunks table
│   ├── research_metadata.sql    # Source tracking table
│   ├── research_cache.sql       # Complete Tavily responses
│   ├── generated_articles.sql   # Article tracking table
│   └── drive_documents.sql      # Drive document embeddings
├── drafts/                # Output directory for articles
│   └── {keyword}_{timestamp}/  # Per-article output
│       ├── index.html          # Review interface
│       ├── article.html        # Generated article
│       └── research.json       # Research data
└── tests/                 # Test directory
    ├── test_config.py     # Configuration tests
    ├── test_tools.py      # API wrapper tests
    ├── test_agents.py     # Agent tests
    ├── test_workflow.py   # Workflow tests
    └── test_rag/          # RAG system tests
        ├── test_embeddings.py
        ├── test_storage.py
        ├── test_retriever.py
        └── test_drive.py
```

## Data Flow

Understanding how data moves through the system helps you debug and extend it:

1. **User Input** → Keyword string enters via CLI
2. **Research Phase** → Keyword becomes ResearchFindings (Pydantic model)
3. **Writing Phase** → ResearchFindings becomes ArticleOutput (Pydantic model)
4. **Output Phase** → ArticleOutput becomes HTML files and JSON metadata

### Research Data Model

```python
class ResearchFindings(BaseModel):
    keyword: str
    summary: str
    academic_sources: List[AcademicSource]
    key_statistics: List[str]
    research_gaps: List[str]
```

### Article Output Model

```python
class ArticleOutput(BaseModel):
    title: str
    meta_description: str
    introduction: str
    main_content: str
    conclusion: str
    word_count: int
```

## Data Persistence & Knowledge Management

The RAG system provides intelligent caching and knowledge persistence:

### RAG System Architecture

```
                    +------------------+
                    |  Research Query  |
                    +--------+---------+
                             |
                    +--------v---------+
                    |   RAG Retriever  |
                    |  (Semantic Search)|
                    +--------+---------+
                             |
                +------------+------------+
                |                         |
       +--------v--------+       +--------v--------+
       |  Cache Hit?     |  No   |   Tavily API   |
       |  (Similarity>0.8)| ----> |   (Fresh Data)  |
       +--------+--------+       +--------+--------+
                |                         |
                | Yes                     |
                |                +--------v--------+
                |                |  Store in RAG   |
                |                |  (Embeddings)   |
                +--------+-------+--------+--------+
                         |                |
                +--------v--------+       |
                | Return Cached   |<------+
                | Research Data   |
                +-----------------+
```

### Google Drive Integration

```
SEO Content Automation/
├── Generated Articles/          # Auto-uploaded articles
│   ├── 2024-01/                # Monthly organization
│   │   ├── keyword1_article.gdoc
│   │   └── keyword2_article.gdoc
│   └── 2024-02/
└── Knowledge Base/             # Monitored for embeddings
    ├── Research/               # External research docs
    └── References/             # Reference materials
```

### Vector Storage Design

1. **Research Documents Table**
   - Stores text chunks with embeddings
   - Enables semantic similarity search
   - Links to source metadata

2. **Research Cache Table**
   - Stores complete Tavily API responses
   - Enables exact match lookups
   - Reduces API calls for identical queries

3. **Generated Articles Table**
   - Tracks all generated articles
   - Links research to outputs
   - Enables performance analytics

4. **Drive Documents Table**
   - Stores embeddings from Drive files
   - Enables cross-source search
   - Maintains document versioning

### Caching Strategy

1. **Semantic Cache**: Find similar research even with different keywords
2. **Exact Cache**: Return identical results for repeated queries
3. **TTL Management**: Expire old cache entries (configurable)
4. **Cache Warming**: Pre-populate with common topics

## Error Handling Strategy

The system implements graceful degradation at each level:

1. **API Level**: Exponential backoff with retry limits
2. **Agent Level**: Validation of outputs with fallback options
3. **Workflow Level**: Transaction-like behavior with rollback
4. **User Level**: Clear error messages with actionable guidance

## Testing Strategy

Our testing approach ensures reliability while teaching best practices:

1. **Unit Tests**: Test individual functions in isolation
2. **Integration Tests**: Verify agent interactions
3. **Mock API Tests**: Test without consuming API credits
4. **End-to-End Tests**: Validate complete workflows

## Future Enhancements

These enhancements are planned for after MVP completion:

### Phase 1 Enhancements
- Keyword batch processing
- Alternative API fallbacks
- Multi-language content generation

### Phase 2 Enhancements
- WordPress draft integration
- SEO scoring metrics
- Advanced performance analytics dashboard

### Phase 3 Enhancements
- Web UI with Streamlit
- Scheduled article generation
- Multi-topic support beyond blood sugar/keto

### RAG System Enhancements
- Multi-modal embeddings for images
- Automatic knowledge graph generation
- Cross-article linking suggestions
- Research quality scoring
- Collaborative filtering for content recommendations

## Success Criteria

The MVP is considered complete when:

1. System accepts a keyword and generates an HTML article draft
2. Research focuses on academic sources with credibility scoring
3. Articles are properly formatted with SEO considerations
4. All API errors are handled gracefully
5. Output includes both article and research metadata
6. System is fully documented and tested

## Learning Objectives

Throughout this project, you will:

1. Master async/await patterns in Python
2. Understand structured AI outputs with PydanticAI
3. Learn API integration best practices
4. Practice modular code organization
5. Implement comprehensive error handling
6. Write maintainable, testable code

This planning document evolves with your project. Update it as you learn and make decisions during implementation.
