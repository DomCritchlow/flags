"""Pipeline configuration — paths, API keys, constants."""

import os
from pathlib import Path

# Load .env file if present (local development)
PROJECT_ROOT = Path(__file__).parent.parent
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
AGGREGATED_DIR = DATA_DIR / "aggregated"
GAZETTEER_DIR = PROJECT_ROOT / "gazetteers"

# Pipeline state files
SEEN_IDS_PATH = DATA_DIR / "seen_ids.json"
AUDIT_LOG_PATH = DATA_DIR / "audit_log.jsonl"
MENTIONS_PATH = PROCESSED_DIR / "mentions.jsonl"
LLM_CACHE_PATH = DATA_DIR / "llm_cache.json"

# API credentials (from environment)
CONGRESS_API_KEY = os.environ.get("CONGRESS_API_KEY", "")
CONGRESS_API_BASE = "https://api.congress.gov/v3"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Ingestion settings
DEFAULT_BUFFER_DAYS = 5
ENDPOINTS = [
    "bill",
    # "hearing",  # Disabled: list endpoint lacks dates/titles, requiring
    #              # expensive per-hearing detail fetches. TODO: re-enable
    #              # with smarter date-based strategy.
    "congressional-record",
    "committee-report",
    "amendment",
    "nomination",
    "treaty",  # congress-scoped; detail fetch adds countriesParties + formal titles
]

# Detection settings
CONTEXT_WINDOW_WORDS = 50
DISAMBIGUATION_THRESHOLD_COUNTRY = 5
DISAMBIGUATION_THRESHOLD_NOT_COUNTRY = -5
SIGNAL_WEIGHT_STRONG = 10
SIGNAL_WEIGHT_MODERATE = 3

# LLM fallback
LLM_MODEL = "claude-haiku-4-5-20251001"

# Rate limiting
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds, exponential backoff
REQUESTS_PER_HOUR = 5000
