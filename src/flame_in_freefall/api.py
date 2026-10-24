"""Day 2 (BE): the three contract functions, returning MOCK data for now.
Real versions replace the bodies later (summarize on Day 5, get_table Day 9, search Day 10).
The signatures and return shapes must stay exactly as in docs/contract.md."""

import csv
import json
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parents[2] / "data" / "mock"
ALLOWED_FILTERS = {"experiment", "material", "oxygen_min", "oxygen_max"}


def _load_mock_chunks() -> list[dict]:
    lines = (MOCK_DIR / "chunks.mock.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def search(query: str, k: int = 3) -> list[dict]:
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    chunks = _load_mock_chunks()[:k]
    # fake scores, highest first, so the frontend can show a score badge
    return [{**c, "score": round(1.0 - 0.1 * i, 2)} for i, c in enumerate(chunks)]


def summarize(passages: list[dict]) -> dict:
    if not passages:
        return {"takeaways": [], "not_found": True}
    takeaways = [
        {"text": f"(mock) {p['text'][:80]}", "source": p["source"], "chunk_id": p["id"]}
        for p in passages
    ]
    return {"takeaways": takeaways, "not_found": False}


def get_table(filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    unknown = set(filters) - ALLOWED_FILTERS
    if unknown:
        raise ValueError(f"unknown filter(s): {sorted(unknown)}")
    with open(MOCK_DIR / "master.mock.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:  # CSV gives strings; convert numbers
        for col in ("oxygen_pct", "pressure_kpa", "flow_cm_s", "spread_rate_mm_s"):
            row[col] = float(row[col])
    if "experiment" in filters:
        rows = [r for r in rows if r["experiment"] == filters["experiment"]]
    if "material" in filters:
        rows = [r for r in rows if r["material"] == filters["material"]]
    if "oxygen_min" in filters:
        rows = [r for r in rows if r["oxygen_pct"] >= filters["oxygen_min"]]
    if "oxygen_max" in filters:
        rows = [r for r in rows if r["oxygen_pct"] <= filters["oxygen_max"]]
    return rows
