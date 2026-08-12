"""Raw-record iteration for scripts/audit_boundaries.

Executive orders live under data/raw/executive_orders/ and have no
congressional month-boundary semantics, so the boundary audit must skip them.
"""

import json

from scripts.audit_boundaries import iter_raw_records


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))


def _make_raw_tree(root):
    _write_jsonl(
        root / "118" / "bill.jsonl",
        [{"id": "bill-118-hr-1", "date": "2024-02-01"}],
    )
    _write_jsonl(
        root / "119" / "amendment.jsonl",
        [{"id": "amdt-119-hamdt-2", "date": "2025-03-31"}],
    )
    _write_jsonl(
        root / "executive_orders" / "eos.jsonl",
        [{"id": "eo-14100", "date": "2024-02-02"}],
    )


class TestIterRawRecords:
    def test_excludes_executive_orders(self, tmp_path):
        _make_raw_tree(tmp_path)

        ids = [r["id"] for r in iter_raw_records(tmp_path)]

        assert "eo-14100" not in ids
        assert set(ids) == {"bill-118-hr-1", "amdt-119-hamdt-2"}

    def test_skips_malformed_lines(self, tmp_path):
        path = tmp_path / "118" / "bill.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(
            '{"id": "bill-118-hr-1"}\n'
            "\n"
            "{not json}\n"
            '{"id": "bill-118-hr-2"}\n'
        )

        ids = [r["id"] for r in iter_raw_records(tmp_path)]

        assert ids == ["bill-118-hr-1", "bill-118-hr-2"]

    def test_empty_tree(self, tmp_path):
        assert list(iter_raw_records(tmp_path)) == []
