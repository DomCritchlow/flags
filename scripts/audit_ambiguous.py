"""Audit Tier 2/3 disambiguation decisions.

Reads audit_log.jsonl and summarizes decisions by term. Flags terms
where the default disagrees with the score >20% of the time.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import click

from pipeline import config


@click.command()
@click.option("--month", default=None, help="Filter to a specific month")
@click.option("--term", default=None, help="Filter to a specific term")
@click.option("--limit", default=50, type=int, help="Max entries to show")
def main(month, term, limit):
    """Summarize disambiguation decisions from the audit log."""
    path = config.AUDIT_LOG_PATH
    if not path.exists():
        print("No audit log found. Run the pipeline first.")
        sys.exit(0)

    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if month and not entry.get("record_id", "").startswith(f"crecord-{month}"):
                    # Rough month filter
                    pass
                if term and entry.get("term", "").lower() != term.lower():
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    if not entries:
        print("No matching audit entries found.")
        return

    # Group by term
    by_term = defaultdict(list)
    for e in entries:
        by_term[e.get("key", e.get("term", "unknown"))].append(e)

    print(f"Total audit entries: {len(entries)}")
    print(f"Unique terms: {len(by_term)}")
    print()

    for term_key in sorted(by_term.keys()):
        term_entries = by_term[term_key]
        decisions = Counter(e.get("decision", "UNKNOWN") for e in term_entries)

        print(f"  {term_key}:")
        print(f"    Total: {len(term_entries)}")
        for decision, count in decisions.most_common():
            pct = count / len(term_entries) * 100
            print(f"    {decision}: {count} ({pct:.0f}%)")

        # Flag potential issues
        total = len(term_entries)
        country_count = decisions.get("COUNTRY", 0)
        not_country_count = decisions.get("NOT_COUNTRY", 0)
        if total >= 10:
            minority_pct = min(country_count, not_country_count) / total
            if minority_pct > 0.2:
                print(f"    *** WARNING: {minority_pct:.0%} minority decisions — "
                      f"review default setting ***")
        print()


if __name__ == "__main__":
    main()
