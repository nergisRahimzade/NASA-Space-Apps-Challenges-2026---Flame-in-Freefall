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


# Day 12 (AI): filter by experiment before ranking. Four tagged chunks from two experiments;
# the question points along x, where the FLEX chunk is the closest of all.
TAGGED = [
    {"id": "flex-p1-c0", "text": "a", "source": "FLEX", "page": 1, "experiment": "FLEX"},
    {"id": "flex2-p1-c0", "text": "b", "source": "FLEX-2", "page": 1, "experiment": "FLEX-2"},
    {"id": "flex-p1-c1", "text": "c", "source": "FLEX", "page": 1, "experiment": "FLEX"},
    {"id": "flex2-p1-c1", "text": "d", "source": "FLEX-2", "page": 1, "experiment": "FLEX-2"},
]
TAGGED_VECTORS = np.array([[1.0, 0.0], [0.6, 0.8], [0.0, 1.0], [0.8, 0.6]])


@pytest.fixture
def tagged_index(monkeypatch, tmp_path):
    save_index(TAGGED_VECTORS, TAGGED, tmp_path)
    monkeypatch.setattr(retrieval, "embed_texts", lambda texts: np.array([[1.0, 0.0]]))
    return tmp_path


def test_rows_for_experiment_keeps_saved_order():
    assert retrieval.rows_for_experiment(TAGGED, "FLEX-2") == [1, 3]
    assert retrieval.rows_for_experiment(TAGGED) == [0, 1, 2, 3]  # None = no filter


def test_find_passages_without_filter_mixes_experiments(tagged_index):
    results = retrieval.find_passages("q", k=2, folder=tagged_index)
    assert [r["id"] for r in results] == ["flex-p1-c0", "flex2-p1-c1"]


def test_find_passages_filter_returns_only_that_experiment(tagged_index):
    results = retrieval.find_passages("q", k=2, folder=tagged_index, experiment="FLEX-2")
    # The overall best match (FLEX) is gone; FLEX-2's chunks are ranked among themselves.
    assert [r["id"] for r in results] == ["flex2-p1-c1", "flex2-p1-c0"]
    assert all(r["experiment"] == "FLEX-2" for r in results)
    assert results[0]["score"] == pytest.approx(0.8)  # same cosine as without the filter


def test_find_passages_filter_returns_fewer_when_experiment_is_small(tagged_index):
    results = retrieval.find_passages("q", k=10, folder=tagged_index, experiment="FLEX")
    assert [r["id"] for r in results] == ["flex-p1-c0", "flex-p1-c1"]


def test_find_passages_rejects_unknown_experiment(tagged_index):
    # A typo (or the old BASS name) must not quietly return nothing.
    with pytest.raises(ValueError, match="unknown experiment"):
        retrieval.find_passages("q", folder=tagged_index, experiment="flex-2")


def test_find_passages_filter_needs_tagged_chunks(monkeypatch, tmp_path):
    save_index(VECTORS, CHUNKS, tmp_path)  # untagged: an index built before Day 12
    monkeypatch.setattr(retrieval, "embed_texts", lambda texts: np.array([[1.0, 0.0]]))
    with pytest.raises(ValueError, match="no experiment tag"):
        retrieval.find_passages("q", folder=tmp_path, experiment="FLEX")
    # Without a filter the old index still works.
    assert len(retrieval.find_passages("q", folder=tmp_path)) == 3


EXPERIMENTS = ["FLEX", "FLEX-2", "Saffire-II"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("What oxygen levels were used in the FLEX-2 chamber?", "FLEX-2"),
        ("How did FLEX measure the LOI?", "FLEX"),  # not FLEX-2
        ("what airflow speeds were used in saffire-ii?", "Saffire-II"),  # case is ignored
        ("What is a cool flame?", None),  # no experiment named
        ("Compare FLEX and FLEX-2", None),  # two named: can't filter to one
        ("Was Saffire safe?", None),  # "Saffire" alone isn't "Saffire-II"
        ("What did FLEXIBLE materials do?", None),  # name inside a longer word
    ],
)
def test_experiment_in_question(query, expected):
    assert retrieval.experiment_in_question(query, EXPERIMENTS) == expected
