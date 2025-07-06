# Text Processor Module - Deep Dive Explanation

## Purpose
The `rag/processor.py` module handles all text processing tasks for the RAG system, including intelligent text chunking, preprocessing, and metadata extraction. It ensures that text is properly prepared for embedding generation while preserving semantic meaning and context.

## Architecture

### Core Components

#### 1. **TextChunk Dataclass**
A structured representation of a processed text chunk that includes:
- `content`: The actual text content
- `metadata`: Associated metadata (source, type, etc.)
- `chunk_index`: Position in the original document
- `source_id`: Optional identifier for the source document

#### 2. **TextProcessor Class**
The main processing engine that:
- Chunks text while preserving sentence boundaries
- Handles overlap between chunks for context preservation
- Processes research findings into structured chunks
- Extracts metadata for better searchability

### Key Design Decisions

#### Why Sentence-Aware Chunking?
```python
def _create_chunks_from_sentences(self, sentences: List[str]) -> List[str]:
```
- **Preserves Meaning**: Cutting text mid-sentence loses context
- **Better Embeddings**: Complete thoughts generate more accurate vectors
- **Improved Retrieval**: Users find complete, understandable chunks

#### Why Overlapping Chunks?
```python
if self.chunk_overlap > 0:
    # Keep some sentences from previous chunk
```
- **Context Preservation**: Important information at chunk boundaries isn't lost
- **Better Matching**: Queries might match content that spans chunks
- **Semantic Continuity**: Overlapping content helps maintain narrative flow

## Key Concepts

### 1. **Text Normalization**
```python
def _normalize_text(self, text: str) -> str:
    # Replace multiple whitespaces
    text = self._whitespace.sub(' ', text)
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
```
This ensures consistent processing regardless of source formatting.

### 2. **Sentence Splitting**
```python
# Handle abbreviations
text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr)\.\s*', r'\1<DOT> ', text)
```
Prevents incorrect splits at abbreviations like "Dr. Smith" or "Inc."

### 3. **Metadata Enrichment**
```python
metadata = {
    "source_type": "academic_source",
    "keyword": keyword,
    "credibility_score": source.credibility_score,
    "is_academic": source.domain in [".edu", ".gov", ".org"]
}
```
Rich metadata enables better filtering and ranking during retrieval.

## Decision Rationale

### Why 1000 Character Default Chunk Size?
- **API Limits**: Fits well within embedding model token limits
- **Context Window**: Provides enough context for meaningful embeddings
- **Performance**: Balances between too many small chunks and too few large ones

### Why 200 Character Overlap?
- **Sentence Coverage**: Typically covers 1-2 sentences
- **Context Bridge**: Enough to maintain continuity
- **Storage Efficiency**: Not too much duplicate content

### Why Process Different Content Types Separately?
```python
# Process research summary
# Process academic sources
# Process key findings
# Process statistics
```
Each content type has different characteristics and importance levels, allowing for:
- Type-specific retrieval
- Weighted search results
- Better organization

## Learning Path

### For Beginners:
1. Understand regular expressions for text processing
2. Learn about text tokenization concepts
3. Practice with simple sentence splitting
4. Explore different chunking strategies

### For Intermediate Developers:
1. Implement advanced NLP techniques (spaCy, NLTK)
2. Add language detection and multilingual support
3. Create custom chunking strategies for specific domains
4. Build chunk quality metrics

### For Advanced Developers:
1. Implement semantic chunking using embeddings
2. Create adaptive chunk sizing based on content
3. Add chunk compression techniques
4. Build parallel processing for large documents

## Real-world Applications

### 1. **Document Processing Pipeline**
```python
async def process_document(file_path: Path):
    """Process a document for RAG storage."""
    # Extract text from various formats
    text = extract_text(file_path)
    
    # Process with metadata
    processor = TextProcessor(config)
    chunks = processor.chunk_text(text, metadata={
        "filename": file_path.name,
        "file_type": file_path.suffix,
        "processed_date": datetime.now()
    })
    
    # Generate embeddings and store
    embeddings = await generate_embeddings(chunks)
    await store_chunks(chunks, embeddings)
```

### 2. **Streaming Text Processing**
```python
async def process_stream(text_stream):
    """Process streaming text in real-time."""
    processor = TextProcessor(config)
    buffer = ""
    
    async for text in text_stream:
        buffer += text
        
        # Process complete sentences
        if len(buffer) > processor.chunk_size * 2:
            sentences = processor._split_sentences(buffer)
            # Keep last sentence in buffer
            buffer = sentences[-1] if sentences else ""
            
            # Process complete sentences
            chunks = processor._create_chunks_from_sentences(sentences[:-1])
            yield chunks
```

### 3. **Multi-format Support**
```python
def process_multiple_formats(content: Any) -> List[TextChunk]:
    """Process content from various sources."""
    processor = TextProcessor(config)
    
    if isinstance(content, ResearchFindings):
        return processor.process_research_findings(content)
    elif isinstance(content, dict):  # JSON data
        text = json.dumps(content, indent=2)
        return processor.chunk_text(text, metadata={"format": "json"})
    elif isinstance(content, str):  # Plain text
        return processor.chunk_text(content)
```

## Common Pitfalls

### 1. **Losing Context at Boundaries**
**Problem**: Important information split between chunks
**Solution**: Use overlap and sentence-aware chunking

### 2. **Abbreviation Handling**
**Problem**: "Dr. Smith" becomes two sentences
**Solution**: Pre-process common abbreviations

### 3. **Large Single Sentences**
**Problem**: Scientific texts with very long sentences
**Solution**: Word-level splitting for sentences exceeding chunk size

### 4. **Metadata Bloat**
**Problem**: Metadata larger than chunk content
**Solution**: Store metadata separately with references

## Best Practices

### 1. **Always Normalize Input**
```python
text = self._normalize_text(text)
```
Ensures consistent processing regardless of source.

### 2. **Preserve Original Structure**
Keep paragraph breaks and formatting cues in metadata.

### 3. **Test Edge Cases**
- Empty text
- Single word
- Very long sentences
- Special characters
- Different languages

### 4. **Monitor Chunk Quality**
Track metrics like:
- Average chunk size
- Sentence completeness
- Overlap effectiveness

## Security Considerations

### 1. **Input Sanitization**
```python
# Remove control characters
text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
```
Prevents injection attacks and encoding issues.

### 2. **Size Limits**
Enforce maximum text size to prevent DoS attacks.

### 3. **Content Validation**
Ensure chunks don't contain sensitive patterns (SSN, credit cards).

## Performance Implications

### 1. **Regex Compilation**
```python
# Compile once in __init__
self._sentence_endings = re.compile(r'[.!?]+\s+')
```
Pre-compiled patterns are much faster than runtime compilation.

### 2. **Memory Usage**
Large documents create many chunks. Consider:
- Streaming processing for huge files
- Chunk generation on-demand
- Efficient data structures

### 3. **Processing Speed**
- Sentence splitting: O(n) where n is text length
- Chunking: O(m) where m is number of sentences
- Overall: Linear time complexity

## Interactive Learning Exercises

### Exercise 1: Custom Chunking Strategy
Implement a chunking strategy that preserves markdown headers:
```python
def chunk_by_headers(self, markdown_text: str) -> List[TextChunk]:
    """Chunk markdown text by headers."""
    # Split by headers
    sections = re.split(r'\n#{1,6}\s+', markdown_text)
    
    chunks = []
    for section in sections:
        if len(section) <= self.chunk_size:
            chunks.append(section)
        else:
            # Further chunk large sections
            sub_chunks = self.chunk_text(section)
            chunks.extend(sub_chunks)
    
    return chunks
```

### Exercise 2: Language-Aware Processing
Add language detection and language-specific sentence splitting:
```python
def detect_language(self, text: str) -> str:
    """Detect text language."""
    # Use langdetect or similar
    pass

def split_sentences_by_language(self, text: str, language: str) -> List[str]:
    """Split sentences based on language rules."""
    if language == "en":
        return self._split_sentences(text)
    elif language == "zh":  # Chinese
        # Use different rules
        pass
```

### Exercise 3: Chunk Quality Metrics
Create metrics to evaluate chunk quality:
```python
def evaluate_chunk_quality(self, chunk: TextChunk) -> Dict[str, float]:
    """Evaluate the quality of a chunk."""
    return {
        "completeness": self._sentence_completeness_score(chunk.content),
        "density": len(chunk.content.split()) / len(chunk.content),
        "readability": self._calculate_readability(chunk.content),
        "keyword_relevance": self._keyword_relevance_score(chunk)
    }
```

## What questions do you have about this code, Finn?

Would you like me to explain any specific part in more detail? Perhaps you're curious about:
- How to implement more sophisticated NLP techniques?
- Different chunking strategies for specific use cases?
- How to handle multilingual text processing?

Try this exercise: Implement a method that chunks text based on semantic similarity rather than character count. This would involve generating embeddings for sentences and grouping similar ones together up to the chunk size limit.