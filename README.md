# Congressional World View

Which countries dominate U.S. congressional language? This project tracks every country mention across bills, nominations, amendments, and congressional records — then visualizes the results as a newspaper-style flag grid and interactive bump chart.

Inspired by [The Pudding's NYT country analysis](https://pudding.cool/2018/12/countries).

---

## Live Site

**[View the visualization →](http://critchlow.us/flags/)**

The main page shows a calendar grid: 12 month columns, one row per year, each cell displaying the flag of whichever country led congressional mentions that month. Filter by source type (bills, nominations, amendments) using the toggle bar. Tap any cell for details.

The [Data Story](/bump/) digs deeper: all-time rankings, session-by-session era cards, crisis moment timeline, and a full country-by-month heat map.

## How It Works

```
Congress.gov API → Ingest → Detect → Aggregate → Export → GitHub Pages
```

1. **Ingest** — Pulls records from Congress.gov across 5 endpoints (bill, congressional-record, committee-report, amendment, nomination) with buffered date windows to catch boundary records.

2. **Detect** — Three-tier country detection engine:
   - **Tier 1**: Aho-Corasick dictionary matching against ~200 country gazetteers
   - **Tier 2**: Contextual disambiguation (e.g., "Georgia" the state vs. the country)
   - **Tier 3**: LLM fallback for edge cases (~$0.05/month)

3. **Aggregate** — Counts unique countries per record per month, ranks them, breaks down by source type.

4. **Export** — Produces static JSON files consumed by the frontend.

5. **Deploy** — Committed `docs/` directory is served via GitHub Pages branch deploy on every push.

## Data Coverage

- **Date range**: January 1973 – present (93rd–119th Congress, fully backfilled)
- **Records processed**: ~340,000
- **Country mentions detected**: ~20,700
- **Source types**: Bills, nominations, amendments, congressional records
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
PYTHONPATH=. python -m pipeline.detector --incremental [--reprocess]
PYTHONPATH=. python -m pipeline.aggregator --touched-months [--month 2024-02] [--all]
PYTHONPATH=. python -m pipeline.export [--month 2024-02] [--all]

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
│   ├── gazetteer.py    # Country lookup data loader
│   └── config.py       # Paths, API keys, constants
├── gazetteers/         # YAML country data (~200 countries)
├── data/               # Pipeline outputs (committed)
│   ├── raw/            # JSONL records by congress
│   ├── processed/      # mentions.jsonl
│   └── aggregated/     # Frontend JSON files
├── docs/               # Static frontend (GitHub Pages — branch deploy)
│   ├── index.html      # Flag grid data story
│   ├── css/story.css   # Newspaper theme
│   ├── js/             # Grid renderer, insights, data loader
│   ├── bump/           # Bump chart subsite
│   ├── data/           # Aggregated JSON files (copied from data/aggregated/)
│   └── flags/          # SVG flag images
├── scripts/            # Backfill, validation, auditing
├── tests/              # 128 tests
└── .github/workflows/  # Weekly + monthly ingestion, deploy, tests
```

## Automation

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `weekly-ingest.yml` | Mondays 06:00 UTC | Ingests current month's data, commits updates |
| `monthly-ingest.yml` | 3rd of month 06:00 UTC | Full previous-month ingestion with ±5 day buffer |
| `tests.yml` | On push to pipeline/tests | Runs 128 tests + gazetteer validation |

## License

MIT

