"""Export aggregated data to frontend JSON files.

Produces three files consumed by the GitHub Pages frontend:
- monthly_top.json — one entry per month with the "winner"
- monthly_all.json — full country breakdown per month
- metadata.json — pipeline health and stats
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from pipeline import config
from pipeline.aggregator import Aggregator, load_mentions
from pipeline.gazetteer import Gazetteer

logger = logging.getLogger(__name__)


def export_all(
    gazetteer: Optional[Gazetteer] = None,
    aggregator: Optional[Aggregator] = None,
    output_dir: Optional[Path] = None,
    run_info: Optional[dict] = None,
):
    """Generate all three frontend JSON files."""
    output_dir = output_dir or config.AGGREGATED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    gaz = gazetteer or Gazetteer()
    agg = aggregator or Aggregator()

    # Get all aggregated data
    all_data = agg.aggregate_all()

    if not all_data:
        logger.warning("No data to export")
        return

    # Build monthly_top.json
    monthly_top = _build_monthly_top(all_data, gaz)
    _write_json(output_dir / "monthly_top.json", monthly_top)
    logger.info(f"Exported monthly_top.json ({len(monthly_top)} months)")

    # Build monthly_all.json
    monthly_all = _build_monthly_all(all_data, gaz)
    _write_json(output_dir / "monthly_all.json", monthly_all)
    logger.info(f"Exported monthly_all.json ({len(monthly_all)} months)")

    # Build monthly_top_by_source.json
    by_source_data = agg.aggregate_all_by_source()
    monthly_top_by_source = _build_monthly_top_by_source(by_source_data, gaz)
    _write_json(output_dir / "monthly_top_by_source.json", monthly_top_by_source)
    logger.info(f"Exported monthly_top_by_source.json ({len(monthly_top_by_source)} months)")

    # Build metadata.json
    metadata = _build_metadata(all_data, run_info)
    _write_json(output_dir / "metadata.json", metadata)
    logger.info("Exported metadata.json")


def _build_monthly_top(all_data: dict, gaz: Gazetteer) -> list[dict]:
    """Build the monthly_top.json structure."""
    result = []
    for month in sorted(all_data.keys()):
        data = all_data[month]
        countries = data.get("countries", [])
        if not countries:
            continue

        top = countries[0]
        top_info = gaz.countries.get(top["iso3"], {})
        runner_up = countries[1] if len(countries) > 1 else None
        runner_info = gaz.countries.get(runner_up["iso3"], {}) if runner_up else {}

        entry = {
            "month": month,
            "country_iso3": top["iso3"],
            "country_iso2": top_info.get("iso2", ""),
            "country_name": top_info.get("name", top["iso3"]),
            "mention_count": top["count"],
            "total_records_scanned": data.get("total_records", 0),
            "runner_up_iso3": runner_up["iso3"] if runner_up else None,
            "runner_up_iso2": runner_info.get("iso2", "") if runner_up else None,
            "runner_up_name": runner_info.get("name", "") if runner_up else None,
            "runner_up_count": runner_up["count"] if runner_up else 0,
            "sample_titles": data.get("sample_titles", {}).get(top["iso3"], [])[:3],
        }
        result.append(entry)

    return result


def _build_monthly_all(all_data: dict, gaz: Gazetteer) -> dict:
    """Build the monthly_all.json structure."""
    result = {}
    for month in sorted(all_data.keys()):
        data = all_data[month]
        countries = []
        all_sample_titles = data.get("sample_titles", {})
        for c in data.get("countries", []):
            info = gaz.countries.get(c["iso3"], {})
            countries.append({
                "iso3": c["iso3"],
                "iso2": info.get("iso2", ""),
                "name": info.get("name", c["iso3"]),
                "count": c["count"],
                "sample_titles": all_sample_titles.get(c["iso3"], [])[:3],
            })
        result[month] = {
            "total_records": data.get("total_records", 0),
            "countries": countries,
        }
    return result


def _build_monthly_top_by_source(
    by_source_data: dict[str, dict[str, dict]], gaz: Gazetteer
) -> dict:
    """Build monthly_top_by_source.json.

    Structure: {month: {source_type: {iso3, iso2, name, count, sample_titles}}}
    Only includes sources that have data for that month.
    """
    result = {}
    for month in sorted(by_source_data.keys()):
        sources = by_source_data[month]
        month_entry = {}
        for src, data in sources.items():
            countries = data.get("countries", [])
            if not countries:
                continue
            top = countries[0]
            info = gaz.countries.get(top["iso3"], {})
            month_entry[src] = {
                "iso3": top["iso3"],
                "iso2": info.get("iso2", ""),
                "name": info.get("name", top["iso3"]),
                "count": top["count"],
                "sample_titles": data.get("sample_titles", {}).get(
                    top["iso3"], []
                )[:3],
            }
        if month_entry:
            result[month] = month_entry
    return result


def _build_metadata(all_data: dict, run_info: Optional[dict] = None) -> dict:
    """Build the metadata.json structure."""
    now = datetime.now(timezone.utc).isoformat()
    all_months = sorted(all_data.keys())
    total_mentions = sum(
        sum(c["count"] for c in d.get("countries", []))
        for d in all_data.values()
    )
    total_records = sum(
        d.get("total_records", 0) for d in all_data.values()
    )

    metadata = {
        "last_run": now,
        "last_run_target_month": run_info.get("target_month", "") if run_info else "",
        "last_run_new_records": run_info.get("new_records", 0) if run_info else 0,
        "last_run_months_touched": run_info.get("months_touched", []) if run_info else [],
        "total_records_processed": total_records,
        "total_mentions_detected": total_mentions,
        "date_range": [all_months[0], all_months[-1]] if all_months else [],
        "month_count": len(all_months),
    }
    return metadata


def _write_json(path: Path, data):
    """Write JSON data to file with pretty printing."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# === CLI Entry Point ===

@click.command()
@click.option("--output-dir", default=None, type=click.Path(),
              help="Output directory (default: data/aggregated/)")
def main(output_dir: Optional[str]):
    """Export aggregated data to frontend JSON files."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out = Path(output_dir) if output_dir else None
    export_all(output_dir=out)


if __name__ == "__main__":
    main()
