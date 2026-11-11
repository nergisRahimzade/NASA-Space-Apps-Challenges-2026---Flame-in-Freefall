"""Day 15 (BE): every way summarize() can answer comes back in the contract's shape.

The shape (docs/contract.md): {"takeaways": [{"text", "source", "chunk_id"}], "not_found": bool},
with every takeaway field non-empty text. The plan's shape is {text, source}; chunk_id is ours
too, because it's how each takeaway is checked against its passage.
Fake Gemini client, no network, no key."""

import json
from types import SimpleNamespace

import httpx
import pytest

from flame_in_freefall import api, summarizer

PASSAGES = [
    {"id": "flex-p1-c0", "text": "Flames went out at 13 %. More.", "source": "FLEX", "page": 1},
    {"id": "flex2-p1-c0", "text": "Droplets burned 2 s.", "source": "FLEX-2", "page": 1},
]
QUOTED = "Flames went out at 13 %."  # the fallback quotes each passage's first sentence


def _assert_contract_shape(summary: dict) -> None:
    assert set(summary) == {"takeaways", "not_found"}
    assert isinstance(summary["not_found"], bool)
    assert summary["not_found"] == (summary["takeaways"] == [])  # one or the other, never both
    for t in summary["takeaways"]:
        assert set(t) == {"text", "source", "chunk_id"}
        assert all(isinstance(v, str) and v.strip() for v in t.values())


def _use_fake_gemini(monkeypatch, reply: dict | None = None, error: Exception | None = None):
    # A stand-in client that returns this reply as JSON text, or raises this error.
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def generate_content(**kwargs):
        if error:
            raise error
        return SimpleNamespace(text=json.dumps(reply))

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: client)


# --- every path, same shape -----------------------------------------------------------------

GEMINI_ANSWERS = {
    "answer": {"reply": {"takeaways": [{"text": "Out at 13 %.", "chunk_id": "flex-p1-c0"}]}},
    "nothing useful": {"reply": {"takeaways": [], "not_found": True}},
    "timeout": {"error": httpx.ReadTimeout("too slow")},
    "number as text": {"reply": {"takeaways": [{"text": 5, "chunk_id": "flex-p1-c0"}]}},
    "not_found as text": {"reply": {"takeaways": [], "not_found": "no"}},
}


@pytest.mark.parametrize("answer", GEMINI_ANSWERS.values(), ids=GEMINI_ANSWERS.keys())
def test_every_gemini_answer_comes_back_in_contract_shape(monkeypatch, answer):
    reply = answer.get("reply")
    if reply is not None:
        reply = {"not_found": False, **reply}  # a reply always has both fields
    _use_fake_gemini(monkeypatch, reply, answer.get("error"))
    _assert_contract_shape(api.summarize(PASSAGES))


def test_no_key_fallback_comes_back_in_contract_shape():
    _assert_contract_shape(api.summarize(PASSAGES))


def test_no_passages_comes_back_in_contract_shape():
    _assert_contract_shape(api.summarize([]))


# --- Gemini replies that used to get through --------------------------------------------------


def test_number_as_takeaway_text_falls_back_to_quoting(monkeypatch):
    reply = {"takeaways": [{"text": 5, "chunk_id": "flex-p1-c0"}], "not_found": False}
    _use_fake_gemini(monkeypatch, reply)
    assert api.summarize(PASSAGES)["takeaways"][0]["text"] == QUOTED


def test_not_found_as_text_falls_back_to_quoting(monkeypatch):
    # "no" used to count as true, so a real answer was thrown away as "nothing found".
    _use_fake_gemini(monkeypatch, {"takeaways": [], "not_found": "no"})
    assert api.summarize(PASSAGES)["takeaways"][0]["text"] == QUOTED


# --- passages that would break the shape -------------------------------------------------------


@pytest.mark.parametrize("key", ["id", "text", "source"])
@pytest.mark.parametrize("bad", ["", "   ", 5, None])
def test_passage_fields_must_be_non_empty_text(key, bad):
    passage = {**PASSAGES[0], key: bad}
    with pytest.raises(ValueError, match=f"passage 1 {key}"):
        api.summarize([passage])


# --- the last check before the answer leaves summarize() ---------------------------------------


def test_a_broken_answer_from_our_own_code_fails_loudly(monkeypatch):
    # Stands in for a future bug in summarizer.py: the answer is missing its source.
    broken = {"takeaways": [{"text": "x", "chunk_id": "flex-p1-c0"}], "not_found": False}
    monkeypatch.setattr(api, "summarize_passages", lambda passages, question=None: broken)
    with pytest.raises(RuntimeError, match="broke its contract"):
        api.summarize(PASSAGES)
