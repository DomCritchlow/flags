# Congressional World View

Visualize which countries dominate U.S. congressional language over time.
Inspired by [The Pudding's NYT analysis](https://pudding.cool/2018/12/countries).

Live site: http://critchlow.us/flags/

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v   # 128 tests
```

## Current Data State

- **Coverage**: Jan 2013 – Jan 2025 (Congresses 113–119)
- **Records**: ~98,000 deduplicated across bills, nominations, amendments, congressional records
- **Mentions**: ~5,900 country mentions detected
- **Gap**: Congresses 93–112 (1973–2012) not yet backfilled

### Catching Up / Extending Data

```bash
# Backfill older congresses (run locally, ~3 hrs per 10 congresses)
# Congresses 93-112 cover 1973-2012 — the unfilled historical range
source .venv/bin/activate
PYTHONPATH=. python -m scripts.backfill --congress-start 93 --congress-end 112

# Backfill is restartable — dedup via seen_ids.json means re-running
# picks up where it left off. Safe to ctrl-C and resume later.

# After backfill, re-export and copy to site:
PYTHONPATH=. python -m pipeline.export
cp data/aggregated/*.json site/data/

# Catch up to current month (pipeline also runs weekly via Actions)
PYTHONPATH=. python -m pipeline.run --month current --buffer-days 3
```

### How Backfill Works

Two-phase approach (see `scripts/backfill.py`):
1. **Phase 1**: Bulk-fetch all bills per congress (one API pass, no date filter — historical bills don't respond to date filtering since it filters by *update* date)
2. **Phase 2**: Month-by-month for non-bill endpoints (amendments, nominations, CR)

Key constraint: Congress.gov `fromDateTime`/`toDateTime` filter by **update date**, not action date. Historical bills untouched for years return 0 results with date filters. That's why bills are fetched congress-scoped without dates.

## CLI Reference

```bash
# Full pipeline (what GitHub Actions runs weekly/monthly)
PYTHONPATH=. python -m pipeline.run --month 2024-02 --buffer-days 5
PYTHONPATH=. python -m pipeline.run --month current --buffer-days 3
PYTHONPATH=. python -m pipeline.run --month previous --buffer-days 5

# Individual stages
PYTHONPATH=. python -m pipeline.ingest --month 2024-02 --buffer-days 5 [--dry-run]
PYTHONPATH=. python -m pipeline.detector --incremental [--reprocess]
PYTHONPATH=. python -m pipeline.aggregator --touched-months [--month 2024-02] [--all]
PYTHONPATH=. python -m pipeline.export [--month 2024-02] [--all]

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
- `pipeline/ingest.py` — Congress.gov API client, 5 endpoints, buffered date windows
- `pipeline/detector.py` — 3-tier country detection (dictionary → disambiguation → LLM)
- `pipeline/aggregator.py` — Monthly rollup + per-source-type breakdown
- `pipeline/export.py` — Produces 4 JSON files for frontend
- `pipeline/gazetteer.py` — Loads ~200 country YAML gazetteers
- `pipeline/dedup.py` — Tracks seen record IDs via `data/seen_ids.json`
- `pipeline/config.py` — Paths, API keys, constants

### Data Files

- `data/raw/{congress}/*.jsonl` — Raw API records by congress
- `data/processed/mentions.jsonl` — All detected country mentions (has `source_type` field)
- `data/aggregated/monthly_top.json` — #1 country per month (all sources combined)
- `data/aggregated/monthly_top_by_source.json` — #1 country per month per source type
- `data/aggregated/monthly_all.json` — Full country breakdown per month
- `data/aggregated/metadata.json` — Pipeline health stats
- `data/seen_ids.json` — Dedup index (~98K IDs)

### Frontend

- `site/index.html` — Flag grid data story (newspaper theme)
- `site/css/story.css` — Playfair Display + IBM Plex Sans, warm newsprint palette
- `site/js/flag-grid.js` — Calendar grid renderer with source-type filtering
- `site/js/story-insights.js` — Auto-generated narrative blocks (pure string templates, no LLM)
- `site/js/story-app.js` — Main page orchestrator, wires toggle + grid + detail panel
- `site/js/data-loader.js` — Shared data fetcher (used by both main site and bump chart)
- `site/bump/` — Bump chart subsite (D3-based interactive ranking visualization)
- `site/flags/` — SVG flag images by ISO2 code

### Automation

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `weekly-ingest.yml` | Mondays 06:00 UTC | Current month ingestion (±3 day buffer) |
| `monthly-ingest.yml` | 3rd of month 06:00 UTC | Previous month ingestion (±5 day buffer) |
| `deploy-pages.yml` | On data/site push | Deploys `site/` to GitHub Pages |
| `tests.yml` | On pipeline/test push | 128 tests + gazetteer validation |

GitHub Pages source must be set to **GitHub Actions** (not "Deploy from a branch").

## Testing

```bash
pytest tests/ -v                          # All 128 tests
pytest tests/test_detector.py -v          # Detection engine
pytest tests/test_known_false_positives.py -v  # Regression suite
pytest tests/ -v --cov=pipeline           # With coverage
```

## Rules

- Never commit `.env` or API keys
- `data/` is committed (pipeline outputs feed the frontend)
- `site/data/` is gitignored — the deploy workflow copies from `data/aggregated/` at build time
- All pipeline modules must be idempotent (safe to re-run)
- Detection changes must add regression tests to `test_known_false_positives.py`
- Backfill is restartable — dedup prevents reprocessing seen records
