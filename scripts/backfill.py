"""Backfill historical data from Congress.gov API.

Pulls data for a range of Congresses. Designed to be run locally
(too slow for GitHub Actions — ~3 hours for 10 years of data).

Strategy: fetch bills once per congress (they don't support date filtering
for historical data), then run month-by-month for other endpoints.

Restartable: dedup via seen_ids.json means re-running picks up
where it left off.
"""

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import click

from pipeline import config
from pipeline.aggregator import Aggregator, append_mentions
from pipeline.dedup import DedupManager
from pipeline.detector import CountryDetector
from pipeline.export import export_all
from pipeline.gazetteer import Gazetteer
from pipeline.ingest import (
    CongressIngester,
    record_month,
    MAX_RECORDS_PER_CONGRESS,
)

logger = logging.getLogger(__name__)


def congress_date_range(congress_num: int) -> tuple[date, date]:
    """Compute the approximate start and end dates for a Congress.

    Each Congress starts on January 3 of odd-numbered years.
    """
    start_year = 1789 + (congress_num - 1) * 2
    start = date(start_year, 1, 3)
    end = date(start_year + 2, 1, 2)
    return start, end


def months_in_congress(congress_num: int) -> list[str]:
    """Generate all YYYY-MM strings for a Congress."""
    start, end = congress_date_range(congress_num)
    months = []
    current = start.replace(day=1)
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def bulk_fetch_bills(ingester, congress_num, dedup, detector,gazetteer):
    """Fetch ALL bills for a congress in one pass, normalize, detect, save.

    Returns (new_count, months_touched).
    """
    run_id = f"backfill-congress-{congress_num}"
    now = datetime.now(timezone.utc).isoformat()

    logger.info(f"  Bulk-fetching all bills for Congress {congress_num}...")

    # Fetch all bills (no date filter — these are congress-scoped)
    raw_records = ingester._fetch_endpoint(
        "bill", "", "",
        congress=congress_num,
        use_date_filter=False,
    )
    logger.info(f"  Fetched {len(raw_records)} bills from API")

    # Normalize
    normalized = []
    for raw in raw_records:
        record = ingester._normalize(raw, "bill", run_id, now)
        if record:
            normalized.append(record)

    # Dedup
    new_records = [r for r in normalized if not dedup.is_seen(r["id"])]

    if not new_records:
        logger.info(f"  All {len(normalized)} bills already seen")
        return 0, set()

    # Mark all new IDs as seen (auto-persists to disk)
    dedup.mark_seen([r["id"] for r in new_records])

    # Save to raw JSONL
    congress_dir = config.RAW_DIR / str(congress_num)
    congress_dir.mkdir(parents=True, exist_ok=True)
    out_path = congress_dir / "bills.jsonl"
    with open(out_path, "a") as f:
        for record in new_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Detect country mentions
    mentions = []
    months_touched = set()
    for record in new_records:
        text = f"{record.get('title', '')} {record.get('summary', '')}"
        record_mentions = detector.detect(text, record["id"], record["source"])
        month_str = record_month(record.get("date", ""))
        if month_str:
            months_touched.add(month_str)
        for m in record_mentions:
            m.month = month_str
        mentions.extend(record_mentions)

    if mentions:
        append_mentions(mentions)

    logger.info(
        f"  Congress {congress_num} bills: {len(new_records)} new, "
        f"{len(mentions)} mentions, months: {sorted(months_touched)}"
    )
    return len(new_records), months_touched


@click.command()
@click.option("--congress-start", type=int, default=93,
              help="Starting Congress number (default: 93, year 1973)")
@click.option("--congress-end", type=int, default=118,
              help="Ending Congress number (default: 118, year 2023-2024)")
@click.option("--buffer-days", type=int, default=config.DEFAULT_BUFFER_DAYS,
              help="Buffer days on each side of month")
@click.option("--dry-run", is_flag=True,
              help="Print months without fetching data")
@click.option("--skip-export", is_flag=True,
              help="Skip final export step (do it manually after)")
def main(
    congress_start: int,
    congress_end: int,
    buffer_days: int,
    dry_run: bool,
    skip_export: bool,
):
    """Backfill historical congressional data."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    congresses = list(range(congress_start, congress_end + 1))
    all_months = []
    for congress in congresses:
        months = months_in_congress(congress)
        all_months.extend(months)
        start, end = congress_date_range(congress)
        logger.info(
            f"Congress {congress}: {start.year}-{end.year} "
            f"({len(months)} months)"
        )

    logger.info(f"\nTotal: {len(congresses)} congresses, {len(all_months)} months")

    if dry_run:
        for m in all_months:
            print(m)
        return

    # Initialize pipeline components
    dedup = DedupManager()
    ingester = CongressIngester(dedup=dedup)
    gazetteer = Gazetteer()
    detector = CountryDetector(gazetteer)

    total_new = 0
    all_touched = set()

    # Phase 1: Bulk-fetch bills per congress (one API pass each)
    logger.info("\n=== Phase 1: Bulk bill fetch ===")
    for congress in congresses:
        try:
            new_count, months = bulk_fetch_bills(
                ingester, congress, dedup, detector, gazetteer
            )
            total_new += new_count
            all_touched.update(months)
        except Exception as e:
            logger.error(f"  ERROR fetching bills for Congress {congress}: {e}")
            continue

    logger.info(f"Phase 1 complete: {total_new} new bill records\n")

    # Phase 2: Month-by-month for other endpoints (CR, amendments, etc.)
    # Temporarily remove "bill" from endpoints since we already have them
    original_endpoints = config.ENDPOINTS[:]
    config.ENDPOINTS = [e for e in config.ENDPOINTS if e != "bill"]

    logger.info("=== Phase 2: Monthly non-bill endpoints ===")
    for i, month in enumerate(all_months, 1):
        logger.info(f"[{i}/{len(all_months)}] Processing {month}...")

        try:
            result = ingester.ingest_month(month, buffer_days)

            if result.new_records:
                mentions = []
                for record in result.new_records:
                    text = f"{record.get('title', '')} {record.get('summary', '')}"
                    record_mentions = detector.detect(
                        text, record["id"], record["source"]
                    )
                    month_str = record_month(record.get("date", ""))
                    for m in record_mentions:
                        m.month = month_str
                    mentions.extend(record_mentions)

                append_mentions(mentions)
                total_new += len(result.new_records)
                all_touched.update(result.months_touched)

                logger.info(
                    f"  {len(result.new_records)} new records, "
                    f"{len(mentions)} mentions"
                )
            else:
                logger.info("  No new records (already ingested or empty)")

        except Exception as e:
            logger.error(f"  ERROR processing {month}: {e}")
            continue

    # Restore endpoints
    config.ENDPOINTS = original_endpoints

    logger.info(f"\nBackfill complete: {total_new} total new records")
    logger.info(f"Months touched: {sorted(all_touched)}")
    logger.info(f"Total seen IDs: {dedup.count}")

    # Final aggregation and export
    if not skip_export and total_new > 0:
        logger.info("Running final aggregation and export...")
        aggregator = Aggregator()
        aggregator.aggregate_all()
        export_all(gazetteer=gazetteer, aggregator=aggregator)
        logger.info("Export complete.")


if __name__ == "__main__":
    main()
