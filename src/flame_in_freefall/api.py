"""Day 2 (BE): the three contract functions, returning MOCK data for now.
Real versions replace the bodies later (summarize on Day 5, get_table Day 9, search Day 10).
The signatures and return shapes must stay exactly as in docs/contract.md.
Day 5 (BE): summarize is real now; the Gemini work lives in summarizer.py."""

import csv
import json
from pathlib import Path

from flame_in_freefall.summarizer import summarize_passages

# Build the path from this file's own location (up 2 folders = repo root),
# so it works no matter which folder the app is started from.
MOCK_DIR = Path(__file__).resolve().parents[2] / "data" / "mock"
# The only filter keys the contract allows; get_table() rejects anything else.
ALLOWED_FILTERS = {"experiment", "material", "oxygen_min", "oxygen_max"}


def _load_mock_chunks() -> list[dict]:
    # JSONL = one JSON object per line; skip blank lines so a trailing newline can't break it.
    lines = (MOCK_DIR / "chunks.mock.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def search(query: str, k: int = 3) -> list[dict]:
    # Fail loudly on a blank question instead of running an empty search.
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    chunks = _load_mock_chunks()[:k]
    # fake scores, highest first, so the frontend can show a score badge
    return [{**c, "score": round(1.0 - 0.1 * i, 2)} for i, c in enumerate(chunks)]


def summarize(passages: list[dict]) -> dict:
    # Thin wrapper: the contract signature stays here, the Gemini call lives in summarizer.py.
    return summarize_passages(passages)


def get_table(filters: dict | None = None) -> list[dict]:
    filters = filters or {}  # None means "no filters"
    # Reject typos like "colour" instead of silently returning the whole table.
    unknown = set(filters) - ALLOWED_FILTERS
    if unknown:
        raise ValueError(f"unknown filter(s): {sorted(unknown)}")
    with open(MOCK_DIR / "master.mock.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:  # CSV gives strings; convert numbers
        for col in ("oxygen_pct", "pressure_kpa", "flow_cm_s", "spread_rate_mm_s"):
            row[col] = float(row[col])
    # Each filter that was given narrows the rows further; missing ones are skipped.
    if "experiment" in filters:
        rows = [r for r in rows if r["experiment"] == filters["experiment"]]
    if "material" in filters:
        rows = [r for r in rows if r["material"] == filters["material"]]
    if "oxygen_min" in filters:
        rows = [r for r in rows if r["oxygen_pct"] >= filters["oxygen_min"]]
    if "oxygen_max" in filters:
        rows = [r for r in rows if r["oxygen_pct"] <= filters["oxygen_max"]]
    return rows
