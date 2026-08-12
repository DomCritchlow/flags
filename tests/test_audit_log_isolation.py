"""The disambiguation audit log must never touch committed production data.

`Disambiguator._log_decision` appends a line per Tier-2 decision. Before the
path became injectable, every test run appended to the git-tracked
`data/audit_log.jsonl`.
"""

import json

import pytest

from pipeline import config
from pipeline.disambiguator import Disambiguator
from pipeline.gazetteer import Gazetteer

# Deliberately NOT config.AUDIT_LOG_PATH — that attribute is redirected to a
# tmp file by the autouse fixture in conftest. This is the real committed file.
REAL_AUDIT_LOG = config.DATA_DIR / "audit_log.jsonl"

# Standard-scoring ambiguous term (not EXACT_SPELLING, not require_full_name),
# so it reaches _log_decision.
GEORGIA_TEXT = (
    "The situation in Georgia following protests in Tbilisi against the "
    "government was raised by the ambassador."
)


@pytest.fixture(scope="module")
def gazetteer():
    return Gazetteer()


def _fingerprint(path):
    if not path.exists():
        return None
    st = path.stat()
    return (st.st_size, st.st_mtime_ns)


class TestAuditLogInjection:
    def test_writes_to_injected_path(self, gazetteer, tmp_path):
        injected = tmp_path / "injected" / "audit.jsonl"
        disamb = Disambiguator(gazetteer, audit_log_path=injected)

        disamb.disambiguate("Georgia", "georgia", GEORGIA_TEXT, "rec-1", "crecord")

        assert injected.exists(), "injected audit log was not written"
        lines = [json.loads(ln) for ln in injected.read_text().splitlines() if ln]
        assert len(lines) == 1
        assert lines[0]["term"] == "Georgia"
        assert lines[0]["record_id"] == "rec-1"
        assert lines[0]["source_type"] == "crecord"

    def test_injected_path_wins_over_config(
        self, gazetteer, tmp_path, audit_log_path
    ):
        """An explicit path must not also write to the config default."""
        injected = tmp_path / "injected.jsonl"
        disamb = Disambiguator(gazetteer, audit_log_path=injected)

        disamb.disambiguate("Georgia", "georgia", GEORGIA_TEXT, "rec-2", "crecord")

        assert injected.exists()
        assert not audit_log_path.exists(), (
            "decision leaked into the config default path"
        )

    def test_default_resolves_to_patched_config(self, gazetteer, audit_log_path):
        """With no explicit path, the conftest redirect must capture the write."""
        disamb = Disambiguator(gazetteer)

        assert disamb.audit_log_path == audit_log_path

        disamb.disambiguate("Georgia", "georgia", GEORGIA_TEXT, "rec-3", "crecord")

        assert audit_log_path.exists()
        assert "rec-3" in audit_log_path.read_text()


class TestRealAuditLogUntouched:
    def test_conftest_redirects_away_from_committed_file(self):
        assert config.AUDIT_LOG_PATH != REAL_AUDIT_LOG, (
            "conftest autouse fixture is not redirecting the audit log"
        )

    def test_disambiguating_does_not_touch_committed_file(self, gazetteer):
        before = _fingerprint(REAL_AUDIT_LOG)

        Disambiguator(gazetteer).disambiguate(
            "Georgia", "georgia", GEORGIA_TEXT, "rec-4", "crecord"
        )

        assert _fingerprint(REAL_AUDIT_LOG) == before, (
            f"{REAL_AUDIT_LOG} was modified by the test suite"
        )
