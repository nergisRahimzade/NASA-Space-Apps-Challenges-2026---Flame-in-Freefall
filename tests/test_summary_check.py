"""Day 6 (AI): check_summary catches claims without a real citation, and every summary
summarize_passages hands out passes the check (fake Gemini client, no network, no key)."""

import json
from types import SimpleNamespace

from flame_in_freefall import summarizer
from flame_in_freefall.summary_check import check_summary

PASSAGES = [
    {"id": "bass-001-p3-c0", "text": "Spread was 1.2 mm/s. More.", "source": "BASS", "page": 3},
    {"id": "flex-002-p1-c0", "text": "Droplet burned 2 s.", "source": "FLEX", "page": 1},
]


def _summary(*takeaways: dict) -> dict:
    return {"takeaways": list(takeaways), "not_found": not takeaways}


def _takeaway(text="Spread was 1.2 mm/s.", source="BASS", chunk_id="bass-001-p3-c0") -> dict:
    return {"text": text, "source": source, "chunk_id": chunk_id}


def _use_fake_gemini(monkeypatch, reply: dict) -> None:
    # A stand-in client whose generate_content always returns this reply as JSON text.
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fake = SimpleNamespace(text=json.dumps(reply))
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs: fake))
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: client)


# --- the rules, one at a time ----------------------------------------------------------


def test_good_summary_passes():
    assert check_summary(_summary(_takeaway()), PASSAGES) == []


def test_nothing_found_passes():
    assert check_summary({"takeaways": [], "not_found": True}, PASSAGES) == []


def test_claim_without_chunk_id_fails():
    assert check_summary(_summary(_takeaway(chunk_id="")), PASSAGES)


def test_claim_citing_unknown_chunk_fails():
    assert check_summary(_summary(_takeaway(chunk_id="made-up-p9-c9")), PASSAGES)


def test_claim_with_wrong_source_fails():
    assert check_summary(_summary(_takeaway(source="FLEX")), PASSAGES)


def test_claim_without_text_fails():
    assert check_summary(_summary(_takeaway(text="  ")), PASSAGES)


def test_not_found_with_takeaways_fails():
    assert check_summary({"takeaways": [_takeaway()], "not_found": True}, PASSAGES)


def test_wrong_keys_fail():
    assert check_summary({"takeaways": [], "not_found": True, "extra": 1}, PASSAGES)


# Day 15 (BE): each takeaway's own shape.


def test_takeaway_that_is_not_a_dict_is_reported_not_crashed():
    assert check_summary({"takeaways": ["Spread was 1.2 mm/s."], "not_found": False}, PASSAGES)


def test_takeaway_with_an_extra_key_fails():
    assert check_summary(_summary({**_takeaway(), "page": 3}), PASSAGES)


def test_takeaway_with_a_number_as_text_fails():
    assert check_summary(_summary(_takeaway(text=5)), PASSAGES)


# --- what summarize_passages really hands out -----------------------------------------


def test_fallback_without_key_passes():
    assert check_summary(summarizer.summarize_passages(PASSAGES), PASSAGES) == []


def test_good_gemini_reply_passes(monkeypatch):
    reply = {"takeaways": [{"text": "Droplet burned 2 s.", "chunk_id": "flex-002-p1-c0"}]}
    _use_fake_gemini(monkeypatch, {**reply, "not_found": False})
    summary = summarizer.summarize_passages(PASSAGES)
    assert summary["takeaways"][0]["text"] == "Droplet burned 2 s."  # Gemini's text was used
    assert check_summary(summary, PASSAGES) == []


def test_reply_failing_the_check_falls_back(monkeypatch):
    # Gemini returns a takeaway with no text: the check rejects it, so passages are quoted.
    reply = {"takeaways": [{"text": "", "chunk_id": "bass-001-p3-c0"}], "not_found": False}
    _use_fake_gemini(monkeypatch, reply)
    summary = summarizer.summarize_passages(PASSAGES)
    assert summary["takeaways"][0]["text"] == "Spread was 1.2 mm/s."  # quoted first sentence
    assert check_summary(summary, PASSAGES) == []
