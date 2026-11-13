"""FIF-D17-AI, Day 17: stale recordings must collect and report how to re-record.

test_summary_accuracy.py reads the chunks and the fixture when it is imported. These tests import
it again with a made-up recording and made-up chunks put in place of those two reads, then make
the recording stale in different ways. Nothing on disk is read for them or changed, so the
result doesn't depend on whether the real recording is current (if it isn't,
test_the_recorded_passages_are_still_the_chunks is the one test that says so).
"""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

from flame_in_freefall import summarizer

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "summaries.json"
# Q1-Q8 can be answered from their passage, Q9-Q12 can't: enough for the coverage test's minimums
# (8 questions, 8 answerable, 4 not, Q9 and Q10 present).
ANSWERABLE_LABELS = [f"Q{n}" for n in range(1, 9)]
NOT_ANSWERABLE_LABELS = ["Q9", "Q10", "Q11", "Q12"]


def _made_up_recording() -> tuple[list[dict], list[dict]]:
    """(chunks, fixture entries): one passage per question, recorded with today's prompt."""
    chunks, entries = [], []
    for n, label in enumerate(ANSWERABLE_LABELS + NOT_ANSWERABLE_LABELS, start=1):
        chunk = {"id": f"x-p1-c{n}", "text": f"Recorded passage {n}.", "source": "X", "page": 1}
        chunks.append(chunk)
        entries.append(
            {
                "id": f"{label}-picked",
                "question": f"Made-up question {n}?",
                "experiment": None,
                "evidence": [chunk["text"]] if label in ANSWERABLE_LABELS else [],
                "passage_ids": [chunk["id"]],
                "passage_sha256": [hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()],
                "raw_reply": json.dumps({"takeaways": [], "not_found": True}),
                "model": "made-up-model",
                "prompt": summarizer.PROMPT_PATH.name,
                "recorded": "2026-11-12",
            }
        )
    return chunks, entries


def _collect_with(chunks: list[dict], entries: list[dict]) -> ModuleType:
    # Import test_summary_accuracy.py as if these were the chunks and the fixture on disk.
    made_up = {
        CHUNKS_PATH: "\n".join(json.dumps(c) for c in chunks),
        FIXTURE_PATH: json.dumps(entries),
    }
    original_read = Path.read_text

    def read(path: Path, *args, **kwargs) -> str:
        return made_up[path] if path in made_up else original_read(path, *args, **kwargs)

    spec = importlib.util.spec_from_file_location(
        "accuracy_collection_probe", ROOT / "tests" / "test_summary_accuracy.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.object(Path, "read_text", read):
        spec.loader.exec_module(module)
    return module


def test_an_unchanged_made_up_recording_is_current(monkeypatch: pytest.MonkeyPatch):
    # The control: without it, the test below could pass because the made-up data is always stale.
    monkeypatch.setenv("RUN_LIVE", "0")  # a collection probe, never a request for live tests
    module = _collect_with(*_made_up_recording())
    module.test_the_recorded_passages_are_still_the_chunks()  # doesn't raise
    module.test_the_fixture_covers_the_eight_plus_questions_and_the_no_answer_ones()
    assert len(module.ANSWERABLE) == 8 and len(module.NOT_ANSWERABLE) == 4


@pytest.mark.parametrize("change", ["removed", "edited", "prompt", "all_removed"])
def test_stale_recordings_collect_and_report_the_rerecord_steps(
    monkeypatch: pytest.MonkeyPatch, change: str
):
    monkeypatch.setenv("RUN_LIVE", "0")  # a collection probe, never a request for live tests
    chunks, entries = _made_up_recording()
    entry = entries[0]
    chunk_id = entry["passage_ids"][0]
    if change == "removed":
        chunks = [c for c in chunks if c["id"] != chunk_id]
    elif change == "edited":
        next(c for c in chunks if c["id"] == chunk_id)["text"] += " Changed."
    elif change == "all_removed":
        chunks = []
    else:
        monkeypatch.setattr(summarizer, "PROMPT_PATH", Path("summary_collection_probe.txt"))

    module = _collect_with(chunks, entries)  # collecting must not crash (it used to: KeyError)

    # The dedicated test fails with instructions...
    with pytest.raises(AssertionError, match="Re-record:") as error:
        module.test_the_recorded_passages_are_still_the_chunks()
    if change != "prompt":
        assert chunk_id in str(error.value)
    # ...while the replays and the coverage count skip instead of failing for the same reason.
    with pytest.raises(pytest.skip.Exception, match="recording is out of date"):
        module._replay(entry, monkeypatch)
    with pytest.raises(pytest.skip.Exception):
        module.test_the_fixture_covers_the_eight_plus_questions_and_the_no_answer_ones()
    # Only entries that are still current get classified as answerable or not.
    for classified in module.ANSWERABLE + module.NOT_ANSWERABLE:
        assert not module._stale_reasons(classified, module.CHUNKS_NOW)
