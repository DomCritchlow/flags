"""Shared test fixtures."""

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory mirroring the real structure."""
    for subdir in ["raw", "processed", "aggregated"]:
        (tmp_path / subdir).mkdir()
    return tmp_path
