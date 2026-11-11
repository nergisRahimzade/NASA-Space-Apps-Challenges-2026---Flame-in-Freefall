import pytest

from flame_in_freefall.api import get_table, search, summarize

CHUNK_KEYS = {"id", "text", "source", "page", "score"}


def test_search_shape():
    results = search("which materials are riskiest?")
    assert results and len(results) <= 5  # contract v1.1 default k
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
    # Contract v1.2: real rows from data/master.csv, numbers as float, empty cells as None.
    assert len(get_table()) == 419
    flex2 = get_table({"experiment": "FLEX-2"})
    assert flex2 and all(r["experiment"] == "FLEX-2" for r in flex2)
    assert all(isinstance(r["oxygen_pct_min"], float) for r in flex2)
    assert all(r["spread_rate_mm_s"] is None for r in flex2)  # FLEX-2 has no spread rate


def test_get_table_unknown_filter():
    with pytest.raises(ValueError):
        get_table({"colour": "red"})
