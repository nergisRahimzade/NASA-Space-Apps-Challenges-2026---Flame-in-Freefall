"""Day 3 (BE): remember answers by query so a repeated question is instant and free."""

import functools
import hashlib
import json
from pathlib import Path


def normalize(query: str) -> str:
    """'  Which MATERIAL burns?? ' and 'which material burns??' share a cache entry."""
    # lower() ignores capitals; split() + join() trims the ends and squeezes spaces,
    # tabs and newlines down to single spaces.
    return " ".join(query.lower().split())


class QueryCache:
    """Small JSON-file cache. Survives restarts; one file per query."""

    def __init__(self, folder: str | Path = "artifacts/cache"):
        # artifacts/ is git-ignored, so cached answers (generated files) never get committed.
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)  # create it if missing, fine if it exists

    def _path(self, query: str) -> Path:
        # Hash the cleaned query into a short, safe file name: questions can contain
        # characters like ? or / that aren't allowed in file names.
        key = hashlib.sha256(normalize(query).encode()).hexdigest()[:16]
        return self.folder / f"{key}.json"

    def get(self, query: str):
        # None = nothing saved for this query yet, so the caller does the real work.
        p = self._path(query)
        return json.loads(p.read_text()) if p.exists() else None

    def set(self, query: str, value) -> None:
        self._path(query).write_text(json.dumps(value))


def memo(func):
    """In-memory cache decorator keyed on the normalized query (first argument)."""
    store: dict = {}

    @functools.wraps(func)
    def wrapper(query: str, *args, **kwargs):
        # The key includes the other arguments too, so search("q", k=3) and search("q", k=5)
        # are remembered separately.
        key = (normalize(query), args, tuple(sorted(kwargs.items())))
        if key not in store:  # first time: do the real work and remember the answer
            store[key] = func(query, *args, **kwargs)
        return store[key]

    wrapper.cache = store  # lets tests or debugging look inside (or clear) the memory
    return wrapper
