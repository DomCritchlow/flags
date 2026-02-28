"""Deduplication manager — tracks seen record IDs to prevent reprocessing."""

import json
from pathlib import Path
from typing import Optional

from pipeline import config


class DedupManager:
    """Manages the seen-records index for deduplication.

    Persists a set of record IDs to JSON. Any record whose ID is already
    in the set is skipped during ingestion.
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = path or config.SEEN_IDS_PATH
        self._ids: set[str] = self._load()

    def _load(self) -> set[str]:
        """Load seen IDs from disk."""
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                return set(data)
            except (json.JSONDecodeError, OSError):
                return set()
        return set()

    def is_seen(self, record_id: str) -> bool:
        """Check if a record ID has already been processed."""
        return record_id in self._ids

    def mark_seen(self, record_ids: list[str]) -> None:
        """Add record IDs to the seen set and persist to disk."""
        if not record_ids:
            return
        self._ids.update(record_ids)
        self._save()

    def _save(self) -> None:
        """Write the seen IDs to disk as a sorted JSON array."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(sorted(self._ids), indent=2))

    @property
    def count(self) -> int:
        """Number of seen record IDs."""
        return len(self._ids)

    def contains(self, record_id: str) -> bool:
        """Alias for is_seen (used by CLI)."""
        return self.is_seen(record_id)

    def status(self) -> dict:
        """Return status information about the dedup index."""
        return {
            "total_ids": self.count,
            "path": str(self.path),
            "exists": self.path.exists(),
        }
