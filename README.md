# Congressional World View

Which countries dominate U.S. congressional language? This project tracks every country mention across bill, treaty, nomination, and amendment titles — then visualizes the results as a newspaper-style data story built around a flag grid.

Inspired by [The Pudding's NYT country analysis](https://pudding.cool/2018/12/countries).

---

## Live Site

**[View the visualization →](https://critchlow.us/flags/)**

The main page is a single scrolling data story. It opens with a calendar grid — 12 month columns, one row per year, each cell displaying the flag of whichever country led congressional mentions that month. Tap any cell for details.

Scroll on for all-time rankings, a crisis-moment timeline, era-by-era narrative cards, a Congress-vs-executive-orders comparison, and a full country-by-month heat map. (`docs/bump/` is a legacy path — its `index.html` now just redirects to the main page.)

## How It Works

```
Congress.gov API → Ingest → Detect → Aggregate → Export → GitHub Pages
```

1. **Ingest** — Pulls records from the 5 endpoints in `pipeline/config.py` (`ENDPOINTS`) with buffered date windows to catch boundary records. Four supply the mentions you see on the site: `bill`, `treaty`, `nomination`, `amendment`. The fifth, `congressional-record`, is ingested but has never produced a single country mention: the API returns daily *issue* objects rather than floor text, so the only string available to normalize into a title is the section-label list ("Senate Section | House Section | Daily Digest…"), which is near-identical for every issue and names no countries.

   `pipeline/ingest.py` implements normalizers for 6 endpoints — bill, hearing, congressional-record, amendment, nomination, treaty — of which those 5 are enabled. `hearing` is implemented but commented out in `config.ENDPOINTS`. `committee-report` was removed outright: same defect as `hearing` (a list payload with neither title nor action date), but unlike `hearing` its normalizer is gone too.

2. **Detect** — Three-tier country detection engine:
   - **Tier 1**: Aho-Corasick dictionary matching against ~200 country gazetteers
   - **Tier 2**: Contextual disambiguation (e.g., "Georgia" the state vs. the country)
   - **Tier 3**: LLM fallback for edge cases (~$0.05/month)

3. **Aggregate** — Counts unique countries per record per month, ranks them, breaks down by source type. Aggregation is pure computation — it returns rankings and persists nothing.

4. **Export** — Produces static JSON files consumed by the frontend: `monthly_top.json`, `monthly_all.json`, `monthly_top_by_source.json`, and `metadata.json` (plus three `executive_*.json` files from `pipeline/export_executive.py`).

5. **Deploy** — There is no build or deploy job. GitHub Pages is configured to serve the `docs/` directory straight off `main`; the ingest workflows copy `data/aggregated/*.json` into `docs/data/` and commit, and the push is the deploy.

## Data Coverage

- **Date range**: January 1973 – present (93rd–119th Congress, fully backfilled)
- **Records ingested**: ~370,000 congressional records (369,980 distinct IDs across `data/raw/`; the `data/seen_ids.json` dedup index holds ~371,500 entries, which also covers executive orders)
- **Records containing a country mention**: 17,702 — this is the number `data/aggregated/metadata.json` reports as `total_records_processed`, so read that field as "records with at least one mention," not "records ingested"
- **Country mentions detected**: 20,248 unique country-per-record pairs (`total_mentions_detected`), from 20,758 raw rows in `data/processed/mentions.jsonl`
- **Source types with mentions**: bills (20,354), treaties (158), nominations (144), amendments (102)
- **Update frequency**: Weekly (Mondays) + monthly (3rd of each month)

## Quick Start

```bash
# Clone and install
git clone https://github.com/DomCritchlow/flags.git
cd flags
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Set API keys
cp .env.example .env  # Then edit with your keys
# CONGRESS_API_KEY from https://api.congress.gov/sign-up/ (free)
# ANTHROPIC_API_KEY for Tier 3 LLM fallback (optional, ~$0.05/month)

# Run tests
pytest tests/ -v

# Run the pipeline for a specific month
PYTHONPATH=. python -m pipeline.run --month 2024-12 --buffer-days 5

# Preview the site
cd docs && python -m http.server 8000
```

## CLI Reference

```bash
# Full pipeline (what GitHub Actions runs)
PYTHONPATH=. python -m pipeline.run --month 2024-02 --buffer-days 5

# Individual stages
PYTHONPATH=. python -m pipeline.ingest --month 2024-02 --buffer-days 5 [--dry-run]

# Detection. --incremental is the default; --reprocess rebuilds mentions.jsonl
# from scratch (use it after a gazetteer change). --enable-llm is off by default.
PYTHONPATH=. python -m pipeline.detector [--incremental | --reprocess] [--enable-llm] [--dry-run]

# Aggregation only computes and prints — pipeline.export is what writes the JSON.
PYTHONPATH=. python -m pipeline.aggregator --touched-months [--month 2024-02] [--all]
PYTHONPATH=. python -m pipeline.export [--output-dir DIR]

# Executive-order side pipeline (run by the same workflows)
PYTHONPATH=. python -m scripts.ingest_executive_orders
PYTHONPATH=. python -m scripts.reprocess_executive
PYTHONPATH=. python -m pipeline.export_executive

# Validation
PYTHONPATH=. python -m scripts.validate_gazetteers
PYTHONPATH=. python -m scripts.audit_ambiguous --month 2024-02
```

## Project Structure

```
flags/
├── pipeline/           # Python data pipeline
│   ├── run.py          # Full pipeline orchestrator
│   ├── ingest.py       # Congress.gov API client
│   ├── detector.py     # Country detection engine
│   ├── aggregator.py   # Monthly rollup + source breakdown
│   ├── export.py       # JSON export for frontend
│   ├── export_executive.py  # JSON export for the executive-orders view
│   ├── gazetteer.py    # Country lookup data loader
│   └── config.py       # Paths, API keys, constants
├── gazetteers/         # YAML country data (~200 countries)
├── data/               # Pipeline outputs (committed)
│   ├── raw/            # JSONL records by congress
│   ├── processed/      # mentions.jsonl
│   └── aggregated/     # Frontend JSON files
├── docs/               # Static frontend, served directly off main by GitHub Pages
│   ├── index.html      # The whole data story — grid, rankings, eras, heat map
│   ├── css/story.css   # Newspaper theme
│   ├── js/             # Grid renderer, heat matrix, insights, data loader
│   ├── bump/           # Legacy path; index.html redirects to the main page
│   ├── data/           # Aggregated JSON files (copied from data/aggregated/)
│   └── flags/          # SVG flag images
├── scripts/            # Backfill, validation, auditing, executive-order pipeline
├── tests/              # 197 tests
└── .github/workflows/  # Weekly + monthly ingestion, tests
```

## Automation

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `weekly-ingest.yml` | Mondays 06:00 UTC | Current-month ingestion (±3 day buffer) + executive orders; copies JSON into `docs/data/` and commits |
| `monthly-ingest.yml` | 3rd of month 06:00 UTC | Previous-month ingestion (±5 day buffer); same copy-and-commit step |
| `tests.yml` | On push/PR touching `pipeline/`, `scripts/`, `gazetteers/`, `tests/`, or the dependency pins | Runs 197 tests + gazetteer validation |

There is no separate deploy workflow — the commit from an ingest run *is* the deploy, because Pages serves `docs/` from `main`.

## License

MIT

