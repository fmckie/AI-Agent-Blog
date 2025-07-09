# Phase 2 Quick Reference Guide

## 🚀 What's New in Phase 2?

### Enhanced Research Capabilities
- **Full Tavily API**: Search, Extract, Crawl, Map
- **Intelligent Strategy**: Automatic tool selection
- **Progress Tracking**: Real-time workflow monitoring
- **Adaptive Research**: Strategy adjusts based on results

## 📝 Quick Start

### Basic Usage
```python
from research_agent import create_research_agent, run_research_workflow
from config import get_config

async def research(keyword):
    config = get_config()
    agent = create_research_agent(config)
    findings = await run_research_workflow(agent, keyword, config)
    return findings
```

### With Progress Tracking
```python
def progress_callback(progress):
    print(f"{progress.get_completion_percentage():.0f}% - {progress.current_stage.value}")

findings = await run_research_workflow(
    agent, keyword, config, 
    progress_callback=progress_callback
)
```

## 🎯 Research Strategies

### Configuration Options
```env
RESEARCH_STRATEGY=standard    # basic | standard | comprehensive
ENABLE_ADAPTIVE_STRATEGY=true # Strategy adapts to results
```

### Strategy Comparison
| Strategy | Stages | Tools Used | Time | Best For |
|----------|--------|------------|------|----------|
| basic | 4 | Search only | ~30s | Quick overview |
| standard | 6 | Search + Extract | ~2min | Balanced research |
| comprehensive | 8 | All tools | ~5min | Deep investigation |

## 🛠️ Key Components

### ResearchWorkflow
Orchestrates the multi-stage research pipeline:
```python
workflow = ResearchWorkflow(agent, config, progress_callback)
findings = await workflow.execute_research_pipeline(keyword, strategy)
```

### ResearchStrategy
Intelligently selects tools based on topic:
```python
strategy = ResearchStrategy()
plan = strategy.create_research_plan(keyword)
# Returns: topic_type, research_depth, tool_recommendations
```

### Progress Tracking
```python
progress.current_stage          # Current workflow stage
progress.get_completion_percentage()  # 0-100%
progress.get_summary()          # Detailed progress info
```

## 📊 Workflow Stages

1. **INITIALIZATION** - Validate configuration
2. **DISCOVERY** - Initial search for sources
3. **ANALYSIS** - Analyze domains and quality
4. **EXTRACTION** - Get full content from top sources
5. **CRAWLING** - Deep exploration of domains
6. **SYNTHESIS** - Combine all findings
7. **VALIDATION** - Quality checks
8. **COMPLETION** - Finalize results

## 🎨 Topic Classification

The system classifies topics automatically:

| Topic Type | Indicators | Tool Focus | Example |
|------------|-----------|------------|---------|
| ACADEMIC | "research", "study", "journal" | Crawl .edu sites | "quantum physics research" |
| TECHNICAL | "programming", "API", "tutorial" | Extract docs | "Python async tutorial" |
| MEDICAL | "health", "treatment", "clinical" | High credibility | "diabetes management" |
| BUSINESS | "market", "revenue", "startup" | Recent data | "startup funding trends" |
| NEWS | "latest", "breaking", "update" | Time-sensitive | "AI news 2024" |
| EMERGING | "new", "breakthrough", "novel" | Multi-angle | "quantum computing breakthrough" |

## ⚙️ Configuration

### Essential Settings
```env
# Strategy Control
RESEARCH_STRATEGY=standard
ENABLE_ADAPTIVE_STRATEGY=true

# Performance
WORKFLOW_MAX_RETRIES=3
WORKFLOW_STAGE_TIMEOUT=120

# Quality
REQUIRE_MINIMUM_SOURCES=3
MIN_CREDIBILITY_THRESHOLD=0.7
```

### Advanced Settings
```env
# Tool Control
TOOL_PRIORITY_THRESHOLD=5
MAX_PARALLEL_TOOLS=2

# Caching
ENABLE_RESULT_CACHING=true
CACHE_TTL_MINUTES=60

# Progress
WORKFLOW_PROGRESS_REPORTING=true
WORKFLOW_FAIL_FAST=false
```

## 🔍 Debugging

### Enable Detailed Logging
```env
LOG_LEVEL=DEBUG
```

### Monitor Workflow Execution
```python
import logging
logging.basicConfig(level=logging.INFO)

# Watch stage transitions
logger = logging.getLogger('research_agent.workflow')
```

### Track Strategy Decisions
```python
# See why tools were selected
plan = strategy.create_research_plan(keyword)
for tool in plan.primary_tools:
    print(f"{tool.tool}: {tool.reasoning}")
```

## 📈 Performance Tips

### Optimize for Speed
```env
RESEARCH_STRATEGY=basic
WORKFLOW_FAIL_FAST=true
MAX_PARALLEL_TOOLS=3
```

### Optimize for Quality
```env
RESEARCH_STRATEGY=comprehensive
ENABLE_ADAPTIVE_STRATEGY=true
REQUIRE_MINIMUM_SOURCES=5
FACT_VERIFICATION_LEVEL=strict
```

### Balance Performance
```env
RESEARCH_STRATEGY=standard
ENABLE_RESULT_CACHING=true
WORKFLOW_CACHE_RESULTS=true
```

## 🚨 Common Issues

### Slow Performance
- Check `WORKFLOW_STAGE_TIMEOUT` - increase for complex topics
- Enable caching: `ENABLE_RESULT_CACHING=true`
- Use `basic` strategy for faster results

### Poor Quality Results
- Increase `MIN_CREDIBILITY_THRESHOLD`
- Use `comprehensive` strategy
- Enable `DIVERSITY_CHECK=true`

### API Rate Limits
- Reduce `MAX_PARALLEL_TOOLS`
- Increase `WORKFLOW_MAX_RETRIES`
- Enable caching to reduce API calls

## 📚 Examples

### Run Examples
```bash
# Quick start
python examples/quick_start_workflow.py

# Full demonstration
python examples/research_workflow_example.py

# Strategy deep dive
python examples/strategy_demonstration.py
```

### Custom Progress Handler
```python
class CustomProgress:
    def __call__(self, progress):
        # Your custom UI update
        update_ui(progress.get_summary())
        
tracker = CustomProgress()
findings = await run_research_workflow(
    agent, keyword, config, tracker
)
```

## 🔗 Related Documentation

- [Workflow Architecture](../research_agent/workflow_explanation.md)
- [Strategy System](../research_agent/strategy_explanation.md)
- [Configuration Guide](../config_workflow_enhancements_explanation.md)
- [Integration Details](../research_agent/integration_explanation.md)