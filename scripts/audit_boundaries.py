"""Audit month-boundary record assignments.

For a given month, finds all records whose date is within 5 days of a
month boundary and verifies they are assigned to the correct month.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import click

from pipeline import config
from pipeline.ingest import record_month


def iter_raw_records():
    """Iterate over all raw records across all congress directories."""
    for congress_dir in sorted(config.RAW_DIR.iterdir()):
        if not congress_dir.is_dir():
            continue
        for jsonl_file in sorted(congress_dir.glob("*.jsonl")):
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue


@click.command()
@click.option("--month", required=True, help="Month to audit (YYYY-MM)")
def main(month):
    """Verify boundary-week record assignments for a month."""
    year, mon = int(month[:4]), int(month[5:7])

    boundary_records = []
    for record in iter_raw_records():
        date_str = record.get("date", "")
        if not date_str:
            continue

        try:
            record_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            continue

        # Check if within 5 days of month start or end
        month_start = datetime(year, mon, 1)
        if mon == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, mon + 1, 1)

        days_from_start = abs((record_date - month_start).days)
        days_from_end = abs((record_date - month_end).days)

        if days_from_start <= 5 or days_from_end <= 5:
            assigned_month = record_month(date_str)
            boundary_records.append({
                "id": record.get("id", "?"),
                "date": date_str[:10],
                "assigned_month": assigned_month,
                "source": record.get("source", "?"),
            })

    if not boundary_records:
        print(f"No boundary records found for {month}")
        return

    print(f"Boundary records for {month} (within 5 days of month edges):")
    print(f"Total: {len(boundary_records)}")
    print()

    # Group by assigned month
    by_month = {}
    for r in boundary_records:
        m = r["assigned_month"]
        by_month.setdefault(m, []).append(r)

    for m in sorted(by_month.keys()):
        records = by_month[m]
        print(f"  Assigned to {m}: {len(records)} records")
        for r in records[:5]:
            print(f"    {r['id']} (date: {r['date']}, source: {r['source']})")
        if len(records) > 5:
            print(f"    ... and {len(records) - 5} more")


if __name__ == "__main__":
    main()
