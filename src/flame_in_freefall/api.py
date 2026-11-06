"""Day 2 (BE): the three contract functions, first returning MOCK data.
Real versions replaced the bodies later (summarize on Day 5, get_table Day 9, search Day 10).
The signatures and return shapes must stay exactly as in docs/contract.md.
Day 5 (BE): summarize is real now; the Gemini work lives in summarizer.py.
Day 9 (BE): get_table is real now; it reads data/master.csv (built by the data role).
Day 10 (BE): search is real now; it ranks the report chunks with retrieval.find_passages."""

import threading
from pathlib import Path

import pandas as pd

from flame_in_freefall import ingest
from flame_in_freefall.retrieval import find_passages
from flame_in_freefall.store import _paths
from flame_in_freefall.summarizer import summarize_passages

# Build the paths from this file's own location (up 2 folders = repo root),
# so they work no matter which folder the app is started from.
MASTER_CSV = Path(__file__).resolve().parents[2] / "data" / "master.csv"
CHUNKS = ingest.CHUNKS  # data/processed/chunks.jsonl (committed)
INDEX = ingest.INDEX  # artifacts/index/ (git-ignored, so the live app starts without it)
# The only filter keys the contract allows; get_table() rejects anything else.
TEXT_FILTERS = {"experiment", "material", "material_category"}
NUMBER_FILTERS = {"oxygen_min", "oxygen_max"}
ALLOWED_FILTERS = TEXT_FILTERS | NUMBER_FILTERS

# Two people searching at the same moment must not both build the index (Streamlit runs
# each visitor in its own thread).
_index_lock = threading.Lock()


def _ensure_index() -> None:
    # Missing (a fresh deploy) or older than chunks.jsonl: embed the committed chunks once
    # (~10 s, plus a one-time model download). Later searches find it fresh and skip this.
    with _index_lock:
        if not ingest._is_fresh(list(_paths(INDEX)), [CHUNKS]):
            ingest.build_index(CHUNKS, INDEX)


def search(query: str, k: int = 5) -> list[dict]:  # contract v1.1: default 5 (was 3)
    # Fail loudly on a blank question instead of running an empty search.
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    _ensure_index()
    # {id, text, source, page, score} best first, plus each chunk's experiment (Day 12).
    return find_passages(query, k, folder=INDEX)


def summarize(passages: list[dict]) -> dict:
    # Thin wrapper: the contract signature stays here, the Gemini call lives in summarizer.py.
    return summarize_passages(passages)


def _check_filters(filters: dict) -> None:
    # Reject typos like "colour" instead of silently returning the whole table.
    unknown = set(filters) - ALLOWED_FILTERS
    if unknown:
        raise ValueError(f"unknown filter(s): {sorted(unknown)}")
    for key in TEXT_FILTERS & set(filters):
        if not isinstance(filters[key], str) or not filters[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    for key in NUMBER_FILTERS & set(filters):
        # bool is a kind of int in Python, so True would pass as 1 without this check.
        if isinstance(filters[key], bool) or not isinstance(filters[key], int | float):
            raise ValueError(f"{key} must be a number")
    if filters.get("oxygen_min", 0) > filters.get("oxygen_max", 100):
        raise ValueError("oxygen_min must not be larger than oxygen_max")


def get_table(filters: dict | None = None) -> list[dict]:
    filters = filters or {}  # None means "no filters"
    _check_filters(filters)
    table = pd.read_csv(MASTER_CSV)
    # Each filter that was given narrows the rows further; missing ones are skipped.
    for key in TEXT_FILTERS & set(filters):
        table = table[table[key] == filters[key]]
    # Oxygen is a range per row (FLEX-2 tested 17-30 %). A row matches when its range
    # overlaps the filter's range, so a test that covered the chosen oxygen level isn't hidden.
    if "oxygen_min" in filters:
        table = table[table["oxygen_pct_max"] >= filters["oxygen_min"]]
    if "oxygen_max" in filters:
        table = table[table["oxygen_pct_min"] <= filters["oxygen_max"]]
    # Empty cells (e.g. no pressure for Saffire-II) come back as None, not NaN, so callers
    # can test "is None" and the rows turn into JSON cleanly.
    table = table.astype(object).where(table.notna(), None)
    return table.to_dict(orient="records")
