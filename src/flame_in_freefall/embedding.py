"""Day 3 (AI): turn text into numbers (embeddings) with a small local model.

Texts with similar meaning get vectors that point in similar directions, which is how
search (Day 4) finds the passages closest to a question. The model runs on this computer,
so it's free and needs no API key."""

import threading
from functools import lru_cache

import numpy as np

from flame_in_freefall.config import get_settings

# Day 19 (FE): lru_cache doesn't stop two threads from loading at the same time. In the app,
# clicking several example buttons during the first (slow) search started several loads at
# once, and the server crashed (segfault, exit code 139). The lock lets one thread load while
# the others wait, then they all reuse the cached model.
_model_lock = threading.Lock()


@lru_cache(maxsize=1)  # loading takes a few seconds, so do it once and reuse the model
def _load_model(name: str):
    # Imported here, not at the top: it pulls in PyTorch (slow), and only code that
    # really embeds should pay that cost (tests swap in a fake model instead).
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name)


def _load_model_once(name: str):
    with _model_lock:
        return _load_model(name)


def _get_model(name: str):
    # Kept as its own name: tests swap _get_model for a fake model (tests/conftest.py).
    return _load_model_once(name)


def embed_texts(texts: list[str]) -> np.ndarray:
    """One row per text (384 numbers each for all-MiniLM-L6-v2), every row of length 1."""
    # Fail loudly: an empty list or blank text means a bug upstream, not something to embed.
    if not texts:
        raise ValueError("texts must not be empty")
    if any(not t.strip() for t in texts):
        raise ValueError("texts must not contain blank strings")
    model = _get_model(get_settings().embed_model)
    # normalize_embeddings=True makes every vector length 1, so cosine similarity
    # is just a dot product when we search.
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
