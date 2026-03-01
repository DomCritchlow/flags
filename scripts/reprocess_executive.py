"""Detect country mentions in all Executive Order records.

Clears executive_mentions.jsonl and rebuilds it from
data/raw/executive_orders/eos.jsonl using the current gazetteer.

Usage:
    PYTHONPATH=. python -m scripts.reprocess_executive
"""

import json
import logging

from pipeline.aggregator import append_mentions
from pipeline.detector import CountryDetector
from pipeline.gazetteer import Gazetteer
from pipeline import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reprocess_executive")


def main():
    if not config.EXECUTIVE_RAW_PATH.exists():
        log.error(f"No raw EO data found at {config.EXECUTIVE_RAW_PATH}")
        log.error("Run: PYTHONPATH=. python -m scripts.ingest_executive_orders first")
        return

    # Clear existing executive mentions
    config.EXECUTIVE_MENTIONS_PATH.write_text("")
    log.info("Cleared executive_mentions.jsonl")

    gazetteer = Gazetteer()
    detector = CountryDetector(gazetteer, enable_llm=False)
    log.info(f"Gazetteer loaded: {gazetteer.stats()}")

    # Load all EO records
    records = []
    with open(config.EXECUTIVE_RAW_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    log.info(f"Loaded {len(records)} EO records")

    mentions = []
    for rec in records:
        text = (rec.get("title", "") + " " + rec.get("summary", "")).strip()
        if not text:
            continue
        record_mentions = detector.detect(text, rec["id"], "executive_order")
        month = (rec.get("date") or "")[:7]
        for m in record_mentions:
            m.month = month
            m.title = rec.get("title", "")
        mentions.extend(record_mentions)

    append_mentions(mentions, path=config.EXECUTIVE_MENTIONS_PATH)

    log.info(f"Reprocess complete: {len(records)} EOs, {len(mentions)} country mentions")
    log.info("Now run: PYTHONPATH=. python -m pipeline.export_executive")


if __name__ == "__main__":
    main()
