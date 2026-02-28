"""Tests for the dedup manager."""

import json
import pytest
from pipeline.dedup import DedupManager


class TestDedupManager:
    def test_empty_on_first_load(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        dm = DedupManager(path=path)
        assert dm.count == 0

    def test_is_seen_false_for_new(self, tmp_path):
        dm = DedupManager(path=tmp_path / "seen_ids.json")
        assert not dm.is_seen("record-1")

    def test_mark_seen_and_check(self, tmp_path):
        dm = DedupManager(path=tmp_path / "seen_ids.json")
        dm.mark_seen(["record-1", "record-2"])
        assert dm.is_seen("record-1")
        assert dm.is_seen("record-2")
        assert not dm.is_seen("record-3")
        assert dm.count == 2

    def test_persistence(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        dm1 = DedupManager(path=path)
        dm1.mark_seen(["record-1", "record-2"])

        # New instance loads from same file
        dm2 = DedupManager(path=path)
        assert dm2.is_seen("record-1")
        assert dm2.is_seen("record-2")
        assert dm2.count == 2

    def test_idempotent_mark(self, tmp_path):
        dm = DedupManager(path=tmp_path / "seen_ids.json")
        dm.mark_seen(["record-1"])
        dm.mark_seen(["record-1"])  # same ID again
        assert dm.count == 1

    def test_sorted_output(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        dm = DedupManager(path=path)
        dm.mark_seen(["c-record", "a-record", "b-record"])
        data = json.loads(path.read_text())
        assert data == ["a-record", "b-record", "c-record"]

    def test_empty_mark_no_op(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        dm = DedupManager(path=path)
        dm.mark_seen([])
        assert not path.exists()  # No file created for empty mark

    def test_status(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        dm = DedupManager(path=path)
        dm.mark_seen(["x"])
        status = dm.status()
        assert status["total_ids"] == 1
        assert status["exists"] is True
