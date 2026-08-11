"""Aggregator CLI surface: --touched-months and its metadata dependency.

A scheduled run that ingested nothing touches no months. That is a normal
outcome, not a failure, so the CLI must exit 0 — a non-zero exit would fail
the weekly workflow every quiet week.
"""

import json

import pytest
from click.testing import CliRunner

from pipeline import config
from pipeline.aggregator import load_touched_months, main


@pytest.fixture
def metadata_path(tmp_path):
    return tmp_path / "aggregated" / "metadata.json"


def _write_metadata(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


class TestLoadTouchedMonths:
    def test_missing_file_returns_empty(self, metadata_path):
        assert not metadata_path.exists()
        assert load_touched_months(metadata_path) == []

    def test_empty_file_returns_empty(self, metadata_path):
        metadata_path.parent.mkdir(parents=True)
        metadata_path.write_text("")

        assert load_touched_months(metadata_path) == []

    def test_corrupt_json_returns_empty(self, metadata_path):
        metadata_path.parent.mkdir(parents=True)
        metadata_path.write_text('{"last_run_months_touched": ["2024-02"')

        assert load_touched_months(metadata_path) == []

    def test_corrupt_json_is_logged(self, metadata_path, caplog):
        metadata_path.parent.mkdir(parents=True)
        metadata_path.write_text("not json")

        with caplog.at_level("ERROR"):
            load_touched_months(metadata_path)

        assert str(metadata_path) in caplog.text

    def test_missing_key_returns_empty(self, metadata_path):
        _write_metadata(metadata_path, {"total_mentions": 5})

        assert load_touched_months(metadata_path) == []

    def test_null_value_returns_empty(self, metadata_path):
        _write_metadata(metadata_path, {"last_run_months_touched": None})

        assert load_touched_months(metadata_path) == []

    def test_reads_months(self, metadata_path):
        _write_metadata(
            metadata_path, {"last_run_months_touched": ["2024-01", "2024-02"]}
        )

        assert load_touched_months(metadata_path) == ["2024-01", "2024-02"]

    def test_filters_non_string_and_empty_entries(self, metadata_path):
        _write_metadata(
            metadata_path,
            {"last_run_months_touched": ["2024-01", "", None, 7, "2024-02"]},
        )

        assert load_touched_months(metadata_path) == ["2024-01", "2024-02"]

    def test_defaults_to_configured_aggregated_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "AGGREGATED_DIR", tmp_path)
        (tmp_path / "metadata.json").write_text(
            json.dumps({"last_run_months_touched": ["2025-03"]})
        )

        assert load_touched_months() == ["2025-03"]


class TestTouchedMonthsCLI:
    @pytest.fixture
    def cli_env(self, monkeypatch, tmp_path):
        """Point the aggregator at an empty tmp workspace."""
        monkeypatch.setattr(config, "AGGREGATED_DIR", tmp_path / "aggregated")
        monkeypatch.setattr(
            config, "MENTIONS_PATH", tmp_path / "processed" / "mentions.jsonl"
        )
        monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
        return tmp_path

    def test_missing_metadata_exits_zero(self, cli_env):
        result = CliRunner().invoke(main, ["--touched-months"])

        assert result.exit_code == 0, result.output
        assert "No months touched" in result.output

    def test_corrupt_metadata_exits_zero(self, cli_env):
        meta = cli_env / "aggregated" / "metadata.json"
        meta.parent.mkdir(parents=True)
        meta.write_text("{ truncated")

        result = CliRunner().invoke(main, ["--touched-months"])

        assert result.exit_code == 0, result.output
        assert "No months touched" in result.output

    def test_empty_month_list_exits_zero(self, cli_env):
        meta = cli_env / "aggregated" / "metadata.json"
        meta.parent.mkdir(parents=True)
        meta.write_text(json.dumps({"last_run_months_touched": []}))

        result = CliRunner().invoke(main, ["--touched-months"])

        assert result.exit_code == 0, result.output
        assert "No months touched" in result.output
