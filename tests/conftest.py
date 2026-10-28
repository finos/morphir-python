"""Pytest configuration and shared fixtures for Morphir tests."""

import pytest


@pytest.fixture
def sample_version() -> str:
    """Provide the expected version string for tests."""
    return "0.1.0"
