"""Day 17 (AI): the summary accuracy tests, in CI, with Gemini's real answers replayed.

CI has no key and no network. So each test here replays an answer the real Gemini gave on
2026-11-12 (recorded by scripts/day16_test_summaries.py, copied into tests/fixtures/summaries.json
by scripts/day17_record_summaries.py) through the real api.summarize(), with a fake client that
hands back the recorded reply. Per recorded question:
- the answer is Gemini's, not the quoting fallback, and it was sent the recorded passages;
- a question whose passages hold the evidence cites a passage that holds it;
- a question whose passages don't (Q6, Q9, Q10, H7) gets "not found" and no takeaways;
- claim_check finds no number or experiment name that the cited passage lacks.

What this proves: our parsing and checks accept real Gemini answers, and those answers match their
passages. What it can NOT prove: that Gemini still answers this way. A changed prompt text, model
or Gemini itself is not noticed until someone re-records (the fixture names the prompt file, so a
renamed prompt is noticed). The opt-in live test at the bottom is how to check that by hand:

    RUN_LIVE=1 GEMINI_MODEL=gemini-flash-lite-latest uv run --env-file .env pytest -m live

To re-record: run scripts/day16_test_summaries.py (needs a key, ~32 Gemini calls), then
scripts/day17_record_summaries.py, and commit the new fixture."""

import hashlib
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from flame_in_freefall import api, summarizer
from flame_in_freefall.claim_check import check_claims
from flame_in_freefall.retrieval_eval import contains_evidence

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
FIXTURE = ROOT / "tests" / "fixtures" / "summaries.json"
RERECORD = (
    "Re-record: run scripts/day16_test_summaries.py (needs a Gemini key), then "
    "scripts/day17_record_summaries.py, and commit tests/fixtures/summaries.json."
)

# Opt-in live test (bottom of the file). conftest.py removes GEMINI_API_KEY for every test, so the
# key is read here, when the file is imported, and put back inside the live test. Without
# RUN_LIVE=1 (and a key) nothing here is read and the test is skipped.
LIVE = os.getenv("RUN_LIVE") == "1" and bool(os.getenv("GEMINI_API_KEY"))
LIVE_KEY = os.getenv("GEMINI_API_KEY") if LIVE else None
LIVE_MODEL = os.getenv("GEMINI_MODEL") if LIVE else None

# A flag claim_check raises on a real recorded answer that a human judged to be fine, with the
# reason. The D16 hand check found none in 75 takeaways (tests/summaries.md), so this is empty:
# {"Q4-picked": {"takeaway 1 (flex2-p1-c3): numbers not in the passage: 3": "reason"}}.
KNOWN_FALSE_ALARMS: dict[str, dict[str, str]] = {}


def _load_chunks(path: Path = CHUNKS) -> dict[str, dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    chunks = [json.loads(line) for line in lines if line.strip()]
    return {c["id"]: c for c in chunks}


def _load_entries() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stale_reasons(entry: dict, chunks: dict[str, dict]) -> list[str]:
    """Why the recording no longer matches the repo, one line each; empty = still valid."""
    reasons = []
    for chunk_id, recorded in zip(entry["passage_ids"], entry["passage_sha256"], strict=True):
        if chunk_id not in chunks:
            reasons.append(f"{entry['id']}: chunk {chunk_id!r} no longer exists")
        elif _sha256(chunks[chunk_id]["text"]) != recorded:
            reasons.append(f"{entry['id']}: the text of chunk {chunk_id!r} has changed")
    if entry["prompt"] != summarizer.PROMPT_PATH.name:
        reasons.append(
            f"{entry['id']}: recorded with {entry['prompt']}, the app now uses "
            f"{summarizer.PROMPT_PATH.name}"
        )
    return reasons


CHUNKS_NOW = _load_chunks()
ENTRIES = _load_entries()


def _passages(entry: dict, chunks: dict[str, dict] = CHUNKS_NOW) -> list[dict]:
    # The same passages, in the same order, that Gemini was sent. Copies: summarize() may not
    # change them, but a test must not be able to change the chunks for the next one.
    return [dict(chunks[i]) for i in entry["passage_ids"]]


def _holds_evidence(passage: dict, entry: dict) -> bool:
    return contains_evidence(entry["evidence"], passage["text"])


def _answerable(entry: dict) -> bool:
    # Q9 and Q10 have no evidence phrase (the reports don't cover them). Q6 and H7 have one, but
    # the passages retrieved for them don't contain it, so "not found" is the right answer.
    return any(_holds_evidence(p, entry) for p in _passages(entry))


# Collection must not dereference missing chunks or classify changed passages. The dedicated
# staleness test reports the problem; the general replay cases still include stale entries so
# _replay() can skip them with an explanation.
CURRENT_ENTRIES = [e for e in ENTRIES if not _stale_reasons(e, CHUNKS_NOW)]
ANSWERABLE = [e for e in CURRENT_ENTRIES if _answerable(e)]
NOT_ANSWERABLE = [e for e in CURRENT_ENTRIES if not _answerable(e)]


class RecordedGemini:
    """A fake Gemini client that hands back the recorded reply and notes what it was sent."""

    def __init__(self, reply: str):
        self.reply, self.contents, self.calls = reply, [], 0
        self.models = self  # so client.models.generate_content(...) works like the real one

    def generate_content(self, **kwargs):
        self.calls += 1
        self.contents.append(kwargs["contents"])
        return SimpleNamespace(text=self.reply)


def _replay(
    entry: dict, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict, list[dict], RecordedGemini]:
    stale = _stale_reasons(entry, CHUNKS_NOW)
    if stale:  # test_the_recorded_passages_are_still_the_chunks fails with the full explanation
        pytest.skip("recording is out of date: " + stale[0])
    client = RecordedGemini(entry["raw_reply"])
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")  # conftest.py removed any real one
    monkeypatch.setenv("GEMINI_MODEL", entry["model"])
    # The lambda keeps `client` alive for the whole call (see test_client_stays_open_for_the_
    # whole_call in test_summarizer.py for why that matters).
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: client)
    passages = _passages(entry)
    return api.summarize(passages, question=entry["question"]), passages, client


def _assert_not_the_fallback(summary: dict, passages: list[dict]) -> None:
    assert summary != summarizer._quote_passages(passages), (
        "got the quoting fallback, not Gemini's answer"
    )


def _assert_answers_from_the_evidence(summary: dict, passages: list[dict], entry: dict) -> None:
    by_id = {p["id"]: p for p in passages}
    assert summary["not_found"] is False and summary["takeaways"]
    assert any(_holds_evidence(by_id[t["chunk_id"]], entry) for t in summary["takeaways"]), (
        f"no takeaway cites a passage holding {entry['evidence']}"
    )


def _assert_not_found(summary: dict) -> None:
    assert summary == {"takeaways": [], "not_found": True}


def _assert_no_unexplained_flags(summary: dict, passages: list[dict], entry: dict) -> None:
    flags = check_claims(summary, passages)
    unexplained = [f for f in flags if f not in KNOWN_FALSE_ALARMS.get(entry["id"], {})]
    assert unexplained == []


# --- the fixture itself -----------------------------------------------------------------------


def test_the_fixture_covers_the_eight_plus_questions_and_the_no_answer_ones():
    questions = {e["question"] for e in ENTRIES}
    assert len(questions) >= 8  # the ticket: "turn the 8 questions into pytest"
    labels = {e["id"].split("-")[0] for e in ENTRIES}
    assert {"Q9", "Q10"} <= labels  # the questions the reports don't answer
    if len(CURRENT_ENTRIES) != len(ENTRIES):
        pytest.skip("answerability coverage needs a current recording. " + RERECORD)
    assert len(ANSWERABLE) >= 8 and len(NOT_ANSWERABLE) >= 4  # Q6, Q9, Q10 and H7 at least


def test_the_fixture_holds_recorded_json_replies():
    for e in ENTRIES:
        reply = json.loads(e["raw_reply"])
        assert set(reply) == {"takeaways", "not_found"}, e["id"]


# --- staleness: the recording must still match the repo ---------------------------------------


def test_the_recorded_passages_are_still_the_chunks():
    stale = [reason for e in ENTRIES for reason in _stale_reasons(e, CHUNKS_NOW)]
    assert not stale, "\n".join(stale) + "\n" + RERECORD


# The checks below use a made-up recording, so they say the same thing whatever state the repo's
# own chunks and prompt are in (when those are stale, only the test above should complain).
def _made_up_entry() -> tuple[dict, dict[str, dict]]:
    entry = {
        "id": "X-picked",
        "passage_ids": ["x-p1-c0"],
        "passage_sha256": [_sha256("The recorded text.")],
        "prompt": summarizer.PROMPT_PATH.name,
    }
    return entry, {"x-p1-c0": {"id": "x-p1-c0", "text": "The recorded text."}}


def test_an_unchanged_recording_is_not_stale():
    entry, chunks = _made_up_entry()
    assert _stale_reasons(entry, chunks) == []


def test_an_edited_chunk_is_noticed():
    entry, chunks = _made_up_entry()
    chunks["x-p1-c0"]["text"] += " One word added."
    [reason] = _stale_reasons(entry, chunks)
    assert "x-p1-c0" in reason and "changed" in reason


def test_a_removed_chunk_is_noticed():
    entry, _ = _made_up_entry()
    [reason] = _stale_reasons(entry, {})
    assert "x-p1-c0" in reason and "no longer exists" in reason


def test_a_renamed_prompt_is_noticed(monkeypatch: pytest.MonkeyPatch):
    entry, chunks = _made_up_entry()
    # Not "summary_v3.txt": that is the likely next real prompt, and if the app used it, this
    # made-up entry would be recorded with it too and nothing would look renamed.
    monkeypatch.setattr(summarizer, "PROMPT_PATH", Path("summary_renamed_for_test.txt"))
    [reason] = _stale_reasons(entry, chunks)
    assert "summary_renamed_for_test.txt" in reason


# --- the replays: one case per recorded question ----------------------------------------------


@pytest.fixture(params=ENTRIES, ids=lambda e: e["id"])
def any_entry(request) -> dict:
    return request.param


@pytest.fixture(params=ANSWERABLE, ids=lambda e: e["id"])
def answerable_entry(request) -> dict:
    return request.param


@pytest.fixture(params=NOT_ANSWERABLE, ids=lambda e: e["id"])
def not_answerable_entry(request) -> dict:
    return request.param


def test_the_replay_is_geminis_answer_to_the_recorded_passages(
    any_entry: dict, monkeypatch: pytest.MonkeyPatch
):
    summary, passages, client = _replay(any_entry, monkeypatch)
    assert client.calls == 1
    sent = client.contents[0]
    assert sent.startswith(f"Question: {any_entry['question']}")
    # The passages go in as "[id] (source, p. N)" headings, in the recorded order.
    assert re.findall(r"^\[([^\]]+)\] \(", sent, flags=re.MULTILINE) == any_entry["passage_ids"]
    _assert_not_the_fallback(summary, passages)


def test_a_question_the_passages_answer_cites_the_evidence(
    answerable_entry: dict, monkeypatch: pytest.MonkeyPatch
):
    summary, passages, _ = _replay(answerable_entry, monkeypatch)
    _assert_answers_from_the_evidence(summary, passages, answerable_entry)


def test_a_question_the_passages_cant_answer_gives_not_found(
    not_answerable_entry: dict, monkeypatch: pytest.MonkeyPatch
):
    summary, passages, _ = _replay(not_answerable_entry, monkeypatch)
    _assert_not_found(summary)


def test_no_takeaway_has_a_number_or_experiment_its_passage_lacks(
    any_entry: dict, monkeypatch: pytest.MonkeyPatch
):
    summary, passages, _ = _replay(any_entry, monkeypatch)
    _assert_no_unexplained_flags(summary, passages, any_entry)


# --- opt-in: ask the real Gemini (never in CI) ------------------------------------------------


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="asks the real Gemini: set RUN_LIVE=1 and GEMINI_API_KEY")
@pytest.mark.parametrize("entry_id", ["Q1-picked", "Q9-picked"])  # one answerable, one not
def test_live_gemini_still_answers_like_the_recording(
    entry_id: str, monkeypatch: pytest.MonkeyPatch
):
    entry = next(e for e in ENTRIES if e["id"] == entry_id)
    assert not _stale_reasons(entry, CHUNKS_NOW), RERECORD
    monkeypatch.setenv("GEMINI_API_KEY", LIVE_KEY)
    if LIVE_MODEL:
        monkeypatch.setenv("GEMINI_MODEL", LIVE_MODEL)
    passages = _passages(entry)
    summary = api.summarize(passages, question=entry["question"])  # the real client: costs a call
    # An overloaded model quotes the passages instead, and that would look like an answer.
    _assert_not_the_fallback(summary, passages)
    if _answerable(entry):
        _assert_answers_from_the_evidence(summary, passages, entry)
    else:
        _assert_not_found(summary)
    _assert_no_unexplained_flags(summary, passages, entry)
