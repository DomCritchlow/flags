"""Regression tests: a corrupt dedup index must abort, never silently reset.

Returning an empty set for an unreadable seen_ids.json defeats deduplication,
which re-ingests the whole archive and doubles every count on the live site.
"""

import json
import os
import stat

import pytest

from pipeline.dedup import DedupIndexError, DedupManager


class TestCorruptIndexAborts:
    def test_missing_file_is_empty_first_run(self, tmp_path):
        """A file that was never written is the legitimate first-run case."""
        path = tmp_path / "seen_ids.json"
        assert not path.exists()

        dm = DedupManager(path=path)

        assert dm.count == 0
        assert dm.is_seen("bill-118-hr-1") is False

    def test_truncated_json_raises(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        path.write_text('["bill-118-hr-1", "bill-118-hr-2"')  # truncated write

        with pytest.raises(DedupIndexError) as exc:
            DedupManager(path=path)

        assert str(path) in str(exc.value)

    def test_garbage_content_raises(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        path.write_text("not json at all")

        with pytest.raises(DedupIndexError):
            DedupManager(path=path)

    def test_empty_file_raises(self, tmp_path):
        """A zero-byte file is a failed write, not an empty index."""
        path = tmp_path / "seen_ids.json"
        path.write_text("")

        with pytest.raises(DedupIndexError):
            DedupManager(path=path)

    def test_wrong_json_structure_raises(self, tmp_path):
        """Valid JSON of the wrong shape is still an untrustworthy index."""
        path = tmp_path / "seen_ids.json"
        path.write_text(json.dumps({"ids": ["bill-118-hr-1"]}))

        with pytest.raises(DedupIndexError):
            DedupManager(path=path)

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permissions")
    def test_unreadable_file_raises(self, tmp_path):
        path = tmp_path / "seen_ids.json"
        path.write_text(json.dumps(["bill-118-hr-1"]))
        path.chmod(stat.S_IWUSR)  # write-only: exists but cannot be read

        try:
            with pytest.raises(DedupIndexError):
                DedupManager(path=path)
        finally:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_valid_index_still_loads(self, tmp_path):
        """The happy path is unaffected by the new strictness."""
        path = tmp_path / "seen_ids.json"
        path.write_text(json.dumps(["bill-118-hr-1", "bill-118-hr-2"]))

        dm = DedupManager(path=path)

        assert dm.count == 2
        assert dm.is_seen("bill-118-hr-1")

    def test_valid_empty_array_loads(self, tmp_path):
        """An explicitly empty index is legitimate and must not raise."""
        path = tmp_path / "seen_ids.json"
        path.write_text("[]")

        assert DedupManager(path=path).count == 0
