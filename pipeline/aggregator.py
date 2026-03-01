"""Monthly aggregation — rollup mentions into per-month country rankings.

Reads mentions.jsonl, counts unique countries per month (one count per
country per record), and writes aggregated output files.
"""

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import click

from pipeline import config

logger = logging.getLogger(__name__)


def load_mentions(path: Optional[Path] = None) -> list[dict]:
    """Load all mentions from mentions.jsonl."""
    path = path or config.MENTIONS_PATH
    if not path.exists():
        return []
    mentions = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    mentions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return mentions


def append_mentions(mentions: list, path: Optional[Path] = None):
    """Append new mentions to mentions.jsonl."""
    path = path or config.MENTIONS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for m in mentions:
            data = m.to_dict() if hasattr(m, "to_dict") else m
            f.write(json.dumps(data) + "\n")


def load_title_index() -> dict[str, str]:
    """Build record_id → title mapping from raw data files."""
    index = {}
    if not config.RAW_DIR.exists():
        return index
    for congress_dir in config.RAW_DIR.iterdir():
        if not congress_dir.is_dir():
            continue
        for jsonl_file in congress_dir.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                        rid = r.get("id", "")
                        title = r.get("title", "")
                        if rid and title:
                            index[rid] = title
                    except json.JSONDecodeError:
                        continue
    return index


class Aggregator:
    """Aggregates mentions into monthly country rankings."""

    def __init__(self, mentions_path: Optional[Path] = None):
        self.mentions_path = mentions_path or config.MENTIONS_PATH
        self._title_index = None

    @property
    def title_index(self) -> dict[str, str]:
        if self._title_index is None:
            self._title_index = load_title_index()
        return self._title_index

    def aggregate_month(self, month: str, mentions: list[dict]) -> dict:
        """Aggregate a single month's data.

        Counting rule: one count per country per record (not per occurrence).
        """
        month_mentions = [m for m in mentions if m.get("month") == month]

        # Count unique (country, record) pairs
        country_counts = Counter()
        seen_pairs = set()
        sample_titles = defaultdict(list)

        for m in month_mentions:
            iso3 = m.get("iso3", "")
            record_id = m.get("record_id", "")
            pair = (iso3, record_id)

            if pair not in seen_pairs:
                seen_pairs.add(pair)
                country_counts[iso3] += 1

            # Collect sample titles (up to 3 per country)
            # Prefer the title stored on the mention (set at detection time),
            # fall back to title_index for older mentions that predate this field.
            if len(sample_titles[iso3]) < 3 and record_id:
                title = m.get("title") or self.title_index.get(record_id, record_id)
                if title not in sample_titles[iso3]:
                    sample_titles[iso3].append(title)

        total_records = len({m.get("record_id") for m in month_mentions})
        ranked = country_counts.most_common()

        return {
            "month": month,
            "total_records": total_records,
            "countries": [
                {"iso3": iso3, "count": count}
                for iso3, count in ranked
            ],
            "sample_titles": dict(sample_titles),
        }

    def aggregate_touched(self, touched_months: list[str]) -> dict[str, dict]:
        """Reaggregate only the months that received new data."""
        all_mentions = load_mentions(self.mentions_path)
        results = {}
        for month in touched_months:
            results[month] = self.aggregate_month(month, all_mentions)
            logger.info(
                f"Aggregated {month}: {len(results[month]['countries'])} countries, "
                f"{results[month]['total_records']} records"
            )
        return results

    def aggregate_all(self) -> dict[str, dict]:
        """Full rebuild — aggregate all months from mentions.jsonl."""
        all_mentions = load_mentions(self.mentions_path)

        # Find all unique months
        months = sorted({m.get("month", "") for m in all_mentions if m.get("month")})

        results = {}
        for month in months:
            results[month] = self.aggregate_month(month, all_mentions)

        logger.info(f"Aggregated {len(results)} months")
        return results

    def aggregate_all_by_source(self) -> dict[str, dict[str, dict]]:
        """Full rebuild with per-source-type breakdown.

        Returns {month: {source_type: {countries: [...], total_records: N}}}.
        """
        all_mentions = load_mentions(self.mentions_path)
        months = sorted({m.get("month", "") for m in all_mentions if m.get("month")})

        # Collect unique source types
        source_types = sorted({m.get("source_type", "") for m in all_mentions
                               if m.get("source_type")})

        results = {}
        for month in months:
            month_data = {}
            for src in source_types:
                filtered = [m for m in all_mentions
                            if m.get("source_type") == src]
                agg = self.aggregate_month(month, filtered)
                if agg["countries"]:
                    month_data[src] = agg
            results[month] = month_data

        logger.info(
            f"Aggregated {len(results)} months by source "
            f"({len(source_types)} types: {source_types})"
        )
        return results


# === CLI Entry Point ===

@click.command()
@click.option("--month", default=None, help="Aggregate a specific month (YYYY-MM)")
@click.option("--all", "all_months", is_flag=True, help="Rebuild all months")
@click.option("--touched-months", "touched", is_flag=True,
              help="Reaggregate months from last run (reads metadata)")
def main(month: Optional[str], all_months: bool, touched: bool):
    """Aggregate country mentions into monthly rankings."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    agg = Aggregator()

    if all_months:
        results = agg.aggregate_all()
        print(f"Aggregated {len(results)} months")
    elif month:
        all_mentions = load_mentions()
        result = agg.aggregate_month(month, all_mentions)
        print(f"{month}: {len(result['countries'])} countries, "
              f"{result['total_records']} records")
        if result["countries"]:
            top = result["countries"][0]
            print(f"  Top: {top['iso3']} ({top['count']} mentions)")
    else:
        print("Specify --month YYYY-MM, --all, or --touched-months")


if __name__ == "__main__":
    main()
