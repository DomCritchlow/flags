# Congressional World View

Visualize which countries dominate U.S. congressional language over time.
Inspired by [The Pudding's NYT analysis](https://pudding.cool/2018/12/countries).

Live site: https://critchlow.us/flags/

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v   # 197 tests
```

## Current Data State

- **Coverage**: Jan 1973 – present (Congresses 93–119, fully backfilled)
- **Records ingested**: ~370,000 congressional records deduplicated (369,980 distinct IDs across `data/raw/`; `data/seen_ids.json` holds ~371,500 entries, executive orders included)
- **Records with a mention**: 17,702 — beware, this is what `metadata.json` calls `total_records_processed`. It is *not* the ingest count
- **Mentions**: 20,248 unique country-per-record pairs (`total_mentions_detected`); `data/processed/mentions.jsonl` has 20,758 rows before that dedup
- **Where mentions come from**: bill 20,354 · treaty 158 · nomination 144 · amendment 102. Congressional-record is ingested but contributes nothing (see Endpoints below)
- **Gap**: None — full historical range complete

### Catching Up to Current Month

```bash
# Catch up to current month (pipeline also runs weekly via Actions)
source .venv/bin/activate
PYTHONPATH=. python -m pipeline.run --month current --buffer-days 3
```

### How Backfill Works

Two-phase approach (see `scripts/backfill.py`):
1. **Phase 1**: Bulk-fetch bills *and treaties* per congress (one API pass, no date filter — historical bills don't respond to date filtering since it filters by *update* date)
2. **Phase 2**: Month-by-month for everything else in `config.ENDPOINTS` (amendments, nominations, CR)

Both phases are selectable: `--phase 1|2` and `--sources bill,treaty,…`.

Key constraint: Congress.gov `fromDateTime`/`toDateTime` filter by **update date**, not action date. Historical bills untouched for years return 0 results with date filters. That's why bills are fetched congress-scoped without dates.

## CLI Reference

```bash
# Full pipeline (what GitHub Actions runs weekly/monthly)
PYTHONPATH=. python -m pipeline.run --month 2024-02 --buffer-days 5
PYTHONPATH=. python -m pipeline.run --month current --buffer-days 3
PYTHONPATH=. python -m pipeline.run --month previous --buffer-days 5

# Individual stages
PYTHONPATH=. python -m pipeline.ingest --month 2024-02 --buffer-days 5 [--dry-run]
PYTHONPATH=. python -m pipeline.detector [--incremental | --reprocess] [--enable-llm] [--dry-run]
PYTHONPATH=. python -m pipeline.aggregator --touched-months [--month 2024-02] [--all]
PYTHONPATH=. python -m pipeline.export [--output-dir DIR]   # no --month/--all; always exports every month

# Executive-orders side pipeline (both ingest workflows run these three)
PYTHONPATH=. python -m scripts.ingest_executive_orders
PYTHONPATH=. python -m scripts.reprocess_executive
PYTHONPATH=. python -m pipeline.export_executive

# Backfill historical data (run locally, ~3-6 hours for full range)
PYTHONPATH=. python -m scripts.backfill [--congress-start 93] [--congress-end 118] [--dry-run]

# Validation and audit
PYTHONPATH=. python -m scripts.validate_gazetteers
PYTHONPATH=. python -m scripts.audit_ambiguous --month 2024-02
PYTHONPATH=. python -m scripts.audit_boundaries --month 2024-02
```

## Environment Variables

- `CONGRESS_API_KEY` — from https://api.congress.gov/sign-up/ (free)
- `ANTHROPIC_API_KEY` — for Tier 3 LLM fallback (~$0.05/month)

## Architecture

See `architecture.md` for the full specification.

### Pipeline

- `pipeline/run.py` — Full orchestrator: ingest → detect → aggregate → export
- `pipeline/ingest.py` — Congress.gov API client, buffered date windows; endpoints come from `config.ENDPOINTS`
- `pipeline/detector.py` — 3-tier country detection (dictionary → disambiguation → LLM); see "Detection runs" below
- `pipeline/aggregator.py` — Monthly rollup + per-source-type breakdown; counts one per (country, record) pair
- `pipeline/export.py` — Produces 4 JSON files for frontend
- `pipeline/export_executive.py` — Produces the 3 `executive_*.json` files
- `pipeline/gazetteer.py` — Loads the 4 YAMLs in `gazetteers/` (197 countries)
- `pipeline/dedup.py` — Tracks seen record IDs via `data/seen_ids.json`
- `pipeline/config.py` — Paths, API keys, constants, `ENDPOINTS`

### Endpoints

`config.ENDPOINTS` is the authoritative list. `pipeline/ingest.py` implements normalizers for 6
Congress.gov endpoints — bill, hearing, congressional-record, amendment, nomination, treaty — of
which **5 are enabled** in `config.ENDPOINTS`; `hearing` is implemented but commented out there.

Detection reads `title` only; no ingested congressional record has a non-empty `summary`.

- **Producing mentions**: `bill`, `treaty`, `nomination`, `amendment`
- **Active, zero mentions**: `congressional-record` — the API returns daily *issues*, not floor
  text, so the normalized title is just the section-label list ("Senate Section | House Section |
  Daily Digest | …"). 5,851 issues in `data/raw/`, 0 mentions. Reading actual speeches would mean
  fetching the linked full-text documents.
- **Implemented but disabled**: `hearing` — commented out in `config.ENDPOINTS`. Re-enabling it is
  a config edit plus a per-hearing detail fetch; the normalizer is still there.
- **Removed outright**: `committee-report` — same defect as `hearing` (list payload with neither
  title nor action date, only `updateDate`), so every record normalized to an empty title and was
  dropped by the date post-filter. It never landed a single record in `data/raw/`. No normalizer,
  no `key_map` entry, no dispatch branch — reviving it means writing it again.

So: 6 normalizers implemented, 5 active, 1 disabled, 1 removed.

Do not describe the site as covering hearings, committee reports, or floor speeches. It does not.

### Detection runs

```bash
PYTHONPATH=. python -m pipeline.detector [--incremental | --reprocess] [--enable-llm] [--dry-run]
```

`--incremental` is the default when no mode flag is given. The two modes are mutually exclusive
(exit 2 if combined); the CLI exits 1 if no congressional raw files exist under `data/raw/`.

- **`--incremental`** — skips records whose ID already appears in `data/processed/mentions.jsonl`
  and appends the rest.
- **`--reprocess`** — truncates `mentions.jsonl` and re-detects the whole corpus.

Both modes build a fresh `Gazetteer()`, so **both pick up gazetteer edits.** The difference is only
which records get rescored. After a gazetteer change you usually want `--reprocess`, because
incremental will not revisit records that already matched.

**Known limitation, by design:** `mentions.jsonl` is the only durable record of what detection has
seen, and a record that produces zero mentions leaves no trace there. So `--incremental` rescans
every zero-mention record on every run. "Incremental" means *skips records that already have
mentions*, not *skips records already scanned*. This is idempotent and harmless — detection is
pure and nothing gets appended — just not free. Do not "fix" this by having the detector read
`seen_ids.json`: `ingest` marks IDs seen at ingest time, so that set is always empty by the time
the detector runs.

`--enable-llm` is **off by default**. A corpus-wide run with Tier 3 on would hit the Anthropic API
for ~370K records.

`scripts/reprocess_all.py` still exists and does the same thing as `--reprocess`, minus the flags.
Prefer the detector CLI; treat the script as the older equivalent.

### Data Files

- `data/raw/{congress}/*.jsonl` — Raw API records by congress
- `data/processed/mentions.jsonl` — All detected country mentions (has `source_type` field)
- `data/aggregated/monthly_top.json` — #1 country per month (all sources combined)
- `data/aggregated/monthly_top_by_source.json` — #1 country per month per source type
- `data/aggregated/monthly_all.json` — Full country breakdown per month
- `data/aggregated/metadata.json` — Pipeline health stats
- `data/aggregated/executive_{monthly_top,monthly_all,metadata}.json` — Executive-orders pipeline
- `data/seen_ids.json` — Dedup index (~371,500 IDs, executive orders included)

`docs/data/` holds 7 files: the 4 congressional JSONs above plus the 3 `executive_*.json`. The
ingest workflows `cp data/aggregated/*.json docs/data/` and commit; nothing else writes there.

### Frontend

- `docs/index.html` — The entire data story (newspaper theme): grid → insights → rankings →
  crisis timeline → eras → Congress-vs-executive → heat map
- `docs/css/story.css` — Playfair Display + IBM Plex Sans, warm newsprint palette
- `docs/js/flag-grid.js` — Calendar grid renderer. **No source-type filtering** — there is no
  toggle UI anywhere on the site. `monthly_top_by_source.json` is still fetched by the loader but
  no renderer consumes it
- `docs/js/heat-matrix.js` — Country-by-month heat map
- `docs/js/story-insights.js` — Auto-generated narrative blocks (pure string templates, no LLM)
- `docs/js/story-app.js` — Main page orchestrator: wires grid, sections, and detail panel
- `docs/js/data-loader.js` — Shared data fetcher (`loadAll()` + `loadExecutive()`)
- `docs/bump/` — Legacy path, now a single `index.html` that meta-refreshes to `../`
- `docs/flags/` — SVG flag images by ISO2 code

### Automation

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `weekly-ingest.yml` | Mondays 06:00 UTC | Current month ingestion (±3 day buffer) + executive orders, then copy to `docs/data/` and commit to `main` |
| `monthly-ingest.yml` | 3rd of month 06:00 UTC | Previous month ingestion (±5 day buffer), same copy-and-commit |
| `tests.yml` | On push/PR touching `pipeline/`, `scripts/`, `gazetteers/`, `tests/`, or dependency pins | 197 tests + gazetteer validation |

There is no deploy workflow. GitHub Pages source is **Deploy from branch** → `main` → `/docs`, so
an ingest workflow's commit to `main` *is* the deploy.

## Testing

```bash
pytest tests/ -v                          # All 197 tests
pytest tests/test_detector.py -v          # Detection engine
pytest tests/test_known_false_positives.py -v  # Regression suite
pytest tests/ -v --cov=pipeline           # With coverage
```

## Rules

- Never commit `.env` or API keys
- `data/` is committed (pipeline outputs feed the frontend)
- `docs/data/` is committed — ingest workflows copy from `data/aggregated/` and commit directly
- All pipeline modules must be idempotent (safe to re-run)
- Detection changes must add regression tests to `test_known_false_positives.py`
- Backfill is restartable — dedup prevents reprocessing seen records
