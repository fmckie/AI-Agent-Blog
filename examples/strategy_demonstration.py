#!/usr/bin/env python3
"""
Demonstration of the ResearchStrategy system.

This script shows how the intelligent strategy system works:
- Topic classification
- Tool selection
- Adaptive planning
"""

import asyncio
from typing import List
from research_agent.strategy import (
    ResearchStrategy, 
    TopicType, 
    ResearchDepth,
    ToolType
)
from models import AcademicSource


def demonstrate_topic_classification():
    """
    Show how topics are classified into different types.
    """
    print("\n" + "="*60)
    print("TOPIC CLASSIFICATION DEMONSTRATION")
    print("="*60)
    
    strategy = ResearchStrategy()
    
    # Test various topics
    test_topics = [
        ("machine learning algorithms", "Technical programming topic"),
        ("quantum physics research papers", "Academic research topic"),
        ("COVID-19 vaccine effectiveness", "Medical/health topic"),
        ("startup funding strategies", "Business topic"),
        ("latest AI breakthroughs 2024", "News/current events"),
        ("novel gene therapy techniques", "Emerging/cutting-edge topic"),
        ("how to cook pasta", "General topic")
    ]
    
    print("\nClassifying research topics:")
    print("-" * 50)
    
    for topic, description in test_topics:
        topic_type = strategy.analyze_topic(topic)
        print(f"\n📝 Topic: '{topic}'")
        print(f"   Description: {description}")
        print(f"   → Classification: {topic_type.value.upper()}")


def demonstrate_research_depth():
    """
    Show how research depth is determined.
    """
    print("\n\n" + "="*60)
    print("RESEARCH DEPTH DETERMINATION")
    print("="*60)
    
    strategy = ResearchStrategy()
    
    # Test different scenarios
    scenarios = [
        ("AI basics", {}, "Default depth"),
        ("AI overview", {"quick": True}, "Quick overview requested"),
        ("Deep learning", {"comprehensive": True}, "Comprehensive research"),
        ("Neural networks", {"time_limit_minutes": 3}, "Very short time limit"),
        ("Quantum computing vs classical computing", {}, "Complex comparison topic"),
        ("GPT architecture", {"exhaustive": True}, "Exhaustive research requested")
    ]
    
    print("\nDetermining research depth:")
    print("-" * 50)
    
    for keyword, requirements, description in scenarios:
        depth = strategy.determine_research_depth(keyword, requirements)
        print(f"\n🔍 Keyword: '{keyword}'")
        print(f"   Scenario: {description}")
        print(f"   Requirements: {requirements}")
        print(f"   → Depth: {depth.value.upper()}")


def demonstrate_tool_selection():
    """
    Show how tools are selected based on topic and depth.
    """
    print("\n\n" + "="*60)
    print("TOOL SELECTION DEMONSTRATION")
    print("="*60)
    
    strategy = ResearchStrategy()
    
    # Test different combinations
    test_cases = [
        (TopicType.ACADEMIC, ResearchDepth.STANDARD, "Academic topic, standard depth"),
        (TopicType.TECHNICAL, ResearchDepth.DEEP, "Technical topic, deep research"),
        (TopicType.MEDICAL, ResearchDepth.EXHAUSTIVE, "Medical topic, exhaustive research"),
        (TopicType.EMERGING, ResearchDepth.STANDARD, "Emerging topic, standard depth"),
        (TopicType.GENERAL, ResearchDepth.SURFACE, "General topic, surface level")
    ]
    
    print("\nTool selection for different scenarios:")
    print("-" * 50)
    
    for topic_type, depth, description in test_cases:
        primary_tools, optional_tools = strategy.select_tools(topic_type, depth)
        
        print(f"\n🎯 Scenario: {description}")
        print(f"   Topic Type: {topic_type.value}")
        print(f"   Research Depth: {depth.value}")
        
        print(f"\n   Primary Tools (must use):")
        for tool in primary_tools:
            print(f"     • {tool.tool.value} (priority: {tool.priority})")
            print(f"       Reason: {tool.reasoning}")
        
        if optional_tools:
            print(f"\n   Optional Tools (use if beneficial):")
            for tool in optional_tools:
                print(f"     • {tool.tool.value} (priority: {tool.priority})")
                print(f"       Reason: {tool.reasoning}")


def demonstrate_research_planning():
    """
    Show complete research plan creation.
    """
    print("\n\n" + "="*60)
    print("RESEARCH PLAN CREATION")
    print("="*60)
    
    strategy = ResearchStrategy()
    
    # Create a research plan
    keyword = "artificial intelligence in medical diagnosis"
    requirements = {
        "comprehensive": True,
        "time_limit_minutes": 30,
        "context": "for a research paper on AI applications in healthcare"
    }
    
    print(f"\n📋 Creating research plan for: '{keyword}'")
    print(f"   Requirements: {requirements}")
    
    plan = strategy.create_research_plan(keyword, requirements)
    
    print(f"\n🎯 Research Plan:")
    print(f"   Topic Classification: {plan.topic_type.value}")
    print(f"   Research Depth: {plan.research_depth.value}")
    print(f"   Time Constraint: {plan.time_constraints}")
    
    print(f"\n🔍 Search Queries:")
    for i, query in enumerate(plan.search_queries, 1):
        print(f"   {i}. {query}")
    
    print(f"\n🌐 Target Domains:")
    for domain in plan.target_domains:
        print(f"   • {domain}")
    
    print(f"\n🛠️ Tool Strategy:")
    print(f"   Primary tools: {len(plan.primary_tools)}")
    for tool in plan.primary_tools[:3]:  # Show first 3
        print(f"     • {tool.tool.value} (priority {tool.priority})")
    
    if plan.special_instructions:
        print(f"\n📝 Special Instructions:")
        print(f"   {plan.special_instructions}")


def demonstrate_adaptive_strategy():
    """
    Show how strategy adapts based on results.
    """
    print("\n\n" + "="*60)
    print("ADAPTIVE STRATEGY DEMONSTRATION")
    print("="*60)
    
    strategy = ResearchStrategy()
    
    # Create initial plan
    initial_plan = strategy.create_research_plan("quantum computing algorithms")
    
    print(f"\n🎯 Initial Plan:")
    print(f"   Search queries: {len(initial_plan.search_queries)}")
    print(f"   Primary tools: {len(initial_plan.primary_tools)}")
    print(f"   Optional tools: {len(initial_plan.optional_tools)}")
    
    # Simulate different result scenarios
    scenarios = [
        {
            "name": "Poor Results",
            "results": {
                "sources_count": 2,
                "average_credibility": 0.4,
                "domains": ["blog.com", "medium.com"]
            }
        },
        {
            "name": "Excellent Results",
            "results": {
                "sources_count": 15,
                "average_credibility": 0.85,
                "domains": ["mit.edu", "stanford.edu", "arxiv.org", "ieee.org"]
            }
        },
        {
            "name": "Good Academic Domains",
            "results": {
                "sources_count": 8,
                "average_credibility": 0.75,
                "domains": ["cs.stanford.edu", "ai.mit.edu", "research.google.com"]
            }
        }
    ]
    
    print("\n🔄 Adaptations based on intermediate results:")
    print("-" * 50)
    
    for scenario in scenarios:
        print(f"\n📊 Scenario: {scenario['name']}")
        print(f"   Sources found: {scenario['results']['sources_count']}")
        print(f"   Avg credibility: {scenario['results']['average_credibility']:.2f}")
        print(f"   Domains: {', '.join(scenario['results']['domains'][:3])}")
        
        # Adapt strategy
        adapted_plan = strategy.adapt_strategy(initial_plan, scenario['results'])
        
        print(f"\n   → Adaptations:")
        print(f"     Search queries: {len(initial_plan.search_queries)} → {len(adapted_plan.search_queries)}")
        print(f"     Primary tools: {len(initial_plan.primary_tools)} → {len(adapted_plan.primary_tools)}")
        
        # Show specific changes
        if len(adapted_plan.search_queries) > len(initial_plan.search_queries):
            print(f"     ✅ Broadened search with additional queries")
        if len(adapted_plan.primary_tools) > len(initial_plan.primary_tools):
            print(f"     ✅ Upgraded optional tools to primary")
        if len(adapted_plan.primary_tools) < len(initial_plan.primary_tools):
            print(f"     ✅ Focused on high-priority tools only")


def demonstrate_edge_cases():
    """
    Show how the strategy handles edge cases.
    """
    print("\n\n" + "="*60)
    print("EDGE CASE HANDLING")
    print("="*60)
    
    strategy = ResearchStrategy()
    
    # Test edge cases
    edge_cases = [
        ("", "Empty keyword"),
        ("a " * 100, "Very long keyword"),
        ("C++ vs C# @2024 #performance", "Special characters"),
        ("🤖 AI 🧠 research", "Emojis in keyword"),
        ("the", "Single common word")
    ]
    
    print("\nHandling edge cases:")
    print("-" * 50)
    
    for keyword, description in edge_cases:
        try:
            plan = strategy.create_research_plan(keyword)
            print(f"\n✅ {description}")
            print(f"   Keyword: '{keyword[:50]}...' (truncated)" if len(keyword) > 50 else f"   Keyword: '{keyword}'")
            print(f"   → Successfully created plan")
            print(f"   → Topic: {plan.topic_type.value}")
            print(f"   → Tools: {len(plan.primary_tools)} primary")
        except Exception as e:
            print(f"\n❌ {description}")
            print(f"   Keyword: '{keyword}'")
            print(f"   → Error: {str(e)}")


def main():
    """
    Run all demonstrations.
    """
    print("\n" + "="*60)
    print("RESEARCH STRATEGY SYSTEM DEMONSTRATION")
    print("Understanding the Intelligence Behind Research")
    print("="*60)
    
    # Run demonstrations
    demonstrate_topic_classification()
    demonstrate_research_depth()
    demonstrate_tool_selection()
    demonstrate_research_planning()
    demonstrate_adaptive_strategy()
    demonstrate_edge_cases()
    
    print("\n\n✨ Strategy demonstration complete!")
    print("\nKey Takeaways:")
    print("• Topics are intelligently classified for targeted research")
    print("• Research depth adapts to requirements and constraints")
    print("• Tools are selected based on topic type and depth")
    print("• Strategy adapts based on intermediate results")
    print("• Edge cases are handled gracefully")


if __name__ == "__main__":
    main()