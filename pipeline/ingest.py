"""Congress.gov API ingestion with buffered windows and deduplication.

Pulls records from 7 endpoints (bill, hearing, congressional-record,
committee-report, amendment, nomination, treaty) using a ±N day buffer
around the target month to catch late-published and boundary-week records.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
import requests
from dateutil.relativedelta import relativedelta
from datetime import timedelta

from pipeline import config
from pipeline.dedup import DedupManager

# Maximum records to fetch per endpoint to prevent runaway pagination.
# Congress-scoped endpoints (bill) can have 10-20K records per congress,
# so the cap is per-congress, not per-endpoint overall.
MAX_RECORDS_PER_ENDPOINT = 5000
MAX_RECORDS_PER_CONGRESS = 25000

# Congress sessions: each Congress covers 2 years starting Jan 3 of odd years.
# The 1st Congress started in 1789.
FIRST_CONGRESS_YEAR = 1789

logger = logging.getLogger(__name__)


def congresses_for_date_range(start_date: str, end_date: str) -> list[int]:
    """Return Congress numbers that overlap with [start_date, end_date].

    Each Congress spans Jan 3 of an odd year to Jan 3 two years later.
    Example: 118th Congress = Jan 3, 2023 → Jan 3, 2025.
    """
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])

    congresses = set()
    for year in range(start_year, end_year + 1):
        # Congress number from year: (year - 1789) // 2 + 1
        congress = (year - FIRST_CONGRESS_YEAR) // 2 + 1
        congresses.add(congress)
        # A date in January before the 3rd belongs to the prior Congress
        congresses.add(congress - 1)

    # Filter to reasonable range (93rd Congress / 1973 is the practical floor
    # for meaningful electronic records with titles)
    return sorted(c for c in congresses if c >= 93)


@dataclass
class IngestResult:
    """Result of an ingestion run."""
    new_records: list[dict] = field(default_factory=list)
    months_touched: list[str] = field(default_factory=list)
    skipped_count: int = 0
    error_count: int = 0


def resolve_month(month_str: str) -> str:
    """Resolve a month string to YYYY-MM format.

    Accepts:
    - "previous" or "prev" → last calendar month
    - "YYYY-MM" → as-is
    """
    if month_str.lower() in ("previous", "prev"):
        last_month = datetime.now(timezone.utc).date().replace(day=1) - relativedelta(months=1)
        return last_month.strftime("%Y-%m")
    if month_str.lower() in ("current", "cur"):
        return datetime.now(timezone.utc).date().strftime("%Y-%m")
    # Validate format
    try:
        datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        raise ValueError(
            f"Invalid month format: '{month_str}'. "
            "Use YYYY-MM, 'previous', or 'current'."
        )
    return month_str


def compute_window(target_month: str, buffer_days: int = 5) -> tuple[str, str]:
    """Compute the pull window with buffer days on each side.

    Returns (start_date, end_date) as YYYY-MM-DD strings.
    """
    first_day = datetime.strptime(target_month + "-01", "%Y-%m-%d").date()
    last_day = first_day + relativedelta(months=1) - relativedelta(days=1)

    start = first_day - relativedelta(days=buffer_days)
    end = last_day + relativedelta(days=buffer_days)

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def record_month(date_str: str) -> str:
    """Extract YYYY-MM from a date string for month assignment."""
    if not date_str:
        return ""
    # Handle various date formats
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(date_str[:19], fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            continue
    # Fallback: try just the first 7 characters
    if len(date_str) >= 7:
        return date_str[:7]
    return ""


class CongressIngester:
    """Fetches records from Congress.gov API with buffered windows."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        dedup: Optional[DedupManager] = None,
    ):
        self.api_key = api_key or config.CONGRESS_API_KEY
        if not self.api_key:
            raise ValueError(
                "CONGRESS_API_KEY not set. Get one at "
                "https://api.congress.gov/sign-up/"
            )
        self.dedup = dedup or DedupManager()
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def ingest_month(
        self,
        target_month: str,
        buffer_days: int = config.DEFAULT_BUFFER_DAYS,
        dry_run: bool = False,
    ) -> IngestResult:
        """Pull all records for target_month with ±buffer_days window.

        Returns IngestResult with new records and months touched.
        """
        start_date, end_date = compute_window(target_month, buffer_days)
        run_id = f"monthly-{target_month}"
        now = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Ingesting {target_month} with buffer ±{buffer_days}d: "
            f"{start_date} → {end_date}"
        )

        if dry_run:
            logger.info("DRY RUN — no records will be fetched or saved")
            for endpoint in config.ENDPOINTS:
                logger.info(f"  Would fetch: {endpoint}")
            return IngestResult()

        all_new = []
        months_touched = set()

        # Determine which congresses overlap our date window
        active_congresses = congresses_for_date_range(start_date, end_date)
        logger.info(f"Active congresses for window: {active_congresses}")

        # Endpoints that need congress-scoped queries (list endpoint
        # returns stubs without titles/dates unless scoped to a congress)
        CONGRESS_SCOPED = {"bill", "hearing", "treaty"}

        # Endpoints where fromDateTime/toDateTime don't work or are harmful.
        # Bill: date params filter by *update* date, so historical bills that
        # haven't been updated recently return 0 results. Instead, fetch all
        # bills per congress and post-filter by action date.
        # Treaty: same issue — transmittedDate is the meaningful date but
        # the API filters by updateDate, so we post-filter instead.
        NO_DATE_FILTER = {"bill", "hearing", "congressional-record", "treaty"}

        for endpoint in config.ENDPOINTS:
            try:
                # Congressional Record uses y/m/d params instead
                if endpoint == "congressional-record":
                    raw_records = self._fetch_congressional_record(
                        start_date, end_date
                    )
                # Congress-scoped endpoints (most recent congress first
                # so the hearing enrichment cap captures recent hearings)
                elif endpoint in CONGRESS_SCOPED:
                    raw_records = []
                    for congress_num in reversed(active_congresses):
                        use_dates = endpoint not in NO_DATE_FILTER
                        batch = self._fetch_endpoint(
                            endpoint, start_date, end_date,
                            congress=congress_num,
                            use_date_filter=use_dates,
                        )
                        raw_records.extend(batch)
                        logger.info(
                            f"  {endpoint}/{congress_num}: "
                            f"{len(batch)} fetched"
                        )
                else:
                    raw_records = self._fetch_endpoint(
                        endpoint, start_date, end_date
                    )

                # For hearings, fetch detail pages to get title + date.
                # The list endpoint only returns stubs without titles/dates.
                # Enrichment is capped; date post-filter discards the rest.
                if endpoint == "hearing":
                    raw_records = self._enrich_hearings(raw_records)

                # For treaties, fetch detail pages to get countriesParties
                # and formal titles. Treaties are few (~50-150 per congress)
                # so per-item fetches are cheap.
                if endpoint == "treaty":
                    raw_records = self._enrich_treaties(raw_records)

                normalized = []
                for raw in raw_records:
                    record = self._normalize(raw, endpoint, run_id, now)
                    if record:
                        normalized.append(record)

                # Post-filter: Congress.gov API date params filter by update
                # time, not action date. Discard records outside our window.
                before_filter = len(normalized)
                normalized = self._filter_by_date(
                    normalized, start_date, end_date
                )
                filtered_out = before_filter - len(normalized)
                if filtered_out:
                    logger.info(
                        f"  {endpoint}: filtered {filtered_out} out-of-range "
                        f"records (kept {len(normalized)})"
                    )

                # Dedup
                new_records = [
                    r for r in normalized
                    if not self.dedup.is_seen(r["id"])
                ]

                for r in new_records:
                    month = record_month(r["date"])
                    if month:
                        months_touched.add(month)

                all_new.extend(new_records)
                logger.info(
                    f"  {endpoint}: {len(normalized)} in-range, "
                    f"{len(new_records)} new"
                )

            except Exception as e:
                logger.error(f"  {endpoint}: ERROR — {e}")

        # Persist new records
        if all_new:
            self._save_raw(all_new)
            self.dedup.mark_seen([r["id"] for r in all_new])

        result = IngestResult(
            new_records=all_new,
            months_touched=sorted(months_touched),
        )
        logger.info(
            f"Ingestion complete: {len(all_new)} new records, "
            f"months touched: {result.months_touched}"
        )
        return result

    def _filter_by_date(
        self, records: list[dict], start_date: str, end_date: str
    ) -> list[dict]:
        """Keep only records whose date falls within [start_date, end_date].

        Records without dates are dropped — they can't be assigned to months.
        """
        filtered = []
        no_date = 0
        for r in records:
            date_str = r.get("date", "")
            if not date_str:
                no_date += 1
                continue
            record_date = date_str[:10]  # YYYY-MM-DD
            if start_date <= record_date <= end_date:
                filtered.append(r)
        if no_date:
            logger.debug(f"Dropped {no_date} records with no date")
        return filtered

    def _enrich_hearings(
        self, hearings: list[dict], start_date: str = "",
        end_date: str = "", max_detail_fetches: int = 200,
    ) -> list[dict]:
        """Fetch detail pages for hearings to get title and date.

        The hearing list endpoint only returns chamber/congress/jacket
        and updateDate (which is system update, not hearing date).
        We must hit each detail URL to get the actual hearing date/title.

        Caps at max_detail_fetches to keep run times reasonable.
        The post-filter by date will discard out-of-range hearings.
        """
        enriched = []
        total = min(len(hearings), max_detail_fetches)
        if len(hearings) > max_detail_fetches:
            logger.warning(
                f"  hearing: capping detail fetches at {max_detail_fetches} "
                f"(of {len(hearings)} total)"
            )
            hearings = hearings[:max_detail_fetches]
        for i, h in enumerate(hearings):
            detail_url = h.get("url", "")
            if not detail_url:
                continue

            response = self._request_with_retry(detail_url, {
                "api_key": self.api_key,
                "format": "json",
            })
            if response is None:
                continue

            data = response.json()
            detail = data.get("hearing", {})
            if detail:
                # Merge detail fields into the stub
                h["title"] = detail.get("title", "")
                # dates is a list of {date: "YYYY-MM-DD"} objects
                dates = detail.get("dates", [])
                if dates and isinstance(dates[0], dict):
                    h["date"] = dates[0].get("date", "")
                committees = detail.get("committees", [])
                if committees:
                    h["committee"] = committees[0].get("name", "")
                enriched.append(h)

            if (i + 1) % 50 == 0:
                logger.info(
                    f"  hearing: enriched {i + 1}/{total} detail pages"
                )

        logger.info(
            f"  hearing: enriched {len(enriched)}/{total} "
            f"(skipped {total - len(enriched)} without detail)"
        )
        return enriched

    def _fetch_congressional_record(
        self, start_date: str, end_date: str,
    ) -> list[dict]:
        """Fetch Congressional Record issues using y/m/d params.

        The CR endpoint doesn't support fromDateTime/toDateTime.
        Instead it uses y (year), m (month), d (day) query params.
        We query each day in the window.
        """
        all_records = []
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        current = start
        while current <= end:
            url = f"{config.CONGRESS_API_BASE}/congressional-record"
            params = {
                "api_key": self.api_key,
                "format": "json",
                "y": current.year,
                "m": current.month,
                "d": current.day,
                "limit": 250,
            }
            response = self._request_with_retry(url, params)
            if response is not None:
                data = response.json()
                records = self._extract_records(data, "congressional-record")
                if records:
                    all_records.extend(records)
                    logger.debug(
                        f"  congressional-record {current}: "
                        f"{len(records)} issues"
                    )
            current += timedelta(days=1)

        logger.info(
            f"  congressional-record: {len(all_records)} issues "
            f"across {(end - start).days + 1} days"
        )
        return all_records

    def _fetch_endpoint(
        self, endpoint: str, start_date: str, end_date: str,
        congress: Optional[int] = None,
        use_date_filter: bool = True,
    ) -> list[dict]:
        """Fetch all records from an endpoint within the date range.

        Handles pagination by following 'next' URLs.
        Caps at MAX_RECORDS_PER_ENDPOINT to prevent runaway fetches.
        If congress is provided, scopes the query to that congress number.
        If use_date_filter is False, omits fromDateTime/toDateTime params.
        """
        # Build initial URL (optionally scoped to a congress)
        if congress:
            base_url = f"{config.CONGRESS_API_BASE}/{endpoint}/{congress}"
        else:
            base_url = f"{config.CONGRESS_API_BASE}/{endpoint}"
        params = {
            "api_key": self.api_key,
            "format": "json",
            "limit": 250,
        }
        if use_date_filter:
            params["fromDateTime"] = f"{start_date}T00:00:00Z"
            params["toDateTime"] = f"{end_date}T23:59:59Z"

        all_records = []
        url = base_url
        page = 0

        while url:
            page += 1
            response = self._request_with_retry(url, params if page == 1 else None)
            if response is None:
                break

            data = response.json()

            # Extract records — the key varies by endpoint
            records = self._extract_records(data, endpoint)
            all_records.extend(records)

            # Safety cap to prevent runaway pagination
            cap = MAX_RECORDS_PER_CONGRESS if congress else MAX_RECORDS_PER_ENDPOINT
            if len(all_records) >= cap:
                logger.warning(
                    f"  {endpoint}: hit {cap} record cap "
                    f"at page {page} — stopping pagination"
                )
                break

            # Follow pagination
            url = self._get_next_url(data)
            params = None  # subsequent pages use the full next URL

        return all_records

    def _request_with_retry(
        self, url: str, params: Optional[dict] = None
    ) -> Optional[requests.Response]:
        """Make a request with exponential backoff retry on rate limits."""
        for attempt in range(config.MAX_RETRIES + 1):
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    delay = config.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Rate limited (429). Waiting {delay}s "
                        f"(attempt {attempt + 1}/{config.MAX_RETRIES + 1})"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"HTTP {response.status_code} from {url}: "
                        f"{response.text[:200]}"
                    )
                    return None

            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_BASE_DELAY * (2 ** attempt))
                else:
                    return None

        return None

    def _extract_records(self, data: dict, endpoint: str) -> list[dict]:
        """Extract the records list from an API response.

        Each endpoint nests records under a different key.
        """
        # Map endpoint names to their response keys
        key_map = {
            "bill": "bills",
            "hearing": "hearings",
            "congressional-record": "Results",
            "committee-report": "reports",
            "amendment": "amendments",
            "nomination": "nominations",
            "treaty": "treaties",
        }
        key = key_map.get(endpoint, endpoint + "s")

        # Try primary key, then common alternatives
        if key in data:
            result = data[key]
            if isinstance(result, list):
                return result
            # Congressional Record: Results is a dict with Issues list
            if isinstance(result, dict) and "Issues" in result:
                return result["Issues"]
            return []

        # Congressional Record has nested structure
        if "dailyCongressionalRecord" in data:
            return data["dailyCongressionalRecord"]
        if "results" in data:
            return data["results"] if isinstance(data["results"], list) else []

        # Fallback: look for any list in the response
        for k, v in data.items():
            if isinstance(v, list) and k not in ("request", "pagination"):
                return v

        return []

    def _get_next_url(self, data: dict) -> Optional[str]:
        """Extract the next page URL from the API response."""
        pagination = data.get("pagination", {})
        next_url = pagination.get("next")
        if next_url:
            # Append API key if not present
            if "api_key" not in next_url:
                separator = "&" if "?" in next_url else "?"
                next_url += f"{separator}api_key={self.api_key}"
            return next_url
        return None

    def _normalize(
        self, raw: dict, endpoint: str, run_id: str, now: str
    ) -> Optional[dict]:
        """Normalize a raw API record to the internal schema."""
        try:
            if endpoint == "bill":
                return self._normalize_bill(raw, run_id, now)
            elif endpoint == "hearing":
                return self._normalize_hearing(raw, run_id, now)
            elif endpoint == "congressional-record":
                return self._normalize_crecord(raw, run_id, now)
            elif endpoint == "committee-report":
                return self._normalize_report(raw, run_id, now)
            elif endpoint == "amendment":
                return self._normalize_amendment(raw, run_id, now)
            elif endpoint == "nomination":
                return self._normalize_nomination(raw, run_id, now)
            elif endpoint == "treaty":
                return self._normalize_treaty(raw, run_id, now)
            else:
                return None
        except Exception as e:
            logger.debug(f"Failed to normalize {endpoint} record: {e}")
            return None

    def _normalize_bill(self, raw: dict, run_id: str, now: str) -> Optional[dict]:
        congress = raw.get("congress", "")
        bill_type = raw.get("type", "").lower()
        number = raw.get("number", "")
        if not (congress and number):
            return None

        latest_action = raw.get("latestAction", {})
        date = latest_action.get("actionDate", "")

        return {
            "id": f"bill-{congress}-{bill_type}{number}",
            "source": "bill",
            "congress": congress,
            "date": date,
            "title": raw.get("title", ""),
            "summary": "",  # Summaries require a separate API call
            "committee": "",
            "url": raw.get("url", ""),
            "ingested_at": now,
            "ingested_by": run_id,
        }

    def _normalize_hearing(self, raw: dict, run_id: str, now: str) -> Optional[dict]:
        congress = raw.get("congress", "")
        jacket = raw.get("jacketNumber", raw.get("number", ""))
        chamber = raw.get("chamber", "")
        if not (congress and jacket):
            return None

        return {
            "id": f"hearing-{congress}-{jacket}",
            "source": "hearing",
            "congress": congress,
            "date": raw.get("date", ""),
            "title": raw.get("title", ""),
            "summary": "",
            "committee": raw.get("committee", {}).get("name", "") if isinstance(raw.get("committee"), dict) else "",
            "url": raw.get("url", ""),
            "ingested_at": now,
            "ingested_by": run_id,
        }

    def _normalize_crecord(self, raw: dict, run_id: str, now: str) -> Optional[dict]:
        # Congressional Record daily issues
        # API returns: PublishDate, Issue, Congress, Volume, Session, Links
        issue_date = (
            raw.get("PublishDate", "")
            or raw.get("issueDate", "")
            or raw.get("date", "")
        )
        issue_number = raw.get("Issue", raw.get("issueNumber", ""))
        congress = raw.get("Congress", raw.get("congress", ""))

        if not issue_date:
            return None

        # Build title from section labels in Links
        sections = []
        links = raw.get("Links", {})
        if isinstance(links, dict):
            for section_key in ["Senate", "House", "Digest",
                                "Remarks", "FullRecord"]:
                section = links.get(section_key, {})
                if isinstance(section, dict):
                    label = section.get("Label", "")
                    if label:
                        sections.append(label)

        # Fallback: try old field names
        if not sections:
            for key in ["fullIssue", "dailyDigest", "senate", "house",
                         "extensionsOfRemarks"]:
                section = raw.get(key)
                if isinstance(section, dict):
                    title = section.get("title", "")
                    if title:
                        sections.append(title)
                elif isinstance(section, str):
                    sections.append(section)

        title = " | ".join(sections) if sections else f"Congressional Record Issue {issue_number}"

        date_part = issue_date[:10] if issue_date else ""
        record_id = f"crecord-{date_part}"
        if issue_number:
            record_id = f"crecord-{date_part}-{issue_number}"

        return {
            "id": record_id,
            "source": "crecord",
            "congress": congress,
            "date": date_part,
            "title": title,
            "summary": "",
            "committee": "",
            "url": raw.get("url", ""),
            "ingested_at": now,
            "ingested_by": run_id,
        }

    def _normalize_report(self, raw: dict, run_id: str, now: str) -> Optional[dict]:
        congress = raw.get("congress", "")
        report_type = raw.get("type", "").lower()
        number = raw.get("number", "")
        if not (congress and number):
            return None

        return {
            "id": f"report-{congress}-{report_type}{number}",
            "source": "report",
            "congress": congress,
            "date": raw.get("issueDate", raw.get("date", "")),
            "title": raw.get("title", ""),
            "summary": "",
            "committee": raw.get("committee", {}).get("name", "") if isinstance(raw.get("committee"), dict) else "",
            "url": raw.get("url", ""),
            "ingested_at": now,
            "ingested_by": run_id,
        }

    def _normalize_amendment(self, raw: dict, run_id: str, now: str) -> Optional[dict]:
        congress = raw.get("congress", "")
        amdt_type = raw.get("type", "").lower()
        number = raw.get("number", "")
        if not (congress and number):
            return None

        latest_action = raw.get("latestAction", {})
        date = latest_action.get("actionDate", "")

        return {
            "id": f"amdt-{congress}-{amdt_type}{number}",
            "source": "amendment",
            "congress": congress,
            "date": date,
            "title": raw.get("purpose", raw.get("description", "")),
            "summary": "",
            "committee": "",
            "url": raw.get("url", ""),
            "ingested_at": now,
            "ingested_by": run_id,
        }

    def _normalize_nomination(self, raw: dict, run_id: str, now: str) -> Optional[dict]:
        congress = raw.get("congress", "")
        number = raw.get("number", raw.get("nominationNumber", ""))
        if not (congress and number):
            return None

        latest_action = raw.get("latestAction", {})
        date = latest_action.get("actionDate", "")

        return {
            "id": f"nom-{congress}-{number}",
            "source": "nomination",
            "congress": congress,
            "date": date,
            "title": raw.get("description", raw.get("title", "")),
            "summary": "",
            "committee": raw.get("committee", {}).get("name", "") if isinstance(raw.get("committee"), dict) else "",
            "url": raw.get("url", ""),
            "ingested_at": now,
            "ingested_by": run_id,
        }

    def _normalize_treaty(self, raw: dict, run_id: str, now: str) -> Optional[dict]:
        congress = raw.get("congressReceived", raw.get("congress", ""))
        number = raw.get("number", "")
        if not (congress and number):
            return None

        suffix = (raw.get("suffix") or "").upper()
        record_id = f"treaty-{congress}-{number}{suffix}"

        # Prefer formal treaty title from detail endpoint
        title = ""
        for t in raw.get("titles", []):
            if isinstance(t, dict):
                title = t.get("title", "")
                if title:
                    break

        # Fallback: build from countriesParties + topic
        if not title:
            countries = raw.get("countriesParties", "")
            topic = raw.get("topic", "")
            if countries and topic:
                title = f"{topic} Treaty: {countries}"
            else:
                title = countries or topic

        date = (raw.get("transmittedDate") or raw.get("updateDate") or "")[:10]

        return {
            "id": record_id,
            "source": "treaty",
            "congress": congress,
            "date": date,
            "title": title,
            "summary": "",
            "committee": "",
            "url": raw.get("url", ""),
            "ingested_at": now,
            "ingested_by": run_id,
        }

    def _enrich_treaties(self, raw_records: list[dict]) -> list[dict]:
        """Fetch treaty detail pages to get countriesParties and formal titles.

        Treaties are few (~50-150 per congress) so per-item fetches are cheap.
        The detail endpoint adds: titles (formal treaty name), countriesParties,
        indexTerms, and resolutionText — all high-signal for country detection.
        """
        enriched = []
        for rec in raw_records:
            url = rec.get("url", "")
            if not url:
                enriched.append(rec)
                continue
            detail_url = url
            response = self._request_with_retry(detail_url, {
                "api_key": self.api_key,
                "format": "json",
            })
            if response is None:
                enriched.append(rec)
                continue
            detail = response.json().get("treaty", {})
            # Some treaty endpoints return a list (multi-part treaties)
            if isinstance(detail, list):
                detail = detail[0] if detail else {}
            if isinstance(detail, dict) and detail:
                enriched.append({**rec, **detail})
            else:
                enriched.append(rec)
        logger.info(f"  treaty: enriched {len(enriched)} records with detail pages")
        return enriched

    def _save_raw(self, records: list[dict]) -> None:
        """Append records to raw data files organized by congress."""
        by_congress: dict[str, list[dict]] = {}
        for r in records:
            congress = str(r.get("congress", "unknown"))
            by_congress.setdefault(congress, []).append(r)

        for congress, recs in by_congress.items():
            congress_dir = config.RAW_DIR / congress
            congress_dir.mkdir(parents=True, exist_ok=True)

            # Group by source type
            by_source: dict[str, list[dict]] = {}
            for r in recs:
                source = r["source"]
                by_source.setdefault(source, []).append(r)

            for source, source_recs in by_source.items():
                filename = f"{source}s.jsonl"
                filepath = congress_dir / filename
                with open(filepath, "a") as f:
                    for r in source_recs:
                        f.write(json.dumps(r) + "\n")


# === CLI Entry Point ===

@click.command()
@click.option("--month", default="previous", help="Target month (YYYY-MM or 'previous')")
@click.option("--buffer-days", default=config.DEFAULT_BUFFER_DAYS, type=int,
              help="Buffer days on each side of target month")
@click.option("--dry-run", is_flag=True, help="Print what would happen without fetching")
def main(month: str, buffer_days: int, dry_run: bool):
    """Ingest records from Congress.gov API."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    target = resolve_month(month)
    start, end = compute_window(target, buffer_days)
    print(f"Target month: {target}")
    print(f"Pull window:  {start} → {end}")

    if dry_run:
        print("\nDRY RUN — endpoints that would be fetched:")
        for ep in config.ENDPOINTS:
            print(f"  • {ep}")
        return

    ingester = CongressIngester()
    result = ingester.ingest_month(target, buffer_days)

    print(f"\nResults:")
    print(f"  New records:    {len(result.new_records)}")
    print(f"  Months touched: {result.months_touched}")
    print(f"  Total seen IDs: {ingester.dedup.count}")


if __name__ == "__main__":
    main()
