# MD Pilot Content Strategy Implementation Tasks

**Start Date**: 2025-01-02  
**Objective**: Implement a flexible content type system supporting PRIMARY (2,500-4,000 words) and SUPPORTING (1,200-2,000 words) content based on MD Pilot strategy.

## Overview
- [ ] Review MD Pilot Content Strategy document
- [ ] Understand current codebase architecture
- [ ] Plan implementation approach
- [ ] Create this TASK.md tracking file

## Phase 1: Data Models & Content Types Foundation

### 1.1 Create ContentType Enum
- [ ] Add ContentType enum to models.py
  - [ ] PRIMARY = "primary" 
  - [ ] SUPPORTING = "supporting"
- [ ] Add content type metadata
  - [ ] Word count ranges (PRIMARY: 2500-4000, SUPPORTING: 1200-2000)
  - [ ] Required sections count (PRIMARY: 6, SUPPORTING: 3-4)
  - [ ] Citation requirements (PRIMARY: 10+, SUPPORTING: 3-5)

### 1.2 Extend ArticleOutput Model
- [ ] Add content_type field with ContentType enum
- [ ] Create dynamic validators
  - [ ] Dynamic word_count validator based on content_type
  - [ ] Dynamic main_sections length validator
  - [ ] Dynamic citation count validator
- [ ] Update existing validators to be content-type aware
- [ ] Add backward compatibility (default to PRIMARY)

### 1.3 Create Content Structure Models
- [ ] Create PrimaryContentStructure model
  - [ ] Introduction (200-300 words)
  - [ ] What is [Topic] (400-500 words)
  - [ ] Science & Research (600-800 words)
  - [ ] Practical Application (800-1000 words)
  - [ ] Common Questions (400-500 words)
  - [ ] Key Takeaways (200-300 words)
- [ ] Create SupportingContentStructure model
  - [ ] Introduction (100-150 words)
  - [ ] Main Content (800-1200 words)
  - [ ] Practical Tips (200-300 words)
  - [ ] Conclusion (100-150 words)
- [ ] Add validation for section word counts
- [ ] Create section template helpers

## Phase 2: Content Templates System

### 2.1 Create content_templates.py Module
- [ ] Create base ContentTemplate class
- [ ] Implement PrimaryContentTemplate
  - [ ] Define section structure
  - [ ] Add section prompts/guidelines
  - [ ] Include SEO requirements
  - [ ] Add YMYL considerations
- [ ] Implement SupportingContentTemplate
  - [ ] Define focused structure
  - [ ] Add long-tail keyword focus
  - [ ] Include quick-answer format
- [ ] Create template selection logic

### 2.2 Template Validation System
- [ ] Create validate_content_structure function
- [ ] Check required sections presence
- [ ] Validate section word counts
- [ ] Ensure total word count compliance
- [ ] Verify citation requirements met
- [ ] Add helpful error messages

### 2.3 Template Testing
- [ ] Unit tests for each template
- [ ] Validation edge cases
- [ ] Template selection tests

## Phase 3: Enhanced Writer Agent

### 3.1 Update writer_agent/agent.py
- [ ] Add content_type parameter to create_writer_agent
- [ ] Update agent context to include content_type
- [ ] Modify run_writer_agent to accept content_type
- [ ] Update prompt generation based on content_type
- [ ] Ensure backward compatibility

### 3.2 Dynamic Prompt System
- [ ] Update writer_agent/prompts.py
  - [ ] Create WRITER_AGENT_PRIMARY_PROMPT
  - [ ] Create WRITER_AGENT_SUPPORTING_PROMPT
  - [ ] Add prompt selection logic
- [ ] PRIMARY prompt requirements
  - [ ] Comprehensive coverage emphasis
  - [ ] Multiple perspective inclusion
  - [ ] Deep research integration
  - [ ] Authority building focus
- [ ] SUPPORTING prompt requirements
  - [ ] Specific answer focus
  - [ ] Quick value delivery
  - [ ] Targeted information
  - [ ] Scannable format

### 3.3 Enhanced Writer Tools
- [ ] Update calculate_keyword_density
  - [ ] Different targets for content types
  - [ ] PRIMARY: 1-2% density
  - [ ] SUPPORTING: 2-3% density
- [ ] Create check_ymyl_requirements tool
  - [ ] Citation count validation
  - [ ] Source authority checking
  - [ ] Medical disclaimer verification
- [ ] Add check_content_structure tool
  - [ ] Verify template compliance
  - [ ] Check section completeness

## Phase 4: Research Agent Enhancements

### 4.1 Content-Type Aware Research
- [ ] Update research_agent/agent.py
  - [ ] Accept content_type parameter
  - [ ] Adjust search depth based on type
  - [ ] PRIMARY: 10-15 sources
  - [ ] SUPPORTING: 5-7 sources
- [ ] Modify search strategies
  - [ ] PRIMARY: Comprehensive + academic focus
  - [ ] SUPPORTING: Targeted + practical focus

### 4.2 Enhanced Source Quality
- [ ] Update credibility scoring in tools.py
  - [ ] Boost .edu, .gov, .org domains
  - [ ] Add recency scoring (prefer 2-3 years)
  - [ ] Prioritize peer-reviewed sources
- [ ] Add source diversity checking
  - [ ] Ensure multiple perspectives
  - [ ] Balance academic and practical
- [ ] Create YMYL source validator
  - [ ] Check medical journal sources
  - [ ] Verify author credentials
  - [ ] Validate publication standards

## Phase 5: Workflow Integration

### 5.1 Update WorkflowOrchestrator
- [ ] Add content_type parameter to __init__
- [ ] Pass content_type to research agent
- [ ] Pass content_type to writer agent
- [ ] Update progress messages for content type
- [ ] Add content type to workflow metadata

### 5.2 Output Organization
- [ ] Create content type folders
  - [ ] drafts/primary/
  - [ ] drafts/supporting/
- [ ] Update save_outputs method
  - [ ] Include content_type in metadata
  - [ ] Organize by content type
- [ ] Update filename conventions
  - [ ] {content_type}_{keyword}_{timestamp}
- [ ] Add content type to review interface

### 5.3 State Management
- [ ] Add content_type to workflow state
- [ ] Include in state persistence
- [ ] Handle in rollback scenarios

## Phase 6: CLI Updates

### 6.1 Add Content Type Flag
- [ ] Update main.py generate command
  - [ ] Add --content-type flag
  - [ ] Add -c short option
  - [ ] Set default to "primary"
  - [ ] Add choices validation
- [ ] Update command help text
- [ ] Add usage examples

### 6.2 Enhanced CLI Features
- [ ] Add content strategy info command
  - [ ] Show content type details
  - [ ] Display requirements
  - [ ] List best practices
- [ ] Update verbose output
  - [ ] Show content type selection
  - [ ] Display template being used
  - [ ] Show validation results

### 6.3 Documentation Updates
- [ ] Update CLI docstrings
- [ ] Add content type examples
- [ ] Explain use cases for each type
- [ ] Reference MD Pilot strategy

## Phase 7: Quality Assurance Implementation

### 7.1 YMYL Compliance Checker
- [ ] Create ymyl_checker.py module
- [ ] Implement citation validator
  - [ ] Count citations per article
  - [ ] Verify minimum requirements
  - [ ] Check citation quality
- [ ] Add source authority checker
  - [ ] Validate domain authority
  - [ ] Check publication credentials
  - [ ] Verify peer review status
- [ ] Create medical disclaimer validator
  - [ ] Ensure disclaimer presence
  - [ ] Check disclaimer placement
  - [ ] Validate disclaimer content

### 7.2 Content Structure Validator
- [ ] Create structure_validator.py
- [ ] Implement section validator
  - [ ] Check all sections present
  - [ ] Validate section order
  - [ ] Verify section headings
- [ ] Add word count validator
  - [ ] Per-section validation
  - [ ] Total count validation
  - [ ] Distribution checking
- [ ] Create readability checker
  - [ ] Flesch reading ease
  - [ ] Average sentence length
  - [ ] Paragraph structure

### 7.3 Integration with Workflow
- [ ] Add validation steps to workflow
- [ ] Create validation reports
- [ ] Handle validation failures
- [ ] Add override options for edge cases

## Phase 8: Comprehensive Testing Suite

### 8.1 Unit Tests
- [ ] Test ContentType enum and models
  - [ ] test_content_type_enum.py
  - [ ] test_article_output_validation.py
  - [ ] test_content_structures.py
- [ ] Test content templates
  - [ ] test_content_templates.py
  - [ ] test_template_validation.py
- [ ] Test enhanced agents
  - [ ] test_writer_agent_content_types.py
  - [ ] test_research_agent_content_types.py
- [ ] Test quality checkers
  - [ ] test_ymyl_checker.py
  - [ ] test_structure_validator.py

### 8.2 Integration Tests
- [ ] Full workflow tests
  - [ ] test_primary_content_workflow.py
  - [ ] test_supporting_content_workflow.py
- [ ] Error handling tests
  - [ ] test_validation_failures.py
  - [ ] test_api_failures.py
- [ ] CLI integration tests
  - [ ] test_cli_content_types.py
  - [ ] test_cli_validation.py

### 8.3 Performance Tests
- [ ] API usage benchmarks
  - [ ] Measure tokens per content type
  - [ ] Track API costs
  - [ ] Monitor rate limits
- [ ] Generation time benchmarks
  - [ ] Time per content type
  - [ ] Optimization opportunities
- [ ] Memory usage profiling

## Phase 9: Documentation & Deployment

### 9.1 Update Documentation
- [ ] Update README.md
  - [ ] Add content types section
  - [ ] Include examples
  - [ ] Update feature list
- [ ] Create CONTENT_TYPES.md
  - [ ] Detailed explanation
  - [ ] When to use each
  - [ ] Best practices
- [ ] Update API documentation
  - [ ] Document new parameters
  - [ ] Add examples
  - [ ] Include validation rules

### 9.2 Migration Guide
- [ ] Create MIGRATION.md
  - [ ] Backward compatibility notes
  - [ ] Update instructions
  - [ ] Common issues
- [ ] Add migration scripts if needed
- [ ] Test with existing content

### 9.3 Final Validation
- [ ] Run full test suite
- [ ] Manual testing of all features
- [ ] Performance validation
- [ ] Update version number
- [ ] Create release notes

## Completion Checklist
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Documentation updated
- [ ] Code review completed
- [ ] Performance benchmarks acceptable
- [ ] YMYL compliance verified
- [ ] Content quality validated
- [ ] CLI help text updated
- [ ] Examples provided
- [ ] Ready for deployment

## Notes Section
<!-- Add any implementation notes, discoveries, or decisions made during development -->

### Implementation Notes:
- 

### Technical Decisions:
- 

### Known Issues:
- 

### Future Enhancements:
- 

---
**Last Updated**: 2025-01-02
**Status**: In Progress
**Next Task**: Create ContentType enum in models.py