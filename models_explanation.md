# models.py Explanation

## Purpose
The `models.py` file defines the data structures that flow through our SEO Content Automation System. These Pydantic models ensure type safety, validation, and structured communication between our PydanticAI agents.

## Architecture

### Data Flow Through Models
```
Tavily API → AcademicSource → ResearchFindings → ArticleOutput → HTML
```

Each model represents a stage in our content generation pipeline:
1. **AcademicSource**: Individual research sources
2. **ResearchFindings**: Aggregated research from Research Agent
3. **ArticleOutput**: Complete article from Writer Agent
4. **ArticleSection/Subsection**: Article structure components

## Key Concepts

### Pydantic Models for AI Agents
```python
class ResearchFindings(BaseModel):
    keyword: str = Field(...)
```
- PydanticAI agents output these structured models
- Automatic validation ensures data quality
- Type hints enable IDE support and error catching

### Field Definitions with Constraints
```python
title: str = Field(
    ...,
    min_length=10,
    max_length=70
)
```
- `...` (Ellipsis) = Required field
- Constraints ensure SEO best practices
- Descriptions document each field's purpose

### Validators for Business Logic
```python
@validator("academic_sources")
def validate_source_credibility(cls, v):
```
- Custom validation beyond type checking
- Enforces business rules (e.g., credibility thresholds)
- Transforms data as needed

## Model Deep Dive

### AcademicSource Model
**Purpose**: Represents individual research sources with credibility scoring

**Key Features**:
- URL validation ensures proper format
- Credibility score (0-1) for ranking
- Citation generation for references
- Domain extraction for trust assessment

**Design Decisions**:
- Optional fields for flexibility (not all sources have all metadata)
- 500-char excerpt limit for readability
- Built-in citation formatter for consistency

### ResearchFindings Model
**Purpose**: Output from Research Agent with structured findings

**Key Features**:
- Minimum requirements (1+ source, 3+ findings)
- Automatic source sorting by credibility
- Markdown summary generation
- Timestamp tracking for freshness

**Design Decisions**:
- `min_items` ensures substantial research
- `get_top_sources()` for easy filtering
- Validation requires credible sources (0.7+)

### ArticleOutput Model
**Purpose**: Complete article ready for publishing

**Key Features**:
- SEO-optimized metadata (title, description)
- Structured sections with hierarchy
- Word count and reading time calculation
- Keyword density tracking

**Design Decisions**:
- Title length matches Google's display limits
- Minimum 1000 words for SEO value
- HTML generation built-in for convenience

### Section Models
**Purpose**: Hierarchical article structure (H2/H3 levels)

**Key Features**:
- Enforced content minimums
- Heading validation and cleaning
- Nested structure support

## Decision Rationale

### Why Separate Models?
1. **Single Responsibility**: Each model has one purpose
2. **Agent Isolation**: Research Agent doesn't know about article structure
3. **Testability**: Easy to test each model independently
4. **Flexibility**: Can modify one without affecting others

### Why Validation Constraints?
1. **SEO Requirements**: Title/description lengths matter
2. **Quality Control**: Minimum content lengths ensure substance
3. **Error Prevention**: Catch issues early, not at runtime
4. **User Guidance**: Clear error messages when constraints violated

### Why Built-in Methods?
1. **to_citation()**: Consistent citation format
2. **to_markdown_summary()**: Debug and preview research
3. **to_html()**: Direct output generation
4. **get_top_sources()**: Common operation simplified

## Learning Path

### Basic Model Usage
```python
# Creating a model instance
source = AcademicSource(
    title="Study on Climate Change",
    url="https://example.edu/study",
    excerpt="This study examines...",
    domain=".edu",
    credibility_score=0.9
)

# Accessing fields
print(source.title)
print(source.credibility_score)

# Using methods
citation = source.to_citation()
```

### Validation in Action
```python
# This will raise ValidationError
bad_source = AcademicSource(
    title="Study",
    url="not-a-url",  # Invalid URL
    excerpt="...",
    domain="edu",
    credibility_score=1.5  # Out of range
)
```

### Working with Nested Models
```python
article = ArticleOutput(
    title="Understanding AI",
    meta_description="Learn about artificial intelligence...",
    main_sections=[
        ArticleSection(
            heading="What is AI?",
            content="AI is...",
            subsections=[
                ArticleSubsection(
                    heading="Machine Learning",
                    content="ML is a subset..."
                )
            ]
        )
    ]
)
```

## Real-world Applications

### Agent Integration
```python
# Research Agent outputs ResearchFindings
research_agent = Agent(
    model='openai:gpt-4',
    output_type=ResearchFindings,
    system_prompt="Research academic sources..."
)

# Writer Agent consumes ResearchFindings, outputs ArticleOutput
writer_agent = Agent(
    model='openai:gpt-4',
    output_type=ArticleOutput,
    system_prompt="Write SEO-optimized articles..."
)
```

### Data Pipeline
```python
# Research phase
findings = await research_agent.run(keyword)

# Writing phase (findings passed as context)
article = await writer_agent.run(
    prompt=f"Write about {keyword}",
    context={"research": findings}
)

# Output phase
html = article.to_html()
```

### Validation Benefits
- Type errors caught at development time
- Clear error messages for users
- Consistent data structure across system
- Self-documenting code

## Common Pitfalls

### 1. Forgetting Forward References
```python
# Wrong - circular reference error
class ArticleSection(BaseModel):
    subsections: List[ArticleSubsection]  # Not defined yet!

# Right - use quotes for forward references
class ArticleSection(BaseModel):
    subsections: List['ArticleSubsection']
    
# Then rebuild after all models defined
ArticleSection.model_rebuild()
```

### 2. Over-Constraining Fields
```python
# Too restrictive
title: str = Field(..., regex="^[A-Za-z ]+$")  # No numbers/symbols!

# Better - allow flexibility
title: str = Field(..., min_length=10, max_length=70)
```

### 3. Missing Default Factories
```python
# Wrong - mutable default
statistics: List[str] = []  # Shared between instances!

# Right - use default_factory
statistics: List[str] = Field(default_factory=list)
```

### 4. Validation Logic in Wrong Place
```python
# Wrong - business logic in model
def save_to_database(self):
    # Models shouldn't know about databases

# Right - keep models pure
def to_dict(self):
    return self.model_dump()
```

## Best Practices

### Model Design
1. **Start Simple**: Add fields as needed
2. **Use Descriptive Names**: `credibility_score` not `score`
3. **Document Fields**: Use Field descriptions
4. **Validate Early**: Add constraints upfront

### Testing Models
```python
def test_academic_source_validation():
    # Test valid source
    source = AcademicSource(...)
    assert source.credibility_score <= 1.0
    
    # Test invalid source
    with pytest.raises(ValidationError):
        AcademicSource(credibility_score=2.0)
```

### Model Evolution
1. **Add Optional Fields**: For backward compatibility
2. **Use Migrations**: When changing required fields
3. **Version Your Models**: For API compatibility
4. **Test Thoroughly**: Especially validators

## Debugging Tips

### Validation Errors
```python
try:
    model = ResearchFindings(**data)
except ValidationError as e:
    print(e.json(indent=2))  # Pretty-printed errors
```

### Model Inspection
```python
# See all fields
print(ResearchFindings.model_fields)

# Get JSON schema
print(ResearchFindings.model_json_schema())

# Export to dict
data = findings.model_dump()
```

### Common Issues
- **Missing required fields**: Check the `...` fields
- **Type mismatches**: Ensure correct types from agents
- **Validation failures**: Check constraint messages
- **Circular imports**: Use forward references

What questions do you have about these models, Finn?

Try this exercise: Create a new model for tracking SEO metrics (keyword occurrences, header structure, etc.) that could be used to score articles!