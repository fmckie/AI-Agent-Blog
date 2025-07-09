# ResearchStrategy Class - Comprehensive Explanation

## Purpose
The ResearchStrategy class implements intelligent decision-making for research operations, analyzing topics to determine the most effective tools and approaches. It acts as the "brain" that decides HOW to research, not just WHAT to research.

## Architecture Overview

### Core Components
1. **TopicType Enum**: Classifies research subjects (Academic, Technical, Medical, etc.)
2. **ResearchDepth Enum**: Defines research intensity levels (Surface → Exhaustive)
3. **ToolType Enum**: Available research tools (Search, Extract, Crawl, Map)
4. **ToolRecommendation**: Structured tool usage suggestions with priorities
5. **ResearchPlan**: Complete research strategy with all recommendations
6. **ResearchStrategy**: The main intelligence class

### Design Philosophy
The class implements **Adaptive Intelligence** through:
- Pattern recognition for topic classification
- Rule-based tool selection
- Dynamic strategy adjustment
- Context-aware decision making

## Key Concepts

### 1. **Topic Classification**
Topics are analyzed using keyword indicators:
```python
# Academic indicators: "research", "study", "peer-reviewed"
# Technical indicators: "programming", "API", "documentation"
# Medical indicators: "health", "treatment", "clinical"
```

### 2. **Tool Prioritization**
Tools are ranked by priority (1-10):
- **10**: Essential tools (always use)
- **7-9**: Primary tools (use in most cases)
- **4-6**: Optional tools (use when beneficial)
- **1-3**: Situational tools (rare use cases)

### 3. **Adaptive Strategy**
The strategy evolves based on:
- Initial result quality
- Source availability
- Time constraints
- Domain coverage

### 4. **Domain Intelligence**
Different topics prefer different domains:
- Academic → .edu, .gov, scholar.google.com
- Technical → .io, github.com, docs.*
- Medical → nih.gov, who.int, .gov

## Decision Rationale

### Why Classification-Based Approach?
1. **Efficiency**: Different topics need different tools
2. **Quality**: Targeted approaches yield better results
3. **Cost**: Avoid unnecessary API calls
4. **Speed**: Skip irrelevant operations

### Why Priority System?
1. **Flexibility**: Tools can be promoted/demoted
2. **Resource Management**: Execute high-priority first
3. **Graceful Degradation**: Skip low-priority on failure
4. **User Control**: Easy to adjust priorities

### Why Adaptive Strategy?
1. **Real-World Variability**: Initial plans may need adjustment
2. **Result-Based Optimization**: Learn from what's working
3. **Failure Recovery**: Adapt when tools don't yield results
4. **Continuous Improvement**: Each stage informs the next

## Learning Path

### For Beginners: Understanding Decision Trees
1. **If-Then Logic**: How rules create decisions
2. **Classification**: Grouping similar things
3. **Prioritization**: Ranking by importance
4. **Adaptation**: Changing plans based on feedback

### For Intermediate: Pattern Recognition
1. **Keyword Analysis**: Extracting meaning from text
2. **Scoring Systems**: Quantifying qualitative decisions
3. **Multi-Criteria Decision Making**: Balancing factors
4. **Feedback Loops**: Using results to improve

### For Advanced: AI Strategy Design
1. **Heuristic Development**: Creating effective rules
2. **Feature Engineering**: What signals matter
3. **Strategy Patterns**: Common decision frameworks
4. **Optimization Theory**: Balancing exploration vs exploitation

## Real-World Applications

### 1. **Search Engine Optimization**
Similar classification used for:
- Query intent detection
- Result ranking algorithms
- Personalization strategies

### 2. **Content Recommendation Systems**
Comparable approaches in:
- Netflix genre classification
- YouTube video categorization
- News feed algorithms

### 3. **Medical Diagnosis Systems**
Pattern matching applied to:
- Symptom analysis
- Treatment selection
- Risk assessment

### 4. **Financial Trading**
Strategy selection used for:
- Market condition analysis
- Algorithm selection
- Risk management

## Common Pitfalls

### 1. **Over-Classification**
- **Mistake**: Creating too many topic types
- **Solution**: Balance granularity with usefulness
- **Example**: Don't separate "AI" and "Machine Learning" topics

### 2. **Rigid Tool Selection**
- **Mistake**: Always using the same tools for a topic type
- **Solution**: Consider context and requirements
- **Example**: Not all technical topics need code crawling

### 3. **Ignoring User Intent**
- **Mistake**: Focusing only on topic keywords
- **Solution**: Consider the research goal
- **Example**: "Python tutorial" vs "Python performance analysis"

### 4. **Poor Adaptation Logic**
- **Mistake**: Overreacting to initial results
- **Solution**: Gradual adjustments with thresholds
- **Example**: Don't abandon strategy after one poor source

## Best Practices

### 1. **Topic Analysis**
```python
# Good: Multi-signal classification
def analyze_topic(self, keyword, context, user_intent):
    signals = {
        'keyword_matches': self._count_keyword_indicators(keyword),
        'context_clues': self._analyze_context(context),
        'intent_markers': self._detect_intent(user_intent),
        'temporal_signals': self._check_recency_needs(keyword)
    }
    return self._classify_from_signals(signals)
```

### 2. **Tool Selection**
```python
# Good: Context-aware tool recommendations
def select_tools(self, topic_type, constraints):
    base_tools = self.tool_matrix[topic_type]
    adjusted_tools = []
    
    for tool in base_tools:
        if self._is_appropriate(tool, constraints):
            priority = self._calculate_priority(tool, topic_type, constraints)
            adjusted_tools.append(ToolRecommendation(tool, priority))
    
    return sorted(adjusted_tools, key=lambda x: x.priority, reverse=True)
```

### 3. **Strategy Adaptation**
```python
# Good: Measured adaptation based on thresholds
def adapt_strategy(self, plan, results):
    quality_score = self._calculate_quality(results)
    
    if quality_score < 0.3:  # Poor results
        return self._broaden_strategy(plan)
    elif quality_score > 0.8:  # Excellent results
        return self._focus_strategy(plan)
    else:  # Adequate results
        return self._tune_strategy(plan, results)
```

### 4. **Domain Targeting**
```python
# Good: Smart domain selection
def identify_targets(self, topic_type, found_domains):
    # Prefer known good domains
    preferred = self.domain_preferences[topic_type]
    matches = [d for d in found_domains if any(p in d for p in preferred)]
    
    # Add backup domains if needed
    if len(matches) < self.min_domains:
        matches.extend(self._get_backup_domains(topic_type))
    
    return self._rank_domains(matches, topic_type)
```

## Implementation Details

### Topic Classification Algorithm
1. **Keyword Scoring**: Count indicator matches
2. **Weight Adjustment**: Keywords weighted 2x context
3. **Threshold Application**: Minimum score for classification
4. **Default Handling**: Fallback to GENERAL type

### Tool Priority Calculation
```python
priority = base_priority * topic_weight * depth_multiplier * success_rate
```
Where:
- base_priority: Tool's inherent importance
- topic_weight: How well tool fits topic
- depth_multiplier: Research depth adjustment
- success_rate: Historical success metric

### Adaptive Feedback Loop
1. **Measure**: Count sources, calculate quality
2. **Analyze**: Compare to expectations
3. **Adjust**: Modify tool selection
4. **Execute**: Run adjusted strategy
5. **Learn**: Store results for future

## Advanced Features

### 1. **Machine Learning Integration**
Future enhancement for topic classification:
```python
def classify_with_ml(self, keyword, context):
    features = self._extract_features(keyword, context)
    prediction = self.classifier.predict(features)
    confidence = self.classifier.predict_proba(features)
    
    if confidence < 0.7:
        # Fall back to rule-based
        return self.analyze_topic(keyword, context)
    return prediction
```

### 2. **Historical Learning**
Track success rates for continuous improvement:
```python
def update_tool_effectiveness(self, topic_type, tool, success):
    key = (topic_type, tool)
    self.effectiveness[key] = (
        self.effectiveness.get(key, 0.5) * 0.9 + 
        (1.0 if success else 0.0) * 0.1
    )
```

### 3. **Cost Optimization**
Balance result quality with API costs:
```python
def optimize_for_budget(self, plan, budget):
    tool_costs = self._calculate_costs(plan.primary_tools)
    if tool_costs > budget:
        return self._reduce_tools(plan, budget)
    return plan
```

### 4. **Parallel Strategy Execution**
Run multiple strategies simultaneously:
```python
async def execute_parallel_strategies(self, keyword):
    strategies = [
        self.create_research_plan(keyword, {"depth": "surface"}),
        self.create_research_plan(keyword, {"depth": "deep"})
    ]
    results = await asyncio.gather(*[
        self.execute_plan(s) for s in strategies
    ])
    return self._merge_best_results(results)
```

## Testing Strategies

### Unit Testing Tool Selection
```python
def test_academic_topic_selection():
    strategy = ResearchStrategy()
    plan = strategy.create_research_plan("quantum computing research")
    
    assert plan.topic_type == TopicType.ACADEMIC
    assert any(t.tool == ToolType.CRAWL for t in plan.primary_tools)
    assert ".edu" in plan.target_domains
```

### Integration Testing Adaptation
```python
def test_strategy_adaptation():
    strategy = ResearchStrategy()
    initial_plan = strategy.create_research_plan("emerging AI trends")
    
    poor_results = {"sources_count": 2, "average_credibility": 0.4}
    adapted_plan = strategy.adapt_strategy(initial_plan, poor_results)
    
    assert len(adapted_plan.search_queries) > len(initial_plan.search_queries)
    assert len(adapted_plan.primary_tools) > len(initial_plan.primary_tools)
```

## Performance Considerations

### 1. **Classification Speed**
- Use compiled regex for pattern matching
- Cache classification results
- Implement early exit conditions

### 2. **Memory Usage**
- Lazy load domain preferences
- Limit history storage
- Use generators for large lists

### 3. **Scalability**
- Stateless design for parallel execution
- Async-ready methods
- Configurable timeouts

## Next Steps

### Immediate Enhancements
1. Add more topic types (Legal, Educational)
2. Implement success tracking
3. Add budget constraints
4. Create strategy templates

### Future Features
1. ML-based classification
2. A/B testing strategies
3. User preference learning
4. Multi-language support

## Exercises for Learning

### Exercise 1: Add a New Topic Type
Add a "LEGAL" topic type:
```python
# 1. Add to TopicType enum
# 2. Add indicators to topic_indicators
# 3. Add domain preferences
# 4. Test classification accuracy
```

### Exercise 2: Implement Cost Awareness
Add cost tracking to tool selection:
```python
# 1. Add cost attribute to ToolRecommendation
# 2. Calculate total plan cost
# 3. Implement budget constraints
# 4. Test cost optimization
```

### Exercise 3: Create Strategy Metrics
Build a performance tracking system:
```python
# 1. Track tool usage frequency
# 2. Measure result quality by strategy
# 3. Calculate success rates
# 4. Generate strategy report
```

What questions do you have about this code, Finn?
Would you like me to explain any specific part in more detail?
Try this exercise: Create a research plan for "machine learning bias in healthcare" and trace through how the strategy class analyzes and plans the research approach.