"""Day 13 (BE): edge cases for the three contract functions: bad input fails loudly with a
ValueError, and "no match" is an explicit empty answer, never an invented one.

The shapes are in tests/test_contract.py; the details of each function in test_search.py,
test_get_table.py and test_summarizer.py. conftest.py gives every test a fake embedding
model and turns MIN_SCORE off; the "no match" tests turn it back on."""

import pytest

from flame_in_freefall import api

# --- search() ------------------------------------------------------------------------------


@pytest.mark.parametrize("query", [None, "", "   ", 5, ["flame"]])
def test_search_rejects_empty_or_non_text_query(query):
    with pytest.raises(ValueError):
        api.search(query)


def test_search_rejects_a_query_over_the_length_limit():
    # Day 16: one character over. The message gives the length and the limit.
    too_long = "a" * (api.MAX_QUERY_CHARS + 1)
    with pytest.raises(ValueError, match=rf"{api.MAX_QUERY_CHARS + 1} characters.*limit.*300"):
        api.search(too_long)


def test_search_accepts_a_query_exactly_at_the_limit():
    api.search("a" * api.MAX_QUERY_CHARS)


def test_search_does_not_count_spaces_around_the_query():
    # The app trims the box the same way, so padding must not push a 300-character query over.
    api.search("  " + "a" * api.MAX_QUERY_CHARS + "  ")


@pytest.mark.parametrize("k", [0, -1, 2.5, "3", True])
def test_search_rejects_bad_k(k):
    with pytest.raises(ValueError):
        api.search("flame", k=k)


def test_search_k_larger_than_the_reports_returns_every_chunk():
    assert len(api.search("flame", k=100)) == 22  # the reports make 22 chunks (BASS-II: 4)


def test_search_with_no_match_returns_nothing(monkeypatch):
    # Nothing scores 1.01, like an off-topic question ("pizza recipes") on the real model.
    monkeypatch.setattr(api, "MIN_SCORE", 1.01)
    assert api.search("flame") == []


def test_search_leaves_out_weak_matches(monkeypatch):
    scores = [r["score"] for r in api.search("flame spread in microgravity", k=18)]
    cutoff = sorted(scores)[len(scores) // 2]  # keep roughly the better half
    monkeypatch.setattr(api, "MIN_SCORE", cutoff)
    kept = api.search("flame spread in microgravity", k=18)
    assert kept and all(r["score"] >= cutoff for r in kept)
    assert len(kept) < len(scores)


# --- summarize() ---------------------------------------------------------------------------

PASSAGE = {"id": "flex-p1-c0", "text": "Droplets burned 2 s.", "source": "FLEX", "page": 1}


@pytest.mark.parametrize("passages", [None, "flame", PASSAGE, [1], ["flex-p1-c0"]])
def test_summarize_rejects_non_passages(passages):
    with pytest.raises(ValueError):
        api.summarize(passages)


@pytest.mark.parametrize("missing", ["id", "text", "source", "page"])
def test_summarize_rejects_a_passage_missing_a_field(missing):
    passage = {k: v for k, v in PASSAGE.items() if k != missing}
    with pytest.raises(ValueError, match=missing):
        api.summarize([passage])


def test_summarize_with_no_passages_is_not_found():
    assert api.summarize([]) == {"takeaways": [], "not_found": True}


def test_summarize_after_a_search_with_no_match_is_not_found(monkeypatch):
    # The app's path for an off-topic question: no passages, so nothing is invented.
    monkeypatch.setattr(api, "MIN_SCORE", 1.01)
    assert api.summarize(api.search("pizza recipes"))["not_found"] is True


def test_summarize_extra_fields_are_fine():
    # search() results also carry score and experiment; summarize() takes them as they are.
    result = api.summarize([{**PASSAGE, "score": 0.7, "experiment": "FLEX"}])
    assert result["takeaways"][0]["chunk_id"] == "flex-p1-c0"


@pytest.mark.parametrize("question", ["", "   ", 5, ["flame"]])
def test_summarize_rejects_a_blank_or_non_text_question(question):
    # v1.7 (FIF-D15-AI): None means "no question"; blank text is a mistake.
    with pytest.raises(ValueError, match="question"):
        api.summarize([PASSAGE], question=question)


def test_summarize_rejects_a_question_over_the_length_limit():
    # Day 16: the same limit as search(), so a long text can't reach the Gemini prompt either.
    with pytest.raises(ValueError, match="question is too long"):
        api.summarize([PASSAGE], question="a" * (api.MAX_QUERY_CHARS + 1))


def test_summarize_accepts_a_question_exactly_at_the_limit():
    api.summarize([PASSAGE], question="a" * api.MAX_QUERY_CHARS)


def test_summarize_passes_the_question_on(monkeypatch):
    seen = {}

    def fake(passages, question=None):
        seen["question"] = question
        return {"takeaways": [], "not_found": True}

    monkeypatch.setattr(api, "summarize_passages", fake)
    api.summarize([PASSAGE], question="How long did droplets burn?")
    assert seen["question"] == "How long did droplets burn?"
    api.summarize([PASSAGE])  # without one: exactly as before v1.7
    assert seen["question"] is None


# --- get_table() ---------------------------------------------------------------------------


@pytest.mark.parametrize("filters", ["FLEX", ["experiment"], 5])
def test_get_table_rejects_filters_that_are_not_a_dict(filters):
    with pytest.raises(ValueError, match="must be a dict"):
        api.get_table(filters)


def test_get_table_empty_dict_means_no_filters():
    assert len(api.get_table({})) == 419


def test_get_table_with_no_match_returns_nothing():
    assert api.get_table({"material": "Wood"}) == []
