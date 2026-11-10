"""Day 4 (AI): find the saved chunks that best match a question.

The question is embedded the same way as the chunks (Day 3), then compared with every chunk
vector by cosine similarity: 1 = same direction (same meaning), near 0 = unrelated.
FIF-D10-BE wires find_passages into api.search(); until then api.search() returns mock data.
Day 12 (AI): find_passages can keep only one experiment's chunks before ranking, using the
`experiment` tag DAT added to every chunk (FLEX-2, Saffire-II or FLEX).
Day 11 (AI): find_passages returns 5 chunks by default, not 3 (tests/top_k.md).
Day 14 (AI): experiment_in_question reads the experiment name out of a question, so search can be
filtered even when nobody picked one in the app (tests/checkpoint.md)."""

import re
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


def rows_for_experiment(chunks: list[dict], experiment: str | None = None) -> list[int]:
    """Row numbers of the chunks tagged with `experiment`, in saved order. None = every row.

    Raises ValueError for an experiment no chunk has (a typo would otherwise return nothing)
    and for chunks with no tag (an index built before Day 12: rebuild it)."""
    if experiment is None:
        return list(range(len(chunks)))
    untagged = [c.get("id", i) for i, c in enumerate(chunks) if not c.get("experiment")]
    if untagged:
        raise ValueError(
            f"{len(untagged)} chunk(s) have no experiment tag (e.g. {untagged[0]}); "
            "rebuild chunks.jsonl and the index"
        )
    rows = [i for i, c in enumerate(chunks) if c["experiment"] == experiment]
    if not rows:
        known = sorted({c["experiment"] for c in chunks})
        raise ValueError(f"unknown experiment {experiment!r}; choose one of {known}")
    return rows


def experiment_in_question(query: str, experiments: list[str]) -> str | None:
    """The one experiment the question names, spelled as in `experiments`, or None.

    Case is ignored, but the name must stand alone: "FLEX" doesn't match inside "FLEX-2", and
    "Saffire" alone doesn't match "Saffire-II". A question naming two experiments ("compare FLEX
    and FLEX-2") gives None, since one filter would hide the other's chunks."""
    named = {
        e
        for e in experiments
        # (?<![\w-]) and (?![\w-]): no letter, digit or hyphen right before or after the name.
        if re.search(rf"(?<![\w-]){re.escape(e)}(?![\w-])", query, flags=re.IGNORECASE)
    }
    return named.pop() if len(named) == 1 else None


def find_passages(
    query: str,
    k: int = 5,  # D11: 5 finds 7 of 8 answerable questions, 3 finds 6
    folder: str | Path = DEFAULT_FOLDER,
    experiment: str | None = None,
) -> list[dict]:
    """The k best chunks for a question, best first, shaped like search() in docs/contract.md:
    {"id", "text", "source", "page", "score"} (plus `experiment` when the index has it).

    `experiment` (e.g. "FLEX-2") keeps only that experiment's chunks *before* ranking, so the
    k results all come from it. None (the default) searches every chunk, as before."""
    # Fail loudly on a blank question instead of running an empty search.
    if not query.strip():
        raise ValueError("query must not be empty")
    vectors, chunks = load_index(folder)  # FileNotFoundError if the index wasn't built yet
    rows = rows_for_experiment(chunks, experiment)
    query_vec = embed_texts([query])[0]
    # Rank only the kept rows. top_k numbers them 0..len(rows)-1, so map back with rows[j];
    # row i of vectors still belongs to chunks[i] (store.py).
    ranked = top_k(query_vec, vectors[rows], k)
    return [{**chunks[rows[j]], "score": score} for j, score in ranked]
