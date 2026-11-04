"""Day 4 (AI): top_k ranks by cosine; find_passages returns contract-shaped results.

A fake embedding stands in for the model, so tests need no download or network."""

import numpy as np
import pytest

from flame_in_freefall import retrieval
from flame_in_freefall.store import save_index

CHUNKS = [
    {"id": f"doc-p1-c{i}", "text": f"text {i}", "source": "Fake report", "page": 1}
    for i in range(3)
]
# Three directions: chunk 0 points along x, chunk 1 along y, chunk 2 in between.
VECTORS = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]])


def test_top_k_orders_by_cosine():
    result = retrieval.top_k(np.array([1.0, 0.1]), VECTORS, k=2)
    assert [i for i, _ in result] == [0, 2]
    assert result[0][1] > result[1][1]


def test_top_k_ignores_vector_length():
    # Same direction, 10x longer: cosine looks at direction only, so the score is the same.
    short = retrieval.top_k(np.array([1.0, 1.0]), VECTORS, k=1)
    long = retrieval.top_k(np.array([10.0, 10.0]), VECTORS, k=1)
    assert short == pytest.approx(long)


def test_top_k_returns_fewer_when_few_chunks():
    assert len(retrieval.top_k(np.array([1.0, 0.0]), VECTORS, k=10)) == 3


def test_top_k_rejects_bad_k():
    with pytest.raises(ValueError):
        retrieval.top_k(np.array([1.0, 0.0]), VECTORS, k=0)


def test_top_k_rejects_vectors_from_another_model():
    with pytest.raises(ValueError):
        retrieval.top_k(np.array([1.0, 0.0, 0.0]), VECTORS)


def test_find_passages_returns_contract_fields(monkeypatch, tmp_path):
    save_index(VECTORS, CHUNKS, tmp_path)
    # Fake question vector pointing along y, so chunk 1 should win.
    monkeypatch.setattr(retrieval, "embed_texts", lambda texts: np.array([[0.0, 1.0]]))
    results = retrieval.find_passages("any question", k=2, folder=tmp_path)
    assert results[0]["id"] == "doc-p1-c1"
    assert set(results[0]) == {"id", "text", "source", "page", "score"}  # docs/contract.md
    assert results[0]["score"] >= results[1]["score"]  # best first


def test_find_passages_rejects_blank_query(tmp_path):
    with pytest.raises(ValueError):
        retrieval.find_passages("   ", folder=tmp_path)


def test_find_passages_needs_an_index(tmp_path):
    with pytest.raises(FileNotFoundError):
        retrieval.find_passages("why do flames go out?", folder=tmp_path)
