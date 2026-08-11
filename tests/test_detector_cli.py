"""Detection CLI surface: incremental / reprocess / dry-run.

Everything here runs against a temporary raw tree and a temporary
mentions.jsonl — the real data/ directory is never read or written.
"""

import json

import pytest
from click.testing import CliRunner

from pipeline import config, detector as detector_mod
from pipeline.detector import (
    CountryDetector,
    clear_mentions,
    detected_record_ids,
    main,
    run_detection,
)
from pipeline.gazetteer import Gazetteer

# Records whose titles contain unambiguous Tier-1 countries.
RECORD_A = {
    "id": "bill-118-hr-1",
    "title": "A bill to strengthen trade relations with France and Japan.",
    "date": "2024-02-10",
    "source": "bill",
}
RECORD_B = {
    "id": "bill-118-hr-2",
    "title": "A resolution recognizing the Federative Republic of Brazil.",
    "date": "2024-02-11",
    "source": "bill",
}
RECORD_EO = {
    "id": "eo-14100",
    "title": "An executive order concerning procurement in Kenya.",
    "date": "2024-02-12",
    "source": "executive_order",
}


@pytest.fixture(scope="module")
def gazetteer():
    return Gazetteer()


@pytest.fixture(scope="module")
def detector(gazetteer):
    return CountryDetector(gazetteer, enable_llm=False)


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))


@pytest.fixture
def raw_dir(tmp_path):
    """A raw tree with two congressional records and one executive order."""
    root = tmp_path / "raw"
    _write_jsonl(root / "118" / "bill.jsonl", [RECORD_A, RECORD_B])
    _write_jsonl(root / "executive_orders" / "eos.jsonl", [RECORD_EO])
    return root


@pytest.fixture
def mentions_path(tmp_path):
    return tmp_path / "processed" / "mentions.jsonl"


def _record_ids_in(path):
    return [json.loads(ln)["record_id"] for ln in path.read_text().splitlines() if ln]


class TestDetectedRecordIds:
    def test_missing_file_is_empty(self, mentions_path):
        assert detected_record_ids(mentions_path) == set()

    def test_reads_ids(self, mentions_path):
        _write_jsonl(
            mentions_path,
            [{"record_id": "a", "iso3": "FRA"}, {"record_id": "b", "iso3": "JPN"}],
        )
        assert detected_record_ids(mentions_path) == {"a", "b"}

    def test_tolerates_blank_and_corrupt_lines(self, mentions_path):
        mentions_path.parent.mkdir(parents=True)
        mentions_path.write_text(
            '{"record_id": "a"}\n\n{bad json}\n{"record_id": ""}\n{"record_id": "b"}\n'
        )
        assert detected_record_ids(mentions_path) == {"a", "b"}


class TestClearMentions:
    def test_truncates_existing(self, mentions_path):
        _write_jsonl(mentions_path, [{"record_id": "stale"}])

        clear_mentions(mentions_path)

        assert mentions_path.exists()
        assert mentions_path.read_text() == ""

    def test_creates_parent_dirs(self, mentions_path):
        assert not mentions_path.parent.exists()

        clear_mentions(mentions_path)

        assert mentions_path.exists()


class TestRunDetection:
    def test_appends_mentions_for_all_records(
        self, detector, raw_dir, mentions_path
    ):
        stats = run_detection(
            detector, raw_dir=raw_dir, mentions_path=mentions_path
        )

        assert stats.records_scanned == 2
        assert stats.mentions == 3  # France + Japan + Brazil
        assert set(_record_ids_in(mentions_path)) == {RECORD_A["id"], RECORD_B["id"]}

    def test_excludes_executive_orders(self, detector, raw_dir, mentions_path):
        run_detection(detector, raw_dir=raw_dir, mentions_path=mentions_path)

        assert RECORD_EO["id"] not in _record_ids_in(mentions_path)

    def test_incremental_skips_already_detected(
        self, detector, raw_dir, mentions_path
    ):
        """Records already in mentions.jsonl are skipped; the rest append."""
        _write_jsonl(mentions_path, [{"record_id": RECORD_A["id"], "iso3": "FRA"}])
        skip_ids = detected_record_ids(mentions_path)

        stats = run_detection(
            detector,
            skip_ids=skip_ids,
            raw_dir=raw_dir,
            mentions_path=mentions_path,
        )

        assert stats.records_scanned == 1
        assert stats.records_skipped == 1
        ids = _record_ids_in(mentions_path)
        assert ids.count(RECORD_A["id"]) == 1, "existing record re-detected"
        assert RECORD_B["id"] in ids
        assert stats.mentions == 1  # Brazil only

    def test_reprocess_truncates_then_redetects(
        self, detector, raw_dir, mentions_path
    ):
        _write_jsonl(mentions_path, [{"record_id": "gone-from-corpus", "iso3": "XXX"}])

        clear_mentions(mentions_path)
        run_detection(detector, raw_dir=raw_dir, mentions_path=mentions_path)

        ids = _record_ids_in(mentions_path)
        assert "gone-from-corpus" not in ids
        assert set(ids) == {RECORD_A["id"], RECORD_B["id"]}

    def test_dry_run_writes_nothing(self, detector, raw_dir, mentions_path):
        stats = run_detection(
            detector, raw_dir=raw_dir, mentions_path=mentions_path, dry_run=True
        )

        assert stats.mentions == 3, "dry run should still report what it found"
        assert not mentions_path.exists()

    def test_dry_run_leaves_existing_file_untouched(
        self, detector, raw_dir, mentions_path
    ):
        _write_jsonl(mentions_path, [{"record_id": "keep-me", "iso3": "FRA"}])
        before = mentions_path.read_text()

        run_detection(
            detector, raw_dir=raw_dir, mentions_path=mentions_path, dry_run=True
        )

        assert mentions_path.read_text() == before

    def test_skips_records_without_text(self, detector, tmp_path, mentions_path):
        root = tmp_path / "raw"
        _write_jsonl(
            root / "118" / "bill.jsonl",
            [{"id": "empty-1", "title": "", "summary": "", "date": "2024-02-01"}],
        )

        stats = run_detection(detector, raw_dir=root, mentions_path=mentions_path)

        assert stats.records_scanned == 0
        assert stats.records_skipped == 1


class TestDetectorCLI:
    """End-to-end via click, with config paths redirected to tmp."""

    @pytest.fixture
    def cli_env(self, monkeypatch, raw_dir, mentions_path):
        monkeypatch.setattr(config, "RAW_DIR", raw_dir)
        monkeypatch.setattr(config, "MENTIONS_PATH", mentions_path)
        # detector.main() calls run_detection() with no path overrides, so it
        # resolves config at call time — which the patches above now own.
        return mentions_path

    def test_incremental_and_reprocess_are_mutually_exclusive(self, cli_env):
        result = CliRunner().invoke(main, ["--incremental", "--reprocess"])

        assert result.exit_code == 2, result.output
        assert "mutually exclusive" in result.output
        assert not cli_env.exists(), "usage error must not write mentions"

    def test_no_raw_records_is_an_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "RAW_DIR", tmp_path / "empty")
        monkeypatch.setattr(config, "MENTIONS_PATH", tmp_path / "mentions.jsonl")

        result = CliRunner().invoke(main, ["--incremental"])

        assert result.exit_code == 1
        assert "No congressional raw records found" in result.output

    def test_dry_run_writes_nothing(self, cli_env):
        result = CliRunner().invoke(main, ["--dry-run"])

        assert result.exit_code == 0, result.output
        assert "(dry run)" in result.output
        assert not cli_env.exists()

    def test_reprocess_dry_run_does_not_clear(self, cli_env):
        _write_jsonl(cli_env, [{"record_id": "stale", "iso3": "XXX"}])

        result = CliRunner().invoke(main, ["--reprocess", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert _record_ids_in(cli_env) == ["stale"]

    def test_reprocess_clears_and_rebuilds(self, cli_env):
        _write_jsonl(cli_env, [{"record_id": "stale", "iso3": "XXX"}])

        result = CliRunner().invoke(main, ["--reprocess"])

        assert result.exit_code == 0, result.output
        ids = _record_ids_in(cli_env)
        assert "stale" not in ids
        assert set(ids) == {RECORD_A["id"], RECORD_B["id"]}

    def test_incremental_appends_only_new_records(self, cli_env):
        _write_jsonl(cli_env, [{"record_id": RECORD_A["id"], "iso3": "FRA"}])

        result = CliRunner().invoke(main, ["--incremental"])

        assert result.exit_code == 0, result.output
        ids = _record_ids_in(cli_env)
        assert ids.count(RECORD_A["id"]) == 1
        assert RECORD_B["id"] in ids
        assert "Records skipped:  1" in result.output

    def test_default_mode_is_incremental(self, cli_env):
        result = CliRunner().invoke(main, [])

        assert result.exit_code == 0, result.output
        assert "Detection (incremental):" in result.output

    def test_cli_never_touches_real_data(self, cli_env):
        """The redirect is what keeps the committed corpus safe."""
        CliRunner().invoke(main, ["--reprocess"])

        assert config.MENTIONS_PATH == cli_env
        assert cli_env != detector_mod.config.PROJECT_ROOT / "data/processed/mentions.jsonl"
