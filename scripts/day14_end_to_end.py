"""Day 14 (BE): run ingest -> search -> table once with the REAL embedding model.

Run from the project root:
    uv run python scripts/day14_end_to_end.py
No API key needed. The first run downloads the model (~90 MB). Stops with an error on the first
step that fails. tests/test_end_to_end.py covers the same path in CI with a fake model; only this
script checks real scores, including the MIN_SCORE "no match" cutoff.

Everything is written to a temporary folder, so the committed chunks.jsonl, artifacts/index/ and
artifacts/speed.log are left exactly as they were."""

import tempfile
from pathlib import Path

from flame_in_freefall import api, ingest, speed
from flame_in_freefall.config import setup_logging
from flame_in_freefall.retrieval_eval import QUESTIONS

# Questions 9 and 10 are the ones the reports can't answer (retrieval_eval.py), so leave them out.
ANSWERABLE = QUESTIONS[:8]
OFF_TOPIC = "What is the best topping for a pizza?"

log = setup_logging()


def _check(passed: bool, message: str) -> None:
    # SystemExit makes the command end with an error code, so a failure can't be missed.
    if not passed:
        raise SystemExit(f"FAILED: {message}")


with tempfile.TemporaryDirectory() as tmp:  # deleted automatically at the end of this block
    folder = Path(tmp)
    # Point the backend at the temporary folder (see the note at the top).
    api.CHUNKS = folder / "chunks.jsonl"
    api.INDEX = folder / "index"
    speed.SPEED_LOG = folder / "speed.log"

    done = ingest.run(force=True, chunks=api.CHUNKS, index=api.INDEX)
    _check(done == {"chunks": "built", "index": "built"}, f"ingest did not build: {done}")

    for question in ANSWERABLE:
        results = api.search(question)
        _check(bool(results), f"no results for: {question}")
        top = results[0]
        rows = api.get_table({"experiment": top["experiment"]})
        _check(bool(rows), f"no table rows for experiment {top['experiment']}")
        log.info("%.3f  %-10s %3d rows  %s", top["score"], top["experiment"], len(rows), question)

    off_topic = api.search(OFF_TOPIC)
    _check(off_topic == [], f"off-topic question should find nothing, got {len(off_topic)}")
    log.info("no match, as expected: %s", OFF_TOPIC)

log.info("End-to-end check passed: ingest -> search -> table.")
