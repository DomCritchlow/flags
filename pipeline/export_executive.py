"""Export Executive Orders aggregated data to frontend JSON files.

Produces three files consumed by the frontend Executive branch view:
  - executive_monthly_top.json  — one entry per month with the "winner"
  - executive_monthly_all.json  — full country breakdown per month
  - executive_metadata.json     — pipeline stats

Usage:
    PYTHONPATH=. python -m pipeline.export_executive
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline import config
from pipeline.aggregator import Aggregator
from pipeline.export import _build_monthly_top, _build_monthly_all, _write_json
from pipeline.gazetteer import Gazetteer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("export_executive")


def export_executive(output_dir: Path = None):
    output_dir = output_dir or config.AGGREGATED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if not config.EXECUTIVE_MENTIONS_PATH.exists():
        log.error(f"No executive mentions found at {config.EXECUTIVE_MENTIONS_PATH}")
        log.error("Run: PYTHONPATH=. python -m scripts.reprocess_executive first")
        return

    gaz = Gazetteer()
    agg = Aggregator(mentions_path=config.EXECUTIVE_MENTIONS_PATH)

    all_data = agg.aggregate_all()
    if not all_data:
        log.warning("No executive order mentions to export")
        return

    # monthly_top.json
    monthly_top = _build_monthly_top(all_data, gaz)
    _write_json(output_dir / "executive_monthly_top.json", monthly_top)
    log.info(f"Exported executive_monthly_top.json ({len(monthly_top)} months)")

    # monthly_all.json
    monthly_all = _build_monthly_all(all_data, gaz)
    _write_json(output_dir / "executive_monthly_all.json", monthly_all)
    log.info(f"Exported executive_monthly_all.json ({len(monthly_all)} months)")

    # metadata.json
    now = datetime.now(timezone.utc).isoformat()
    all_months = sorted(all_data.keys())
    total_mentions = sum(
        sum(c["count"] for c in d.get("countries", []))
        for d in all_data.values()
    )
    total_records = sum(d.get("total_records", 0) for d in all_data.values())
    metadata = {
        "last_run": now,
        "source": "executive_order",
        "total_records_processed": total_records,
        "total_mentions_detected": total_mentions,
        "date_range": [all_months[0], all_months[-1]] if all_months else [],
        "month_count": len(all_months),
    }
    _write_json(output_dir / "executive_metadata.json", metadata)
    log.info("Exported executive_metadata.json")
    log.info(f"Summary: {len(all_months)} months, {total_mentions} mentions")
    log.info(f"Next: cp data/aggregated/executive_*.json docs/data/")


def main():
    export_executive()


if __name__ == "__main__":
    main()
