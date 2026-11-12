"""Day 17 (BE): summarize() remembers Gemini's answers (fake client: no network, no key, no cost).

conftest.py empties the summary cache before every test."""

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from flame_in_freefall import api, speed, summarizer
from flame_in_freefall.summarizer import MAX_CACHED_SUMMARIES, summarize_passages

PASSAGES = [
    {"id": "bass-001-p3-c0", "text": "Spread was 1.2 mm/s. More.", "source": "BASS", "page": 3},
    {"id": "flex-002-p1-c0", "text": "Droplet burned 2 s.", "source": "FLEX", "page": 1},
]
GOOD_REPLY = json.dumps(
    {"takeaways": [{"text": "Spread is slow.", "chunk_id": "bass-001-p3-c0"}], "not_found": False}
)


class CountingClient:
    """A fake Gemini that counts its calls and replies with `reply` (or raises `error`)."""

    def __init__(self, reply: str = GOOD_REPLY, error: Exception | None = None):
        self.calls = 0
        self.reply, self.error = reply, error
        self.models = self

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.reply)


@pytest.fixture
def gemini(monkeypatch) -> CountingClient:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = CountingClient()
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: client)
    return client


def test_the_second_identical_call_does_not_reach_gemini(gemini):
    first = summarize_passages(PASSAGES, "How fast does it spread?")
    second = summarize_passages(PASSAGES, "How fast does it spread?")
    assert gemini.calls == 1
    assert second == first and first["takeaways"][0]["text"] == "Spread is slow."


def test_capitals_and_spaces_in_the_question_share_an_entry(gemini):
    summarize_passages(PASSAGES, "How fast does it spread?")
    summarize_passages(PASSAGES, "  how FAST does it   spread? ")
    assert gemini.calls == 1


def test_a_different_question_asks_gemini_again(gemini):
    summarize_passages(PASSAGES, "How fast does it spread?")
    summarize_passages(PASSAGES, "How long did the droplet burn?")
    assert gemini.calls == 2


def test_no_question_and_a_question_are_different_requests(gemini):
    summarize_passages(PASSAGES)
    summarize_passages(PASSAGES, "How fast does it spread?")
    assert gemini.calls == 2


def test_different_passages_ask_gemini_again(gemini):
    summarize_passages(PASSAGES, "q")
    summarize_passages(PASSAGES[:1], "q")  # fewer passages
    summarize_passages(PASSAGES[::-1], "q")  # same passages, other order
    assert gemini.calls == 3


def test_the_same_id_with_new_text_asks_gemini_again(gemini):
    # A re-ingested report keeps its chunk ids but not its words.
    summarize_passages(PASSAGES, "q")
    changed = [{**PASSAGES[0], "text": "Spread was 9.9 mm/s. More."}, PASSAGES[1]]
    summarize_passages(changed, "q")
    assert gemini.calls == 2


def test_a_corrected_source_gets_a_fresh_answer_with_the_current_citation(gemini: CountingClient):
    api.summarize(PASSAGES, question="q")
    corrected = [{**PASSAGES[0], "source": "Corrected BASS report"}, PASSAGES[1]]
    # The cached takeaway holds the old source; reusing it would fail the API's contract check.
    answer = api.summarize(corrected, question="q")
    assert gemini.calls == 2
    assert answer["takeaways"][0]["source"] == "Corrected BASS report"


def test_a_changed_page_asks_gemini_again(gemini: CountingClient):
    api.summarize(PASSAGES, question="q")
    corrected = [{**PASSAGES[0], "page": 4}, PASSAGES[1]]
    # Page numbers are sent to Gemini, even when the passage's id and text haven't changed.
    api.summarize(corrected, question="q")
    assert gemini.calls == 2


def test_the_same_text_under_another_id_asks_gemini_again(gemini):
    # The takeaway cites a chunk id, so an answer about "a" can't be handed out for "b".
    summarize_passages(PASSAGES, "q")
    renamed = [{**PASSAGES[0], "id": "bass-009-p9-c9"}, PASSAGES[1]]
    summarize_passages(renamed, "q")
    assert gemini.calls == 2


def test_a_different_model_asks_gemini_again(gemini, monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "model-a")
    summarize_passages(PASSAGES, "q")
    monkeypatch.setenv("GEMINI_MODEL", "model-b")
    summarize_passages(PASSAGES, "q")
    assert gemini.calls == 2


def test_a_different_prompt_asks_gemini_again(gemini, monkeypatch, tmp_path):
    summarize_passages(PASSAGES, "q")
    other = tmp_path / "summary_v9.txt"
    other.write_text("Another prompt.", encoding="utf-8")
    monkeypatch.setattr(summarizer, "PROMPT_PATH", other)
    summarize_passages(PASSAGES, "q")
    assert gemini.calls == 2


def test_any_page_value_can_be_part_of_the_key(gemini):
    # Gemini sees the page as text ("p. 3"), so 3 and "3" are the same request, and a page that
    # isn't a plain number doesn't crash the cache.
    summarize_passages(PASSAGES, "q")
    summarize_passages([{**PASSAGES[0], "page": "3"}, PASSAGES[1]], "q")
    assert gemini.calls == 1
    odd = [{**PASSAGES[0], "page": [3]}, PASSAGES[1]]
    assert api.summarize(odd, question="q")["takeaways"][0]["text"] == "Spread is slow."


def test_with_no_key_a_remembered_answer_is_not_shown_as_quotes(gemini, monkeypatch):
    # The page labels a summary "quoted word for word" whenever no key is set, so a remembered
    # Gemini answer must not be handed out then: the passages are quoted for real instead.
    api.summarize(PASSAGES, question="q")
    monkeypatch.delenv("GEMINI_API_KEY")
    assert api.summarize(PASSAGES, question="q") == summarizer._quote_passages(PASSAGES)
    assert summarizer.summary_is_cached(PASSAGES, "q") is False  # so the speed log agrees
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")  # once the key is back, memory works again
    assert api.summarize(PASSAGES, question="q")["takeaways"][0]["text"] == "Spread is slow."
    assert gemini.calls == 1


def test_a_real_not_found_is_remembered(gemini):
    gemini.reply = json.dumps({"takeaways": [], "not_found": True})
    assert summarize_passages(PASSAGES, "q") == {"takeaways": [], "not_found": True}
    assert summarize_passages(PASSAGES, "q") == {"takeaways": [], "not_found": True}
    assert gemini.calls == 1


def test_the_quoting_fallback_is_never_remembered(gemini):
    # A failed call must not stick: the next visitor should get a real summary once Gemini is back.
    gemini.error = ValueError("Gemini is down")
    quoted = summarize_passages(PASSAGES, "q")
    assert quoted == summarizer._quote_passages(PASSAGES)
    gemini.error = None
    assert summarize_passages(PASSAGES, "q")["takeaways"][0]["text"] == "Spread is slow."
    assert gemini.calls == 2


def test_a_reply_that_fails_the_checks_is_not_remembered(gemini):
    gemini.reply = json.dumps(
        {"takeaways": [{"text": "Invented.", "chunk_id": "no-such-chunk"}], "not_found": False}
    )
    summarize_passages(PASSAGES, "q")  # falls back: it cites a passage we never sent
    gemini.reply = GOOD_REPLY
    assert summarize_passages(PASSAGES, "q")["takeaways"][0]["text"] == "Spread is slow."
    assert gemini.calls == 2


def test_a_reply_that_passes_parsing_but_fails_the_checks_is_not_remembered(gemini):
    # Cites a real chunk, so it parses, but a blank takeaway fails check_summary: quoted instead.
    gemini.reply = json.dumps(
        {"takeaways": [{"text": " ", "chunk_id": "bass-001-p3-c0"}], "not_found": False}
    )
    assert summarize_passages(PASSAGES, "q") == summarizer._quote_passages(PASSAGES)
    assert summarizer._summary_cache == {}


def test_the_limit_has_no_say_when_the_answer_is_remembered(gemini, monkeypatch):
    # One Gemini call a minute: the 2nd request would be quoted if it were counted.
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "1")
    first = summarize_passages(PASSAGES, "q")
    assert [summarize_passages(PASSAGES, "q") for _ in range(5)] == [first] * 5
    assert gemini.calls == 1


def test_a_remembered_answer_is_still_given_when_the_limit_is_used_up(gemini, monkeypatch):
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "1")
    first = summarize_passages(PASSAGES, "q")
    other = summarize_passages(PASSAGES, "another question")  # over the limit: quoted
    assert other == summarizer._quote_passages(PASSAGES)
    assert summarize_passages(PASSAGES, "q") == first


def test_changing_an_answer_does_not_change_what_is_remembered(gemini):
    first = summarize_passages(PASSAGES, "q")
    first["takeaways"][0]["text"] = "Changed by the caller."
    first["takeaways"].clear()
    again = summarize_passages(PASSAGES, "q")
    again["takeaways"][0]["text"] = "Changed again."
    assert summarize_passages(PASSAGES, "q")["takeaways"][0]["text"] == "Spread is slow."


def test_the_oldest_answer_is_dropped_when_full(gemini, monkeypatch):
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "1000")  # fill it faster than 10 a minute
    for n in range(MAX_CACHED_SUMMARIES):
        summarize_passages(PASSAGES, f"question {n}")
    assert gemini.calls == MAX_CACHED_SUMMARIES
    summarize_passages(PASSAGES, f"question {MAX_CACHED_SUMMARIES}")  # one too many
    assert MAX_CACHED_SUMMARIES == 256  # the size the D17 plan asks for
    assert len(summarizer._summary_cache) == 256
    gemini.calls = 0
    summarize_passages(PASSAGES, "question 1")  # still remembered
    assert gemini.calls == 0
    summarize_passages(PASSAGES, "question 0")  # the first one was dropped
    assert gemini.calls == 1


def test_remembering_a_known_question_again_drops_nothing_when_full(gemini):
    # Two visitors asking something new at the same moment can both get here for one question.
    for n in range(MAX_CACHED_SUMMARIES):
        summarizer._remember(("question", n), {"takeaways": [], "not_found": True})
    summarizer._remember(("question", 5), {"takeaways": [], "not_found": True})
    assert len(summarizer._summary_cache) == MAX_CACHED_SUMMARIES
    assert ("question", 0) in summarizer._summary_cache


class _SlowStoreDict(dict):
    # Pauses while storing, so a missing lock lets other threads get in at the worst moment.
    def __setitem__(self, key, value):
        time.sleep(0.01)
        super().__setitem__(key, value)


def test_remembering_at_the_same_moment_keeps_to_the_size_limit(gemini, monkeypatch):
    full = _SlowStoreDict(((("old", n), {}) for n in range(MAX_CACHED_SUMMARIES)))
    monkeypatch.setattr(summarizer, "_summary_cache", full)
    errors = []

    def remember(n: int) -> None:
        try:
            summarizer._remember(("new", n), {"takeaways": [], "not_found": True})
        except Exception as e:  # noqa: BLE001 - any failure in a thread must fail the test
            errors.append(e)

    threads = [threading.Thread(target=remember, args=(n,)) for n in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert len(full) == MAX_CACHED_SUMMARIES


def test_asking_the_same_thing_again_does_not_use_up_room(gemini):
    for _ in range(3):
        summarize_passages(PASSAGES, "q")
    assert len(summarizer._summary_cache) == 1


def test_visitors_at_the_same_time_leave_the_cache_whole(gemini, monkeypatch):
    # Many threads asking and remembering together, with more questions than the cache holds, so
    # old answers are dropped while others are stored: no crash, nothing over the size limit.
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "10000")  # every question reaches the fake
    errors = []

    def visit(n: int) -> None:
        try:
            for i in range(50):
                summarize_passages(PASSAGES, f"question {n * 50 + i}")
        except Exception as e:  # noqa: BLE001 - any failure in a thread must fail the test
            errors.append(e)

    threads = [threading.Thread(target=visit, args=(n,)) for n in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert gemini.calls == 400  # all 400 questions were new, so the cache had to drop 144
    assert len(summarizer._summary_cache) == MAX_CACHED_SUMMARIES


# --- through api.summarize(): what the app calls -----------------------------------------------


def test_api_logs_the_repeat_as_cached(gemini):
    api.summarize(PASSAGES, question="q")
    api.summarize(PASSAGES, question="q")
    first, second = [e for e in speed.read_log() if e["call"] == "summarize"]
    assert first["cached"] is False and second["cached"] is True


def test_api_summarize_is_one_gemini_call_for_two_identical_requests(gemini):
    # "Repeat is instant" (the D17-BE ticket): what a visitor gets when a slider re-runs the page.
    first = api.summarize(PASSAGES, question="q")
    assert api.summarize(PASSAGES, question="q") == first
    assert gemini.calls == 1


# --- the real page: a slider re-runs it (be_notes.md section 5) ----------------------------------


def test_moving_a_slider_does_not_ask_gemini_again(monkeypatch):
    app = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        first_id = kwargs["contents"].split("[", 1)[1].split("]", 1)[0]
        reply = {"takeaways": [{"text": "It spreads.", "chunk_id": first_id}], "not_found": False}
        return SimpleNamespace(text=json.dumps(reply))

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: client)

    at = AppTest.from_file(str(app), default_timeout=30).run()
    at.text_input[0].input("flame spread").run()
    assert len(calls) == 1
    low, high = at.slider(key="f_oxygen").value
    at.slider(key="f_oxygen").set_value((low + 0.5, high)).run()  # re-runs the whole page
    at.slider(key="f_oxygen").set_value((low + 1.0, high)).run()
    assert not at.exception
    assert len(calls) == 1  # still the one call: the repeats were answered from memory
