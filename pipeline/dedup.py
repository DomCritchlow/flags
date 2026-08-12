"""Deduplication manager — tracks seen record IDs to prevent reprocessing."""

import json
from pathlib import Path
from typing import Optional

from pipeline import config


class DedupIndexError(RuntimeError):
    """Raised when the seen-IDs index exists but cannot be trusted."""


class DedupManager:
    """Manages the seen-records index for deduplication.

    Persists a set of record IDs to JSON. Any record whose ID is already
    in the set is skipped during ingestion.
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = path or config.SEEN_IDS_PATH
        self._ids: set[str] = self._load()

    def _load(self) -> set[str]:
        """Load seen IDs from disk.

        A missing file is the legitimate first-run case and yields an empty
        set. A file that exists but cannot be read or parsed is fatal: it
        would silently defeat deduplication and cause a full re-ingest with
        doubled counts, so abort loudly instead.
        """
        if not self.path.exists():
            return set()

        try:
            raw = self.path.read_text()
        except OSError as exc:
            raise DedupIndexError(
                f"Cannot read dedup index {self.path}: {exc}. "
                "Refusing to continue — an unreadable index would silently "
                "trigger a full re-ingest and duplicate every record."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DedupIndexError(
                f"Dedup index {self.path} is corrupt and could not be parsed: "
                f"{exc}. Refusing to continue — treating it as empty would "
                "silently trigger a full re-ingest and duplicate every record. "
                "Restore the file (e.g. `git checkout -- "
                f"{self.path}`) or delete it deliberately to start fresh."
            ) from exc

        if not isinstance(data, list):
            raise DedupIndexError(
                f"Dedup index {self.path} has unexpected structure: expected a "
                f"JSON array of record IDs, got {type(data).__name__}. "
                "Refusing to continue."
            )

        return set(data)

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
