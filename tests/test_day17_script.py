"""FIF-D17-AI: the fixture builder copies real Gemini replies and refuses anything else.

Made-up records only: no recording, no key, no network."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script() -> ModuleType:
    # scripts/ isn't a package, so the file is loaded by its path.
    spec = importlib.util.spec_from_file_location(
        "day17_record_summaries", ROOT / "scripts" / "day17_record_summaries.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _load_script()


def _record(label: str = "Q1", run: str = "picked", **changes) -> dict:
    record = {
        "label": label,
        "run": run,
        "question": "What gases were tested?",
        "experiment": None,
        "evidence": ["CO2, He, and SF6"],
        "model": "model-x",
        "prompt": "summary_v2.txt",
        "recorded": "2026-11-12",
        # Pretty-printed with a final newline, like Gemini's: "exactly as recorded" includes that.
        "raw_reply": json.dumps({"takeaways": [], "not_found": True}, indent=2) + "\n",
        "error": None,
        "fallback": False,
        "passages": [{"id": "flex-p1-c0", "experiment": "FLEX", "sha256": "ab" * 32}],
        "tokens": {"input": 10, "output": 2},  # not needed by the tests, so not copied
        "summary": {"takeaways": [], "not_found": True},
    }
    record.update(changes)
    return record


def test_an_entry_copies_the_reply_and_the_passage_hashes_unchanged():
    [entry] = script.build([_record()])
    assert entry["id"] == "Q1-picked"
    assert entry["raw_reply"] == _record()["raw_reply"]
    assert entry["passage_ids"] == ["flex-p1-c0"] and entry["passage_sha256"] == ["ab" * 32]
    assert set(entry) == {
        "id", "question", "experiment", "evidence", "passage_ids", "passage_sha256",
        "raw_reply", "model", "prompt", "recorded",
    }  # fmt: skip


def test_a_question_with_no_passages_has_nothing_to_replay():
    # The app shows "no match" for it and never calls Gemini (H4 in the Day 16 recording).
    assert script.build([_record(passages=[], raw_reply=None, summary=None)]) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"fallback": True},  # the quoting fallback, not Gemini's words
        {"error": "ReadTimeout: too slow"},
        {"raw_reply": None},
        {"raw_reply": "Sorry, I can't help with that."},  # not JSON: not a real structured reply
    ],
)
def test_anything_that_isnt_a_gemini_answer_is_refused(changes: dict):
    with pytest.raises((ValueError, json.JSONDecodeError)):
        script.build([_record(**changes)])


def test_the_same_question_and_run_twice_is_refused():
    with pytest.raises(ValueError, match="twice"):
        script.build([_record(), _record()])


def test_the_picked_and_default_runs_of_a_question_are_both_kept():
    entries = script.build([_record(run="picked"), _record(run="default")])
    assert [e["id"] for e in entries] == ["Q1-picked", "Q1-default"]
