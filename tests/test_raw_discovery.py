"""Canonical raw-file discovery (pipeline.aggregator.discover_raw_files).

data/raw/ holds one directory per congress plus data/raw/executive_orders/,
which belongs to a separate Federal Register pipeline. Folding executive
orders into mentions.jsonl would contaminate the congressional dataset.

There must be exactly ONE definition of this rule; the scripts import it.
"""

from pathlib import Path

from pipeline import aggregator
from pipeline.aggregator import EXCLUDED_RAW_DIRS, discover_raw_files


def _make_raw_tree(root: Path) -> None:
    for congress in ("118", "119"):
        d = root / congress
        d.mkdir(parents=True)
        (d / "bill.jsonl").write_text("")
        (d / "amendment.jsonl").write_text("")
    eo = root / "executive_orders"
    eo.mkdir(parents=True)
    (eo / "eos.jsonl").write_text("")


class TestDiscoverRawFiles:
    def test_excludes_executive_orders(self, tmp_path):
        _make_raw_tree(tmp_path)

        found = discover_raw_files(tmp_path)

        assert found, "expected congressional files to be discovered"
        assert all(p.parent.name != "executive_orders" for p in found)
        assert not any(p.name == "eos.jsonl" for p in found)

    def test_includes_congress_directories(self, tmp_path):
        _make_raw_tree(tmp_path)

        found = discover_raw_files(tmp_path)

        assert {p.parent.name for p in found} == {"118", "119"}
        assert len(found) == 4

    def test_results_are_sorted(self, tmp_path):
        _make_raw_tree(tmp_path)

        assert discover_raw_files(tmp_path) == sorted(discover_raw_files(tmp_path))

    def test_ignores_loose_files_at_root(self, tmp_path):
        """Only <congress>/<endpoint>.jsonl is a raw record file."""
        _make_raw_tree(tmp_path)
        (tmp_path / "stray.jsonl").write_text("")

        assert not any(p.name == "stray.jsonl" for p in discover_raw_files(tmp_path))

    def test_empty_tree(self, tmp_path):
        assert discover_raw_files(tmp_path) == []

    def test_missing_dir_returns_empty(self, tmp_path):
        assert discover_raw_files(tmp_path / "does-not-exist") == []

    def test_defaults_to_configured_raw_dir(self, monkeypatch, tmp_path):
        _make_raw_tree(tmp_path)
        monkeypatch.setattr(aggregator.config, "RAW_DIR", tmp_path)

        assert len(discover_raw_files()) == 4

    def test_real_data_dir_has_no_executive_orders(self):
        """Guard against the live data directory regressing."""
        assert all(
            p.parent.name not in EXCLUDED_RAW_DIRS for p in discover_raw_files()
        )


class TestSingleDefinition:
    """The scripts must reuse the helper, not carry their own copies."""

    def test_reprocess_all_reuses_canonical_helper(self):
        from scripts import reprocess_all

        assert reprocess_all.discover_raw_files is discover_raw_files
        assert reprocess_all.EXCLUDED_RAW_DIRS is EXCLUDED_RAW_DIRS

    def test_audit_boundaries_reuses_canonical_helper(self):
        from scripts import audit_boundaries

        assert audit_boundaries.discover_raw_files is discover_raw_files

    def test_detector_reuses_canonical_helper(self):
        from pipeline import detector

        assert detector.discover_raw_files is discover_raw_files
