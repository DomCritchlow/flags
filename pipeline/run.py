"""Full pipeline orchestrator — ingest → detect → aggregate → export.

This is the main entry point for both manual runs and GitHub Actions.
"""

import logging
from typing import Optional

import click

from pipeline import config
from pipeline.aggregator import Aggregator, append_mentions
from pipeline.dedup import DedupManager
from pipeline.detector import CountryDetector
from pipeline.export import export_all
from pipeline.gazetteer import Gazetteer
from pipeline.ingest import CongressIngester, resolve_month, record_month

logger = logging.getLogger(__name__)


@click.command()
@click.option("--month", default="previous",
              help="Target month (YYYY-MM or 'previous')")
@click.option("--buffer-days", default=config.DEFAULT_BUFFER_DAYS, type=int,
              help="Buffer days on each side of target month")
@click.option("--dry-run", is_flag=True,
              help="Print what would happen without making changes")
@click.option("--skip-ingest", is_flag=True,
              help="Skip ingestion (just re-detect, aggregate, export)")
def main(month: str, buffer_days: int, dry_run: bool, skip_ingest: bool):
    """Run the full pipeline: ingest → detect → aggregate → export."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    target = resolve_month(month)
    logger.info(f"Pipeline run for {target} (buffer ±{buffer_days}d)")

    if dry_run:
        logger.info("DRY RUN — no changes will be made")
        return

    # Initialize components
    gazetteer = Gazetteer()
    detector = CountryDetector(gazetteer)
    aggregator = Aggregator()

    # Step 1: Ingest new records from Congress.gov API
    months_touched = []
    new_records = []

    if not skip_ingest:
        logger.info("Step 1: Ingesting from Congress.gov API...")
        dedup = DedupManager()
        ingester = CongressIngester(dedup=dedup)
        result = ingester.ingest_month(target, buffer_days)
        new_records = result.new_records
        months_touched = result.months_touched
        logger.info(f"  Ingested {len(new_records)} new records")
        logger.info(f"  Months touched: {months_touched}")
    else:
        logger.info("Step 1: Skipping ingestion (--skip-ingest)")

    # Step 2: Run country detection on new records
    if new_records:
        logger.info("Step 2: Detecting country mentions...")
        all_mentions = []
        for record in new_records:
            text = f"{record.get('title', '')} {record.get('summary', '')}"
            record_mentions = detector.detect(
                text, record["id"], record["source"]
            )
            # Assign month and title to each mention
            month_str = record_month(record.get("date", ""))
            for m in record_mentions:
                m.month = month_str
                m.title = record.get("title", "")
            all_mentions.extend(record_mentions)

        append_mentions(all_mentions)
        logger.info(f"  Detected {len(all_mentions)} country mentions")
    else:
        logger.info("Step 2: No new records to process")

    # Step 3: Aggregate touched months
    if months_touched:
        logger.info(f"Step 3: Aggregating {len(months_touched)} months...")
        aggregator.aggregate_touched(months_touched)
    else:
        logger.info("Step 3: No months to aggregate")

    # Step 4: Export to frontend JSON
    logger.info("Step 4: Exporting frontend data...")
    run_info = {
        "target_month": target,
        "new_records": len(new_records),
        "months_touched": months_touched,
    }
    export_all(gazetteer=gazetteer, aggregator=aggregator, run_info=run_info)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()
