"""Fetch all Executive Orders from the Federal Register API.

Writes normalized JSONL records to data/raw/executive_orders/eos.jsonl.
Safe to re-run — uses seen_ids.json to skip already-fetched records.

Usage:
    PYTHONPATH=. python -m scripts.ingest_executive_orders
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from pipeline import config
from pipeline.dedup import DedupManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest_executive_orders")

FR_API_URL = f"{config.FEDERAL_REGISTER_API_BASE}/documents.json"
FIELDS = [
    "title",
    "abstract",
    "signing_date",
    "executive_order_number",
    "president",
    "html_url",
    "document_number",
]


def _make_record_id(doc: dict) -> str:
    eo_num = doc.get("executive_order_number")
    if eo_num:
        return f"eo-{eo_num}"
    return f"eo-doc-{doc['document_number']}"


def _normalize(doc: dict, run_id: str) -> dict:
    return {
        "id": _make_record_id(doc),
        "source": "executive_order",
        "date": doc.get("signing_date", ""),
        "title": doc.get("title", ""),
        "summary": doc.get("abstract") or "",
        "url": doc.get("html_url", ""),
        "president": doc.get("president", ""),
        "eo_number": doc.get("executive_order_number"),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "ingested_by": run_id,
    }


def fetch_all_eos() -> list[dict]:
    """Paginate through FR API and return all executive order documents."""
    params = {
        "conditions[type][]": "PRESDOCU",
        "conditions[presidential_document_type][]": "executive_order",
        "order": "oldest",
        "per_page": 1000,
        "page": 1,
    }
    for field in FIELDS:
        params[f"fields[]"] = field  # last one wins — build list below

    # requests handles repeated keys properly via list of tuples
    base_params = [
        ("conditions[type][]", "PRESDOCU"),
        ("conditions[presidential_document_type][]", "executive_order"),
        ("order", "oldest"),
        ("per_page", "1000"),
    ]
    for field in FIELDS:
        base_params.append(("fields[]", field))

    all_docs = []
    page = 1
    total_pages = None

    while True:
        page_params = base_params + [("page", str(page))]
        try:
            resp = requests.get(FR_API_URL, params=page_params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.error(f"  Page {page}: request failed — {e}")
            break

        if total_pages is None:
            total_pages = data.get("total_pages", 1)
            log.info(f"  Total EOs: {data.get('count', '?')} across {total_pages} pages")

        docs = data.get("results", [])
        all_docs.extend(docs)
        log.info(f"  Page {page}/{total_pages}: {len(docs)} records (total so far: {len(all_docs)})")

        if page >= total_pages:
            break
        page += 1
        time.sleep(0.5)  # be polite to FR API

    return all_docs


def main():
    run_id = f"eo-ingest-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    # Ensure output directory exists
    config.EXECUTIVE_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)

    dedup = DedupManager()
    log.info(f"Seen IDs loaded: {dedup.count:,} existing records")

    log.info("Fetching Executive Orders from Federal Register API...")
    docs = fetch_all_eos()
    log.info(f"Fetched {len(docs)} total EO documents")

    new_count = 0
    skip_count = 0
    new_ids = []

    with open(config.EXECUTIVE_RAW_PATH, "a") as out_f:
        for doc in docs:
            record = _normalize(doc, run_id)
            rec_id = record["id"]

            if dedup.is_seen(rec_id):
                skip_count += 1
                continue

            out_f.write(json.dumps(record) + "\n")
            new_ids.append(rec_id)
            new_count += 1

    dedup.mark_seen(new_ids)
    log.info(f"Done: {new_count} new EOs written, {skip_count} already seen")
    log.info(f"Output: {config.EXECUTIVE_RAW_PATH}")
    log.info("Now run: PYTHONPATH=. python -m scripts.reprocess_executive")


if __name__ == "__main__":
    main()
