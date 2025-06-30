"""
Basic tests to verify the test suite is set up correctly.

This file contains simple tests that should always pass,
helping to verify the testing infrastructure is working.
"""

import pytest


class TestBasicSetup:
    """Basic tests to verify pytest is working."""

    def test_pytest_runs(self):
        """Verify pytest can run tests."""
        assert True

    def test_imports_work(self):
        """Verify we can import project modules."""
        try:
            from config import Config
            from models import AcademicSource, ArticleOutput, ResearchFindings
            from workflow import WorkflowOrchestrator

            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    @pytest.mark.asyncio
    async def test_async_support(self):
        """Verify async tests work."""
        import asyncio

        await asyncio.sleep(0.01)
        assert True

    def test_fixtures_work(self):
        """Verify pytest fixtures work."""

        @pytest.fixture
        def sample_data():
            return {"test": "data"}

        def inner_test(sample_data):
            assert sample_data["test"] == "data"

        # Manually call to test
        inner_test({"test": "data"})
        assert True
