"""Reprocess all raw JSONL records through the detection engine.

Clears mentions.jsonl and rebuilds it from scratch using the current
gazetteer. Run this after changing gazetteers/unambiguous_terms.yaml
or gazetteers/ambiguous_terms.yaml.

Usage:
    PYTHONPATH=. python -m scripts.reprocess_all
"""

import json
import logging
import sys
from pathlib import Path

from pipeline.aggregator import Aggregator, append_mentions
from pipeline.detector import CountryDetector
from pipeline.gazetteer import Gazetteer
from pipeline import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reprocess_all")


def main():
    # Clear existing mentions
    config.MENTIONS_PATH.write_text("")
    log.info("Cleared mentions.jsonl")

    gazetteer = Gazetteer()
    detector = CountryDetector(gazetteer, enable_llm=False)
    log.info(f"Gazetteer loaded: {gazetteer.stats()}")

    raw_files = sorted(Path("data/raw").glob("*/*.jsonl"))
    log.info(f"Found {len(raw_files)} raw JSONL files to process")

    total_records = 0
    total_mentions = 0

    for i, filepath in enumerate(raw_files, 1):
        records = []
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        mentions = []
        for rec in records:
            text = (rec.get("title", "") + " " + rec.get("summary", "")).strip()
            if not text:
                continue
            record_mentions = detector.detect(
                text, rec["id"], rec.get("source", "bill")
            )
            month = rec.get("date", "")[:7]
            for m in record_mentions:
                m.month = month
                m.title = rec.get("title", "")
            mentions.extend(record_mentions)

        if mentions:
            append_mentions(mentions)

        total_records += len(records)
        total_mentions += len(mentions)

        if i % 10 == 0 or i == len(raw_files):
            log.info(
                f"[{i}/{len(raw_files)}] {filepath.parent.name}/{filepath.name}"
                f" — {total_records} records, {total_mentions} mentions so far"
            )

    log.info(f"Reprocess complete: {total_records} records, {total_mentions} mentions")
    log.info("Now run: PYTHONPATH=. python -m pipeline.aggregator --all")
    log.info("Then:    PYTHONPATH=. python -m pipeline.export")
    log.info("Then:    cp data/aggregated/*.json docs/data/")


if __name__ == "__main__":
    main()
