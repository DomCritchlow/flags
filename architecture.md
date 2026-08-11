# Congressional World View — Architecture Specification

**Project:** Visualize which countries dominate U.S. congressional language over time, inspired by [The Pudding's NYT analysis](https://pudding.cool/2018/12/countries).

**Data source:** Public congressional records via Congress.gov API
**Frontend:** GitHub Pages (static site, flags + timeline)
**Automation:** GitHub Actions (monthly ingestion + rebuild)

---

## Repository Structure

```
congressional-world-view/
├── .github/
│   └── workflows/
│       ├── weekly-ingest.yml           # Monday pull of the current month
│       ├── monthly-ingest.yml          # 3rd-of-month pull of the previous month
│       └── tests.yml                   # pytest + gazetteer validation
│                                       # (no deploy workflow — see "Deploy Model")
│
├── pipeline/                           # Python data pipeline
│   ├── __init__.py
│   ├── config.py                       # API keys, constants, paths
│   ├── ingest.py                       # Congress.gov API fetcher (buffered window)
│   ├── dedup.py                        # Seen-records index manager
│   ├── detector.py                     # Tiered country detection engine
│   ├── gazetteer.py                    # Country term dictionaries
│   ├── disambiguator.py               # Rule-based context disambiguation
│   ├── llm_fallback.py                # Haiku calls for unresolvable cases
│   ├── aggregator.py                  # Monthly rollups and rankings (multi-month aware)
│   └── export.py                       # Write final JSON for frontend
│
├── gazetteers/                         # All lookup data (version-controlled)
│   ├── countries.yaml                  # Master country registry (197 entries)
│   ├── unambiguous_terms.yaml          # Terms that map 1:1 to a country.
│   │                                   #   Demonyms, cities, historical names
│   │                                   #   and acronyms are category keys
│   │                                   #   inside this file, not separate files.
│   ├── ambiguous_terms.yaml            # Terms requiring disambiguation,
│   │                                   #   with their context signal lists
│   └── congressional_blocklist.yaml    # False positive suppressions
│
├── data/                               # Pipeline outputs (committed to repo)
│   ├── raw/                            # Raw API responses by congress/session
│   │   └── 118/
│   │       ├── bills.jsonl
│   │       ├── hearings.jsonl
│   │       └── crecord.jsonl
│   ├── processed/                      # Detection results
│   │   └── mentions.jsonl              # Every detected mention with metadata
│   ├── aggregated/                     # Frontend-ready rollups
│   │   ├── monthly_top.json            # Top country per month
│   │   ├── monthly_all.json            # All country counts per month
│   │   ├── cumulative.json             # All-time rankings
│   │   └── metadata.json               # Last run date, record counts, etc.
│   ├── seen_ids.json                   # Dedup index — all ingested record IDs
│   └── audit_log.jsonl                 # Tier 2/3 decisions for manual review
│
├── docs/                               # GitHub Pages static frontend
│   ├── index.html                      # The data story (grid → rankings → heat map)
│   ├── css/story.css
│   ├── js/
│   │   ├── story-app.js                # Main visualization logic
│   │   ├── flag-grid.js                # Calendar grid renderer
│   │   ├── heat-matrix.js              # Country-by-month heat map
│   │   ├── story-insights.js           # Templated narrative blocks
│   │   └── data-loader.js              # Fetch JSONs from docs/data/
│   ├── data/                           # Copy of data/aggregated/*.json (7 files)
│   ├── bump/index.html                 # Legacy path; meta-refreshes to ../
│   └── flags/                          # SVG flag files (from lipis/flag-icons)
│
├── tests/
│   ├── test_detector.py                # Unit tests for detection pipeline
│   ├── test_disambiguator.py           # Disambiguation edge cases
│   ├── test_known_false_positives.py   # Regression suite
│   ├── test_boundary_weeks.py          # Month-boundary ingestion correctness
│   └── fixtures/                       # Sample congressional text snippets
│
├── scripts/
│   ├── backfill.py                     # One-time historical data pull
│   ├── validate_gazetteers.py          # Check for conflicts/overlaps
│   ├── audit_ambiguous.py             # Surface new ambiguous terms
│   └── audit_boundaries.py            # Verify month-boundary record assignments
│
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Data Sources — Congress.gov API

The [Congress.gov API](https://api.congress.gov) is free, public, and rate-limited to 5,000 requests/hour with an API key. We pull from multiple endpoints to get broad coverage of how Congress talks about the world.

### Endpoints to Ingest

| Endpoint | What it captures | Volume | Country signal strength |
|----------|-----------------|--------|------------------------|
| `/bill` | Bill titles and short summaries | ~15,000/congress | HIGH — titles like "Ukraine Security Assistance Act" are unambiguous |
| `/hearing` | Hearing titles | ~2,000/congress | HIGH — "China's Military Modernization" |
| `/congressional-record` | Daily digest + floor text | ~250 issues/year | HIGHEST volume, MOST ambiguity — floor speeches mention members by state constantly |
| `/committee-report` | Committee report titles | ~1,000/congress | HIGH |
| `/amendment` | Amendment titles/purposes | ~5,000/congress | MEDIUM |
| `/nomination` | Ambassadorial nominations | ~500/congress | HIGH — "Ambassador to the Republic of Kenya" |
| `/treaty` | Treaty titles + `countriesParties` from the detail fetch | ~700 total | HIGH |

**The table above is the original plan. As built, it is wrong in three places** — `ENDPOINTS` in `pipeline/config.py` is the authoritative list, not this document.

`pipeline/ingest.py` implements normalizers for 6 endpoints — bill, hearing, congressional-record, amendment, nomination, treaty — of which **5 are enabled**: `bill`, `congressional-record`, `amendment`, `nomination`, `treaty`. The other two planned endpoints are gone in different ways:

- `/hearing` — implemented but commented out in `config.ENDPOINTS`. Its list response carries no dates or titles, so it would need a detail fetch per hearing. The normalizer survives, so re-enabling it is a config edit plus that fetch.
- `/committee-report` — **removed outright.** Same defect (list payload with neither a title nor an action date, only `updateDate`), so every record normalized to an empty title and was dropped by the date post-filter. It never landed a single record in `data/raw/` across any congress. Its normalizer, `key_map` entry, and dispatch branch have all been deleted; reviving it means writing it again on top of a per-report detail fetch.

And one of the five active endpoints contributes nothing:

- `/congressional-record` — ingested (5,851 issues) but yields **zero** mentions. The API returns daily-issue objects, not floor text, so the only string available to normalize into a title is the section-label list — "Senate Section | House Section | Daily Digest | Extensions of Remarks Section | Entire Issue" — which is identical for nearly every issue and names no countries. Getting floor speeches would mean fetching and parsing the linked full-text documents.

Every mention on the site today therefore comes from `bill`, `treaty`, `nomination`, or `amendment`. Detection also runs on titles alone: no ingested congressional record has a non-empty `summary` field.

### Ingestion Strategy

**Backfill (one-time):** Pull all available historical data. Congress.gov API goes back to the 113th Congress (2013-2014) with good structured data. Older data is spottier but titles are available back to the 93rd (1973). Run this once locally or in a long-running GitHub Action.

**Monthly incremental with overlap window:** Congressional work weeks routinely span month boundaries — a Tuesday-to-Thursday session week might run Jan 28 – Feb 1, and related activity (floor debate on a bill introduced late in the week, amendments filed the next business day, hearing transcripts published days after the hearing) bleeds across the calendar month line. The Congress.gov API also has a known publishing lag of 1–7 days, meaning records dated Jan 30 may not appear in the API until Feb 3–6.

To handle this cleanly, every monthly pull uses a **buffered window with deduplication:**

```
Target month:   February 2024
Pull window:    January 25 → March 5        (±5 day buffer on each side)
Assign to:      Record's actual date field   (each record lands in its true calendar month)
Dedup key:      record.id                    (API-provided unique identifier per record)
```

The pipeline maintains a persistent **seen-records index** (`data/seen_ids.json`) — a set of all record IDs already ingested. On each run:

1. Pull all records in the buffered window from every endpoint
2. Skip any record whose ID is already in `seen_ids.json`
3. Process new records through the detection engine
4. Append new IDs to `seen_ids.json`
5. Re-aggregate all months that were touched (the target month + the buffer months if any new records landed there)

This means a record from Jan 30 that the API publishes late on Feb 4 gets caught by the February run's buffer, correctly assigned to January, and January's aggregation gets updated. The March run's buffer will overlap the same window but the dedup index skips already-processed records instantly.

**Why ±5 days and not ±1 week:** Congress occasionally takes long recesses (August, holidays) where no new records appear for weeks. A 5-day buffer catches the realistic publishing lag and boundary-week bleed without pulling massive redundant windows. For recess periods, the buffer is irrelevant — there's simply nothing new to pull.

**Congressional recess awareness:** Not implemented. The pipeline has no recess calendar and does not special-case recess months — the scheduled runs fire on the same cadence year-round and a near-zero record count during August or the holidays is simply reported as-is. Reading a low count as normal rather than as a failure is currently a human judgement call, not something the pipeline annotates.

### Record Schema (Internal)

Each ingested record is normalized to:

```yaml
record:
  id: "hr-118-1234"               # Unique ID (from Congress.gov API, globally unique)
  source: "bill"                   # bill | hearing | crecord | report | amendment | nomination
  congress: 118                    # Congress number
  date: "2024-03-15"              # Date of action or publication (canonical month assignment)
  title: "Ukraine Security..."    # The text we scan for country mentions
  summary: "A bill to provide..." # Optional longer text (bills have summaries)
  committee: "Foreign Affairs"    # Committee of jurisdiction (valuable metadata)
  url: "https://congress.gov/..." # Link back to source
  ingested_at: "2024-04-03T06:14" # When this record was first pulled (audit trail)
  ingested_by: "monthly-2024-04"  # Which pipeline run pulled it (traceability)
```

---

## Country Detection Engine — The Three Tiers

### Tier 1: Unambiguous Dictionary Match

**What it does:** Single-pass scan of text against a compiled set of terms that map to exactly one country with no possible confusion.

**Implementation:** [Aho-Corasick](https://pypi.org/project/pyahocorasick/) automaton. Build once, scan any text in O(n) time. This is the workhorse — it handles ~190 of ~200 countries with zero ambiguity and zero cost.

**A note on file layout.** An earlier draft of this spec split the lookup data across ten YAML files, giving demonyms, cities, historical names, and acronyms one file each. As built there are four files, and those four categories are *keys inside each country's entry in `unambiguous_terms.yaml`* rather than separate files — `gazetteer.py::_load_unambiguous` walks `["names", "demonyms", "cities", "historical", "acronyms"]` per entry. Context rules for ambiguous terms likewise live alongside the terms they disambiguate in `ambiguous_terms.yaml`, not in a separate rules file.

**The gazetteer (`unambiguous_terms.yaml`) includes:**

```yaml
afghanistan:
  iso3: AFG
  terms:
    names: ["Afghanistan"]
    demonyms: ["Afghan", "Afghani"]
    cities: ["Kabul", "Kandahar"]
    historical: []
    acronyms: []
    leaders: ["Taliban"]  # Context-specific, use carefully

ukraine:
  iso3: UKR
  terms:
    names: ["Ukraine"]
    demonyms: ["Ukrainian"]
    cities: ["Kyiv", "Kiev", "Kharkiv", "Odesa", "Odessa", "Mariupol"]
    historical: []
    acronyms: []

# ... ~190 countries with zero ambiguity
```

**Critical rules for the unambiguous gazetteer:**

1. **Case-sensitive matching** — "China" is a country, "china" (porcelain) is not. But congressional text is usually well-capitalized, so this works in our favor.
2. **Word-boundary enforcement** — "Iran" must not match "Iranian" separately (the demonym has its own entry) or "Desiree Irani" (a name). Use `\b` word boundaries.
3. **Longest-match-first** — "South Korea" must match before "Korea" does. Aho-Corasick handles this natively with proper configuration.
4. **City deduplication** — Only include cities that are globally unambiguous. "Paris" could be Paris, TX. "Berlin" could be Berlin, NH. These go in the ambiguous tier or get excluded. Include only distinctive cities like "Pyongyang", "Addis Ababa", "Ulaanbaatar".

### Tier 2: Rule-Based Contextual Disambiguation

**What it does:** For the ~20 terms that could refer to a country OR something else in congressional text, examines a context window (±50 words) and scores against signal lists.

**The ambiguous terms registry (`ambiguous_terms.yaml`):**

```yaml
georgia:
  country_iso3: GEO
  conflict_type: us_state
  default: STATE           # In Congress, state wins by frequency 50:1
  country_signals:
    strong:                # Any one of these → COUNTRY (score +10)
      - "Republic of Georgia"
      - "Tbilisi"
      - "Caucasus"
      - "Abkhazia"
      - "South Ossetia"
      - "Saakashvili"
      - "Georgian Dream"
      - "Black Sea"
    moderate:              # These lean country but aren't definitive (score +3)
      - "NATO"
      - "Russia"
      - "Soviet"
      - "annexation"
      - "territorial integrity"
  non_country_signals:
    strong:                # Any one of these → NOT COUNTRY (score -10)
      - "Atlanta"
      - "Savannah"
      - "Augusta"
      - "from Georgia"
      - "of Georgia"
      - "gentleman from Georgia"
      - "gentlewoman from Georgia"
      - "Georgia's [0-9]"      # district number
      - "State of Georgia"
    moderate:              # (score -3)
      - "Representative"
      - "Senator"
      - "Governor"
      - "peach"

jordan:
  country_iso3: JOR
  conflict_type: person_name
  default: PERSON
  country_signals:
    strong:
      - "Amman"
      - "Hashemite"
      - "King Abdullah"
      - "King Hussein"
      - "Jordanian"
      - "Kingdom of Jordan"
      - "Dead Sea"
    moderate:
      - "Middle East"
      - "West Bank"
      - "peace process"
      - "bilateral"
  non_country_signals:
    strong:
      - "Jim Jordan"
      - "Mr. Jordan"
      - "Chairman Jordan"
      - "Representative Jordan"
      - "Jordan said"
      - "Jordan asked"
      - "Ohio"
    moderate:
      - "subcommittee"
      - "hearing"
      - "witness"

chad:
  country_iso3: TCD
  conflict_type: person_name
  default: SKIP            # Too ambiguous without signals; don't count
  country_signals:
    strong:
      - "N'Djamena"
      - "Chadian"
      - "Sahel"
      - "Lake Chad"
      - "Republic of Chad"
    moderate:
      - "Africa"
      - "peacekeeping"
      - "Boko Haram"
  non_country_signals:
    strong:
      - "Mr. Chad"
      - "Representative Chad"
      - "Chad [A-Z][a-z]+"    # Chad + surname pattern
    moderate: []

turkey:
  country_iso3: TUR
  conflict_type: common_noun
  default: COUNTRY          # In congressional context, almost always the country
  country_signals:
    strong:
      - "Ankara"
      - "Istanbul"
      - "Turkish"
      - "Erdogan"
      - "NATO"
      - "Kurdistan"
      - "Bosphorus"
      - "Republic of Turkey"
      - "Türkiye"
    moderate:
      - "sanctions"
      - "bilateral"
      - "Mediterranean"
  non_country_signals:
    strong:
      - "Thanksgiving"
      - "turkey hunting"
      - "wild turkey"
      - "turkey season"
    moderate: []

niger:
  country_iso3: NER
  conflict_type: substring
  default: COUNTRY
  notes: >
    Special handling required. "Niger" must not match "Nigeria" (handled by
    longest-match-first). The real risk is the Niger River being mentioned
    in a Nigeria context. Also must never partial-match offensive terms.
    Use strict word-boundary + capitalization enforcement.
  country_signals:
    strong:
      - "Niamey"
      - "Nigerien"          # NOT "Nigerian"
      - "Republic of Niger"
      - "Sahel"
    moderate:
      - "ECOWAS"
      - "coup"
      - "junta"
  non_country_signals:
    strong:
      - "Nigeria"            # If "Nigeria" is in same sentence, this is probably the river
      - "Niger Delta"        # This is Nigeria, not Niger
      - "Niger River"        # Geographic feature, not the country
    moderate: []

colombia:
  country_iso3: COL
  conflict_type: spelling_collision
  default: COUNTRY
  notes: >
    "Colombia" (country) vs "Columbia" (District of, British, university, river).
    Spelling difference makes this tractable. Enforce exact spelling match.
    "Colombia" with an 'o' = always the country. "Columbia" with a 'u' = never the country.
  matching_rule: EXACT_SPELLING
  country_terms: ["Colombia", "Colombian"]
  never_country_terms: ["Columbia", "Columbian", "District of Columbia"]

guinea:
  country_iso3: GIN
  conflict_type: multi_country
  default: SKIP
  notes: >
    "Guinea" alone is ambiguous between Guinea, Equatorial Guinea, Guinea-Bissau,
    and Papua New Guinea. Only count when full name is present.
  require_full_name: true
  full_names:
    - term: "Equatorial Guinea"
      iso3: GNQ
    - term: "Guinea-Bissau"
      iso3: GNB
    - term: "Papua New Guinea"
      iso3: PNG
    - term: "Republic of Guinea"
      iso3: GIN
    - term: "Conakry"           # Capital → Guinea (GIN)
      iso3: GIN
```

**Full ambiguous terms list (all ~20):**

| Term | Conflict Type | Default | Notes |
|------|--------------|---------|-------|
| Georgia | US state | STATE | Highest-frequency conflict in Congress |
| Jordan | Person (Jim Jordan) | PERSON | Modern Congress dominated by Rep. Jordan |
| Chad | Person name | SKIP | Too common as first name |
| Turkey/Türkiye | Common noun | COUNTRY | Almost always the country in Congress |
| Niger | Substring/sensitivity | COUNTRY | Strict boundary matching required |
| Colombia/Columbia | Spelling | EXACT_SPELLING | 'o' = country, 'u' = not country |
| Guinea | Multi-country | SKIP | Require full compound name |
| Marshall | Marshall Islands vs name | SKIP | Require "Marshall Islands" |
| Panama | Panama City, FL | COUNTRY | Rarely the Florida city in Congress |
| Cuba | Person surname (rare) | COUNTRY | Almost always the country |
| Israel | First name (rare) | COUNTRY | Almost always the country |
| Mali | Name/adjective | COUNTRY | Context check for person name |
| Dominica | Dominican Republic confusion | SKIP | Require full name |
| Tonga | Name (rare) | COUNTRY | Almost always the country |
| Samoa | Name (rare) | COUNTRY | Require "American Samoa" vs "Samoa" split |
| Lebanon | Lebanon, PA / Lebanon, TN | COUNTRY | Almost always the country in Congress |
| Cyprus | Botanical (rare) | COUNTRY | Almost always the country |
| Montenegro | No major conflict | COUNTRY | Low ambiguity |
| Congo | DRC vs Republic of Congo | SKIP | Require full name or "Kinshasa"/"Brazzaville" |

**Scoring algorithm:**

```
score = 0
for each word in context_window(±50 words):
    if word matches strong_country_signal:    score += 10
    if word matches moderate_country_signal:  score += 3
    if word matches strong_noncountry_signal: score -= 10
    if word matches moderate_noncountry_signal: score -= 3

if score > 5:       → COUNTRY
elif score < -5:    → NOT COUNTRY
elif default != SKIP: → use DEFAULT
else:               → send to Tier 3
```

### Tier 3: LLM Fallback

**What it does:** For the rare cases (~0.5-1% of all matches) where Tier 2 scoring is inconclusive, sends the context window to an LLM for classification.

**Model:** Claude Haiku (claude-haiku-4-5-20251001) — cheapest, fastest, more than sufficient for binary classification.

**Prompt template:**

```
You are classifying whether a term refers to a country or something else.

Term: "{term}"
Full context: "...{100 words surrounding the match}..."
Source: {bill title | hearing title | floor speech | committee report}

Does "{term}" refer to the country in this context?
Respond with exactly one word: COUNTRY or OTHER
```

**Cost estimate:** At ~$0.25/million input tokens and ~$1.25/million output tokens for Haiku, 10,000 disambiguation calls per month would cost approximately $0.05. Even 100,000 calls would be under $1.

**Caching:** Cache LLM results keyed on `(term, source_id)`. If the same record is reprocessed, skip the LLM call.

**Batching:** Accumulate all Tier 3 cases from a monthly run, send as a single batch via the Anthropic Batch API for 50% cost reduction.

### Tier 0 (Pre-filter): Congressional Blocklist

Before any matching runs, strip known false-positive patterns from the text. This is cheap insurance.

**`congressional_blocklist.yaml`:**

```yaml
# Phrases to remove/mask before country detection runs
blocklist_phrases:
  - "New Jersey"        # Prevents "Jersey" → Jersey (the island)
  - "New Mexico"        # Prevents "Mexico" match inside state name
  - "New Guinea"        # Only match "Papua New Guinea" as compound
  - "West Virginia"     # Prevents "Virginia" double-count
  - "South Carolina"    # Prevents "Carolina" issues
  - "North Carolina"
  - "South Dakota"
  - "North Dakota"
  - "Rhode Island"      # Prevents "Island" interference
  - "Long Island"
  - "Marshall Plan"     # Historical reference, not Marshall Islands
  - "Turkey Creek"      # Geographic feature
  - "Camp David"        # Not a country reference to Israel
  - "District of Columbia"
  - "British Columbia"
  - "Columbia University"
  - "Columbia River"
  - "George Washington" # Prevents matching country "Georgia" from "George"

# Congressional procedural phrases to strip
procedural_strips:
  - "the gentleman from {STATE}"
  - "the gentlewoman from {STATE}"
  - "I yield to the representative from {STATE}"
  - "the Senator from {STATE}"
```

---

## GitHub Actions — Automation

### Monthly Ingestion Workflow

**`.github/workflows/monthly-ingest.yml`:**

```yaml
name: Monthly Country Ingestion

on:
  schedule:
    - cron: '0 6 3 * *'    # 3rd of every month at 06:00 UTC
                             # Why the 3rd: gives Congress.gov API 2-3 days to
                             # publish records from the last days of the previous month.
                             # The ±5 day buffer handles anything published even later.
  workflow_dispatch:          # Manual trigger for backfills/reruns
    inputs:
      target_month:
        description: 'Target month (YYYY-MM), or "previous" for last month'
        required: false
        default: 'previous'

env:
  CONGRESS_API_KEY: ${{ secrets.CONGRESS_API_KEY }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

jobs:
  ingest:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - run: pip install -r requirements.txt

      # Step 1: Pull records using buffered window (target month ±5 days)
      # Deduplicates against data/seen_ids.json automatically.
      # New records are appended to data/raw/ and seen_ids.json is updated.
      - name: Ingest from Congress.gov API
        run: |
          TARGET=${{ github.event.inputs.target_month || 'previous' }}
          python -m pipeline.ingest --month "$TARGET" --buffer-days 5

      # Step 2: Run country detection over the raw corpus.
      # The detector's skip set is the record IDs already present in
      # data/processed/mentions.jsonl — NOT seen_ids.json. It cannot use
      # seen_ids.json: ingest marks IDs seen the moment it writes them, so
      # by the time the detector runs the set of "ingested but unseen" is
      # always empty. Appends to data/processed/mentions.jsonl.
      - name: Detect country mentions
        run: python -m pipeline.detector --incremental

      # Step 3: Reaggregate all months that received new records.
      # A February run with ±5 day buffer may land new records in
      # January, February, and March. All three get reaggregated.
      # This step WRITES NOTHING — it reads mentions.jsonl and prints a
      # summary. Keep it for the log trail, drop it and nothing breaks.
      - name: Aggregate affected months (reporting only)
        run: python -m pipeline.aggregator --touched-months

      # Step 4: Export. THIS is what produces the committable JSON.
      # export.py re-runs the aggregation internally and writes all four
      # files; there is no incremental export.
      - name: Export frontend JSON
        run: python -m pipeline.export

      # Step 5: Copy into the published directory and commit
      - name: Commit data updates
        run: |
          cp data/aggregated/*.json docs/data/
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/ docs/
          git diff --staged --quiet || git commit -m "data: $(date +%Y-%m) monthly ingestion [buffer ±5d]"
          git push
```

The real workflows collapse steps 1–4 into `python -m pipeline.run --month "$TARGET" --buffer-days 5`, which sequences the same four stages in-process. The expanded form above is here to show the data flow, and to make one thing explicit: **`pipeline.export` is the only module in the pipeline that writes files under `data/aggregated/`.** `Aggregator.aggregate_all`, `aggregate_month`, and `aggregate_touched` compute and return dictionaries — they persist nothing.

**Why `--touched-months` matters:** When the February run pulls records with a Jan 25 – Mar 5 window, it may discover late-published January records that the January run missed (due to API lag). Those records get assigned to January by their `date` field. The aggregator reaggregates only the calendar months that received new records. This means January's "top country" can shift retroactively — which is correct behavior. The alternative (freezing months after their run) would systematically undercount the last few days of every month.

The flag does not recompute that set. It reads `last_run_months_touched` from `data/aggregated/metadata.json`, which `pipeline.ingest` computes from the dates of the new records and `pipeline.export` persists. If that file is missing, empty, or corrupt, the CLI prints a message and **exits 0 rather than failing** — deliberate, so a week that ingested nothing doesn't red-X the scheduled job.

**Idempotency guarantee:** Every step is safe to re-run. `ingest` skips records already in `seen_ids.json`. `detector` skips records already in `mentions.jsonl`. `aggregator` rebuilds month-level rollups from the full `mentions.jsonl` each time (cheap — it's just counting). `export` rewrites all four JSON files from scratch. The git commit is a no-op if nothing changed.

One wrinkle in the detector's skip rule: `mentions.jsonl` records only *successful* detections, so a record that matched no country leaves no trace and is rescanned on every incremental run. Incremental means "skip records that already have mentions," not "skip records already scanned." Harmless — detection is pure, and a rescan that finds nothing appends nothing — but it means incremental cost scales with the whole corpus, not just the new records. `python -m pipeline.detector --reprocess` truncates `mentions.jsonl` and rebuilds it; both modes construct a fresh `Gazetteer()`, so both see gazetteer edits, and only `--reprocess` re-scores records that already matched.

### Deploy Model

There is no deploy workflow, no build artifact, and no `github-pages` environment. GitHub Pages is configured as **Deploy from branch → `main` → `/docs`**, so the checked-in contents of `docs/` *are* the published site.

That makes the ingest workflows the whole deploy path. Each one ends with:

```yaml
      - name: Commit data updates
        run: |
          cp data/aggregated/*.json docs/data/
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/ docs/
          git diff --staged --quiet || git commit -m "data: ..."
          # push to main (with rebase-and-retry, see the workflow file)
```

The aggregated JSON is therefore stored twice on purpose: `data/aggregated/` is the pipeline's output, and `docs/data/` is the copy Pages serves. The copy step keeps them in sync; nothing else writes to `docs/data/`.

Two consequences worth remembering:

- **A push to `main` is a deploy.** Editing `docs/` by hand publishes immediately, with no gate.
- **The two ingest workflows share a concurrency group**, because both commit to `main` and the 3rd of the month is sometimes a Monday.

### Secrets Required

| Secret | Source | Purpose |
|--------|--------|---------|
| `CONGRESS_API_KEY` | [api.congress.gov/sign-up](https://api.congress.gov/sign-up/) | Data ingestion (free) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) | Tier 3 LLM fallback (~$0.05/month) |

---

## Frontend — GitHub Pages Static Site

### Data Contract

The frontend consumes four JSON files, served from `docs/data/` (copied verbatim from `data/aggregated/`): `monthly_top.json`, `monthly_all.json`, `monthly_top_by_source.json`, and `metadata.json`. Three further files — `executive_monthly_top.json`, `executive_monthly_all.json`, `executive_metadata.json` — come from the separate executive-orders pipeline and back the Congress-vs-executive comparison.

**`monthly_top.json`** — One entry per month, the "winner":

```json
[
  {
    "month": "2024-03",
    "country_iso3": "UKR",
    "country_name": "Ukraine",
    "mention_count": 847,
    "total_records_scanned": 3421,
    "runner_up_iso3": "ISR",
    "runner_up_count": 612,
    "sample_titles": [
      "Ukraine Security Supplemental Appropriations Act",
      "Hearing: Ukraine's Counteroffensive and the Path Forward"
    ]
  }
]
```

**`monthly_all.json`** — Full breakdown per month (for drill-down):

```json
{
  "2024-03": {
    "total_records": 3421,
    "countries": [
      {"iso3": "UKR", "name": "Ukraine", "count": 847},
      {"iso3": "ISR", "name": "Israel", "count": 612},
      {"iso3": "CHN", "name": "China", "count": 498}
    ]
  }
}
```

**`metadata.json`** — Pipeline health:

```json
{
  "last_run": "2024-04-03T06:12:00Z",
  "last_run_target_month": "2024-03",
  "last_run_pull_window": ["2024-02-25", "2024-04-05"],
  "last_run_new_records": 342,
  "last_run_months_touched": ["2024-02", "2024-03", "2024-04"],
  "total_records_processed": 284100,
  "total_mentions_detected": 891200,
  "congress_range": [93, 118],
  "date_range": ["1973-01", "2024-03"],
  "tier_stats": {
    "tier1_unambiguous": 891005,
    "tier2_ruled": 180,
    "tier3_llm": 15,
    "tier2_skipped": 42
  },
  "month_last_updated": {
    "2024-01": "2024-03-03T06:12:00Z",
    "2024-02": "2024-04-03T06:12:00Z",
    "2024-03": "2024-04-03T06:12:00Z"
  }
}
```

The `month_last_updated` map tracks when each calendar month's aggregation was last recomputed. This is important because boundary-week ingestion means a month's data can be retroactively updated by later runs. The frontend can use this to show a "last updated" indicator, and the audit trail makes it clear which run changed which months.

### Visualization Approach

Mirror The Pudding's concept but adapted for congressional data:

1. **Hero view:** Large flag of the current month's top country, scrollable timeline
2. **Timeline scrubber:** Horizontal scrollable bar showing flag icons by month
3. **Hover/click detail:** Show mention count, sample bill/hearing titles, runner-up
4. **Era annotations:** Mark major geopolitical events (Cold War, Gulf War, 9/11, etc.)
5. **Source breakdown:** Toggle between bill titles only, hearing titles, full Congressional Record

**Flag assets:** Use [lipis/flag-icons](https://github.com/lipis/flag-icons) (SVG, MIT licensed, ISO 3166-1 keyed — matches our `iso3` codes).

**Framework:** Vanilla JS + D3.js for the timeline. No build step needed — keeps GitHub Pages deployment trivial. If you want interactivity beyond what D3 provides, Svelte with a static adapter is a good option that still outputs pure static files.

---

## Edge Cases & Hardening

### Known Traps and Their Solutions

| Trap | Example | Solution |
|------|---------|----------|
| Boundary work weeks | Session runs Jan 28–Feb 1, related records span both months | ±5 day buffer on pull window, assign by record date, dedup by ID |
| Late-published records | Bill introduced Jan 30 doesn't appear in API until Feb 5 | Buffer catches it; January reaggregated retroactively |
| Recess months | August recess — near-zero records is normal, not an error | Unsolved. No recess calendar exists; a low month is reported as-is and has to be read as normal by a human |
| Double-counting from overlap | March run buffer overlaps February run buffer | `seen_ids.json` dedup index prevents any record from being processed twice |
| Month assignment drift | A hearing on Jan 31 has its transcript published dated Feb 3 | Use the API's `date` field (action date), not publication/update timestamp |
| State-in-country-name | "New Mexico" → Mexico | Blocklist pre-filter removes compound state names before scanning |
| Possessive forms | "Ukraine's" → still Ukraine | Regex strips `'s` before matching |
| Plural demonyms | "Ukrainians" → Ukraine | Include plurals in gazetteer |
| Hyphenated compounds | "US-China" → China | Split on hyphens, match components |
| Quoted speech | Member quoting a foreign leader | No special handling needed — still a mention |
| Historical name changes | "Burma" in old records | Historical names map to current ISO3 |
| Country name changes | "Swaziland" → "Eswatini" | Both map to SWZ |
| Multi-country mentions | One title mentions 3 countries | Count each country once per record (not per occurrence) |
| Abbreviations in titles | "PRC" in a bill title | Acronym gazetteer handles this |
| "Korea" alone | North or South? | Require "North Korea"/"South Korea"/"DPRK"/"ROK". Bare "Korea" → SKIP unless "Korean War" (→ both) |

### Quality Assurance

**Regression test suite (`tests/test_known_false_positives.py`):**

Maintain a growing list of real congressional text snippets with known correct answers:

```python
# Each test case is a real snippet from congressional text
KNOWN_CASES = [
    {
        "text": "Mr. Jordan of Ohio asked the witness to clarify",
        "term": "Jordan",
        "expected": "NOT_COUNTRY",
        "source": "crecord-118-2024-03-15"
    },
    {
        "text": "The situation in Georgia following the Russian invasion of South Ossetia",
        "term": "Georgia",
        "expected": "COUNTRY",
        "source": "hearing-110-2008-09"
    },
    {
        "text": "the gentleman from Georgia yields five minutes",
        "term": "Georgia",
        "expected": "NOT_COUNTRY",
        "source": "crecord-117-2022-06-12"
    },
    {
        "text": "Providing assistance to Colombia to combat narcotics trafficking",
        "term": "Colombia",
        "expected": "COUNTRY",
        "source": "bill-107-hr3421"
    },
    {
        "text": "the District of Columbia Statehood Act",
        "term": "Columbia",
        "expected": "NOT_COUNTRY",
        "source": "bill-117-hr51"
    },
]
```

**Boundary-week ingestion tests (`tests/test_boundary_weeks.py`):**

Separate test suite validating that the buffered-window ingestion handles month boundaries correctly:

```python
BOUNDARY_TESTS = [
    {
        "name": "Record dated last day of month lands in correct month",
        "record_date": "2024-01-31",
        "ingested_during_run": "2024-02",     # February run's buffer catches it
        "expected_month_assignment": "2024-01", # But it belongs to January
    },
    {
        "name": "Record already seen is not reprocessed",
        "record_id": "hr-118-5678",
        "first_ingested_by": "2024-01",
        "second_run": "2024-02",               # Buffer overlaps
        "expected_reprocessed": False,          # Dedup index blocks it
    },
    {
        "name": "Late-published record triggers reaggregation of prior month",
        "record_date": "2024-01-30",
        "api_available_date": "2024-02-05",    # API lag
        "ingested_during_run": "2024-02",
        "expected_months_reaggregated": ["2024-01", "2024-02"],
    },
    {
        "name": "Idempotent run produces no changes",
        "run_month": "2024-02",
        "run_count": 2,                         # Same month run twice
        "expected_new_records_second_run": 0,
        "expected_git_diff": False,             # Nothing to commit
    },
]
```

**Monthly audit job:** After each ingestion, output a `audit_log.jsonl` with every Tier 2 and Tier 3 decision. Periodically review these to find new patterns and harden the rules.

**New-term discovery:** Run a script that scans for any capitalized proper nouns in congressional text that appear frequently but aren't in any gazetteer. This catches emerging terms (new country names, new prominent figures who share country names).

---

## Cost Summary

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| Congress.gov API | $0 | Free, 5,000 req/hr. Buffer window adds ~30% more calls vs. exact-month pull, still well under limit (~260 calls/month) |
| GitHub Actions | $0 | Free tier covers ~2,000 min/month; this pipeline uses ~10-15 min (slightly more for reaggregation of touched months) |
| GitHub Pages | $0 | Free for public repos |
| Anthropic API (Tier 3) | ~$0.05 | Haiku, <1,000 calls/month |
| Flag icons | $0 | MIT licensed |
| **Total** | **~$0.05/month** | |

---

## Implementation Sequence

### Phase 1 — Gazetteer + Detection Engine (Week 1)
Build and validate `countries.yaml`, `unambiguous_terms.yaml`, and `ambiguous_terms.yaml`. Write `detector.py` and `disambiguator.py`. Achieve >99% accuracy on a hand-labeled test set of 500 congressional text snippets.

### Phase 2 — Congress.gov Ingestion + Dedup Engine (Week 1-2)
Build `ingest.py` with buffered window support and `dedup.py` with the seen-records index. Run backfill for Congresses 113-118 (2013-present) as the initial dataset. **Critical validation:** manually check 3-4 month boundaries (pick months where Congress was in session right up to the 31st) and verify that records from boundary work weeks land in the correct calendar month and aren't double-counted. Verify that a second run of the same month produces zero new records (idempotency).

### Phase 3 — Aggregation + Export (Week 2)
Build `aggregator.py` and `export.py`. Generate the three frontend JSON files. Validate against The Pudding's known results for overlapping time periods (sanity check — they used NYT, you'll use Congress, but the top countries should roughly correlate).

### Phase 4 — Frontend (Week 2-3)
Build the static site. Start with a minimal flag + timeline view. Iterate on interactivity. Deploy to GitHub Pages.

### Phase 5 — Automation (Week 3)
Configure GitHub Actions workflows. Test with a manual trigger using `workflow_dispatch` with an explicit `target_month`. Verify the full loop: ingest (with buffer) → dedup → detect → reaggregate touched months → commit → deploy. Run it twice for the same month and confirm idempotency (second run commits nothing). Then run for the *next* month and confirm that the overlap window correctly catches any late-published records from the previous month and reaggregates it.

### Phase 6 — Hardening (Ongoing)
Grow the regression test suite. Review monthly audit logs. Add disambiguation rules as new edge cases surface. Consider expanding to earlier Congresses as data quality allows.
