"""Day 4 (AI): find the saved chunks that best match a question.

The question is embedded the same way as the chunks (Day 3), then compared with every chunk
vector by cosine similarity: 1 = same direction (same meaning), near 0 = unrelated.
FIF-D10-BE wires find_passages into api.search(); until then api.search() returns mock data."""

from pathlib import Path

import numpy as np

from flame_in_freefall.embedding import embed_texts
from flame_in_freefall.store import DEFAULT_FOLDER, load_index


def _normalize_rows(m: np.ndarray) -> np.ndarray:
    # Divide each row by its length so only the direction counts, not the size.
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.where(norms == 0, 1, norms)  # an all-zero row stays zero instead of 0/0


def top_k(query_vec: np.ndarray, chunk_vecs: np.ndarray, k: int = 3) -> list[tuple[int, float]]:
    """Return [(chunk_row, cosine_score), ...], best first, at most k of them."""
    if k <= 0:
        raise ValueError("k must be > 0")
    # Different sizes mean the index was built with another embedding model: rebuild it.
    if query_vec.shape[-1] != chunk_vecs.shape[1]:
        raise ValueError(
            f"question vector has {query_vec.shape[-1]} numbers but chunk vectors have "
            f"{chunk_vecs.shape[1]}; rebuild the index with the same embedding model"
        )
    # embed_texts already gives length-1 vectors; normalizing again keeps this correct
    # for any vectors, and then the dot product is exactly the cosine similarity.
    q = _normalize_rows(query_vec.reshape(1, -1))[0]
    scores = _normalize_rows(chunk_vecs) @ q
    # Minus sign = highest score first. stable: equal scores keep their saved order.
    order = np.argsort(-scores, kind="stable")[:k]
    return [(int(i), float(scores[i])) for i in order]


def find_passages(query: str, k: int = 3, folder: str | Path = DEFAULT_FOLDER) -> list[dict]:
    """The k best chunks for a question, best first, shaped like search() in docs/contract.md:
    {"id", "text", "source", "page", "score"}."""
    # Fail loudly on a blank question instead of running an empty search.
    if not query.strip():
        raise ValueError("query must not be empty")
    vectors, chunks = load_index(folder)  # FileNotFoundError if the index wasn't built yet
    query_vec = embed_texts([query])[0]
    # Row i of vectors belongs to chunks[i] (store.py), so the row number finds the chunk.
    return [{**chunks[i], "score": score} for i, score in top_k(query_vec, vectors, k)]
