# Congressional World View

Visualize which countries dominate U.S. congressional language over time.
Inspired by [The Pudding's NYT analysis](https://pudding.cool/2018/12/countries).

## Quick Start

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## CLI Reference

```bash
# Full pipeline (what GitHub Actions runs monthly)
python -m pipeline.run --month 2024-02 --buffer-days 5

# Individual stages
python -m pipeline.ingest --month 2024-02 --buffer-days 5 [--dry-run]
python -m pipeline.detector --incremental [--reprocess]
python -m pipeline.aggregator --touched-months [--month 2024-02] [--all]
python -m pipeline.export [--month 2024-02] [--all]

# Backfill historical data (run locally, ~6 hours for full 1973-2024 range)
python -m scripts.backfill [--congress-start 93] [--congress-end 118] [--dry-run]

# Validation and audit
python -m scripts.validate_gazetteers
python -m scripts.audit_ambiguous --month 2024-02
python -m scripts.audit_boundaries --month 2024-02
```

## Environment Variables

- `CONGRESS_API_KEY` — from https://api.congress.gov/sign-up/ (free)
- `ANTHROPIC_API_KEY` — for Tier 3 LLM fallback (~$0.05/month)

## Architecture

See `architecture.md` for the full specification. Key modules:

- `pipeline/` — Python data pipeline (ingest, detect, aggregate, export)
- `gazetteers/` — YAML lookup data for ~200 countries
- `data/` — Pipeline outputs (committed to repo, consumed by frontend)
- `site/` — GitHub Pages static frontend (flag grid + bump chart at `/bump/`)
- `.github/workflows/` — Monthly ingestion cron + auto-deploy

## Testing

```bash
pytest tests/ -v                          # All tests
pytest tests/test_detector.py -v          # Detection engine
pytest tests/test_known_false_positives.py -v  # Regression suite
pytest tests/ -v --cov=pipeline           # With coverage
```

## Rules

- Never commit `.env` or API keys
- `data/` is committed (pipeline outputs feed the frontend)
- All pipeline modules must be idempotent (safe to re-run)
- Detection changes must add regression tests to `test_known_false_positives.py`
