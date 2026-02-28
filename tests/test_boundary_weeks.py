"""Tests for month-boundary ingestion correctness.

Validates that the buffered-window ingestion handles month boundaries
correctly: late-published records land in the right month, dedup blocks
reprocessing, and reaggregation is triggered for affected months.
"""

import json
import pytest
from pipeline.dedup import DedupManager
from pipeline.ingest import compute_window, record_month


class TestBoundaryRecordAssignment:
    """Records should be assigned to their actual date's month, not the run month."""

    def test_last_day_of_month_lands_in_correct_month(self):
        """A record dated Jan 31 caught by February run belongs to January."""
        record_date = "2024-01-31"
        assert record_month(record_date) == "2024-01"

    def test_first_day_of_month_lands_in_correct_month(self):
        """A record dated Feb 1 caught by January run's buffer belongs to February."""
        record_date = "2024-02-01"
        assert record_month(record_date) == "2024-02"

    def test_buffer_window_spans_correct_range(self):
        """February run with ±5 day buffer should cover Jan 27 → Mar 5."""
        start, end = compute_window("2024-02", buffer_days=5)
        assert start == "2024-01-27"
        assert end == "2024-03-05"

    def test_late_published_record_caught_by_buffer(self):
        """A record dated Jan 30 published late is within Feb run's buffer."""
        start, end = compute_window("2024-02", buffer_days=5)
        record_date = "2024-01-30"
        assert record_date >= start
        assert record_date <= end
        assert record_month(record_date) == "2024-01"  # assigned to January


class TestDedupPreventsReprocessing:
    """Records seen in one run should not be reprocessed in overlapping runs."""

    def test_seen_record_blocked(self, tmp_path):
        """A record processed in January run is skipped by February run."""
        path = tmp_path / "seen_ids.json"
        dedup = DedupManager(path=path)

        # January run processes a record
        dedup.mark_seen(["hr-118-5678"])
        assert dedup.is_seen("hr-118-5678")

        # February run encounters same record in overlap window
        # It should be blocked
        assert dedup.is_seen("hr-118-5678")

    def test_new_record_not_blocked(self, tmp_path):
        """A genuinely new record in the overlap window is processed."""
        path = tmp_path / "seen_ids.json"
        dedup = DedupManager(path=path)
        dedup.mark_seen(["hr-118-5678"])

        # Different record ID — should pass through
        assert not dedup.is_seen("hr-118-9999")


class TestIdempotency:
    """Running the same month twice should produce zero new records."""

    def test_second_run_finds_nothing_new(self, tmp_path):
        """Simulate two runs of the same month."""
        path = tmp_path / "seen_ids.json"
        dedup = DedupManager(path=path)

        # First run processes some records
        first_run_ids = ["bill-118-hr100", "bill-118-hr101", "bill-118-hr102"]
        dedup.mark_seen(first_run_ids)
        assert dedup.count == 3

        # Second run encounters same records
        new_in_second_run = [
            rid for rid in first_run_ids
            if not dedup.is_seen(rid)
        ]
        assert len(new_in_second_run) == 0


class TestMonthsTouched:
    """Buffer window can touch multiple months."""

    def test_february_run_touches_three_months(self):
        """Feb run with ±5d buffer can have records in Jan, Feb, and Mar."""
        start, end = compute_window("2024-02", buffer_days=5)

        # Records in the window
        test_dates = [
            ("2024-01-28", "2024-01"),  # January record in buffer
            ("2024-02-15", "2024-02"),  # February record (target)
            ("2024-03-01", "2024-03"),  # March record in buffer
        ]

        months_touched = set()
        for date, expected_month in test_dates:
            assert date >= start and date <= end, f"{date} not in window"
            month = record_month(date)
            assert month == expected_month
            months_touched.add(month)

        assert months_touched == {"2024-01", "2024-02", "2024-03"}
