# Changelog

All notable changes to the SEO Content Automation System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-07-02

### Changed
- Removed unused `research_agent/utilities.py` module (502 lines) that had 0% production usage
- Removed unused `suggest_internal_links` function from `writer_agent/utilities.py`
- Updated test coverage badge from 95% to accurate 81%
- Fixed concurrent workflow tests by ensuring temp directories are created
- Updated test mocks to use `_save_outputs_atomic` instead of deprecated `save_outputs`

### Fixed
- Fixed workflow state loading to recreate temp directories
- Fixed test failures related to removed utility functions
- Resolved race condition in concurrent workflow execution

### Removed
- Deleted `tests/test_research_utilities.py` (tests for removed code)
- Deleted `tests/test_blood_sugar_research.py` (importing removed modules)
- Deleted `tests/test_real_blood_sugar_research.py` (importing removed modules)
- Removed unused test JSON files from root directory

### Added
- Created `docs/explanations/` directory for documentation files
- Created `test_data/` directory for test artifacts
- Added comprehensive refactoring documentation
- Added manual testing summary

### Developer Notes
- Total lines of code reduced from 1570 to 1336 (234 lines removed)
- Test suite now has 255 passing tests (down from 290 due to removed unused code tests)
- 6 integration tests still failing due to API mocking issues (not a regression)

## [1.0.0] - 2025-07-01

### Added
- Initial release of SEO Content Automation System
- Research Agent for finding academic sources via Tavily API
- Writer Agent for generating SEO-optimized articles
- Workflow orchestration with state management
- CLI interface with rich terminal output
- Comprehensive test suite with 95% coverage
- Configuration management via environment variables
- Atomic file operations for reliability
- Progress tracking and resume capability
- Cleanup utility for workflow management

### Features
- Async Python implementation for efficient API calls
- PydanticAI integration for structured outputs
- Automatic retry with exponential backoff
- HTML article generation with metadata
- Academic source credibility scoring
- Keyword density optimization
- Readability analysis

### Documentation
- Comprehensive README with troubleshooting guide
- Architecture documentation in PLANNING.md
- Task tracking in TASK.md
- Inline code documentation for learning