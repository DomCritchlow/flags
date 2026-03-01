"""Tests for the Congress.gov API ingestion module."""

import pytest
from pipeline.ingest import resolve_month, compute_window, record_month


class TestResolveMonth:
    def test_explicit_month(self):
        assert resolve_month("2024-02") == "2024-02"

    def test_previous_month(self):
        result = resolve_month("previous")
        # Should be a valid YYYY-MM string
        assert len(result) == 7
        assert result[4] == "-"

    def test_current_month(self):
        result = resolve_month("current")
        assert len(result) == 7
        assert result[4] == "-"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            resolve_month("2024/02")

    def test_invalid_month_raises(self):
        with pytest.raises(ValueError):
            resolve_month("not-a-month")


class TestComputeWindow:
    def test_default_buffer(self):
        start, end = compute_window("2024-02", buffer_days=5)
        assert start == "2024-01-27"  # Feb 1 - 5 days
        assert end == "2024-03-05"    # Feb 29 + 5 days (2024 is leap year)

    def test_zero_buffer(self):
        start, end = compute_window("2024-03", buffer_days=0)
        assert start == "2024-03-01"
        assert end == "2024-03-31"

    def test_year_boundary(self):
        start, end = compute_window("2024-01", buffer_days=5)
        assert start == "2023-12-27"  # crosses year boundary
        assert end == "2024-02-05"

    def test_december(self):
        start, end = compute_window("2024-12", buffer_days=5)
        assert start == "2024-11-26"
        assert end == "2025-01-05"  # crosses into next year


class TestRecordMonth:
    def test_standard_date(self):
        assert record_month("2024-03-15") == "2024-03"

    def test_datetime_format(self):
        assert record_month("2024-03-15T14:30:00") == "2024-03"

    def test_datetime_with_z(self):
        assert record_month("2024-03-15T14:30:00Z") == "2024-03"

    def test_empty_string(self):
        assert record_month("") == ""

    def test_short_date(self):
        assert record_month("2024-03") == "2024-03"


class TestNormalization:
    """Test record normalization for each endpoint type."""

    def test_normalize_bill(self):
        from pipeline.ingest import CongressIngester
        # Can't instantiate without API key, test the static-ish methods
        raw = {
            "congress": 118,
            "type": "HR",
            "number": "1234",
            "title": "Ukraine Security Assistance Act",
            "latestAction": {"actionDate": "2024-03-15"},
            "url": "https://congress.gov/bill/118/hr1234",
        }
        # Test normalization directly
        ingester = CongressIngester.__new__(CongressIngester)
        result = ingester._normalize_bill(raw, "test-run", "2024-04-01")
        assert result["id"] == "bill-118-hr1234"
        assert result["source"] == "bill"
        assert result["date"] == "2024-03-15"
        assert "Ukraine" in result["title"]

    def test_normalize_hearing(self):
        from pipeline.ingest import CongressIngester
        raw = {
            "congress": 118,
            "jacketNumber": "56789",
            "title": "China's Military Modernization",
            "date": "2024-02-20",
            "url": "https://congress.gov/hearing/118/56789",
        }
        ingester = CongressIngester.__new__(CongressIngester)
        result = ingester._normalize_hearing(raw, "test-run", "2024-04-01")
        assert result["id"] == "hearing-118-56789"
        assert result["source"] == "hearing"
        assert "China" in result["title"]

    def test_normalize_bill_missing_number(self):
        from pipeline.ingest import CongressIngester
        raw = {"congress": 118, "type": "HR"}  # no number
        ingester = CongressIngester.__new__(CongressIngester)
        result = ingester._normalize_bill(raw, "test-run", "2024-04-01")
        assert result is None

    def test_normalize_treaty(self):
        from pipeline.ingest import CongressIngester
        raw = {
            "congressReceived": 118,
            "number": 4,
            "suffix": None,
            "topic": "Taxation",
            "transmittedDate": "2023-08-02",
            "titles": [{"title": "Protocol Amending the Convention Between the United States and Luxembourg", "titleType": "Treaty"}],
            "countriesParties": "Luxembourg",
            "url": "https://api.congress.gov/v3/treaty/118/4",
        }
        ingester = CongressIngester.__new__(CongressIngester)
        result = ingester._normalize_treaty(raw, "test-run", "2024-01-01")
        assert result["id"] == "treaty-118-4"
        assert result["source"] == "treaty"
        assert result["date"] == "2023-08-02"
        assert "Luxembourg" in result["title"]

    def test_normalize_treaty_with_suffix(self):
        from pipeline.ingest import CongressIngester
        raw = {
            "congressReceived": 117,
            "number": 1,
            "suffix": "A",
            "topic": "Defense",
            "transmittedDate": "2022-01-10",
            "countriesParties": "Japan",
            "url": "https://api.congress.gov/v3/treaty/117/1/A",
        }
        ingester = CongressIngester.__new__(CongressIngester)
        result = ingester._normalize_treaty(raw, "test-run", "2024-01-01")
        assert result["id"] == "treaty-117-1A"
        assert "Japan" in result["title"]

    def test_normalize_treaty_fallback_title(self):
        from pipeline.ingest import CongressIngester
        # No titles array — should build title from countriesParties + topic
        raw = {
            "congressReceived": 118,
            "number": 7,
            "topic": "Extradition",
            "transmittedDate": "2024-03-15",
            "countriesParties": "Canada",
            "url": "https://api.congress.gov/v3/treaty/118/7",
        }
        ingester = CongressIngester.__new__(CongressIngester)
        result = ingester._normalize_treaty(raw, "test-run", "2024-04-01")
        assert result["id"] == "treaty-118-7"
        assert "Canada" in result["title"]
        assert "Extradition" in result["title"]

    def test_normalize_treaty_missing_required(self):
        from pipeline.ingest import CongressIngester
        ingester = CongressIngester.__new__(CongressIngester)
        assert ingester._normalize_treaty({}, "test-run", "2024-01-01") is None
        assert ingester._normalize_treaty({"congressReceived": 118}, "test-run", "2024-01-01") is None
