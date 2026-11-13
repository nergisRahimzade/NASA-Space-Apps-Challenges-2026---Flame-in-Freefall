"""Day 5 (BE): summarize_passages with a fake Gemini client (no network, no key)."""

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from flame_in_freefall import summarizer
from flame_in_freefall.rate_limit import RateLimiter
from flame_in_freefall.summarizer import summarize_passages

PASSAGES = [
    {"id": "bass-001-p3-c0", "text": "Spread was 1.2 mm/s. More.", "source": "BASS", "page": 3},
    {"id": "flex-002-p1-c0", "text": "Droplet burned 2 s.", "source": "FLEX", "page": 1},
]


class FakeClient:
    """Stands in for genai.Client(): remembers each request and replies with text or an error."""

    def __init__(self, reply: str = "", error: Exception | None = None):
        self.calls = []
        self.reply, self.error = reply, error
        self.models = self  # so fake.models.generate_content(...) works like the real client

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.reply)


@pytest.fixture
def use_fake(monkeypatch):
    # Set a fake key and swap in the fake client; returns a helper that installs one.
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def install(**kwargs) -> FakeClient:
        fake = FakeClient(**kwargs)
        monkeypatch.setattr(summarizer, "_get_client", lambda api_key: fake)
        return fake

    return install


def _reply(takeaways: list[dict], not_found: bool = False) -> str:
    return json.dumps({"takeaways": takeaways, "not_found": not_found})


def test_model_reply_gets_real_source(use_fake):
    use_fake(reply=_reply([{"text": "Spread is slow.", "chunk_id": "bass-001-p3-c0"}]))
    out = summarize_passages(PASSAGES)
    assert out == {
        "takeaways": [{"text": "Spread is slow.", "source": "BASS", "chunk_id": "bass-001-p3-c0"}],
        "not_found": False,
    }


def test_sends_prompt_and_passage_ids(use_fake):
    fake = use_fake(reply=_reply([], not_found=True))
    summarize_passages(PASSAGES)
    sent = fake.calls[0]
    prompt = summarizer.PROMPT_PATH.read_text(encoding="utf-8")
    assert sent["config"].system_instruction == prompt
    assert "[bass-001-p3-c0]" in sent["contents"] and "[flex-002-p1-c0]" in sent["contents"]


def test_not_found_reply(use_fake):
    use_fake(reply=_reply([], not_found=True))
    assert summarize_passages(PASSAGES) == {"takeaways": [], "not_found": True}


def test_no_passages_skips_gemini(use_fake):
    fake = use_fake(reply="unused")
    assert summarize_passages([]) == {"takeaways": [], "not_found": True}
    assert fake.calls == []


def test_no_key_quotes_passages():
    # conftest.py already removed GEMINI_API_KEY, so this is the "no key" case.
    out = summarize_passages(PASSAGES)
    assert out["not_found"] is False
    assert out["takeaways"][0] == {
        "text": "Spread was 1.2 mm/s.",
        "source": "BASS",
        "chunk_id": "bass-001-p3-c0",
    }


# --- Day 16 (BE): the fallback quotes a whole sentence, not a fragment -------------------------


def _quote(text: str) -> str:
    # What the app shows for one passage when Gemini isn't used (no key in tests).
    passage = {"id": "x-p1-c0", "text": text, "source": "FLEX", "page": 1}
    return summarize_passages([passage])["takeaways"][0]["text"]


def test_quote_skips_the_end_of_a_sentence_the_chunk_started_in_the_middle_of():
    # Chunks overlap by 30 words, so most start mid-sentence, and this fragment is long enough
    # (4+ words) that only the lowercase start, not the short-sentence rule, gives it away.
    text = "and enhancing fire safety for future missions. Samples burned for two minutes. End."
    assert _quote(text) == "Samples burned for two minutes."


def test_quote_of_a_passage_that_starts_a_sentence_is_unchanged():
    assert _quote("Droplets burned for two seconds. More text here.") == (
        "Droplets burned for two seconds."
    )


def test_quote_skips_list_numbers_and_headings_that_are_too_short_to_be_sentences():
    assert _quote("Fig. 5. The flame went out at 13 percent oxygen.") == (
        "The flame went out at 13 percent oxygen."
    )


def test_quote_never_uses_a_sentence_the_chunk_cut_off():
    # The chunk ends mid-sentence, so the only candidate has no full stop. Quote it as it is
    # rather than a half sentence dressed up as a whole one, and never return nothing.
    text = "the end of one. Another sentence that stops before the"
    assert _quote(text) == text


def test_quote_of_a_lone_fragment_is_the_fragment_not_nothing():
    assert _quote("the experiment module.") == "the experiment module."


def test_quote_keeps_the_passages_own_words():
    text = "and so on. Flames spread slowly (about 1.2 mm/s) in microgravity! Next."
    assert _quote(text) == "Flames spread slowly (about 1.2 mm/s) in microgravity!"


def test_quotes_of_the_real_chunks_are_whole_sentences_in_the_passages_own_words():
    # The real data this fixes: 17 of the 22 chunks start in the middle of a sentence.
    path = Path(__file__).resolve().parents[1] / "data" / "processed" / "chunks.jsonl"
    chunks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    quoted = summarizer._quote_passages(chunks)["takeaways"]
    assert len(quoted) == len(chunks) >= 22
    for chunk, takeaway in zip(chunks, quoted, strict=True):
        assert takeaway["text"].strip()
        assert takeaway["text"] in chunk["text"]  # word for word, nothing reworded
        # No fragment from mid-sentence. The one allowed exception: a chunk with no whole
        # sentence is quoted in full (none of today's chunks needs that).
        if takeaway["text"] != chunk["text"].strip():
            assert not takeaway["text"][0].islower(), chunk["id"]


def test_timeout_falls_back(use_fake):
    # The error Gemini's client raises when an attempt takes longer than the timeout.
    use_fake(error=httpx.ReadTimeout("timed out"))
    out = summarize_passages(PASSAGES)
    assert [t["chunk_id"] for t in out["takeaways"]] == ["bass-001-p3-c0", "flex-002-p1-c0"]


def test_server_error_falls_back(use_fake):
    # 503 = Gemini overloaded; this is what's left after the client's own retries.
    use_fake(error=errors.ServerError(503, {"error": {"message": "overloaded"}}))
    assert summarize_passages(PASSAGES)["takeaways"][0]["chunk_id"] == "bass-001-p3-c0"


def test_broken_json_falls_back(use_fake):
    use_fake(reply="not json")
    assert summarize_passages(PASSAGES)["takeaways"][1]["text"] == "Droplet burned 2 s."


def test_invented_chunk_id_falls_back(use_fake):
    use_fake(reply=_reply([{"text": "Made up.", "chunk_id": "nope-999"}]))
    texts = [t["text"] for t in summarize_passages(PASSAGES)["takeaways"]]
    assert "Made up." not in texts


def test_prompt_matches_reply_fields():
    # Day 5 (AI): the prompt must name the same fields as REPLY_SCHEMA, or Gemini is told one
    # thing and checked against another. Fails if someone renames a field in only one place.
    # Day 15: renamed from test_prompt_v1_matches_reply_fields; PROMPT_PATH is v2 now.
    prompt = summarizer.PROMPT_PATH.read_text(encoding="utf-8")
    assert "PLACEHOLDER" not in prompt  # the stub from FIF-D05-BE has been replaced
    for field in ("takeaways", "chunk_id", "not_found"):
        assert field in prompt


# --- Day 15 (AI): prompt v2 gets the question --------------------------------------------


def test_question_comes_before_the_passages(use_fake):
    fake = use_fake(reply=_reply([], not_found=True))
    summarize_passages(PASSAGES, question="  How fast does flame spread?  ")
    contents = fake.calls[0]["contents"]
    assert contents.startswith("Question: How fast does flame spread?\n\nPassages:\n\n[bass")
    assert "[flex-002-p1-c0]" in contents


def test_no_question_sends_only_the_passages(use_fake):
    fake = use_fake(reply=_reply([], not_found=True))
    summarize_passages(PASSAGES)
    contents = fake.calls[0]["contents"]
    assert contents.startswith("Passages:\n\n[bass-001-p3-c0]")
    assert "Question:" not in contents


def test_unanswered_question_is_not_found(use_fake):
    # Gemini says the passages don't answer the question -> not found, nothing invented.
    use_fake(reply=_reply([], not_found=True))
    assert summarize_passages(PASSAGES, question="Lithium fires on Mars?") == {
        "takeaways": [],
        "not_found": True,
    }


def test_prompt_v2_has_the_ticket_rules():
    # FIF-D15-AI: takeaways cite their passage, only the passages, "not found" when the
    # passages don't answer the question, even if they are about fire.
    assert summarizer.PROMPT_PATH.name == "summary_v2.txt"
    prompt = summarizer.PROMPT_PATH.read_text(encoding="utf-8")
    assert "Use only the passages" in prompt
    assert "Put that passage's id" in prompt
    assert "none of the passages helps answer the question, set not_found to true" in prompt
    assert "even when the passages are about fire" in prompt
    assert "Question:" in prompt and "Passages:" in prompt  # the layout _build_contents sends
    # v1 stays, unchanged, for comparison (scripts/day15_compare_prompts.py)
    assert (summarizer.PROMPT_PATH.parent / "summary_v1.txt").exists()


class _ClosingModels:
    def __init__(self, reply: str):
        self.reply, self.closed = reply, False

    def generate_content(self, **kwargs):
        if self.closed:  # what httpx does once its client is closed
            raise RuntimeError("Cannot send a request, as the client has been closed.")
        return SimpleNamespace(text=self.reply)


class _ClosingClient:
    """Like the real genai.Client: cleaning it up closes the connection its .models uses."""

    def __init__(self, reply: str):
        self.models = _ClosingModels(reply)

    def __del__(self):
        self.models.closed = True


# --- Day 16 (BE): the call limit and the timeout ------------------------------------------------

QUOTED_FIRST = "Spread was 1.2 mm/s."  # what the fallback quotes from PASSAGES[0]


def _gemini_answer() -> str:
    return _reply([{"text": "Spread is slow.", "chunk_id": "bass-001-p3-c0"}])


def test_over_the_limit_quotes_the_passages_and_does_not_call_gemini(use_fake, monkeypatch):
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "2")
    fake = use_fake(reply=_gemini_answer())
    # Different questions: a repeated one would be answered from the cache (Day 17), not counted.
    results = [summarize_passages(PASSAGES, f"question {n}") for n in range(3)]
    assert len(fake.calls) == 2  # the third summary never reached Gemini
    assert [r["takeaways"][0]["text"] for r in results] == [
        "Spread is slow.",
        "Spread is slow.",
        QUOTED_FIRST,  # quoted, and no error: the app keeps working
    ]
    assert results[2]["not_found"] is False


def test_the_default_limit_is_10_calls_a_minute(use_fake):
    fake = use_fake(reply=_gemini_answer())
    for n in range(11):
        summarize_passages(PASSAGES, f"question {n}")  # different: a repeat wouldn't count
    assert len(fake.calls) == 10


def test_a_slot_frees_up_when_the_minute_has_passed(use_fake, monkeypatch):
    class Clock:
        now = 0.0

        def __call__(self) -> float:
            return self.now

    clock = Clock()
    monkeypatch.setattr(summarizer, "_limiter", RateLimiter(1, 60, clock=clock))
    fake = use_fake(reply=_gemini_answer())
    summarize_passages(PASSAGES, "first")
    summarize_passages(PASSAGES, "second")  # refused: quoted
    assert len(fake.calls) == 1
    clock.now += 60
    summarize_passages(PASSAGES, "second")  # the same question, now with a free slot
    assert len(fake.calls) == 2


def test_calls_that_never_reach_gemini_do_not_use_up_the_limit(use_fake, monkeypatch):
    # No passages, and no key, both return before Gemini, so neither may count against it.
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "1")
    monkeypatch.delenv("GEMINI_API_KEY")
    for _ in range(3):
        summarize_passages([])
        summarize_passages(PASSAGES)  # no key: quoted
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")  # a key now (use_fake only swaps the client)
    fake = use_fake(reply=_gemini_answer())
    # The limit is 1, and still unused, so this call reaches Gemini.
    assert summarize_passages(PASSAGES)["takeaways"][0]["text"] == "Spread is slow."
    assert len(fake.calls) == 1


def test_a_gemini_call_ends_within_about_30_seconds(monkeypatch):
    # Before Day 16: 3 tries of 30 s, about 95 s with the waits, while the page says "up to 30".
    # Checks what is handed to Gemini's client. The 1-2 s wait between tries comes on top.
    seen = {}

    def fake_client(**kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(summarizer.genai, "Client", fake_client)
    summarizer._get_client("test-key")
    options = seen["http_options"]
    assert options.timeout == summarizer.TIMEOUT_MS == 15_000  # milliseconds, per attempt
    assert options.retry_options.attempts == summarizer.ATTEMPTS == 2  # first try + 1 retry
    assert summarizer.TIMEOUT_MS / 1000 * summarizer.ATTEMPTS <= 30


def test_client_stays_open_for_the_whole_call(monkeypatch):
    # Day 15 (AI): with the client written inline, Python cleaned it up before the request was
    # sent, and every real Gemini call crashed. Each call here gets a fresh client that nothing
    # else holds, as in production (the FakeClient above is kept alive by the test).
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    reply = _reply([{"text": "Spread is slow.", "chunk_id": "bass-001-p3-c0"}])
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: _ClosingClient(reply))
    assert summarize_passages(PASSAGES)["takeaways"][0]["text"] == "Spread is slow."
