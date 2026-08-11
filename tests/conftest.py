"""Shared test fixtures."""

from pathlib import Path

import pytest

from pipeline import config

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Committed pipeline outputs that the test suite must never mutate.
PROTECTED_DATA_FILES = (
    config.AUDIT_LOG_PATH,
    config.SEEN_IDS_PATH,
    config.MENTIONS_PATH,
)


def _fingerprint(path: Path) -> tuple:
    """Cheap change-detector for a file: (exists, size, mtime_ns)."""
    try:
        st = path.stat()
    except FileNotFoundError:
        return (False, 0, 0)
    return (True, st.st_size, st.st_mtime_ns)


@pytest.fixture(autouse=True)
def audit_log_path(tmp_path, monkeypatch):
    """Redirect the disambiguation audit log to a per-test temp file.

    ``Disambiguator._log_decision`` appends every Tier-2 decision to
    ``config.AUDIT_LOG_PATH``, which in a real checkout is the committed
    ``data/audit_log.jsonl``. Without this autouse redirect, simply running
    the suite writes junk into production data.

    Yields the temp path so tests can assert on what was logged.
    """
    path = tmp_path / "audit_log.jsonl"
    monkeypatch.setattr(config, "AUDIT_LOG_PATH", path)
    return path


@pytest.fixture(scope="session", autouse=True)
def _protect_committed_data_files():
    """Tripwire: fail the session if the suite mutated committed data files."""
    before = {path: _fingerprint(path) for path in PROTECTED_DATA_FILES}
    yield
    changed = [
        str(path)
        for path, sig in before.items()
        if _fingerprint(path) != sig
    ]
    assert not changed, (
        "Test suite mutated committed data files: "
        + ", ".join(changed)
        + ". Tests must write only to tmp paths."
    )


@pytest.fixture
def fixtures_dir():
    """Directory of static test fixture files.

    ``tests/fixtures/`` is optional; when it is absent, hand tests a clear
    skip instead of a phantom path that fails later with a confusing
    FileNotFoundError deep inside the test body.
    """
    if not FIXTURES_DIR.is_dir():
        pytest.skip(f"No test fixtures directory at {FIXTURES_DIR}")
    return FIXTURES_DIR


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory mirroring the real structure."""
    for subdir in ["raw", "processed", "aggregated"]:
        (tmp_path / subdir).mkdir()
    return tmp_path
