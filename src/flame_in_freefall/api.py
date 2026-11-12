"""Day 2 (BE): the three contract functions, first returning MOCK data.
Real versions replaced the bodies later (summarize on Day 5, get_table Day 9, search Day 10).
The signatures and return shapes must stay exactly as in docs/contract.md.
Day 5 (BE): summarize is real now; the Gemini work lives in summarizer.py.
Day 9 (BE): get_table is real now; it reads data/master.csv (built by the data role).
Day 10 (BE): search is real now; it ranks the report chunks with retrieval.find_passages.
Day 11 (BE): every call is timed (speed.py), and repeated questions come from memory.
Day 15 (BE): summarize() checks its own answer against the contract before handing it out.
Day 16 (BE): questions over MAX_QUERY_CHARS are rejected."""

import copy
import threading
import time
from pathlib import Path

import pandas as pd

from flame_in_freefall import ingest, speed
from flame_in_freefall.cache import memo
from flame_in_freefall.retrieval import find_passages
from flame_in_freefall.store import _paths
from flame_in_freefall.summarizer import summarize_passages
from flame_in_freefall.summary_check import check_summary

# Build the paths from this file's own location (up 2 folders = repo root),
# so they work no matter which folder the app is started from.
MASTER_CSV = Path(__file__).resolve().parents[2] / "data" / "master.csv"
CHUNKS = ingest.CHUNKS  # data/processed/chunks.jsonl (committed)
INDEX = ingest.INDEX  # artifacts/index/ (git-ignored, so the live app starts without it)
# The only filter keys the contract allows; get_table() rejects anything else.
TEXT_FILTERS = {"experiment", "material", "material_category"}
NUMBER_FILTERS = {"oxygen_min", "oxygen_max"}
ALLOWED_FILTERS = TEXT_FILTERS | NUMBER_FILTERS
# Day 13: search() leaves out results scoring under this, so an off-topic question returns []
# ("no match") instead of 5 unrelated passages. Measured with all-MiniLM-L6-v2 on 2026-11-07:
# answerable questions scored 0.42-0.69, clearly off-topic ones -0.01-0.26. Retune it if the
# embedding model or the chunking changes (the scores move with them).
MIN_SCORE = 0.30
# Day 16: the longest question search() and summarize() accept, counted after trimming spaces.
# Our longest test question is under 100 characters, and the embedding model reads only about 200
# words anyway, so a longer text would be silently cut off. The app's search box stops at this
# number too (app/streamlit_app.py), so visitors never see the error below.
MAX_QUERY_CHARS = 300
# The fields summarize() needs in every passage (chunk fields, docs/contract.md section 2).
PASSAGE_KEYS = {"id", "text", "source", "page"}
# Day 15: these become a takeaway's chunk_id, text and source, which must be non-empty text.
PASSAGE_TEXT_KEYS = ("id", "text", "source")

# Two people searching at the same moment must not both build the index (Streamlit runs
# each visitor in its own thread).
_index_lock = threading.Lock()


def _ensure_index() -> None:
    # Missing (a fresh deploy) or older than chunks.jsonl: embed the committed chunks once
    # (~10 s, plus a one-time model download). Later searches find it fresh and skip this.
    with _index_lock:
        if not ingest._is_fresh(list(_paths(INDEX)), [CHUNKS]):
            ingest.build_index(CHUNKS, INDEX)
            _find.cache.clear()  # answers from the old index could be out of date


@memo  # cache.py: the same question (ignoring capitals and spaces), k and filter run once
def _find(query: str, k: int, experiment: str | None) -> list[dict]:
    # {id, text, source, page, score} best first, plus each chunk's experiment (Day 12).
    # An unknown experiment raises ValueError (retrieval.py), and errors are never cached.
    return find_passages(query, k, folder=INDEX, experiment=experiment)


def _check_length(text: str, name: str) -> None:
    # Day 16: say how long it was and what the limit is, so the fix is obvious.
    length = len(text.strip())
    if length > MAX_QUERY_CHARS:
        raise ValueError(f"{name} is too long: {length} characters, the limit is {MAX_QUERY_CHARS}")


def search(query: str, k: int = 5, experiment: str | None = None) -> list[dict]:
    # Contract v1.1: k defaults to 5. Day 12 (v1.4): experiment="FLEX-2" (or "Saffire-II",
    # "FLEX") searches only that experiment's chunks; None searches all of them.
    # Fail loudly on a blank (or non-text) question instead of running an empty search.
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be non-empty text")
    _check_length(query, "query")
    # bool is a kind of int in Python, so True would pass as k=1 without this check.
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a whole number above 0")
    # None means "no filter"; blank text is a mistake, not a way to say "no filter".
    if experiment is not None and (not isinstance(experiment, str) or not experiment.strip()):
        raise ValueError("experiment must be a non-empty string, or None for every experiment")
    start = time.perf_counter()
    # Check the index first, even for a remembered question: it only compares file times, and
    # a rebuild empties the cache, so an out-of-date answer can't be served from memory.
    _ensure_index()
    cached = _find.is_cached(query, k, experiment)
    # A copy, so a caller changing its results can't change what's remembered for others.
    # Weak matches are left out (MIN_SCORE); none left = no match, so [] (never invented).
    results = [r for r in copy.deepcopy(_find(query, k, experiment)) if r["score"] >= MIN_SCORE]
    detail = query if experiment is None else f"{query} [{experiment}]"
    speed.record("search", detail, time.perf_counter() - start, cached)
    return results


def _check_passages(passages: list[dict]) -> None:
    # Fail loudly with a clear message, instead of a KeyError or TypeError deep in summarizer.py.
    if not isinstance(passages, list):
        raise ValueError("passages must be a list (e.g. the results of search())")
    for n, p in enumerate(passages, start=1):
        if not isinstance(p, dict):
            raise ValueError(f"passage {n} must be a dict, got {type(p).__name__}")
        missing = PASSAGE_KEYS - set(p)
        if missing:
            raise ValueError(f"passage {n} is missing {sorted(missing)}")
        # Day 15: blank text would be quoted as an empty takeaway, a number would crash the
        # quoting, and source=None would be shown as the source.
        for key in PASSAGE_TEXT_KEYS:
            if not isinstance(p[key], str) or not p[key].strip():
                raise ValueError(f"passage {n} {key} must be non-empty text")


def summarize(passages: list[dict], question: str | None = None) -> dict:
    # Thin wrapper: the contract signature stays here, the Gemini call lives in summarizer.py.
    # Contract v1.7 (FIF-D15-AI): pass the user's question, so the summary keeps only takeaways
    # that answer it and says "not found" when none do. None works exactly as before.
    _check_passages(passages)
    # None means "no question"; blank text is a mistake, as in search().
    if question is not None and (not isinstance(question, str) or not question.strip()):
        raise ValueError("question must be non-empty text, or None")
    if question is not None:
        _check_length(question, "question")
    start = time.perf_counter()
    summary = summarize_passages(passages, question)
    # Day 15: every path (Gemini, quoting fallback, nothing found) is checked against the
    # contract. Gemini's replies are already checked inside summarizer.py, and the passages were
    # checked above, so a problem here is a bug in our code: fail loudly, don't show it.
    problems = check_summary(summary, passages)
    if problems:
        raise RuntimeError(f"summarize() broke its contract: {'; '.join(problems)}")
    speed.record("summarize", f"{len(passages)} passages", time.perf_counter() - start)
    return summary


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
    # Without this, get_table("FLEX") would complain about unknown filters 'E', 'F', 'L', 'X'.
    if filters is not None and not isinstance(filters, dict):
        raise ValueError('filters must be a dict like {"experiment": "FLEX"}, or None')
    filters = filters or {}  # None (or {}) means "no filters"
    _check_filters(filters)
    start = time.perf_counter()
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
    rows = table.to_dict(orient="records")
    speed.record("get_table", f"{filters} -> {len(rows)} rows", time.perf_counter() - start)
    return rows
