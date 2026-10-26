import pytest

from flame_in_freefall.api import get_table, search, summarize

CHUNK_KEYS = {"id", "text", "source", "page", "score"}


def test_search_shape():
    results = search("which materials are riskiest?")
    assert results and len(results) <= 3
    for r in results:
        assert CHUNK_KEYS <= r.keys()
        assert isinstance(r["page"], int) and isinstance(r["score"], float)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_rejects_empty():
    with pytest.raises(ValueError):
        search("   ")


def test_summarize_shape_and_citations():
    passages = search("flame spread")
    out = summarize(passages)
    assert out["not_found"] is False
    ids = {p["id"] for p in passages}
    for t in out["takeaways"]:
        assert {"text", "source", "chunk_id"} <= t.keys()
        assert t["chunk_id"] in ids


def test_summarize_no_passages():
    assert summarize([]) == {"takeaways": [], "not_found": True}


def test_get_table_filters():
    assert len(get_table()) == 5
    bass = get_table({"experiment": "BASS"})
    assert bass and all(r["experiment"] == "BASS" for r in bass)
    assert all(isinstance(r["spread_rate_mm_s"], float) for r in bass)


def test_get_table_unknown_filter():
    with pytest.raises(ValueError):
        get_table({"colour": "red"})
