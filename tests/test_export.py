"""Tests for the export module."""

import json
import pytest
from pathlib import Path
from pipeline.export import export_all, _build_monthly_top, _build_monthly_all, _build_metadata
from pipeline.gazetteer import Gazetteer


@pytest.fixture
def gazetteer():
    return Gazetteer()


@pytest.fixture
def sample_data():
    """Sample aggregated data for testing."""
    return {
        "2024-01": {
            "month": "2024-01",
            "total_records": 100,
            "countries": [
                {"iso3": "UKR", "count": 50},
                {"iso3": "CHN", "count": 30},
                {"iso3": "IRN", "count": 10},
            ],
            "sample_titles": {
                "UKR": ["bill-1", "bill-2"],
                "CHN": ["bill-3"],
            },
        },
        "2024-02": {
            "month": "2024-02",
            "total_records": 80,
            "countries": [
                {"iso3": "CHN", "count": 40},
                {"iso3": "UKR", "count": 25},
            ],
            "sample_titles": {},
        },
    }


class TestMonthlyTop:
    def test_structure(self, gazetteer, sample_data):
        result = _build_monthly_top(sample_data, gazetteer)
        assert len(result) == 2
        assert result[0]["month"] == "2024-01"
        assert result[0]["country_iso3"] == "UKR"
        assert result[0]["mention_count"] == 50
        assert result[0]["runner_up_iso3"] == "CHN"
        assert result[0]["runner_up_count"] == 30

    def test_iso2_included(self, gazetteer, sample_data):
        result = _build_monthly_top(sample_data, gazetteer)
        assert result[0]["country_iso2"] == "ua"  # Ukraine's iso2

    def test_sorted_by_month(self, gazetteer, sample_data):
        result = _build_monthly_top(sample_data, gazetteer)
        months = [r["month"] for r in result]
        assert months == sorted(months)


class TestMonthlyAll:
    def test_structure(self, gazetteer, sample_data):
        result = _build_monthly_all(sample_data, gazetteer)
        assert "2024-01" in result
        assert "2024-02" in result
        assert result["2024-01"]["total_records"] == 100
        assert len(result["2024-01"]["countries"]) == 3

    def test_country_has_name(self, gazetteer, sample_data):
        result = _build_monthly_all(sample_data, gazetteer)
        first = result["2024-01"]["countries"][0]
        assert first["name"] == "Ukraine"
        assert first["iso2"] == "ua"


class TestMetadata:
    def test_structure(self, sample_data):
        result = _build_metadata(sample_data)
        assert "last_run" in result
        assert result["date_range"] == ["2024-01", "2024-02"]
        assert result["month_count"] == 2
        assert result["total_records_processed"] == 180
        assert result["total_mentions_detected"] == 155  # 50+30+10+40+25


class TestExportIntegration:
    def test_writes_all_files(self, tmp_path, gazetteer):
        """export_all should write all three JSON files."""
        # Create a minimal mentions file
        mentions_path = tmp_path / "mentions.jsonl"
        mentions_path.write_text(
            json.dumps({"iso3": "UKR", "record_id": "b-1",
                        "month": "2024-03", "country_name": "Ukraine",
                        "term": "Ukraine", "source_type": "bill",
                        "tier": 1}) + "\n"
        )

        from pipeline.aggregator import Aggregator
        agg = Aggregator(mentions_path=mentions_path)

        output_dir = tmp_path / "aggregated"
        export_all(gazetteer=gazetteer, aggregator=agg, output_dir=output_dir)

        assert (output_dir / "monthly_top.json").exists()
        assert (output_dir / "monthly_all.json").exists()
        assert (output_dir / "metadata.json").exists()

        # Validate JSON is parseable
        top = json.loads((output_dir / "monthly_top.json").read_text())
        assert isinstance(top, list)
        assert len(top) == 1
        assert top[0]["country_iso3"] == "UKR"
