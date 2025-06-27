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
|   Tavily API      |                 |  Prompt Templates |
|   Integration     |                 |   Management      |
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
├── drafts/                # Output directory for articles
│   └── {keyword}_{timestamp}/  # Per-article output
│       ├── index.html          # Review interface
│       ├── article.html        # Generated article
│       └── research.json       # Research data
└── tests/                 # Test directory
    ├── test_config.py     # Configuration tests
    ├── test_tools.py      # API wrapper tests
    ├── test_agents.py     # Agent tests
    └── test_workflow.py   # Workflow tests
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
- Research result caching
- Alternative API fallbacks

### Phase 2 Enhancements
- WordPress draft integration
- SEO scoring metrics
- Performance analytics

### Phase 3 Enhancements
- Web UI with Streamlit
- Scheduled article generation
- Multi-topic support beyond blood sugar/keto

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
