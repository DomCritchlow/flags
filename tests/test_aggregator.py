"""Tests for the aggregation module."""

import json
import pytest
from pathlib import Path
from pipeline.aggregator import Aggregator, load_mentions, append_mentions


def _make_mention(iso3, record_id, month):
    """Create a minimal mention dict."""
    return {
        "iso3": iso3,
        "country_name": iso3,
        "term": iso3,
        "record_id": record_id,
        "source_type": "bill",
        "tier": 1,
        "month": month,
    }


class TestAggregation:
    def test_basic_count(self, tmp_path):
        path = tmp_path / "mentions.jsonl"
        mentions = [
            _make_mention("UKR", "bill-1", "2024-03"),
            _make_mention("UKR", "bill-2", "2024-03"),
            _make_mention("CHN", "bill-3", "2024-03"),
        ]
        with open(path, "w") as f:
            for m in mentions:
                f.write(json.dumps(m) + "\n")

        agg = Aggregator(mentions_path=path)
        data = agg.aggregate_month("2024-03", load_mentions(path))

        assert data["month"] == "2024-03"
        assert data["total_records"] == 3
        # UKR mentioned in 2 records, CHN in 1
        country_map = {c["iso3"]: c["count"] for c in data["countries"]}
        assert country_map["UKR"] == 2
        assert country_map["CHN"] == 1

    def test_dedup_per_record(self, tmp_path):
        """Same country mentioned twice in same record = 1 count."""
        path = tmp_path / "mentions.jsonl"
        mentions = [
            _make_mention("UKR", "bill-1", "2024-03"),
            _make_mention("UKR", "bill-1", "2024-03"),  # same record
        ]
        with open(path, "w") as f:
            for m in mentions:
                f.write(json.dumps(m) + "\n")

        agg = Aggregator(mentions_path=path)
        data = agg.aggregate_month("2024-03", load_mentions(path))

        country_map = {c["iso3"]: c["count"] for c in data["countries"]}
        assert country_map["UKR"] == 1  # deduplicated

    def test_ranking_order(self, tmp_path):
        """Countries should be ranked by count descending."""
        path = tmp_path / "mentions.jsonl"
        mentions = [
            _make_mention("UKR", "bill-1", "2024-03"),
            _make_mention("UKR", "bill-2", "2024-03"),
            _make_mention("UKR", "bill-3", "2024-03"),
            _make_mention("CHN", "bill-4", "2024-03"),
            _make_mention("CHN", "bill-5", "2024-03"),
            _make_mention("IRN", "bill-6", "2024-03"),
        ]
        with open(path, "w") as f:
            for m in mentions:
                f.write(json.dumps(m) + "\n")

        agg = Aggregator(mentions_path=path)
        data = agg.aggregate_month("2024-03", load_mentions(path))

        assert data["countries"][0]["iso3"] == "UKR"
        assert data["countries"][1]["iso3"] == "CHN"
        assert data["countries"][2]["iso3"] == "IRN"

    def test_month_isolation(self, tmp_path):
        """Only mentions from the target month should be counted."""
        path = tmp_path / "mentions.jsonl"
        mentions = [
            _make_mention("UKR", "bill-1", "2024-03"),
            _make_mention("CHN", "bill-2", "2024-02"),  # different month
        ]
        with open(path, "w") as f:
            for m in mentions:
                f.write(json.dumps(m) + "\n")

        agg = Aggregator(mentions_path=path)
        data = agg.aggregate_month("2024-03", load_mentions(path))

        assert len(data["countries"]) == 1
        assert data["countries"][0]["iso3"] == "UKR"

    def test_aggregate_all(self, tmp_path):
        """aggregate_all should process all months."""
        path = tmp_path / "mentions.jsonl"
        mentions = [
            _make_mention("UKR", "bill-1", "2024-01"),
            _make_mention("CHN", "bill-2", "2024-02"),
            _make_mention("IRN", "bill-3", "2024-03"),
        ]
        with open(path, "w") as f:
            for m in mentions:
                f.write(json.dumps(m) + "\n")

        agg = Aggregator(mentions_path=path)
        results = agg.aggregate_all()

        assert "2024-01" in results
        assert "2024-02" in results
        assert "2024-03" in results

    def test_empty_mentions(self, tmp_path):
        path = tmp_path / "mentions.jsonl"
        path.touch()  # empty file

        agg = Aggregator(mentions_path=path)
        data = agg.aggregate_month("2024-03", [])

        assert data["total_records"] == 0
        assert data["countries"] == []


class TestAppendMentions:
    def test_append_creates_file(self, tmp_path):
        path = tmp_path / "processed" / "mentions.jsonl"

        class FakeMention:
            def to_dict(self):
                return {"iso3": "UKR", "record_id": "test-1", "month": "2024-03"}

        append_mentions([FakeMention()], path=path)
        assert path.exists()
        data = json.loads(path.read_text().strip())
        assert data["iso3"] == "UKR"

    def test_append_accumulates(self, tmp_path):
        path = tmp_path / "mentions.jsonl"
        append_mentions([{"iso3": "UKR"}], path=path)
        append_mentions([{"iso3": "CHN"}], path=path)

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
