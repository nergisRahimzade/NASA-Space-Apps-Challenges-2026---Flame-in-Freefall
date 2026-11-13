"""Day 17 (AI): turn the Day 16 recording into the committed test fixture.

scripts/day16_test_summaries.py asks the real Gemini 22 questions and saves its exact replies in
artifacts/day16_replies.json (git-ignored, so only on the laptop that ran it). CI has no key and
no network, so tests/test_summary_accuracy.py replays those replies. This script copies what the
tests need into tests/fixtures/summaries.json, which is committed:

    uv run python scripts/day17_record_summaries.py

It calls no Gemini and writes no reply of its own: every "raw_reply" is copied from the
recording, and the script refuses a recording that holds a quoting fallback or a Gemini error
(those aren't Gemini's answers). To re-record after the chunks or the prompt change, run the Day 16
script again (needs a key, ~32 calls), then run this one."""

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # so the script runs without installing the package

from flame_in_freefall.config import setup_logging  # noqa: E402

RECORDING = ROOT / "artifacts" / "day16_replies.json"
FIXTURE = ROOT / "tests" / "fixtures" / "summaries.json"

log = logging.getLogger("flame_in_freefall.day17")


def _entry(record: dict) -> dict:
    # Only what the replay needs. The passages themselves are loaded from chunks.jsonl by id, and
    # the hashes say whether they are still the passages Gemini saw.
    return {
        "id": f"{record['label']}-{record['run']}",  # e.g. "Q4-picked", "Q4-default"
        "question": record["question"],
        "experiment": record["experiment"],  # None = nothing picked (the app's default)
        "evidence": record["evidence"],  # phrases that answer it; [] = the reports don't
        "passage_ids": [p["id"] for p in record["passages"]],
        "passage_sha256": [p["sha256"] for p in record["passages"]],
        "raw_reply": record["raw_reply"],
        "model": record["model"],
        "prompt": record["prompt"],
        "recorded": record["recorded"],
    }


def build(records: list[dict]) -> list[dict]:
    """The fixture entries for a recording. Questions with no passages never reach Gemini (the
    app shows "no match"), so they have nothing to replay and are left out."""
    entries = []
    for r in records:
        if not r["passages"]:
            continue
        who = f"{r['label']} ({r['run']})"
        if r["error"] or r["fallback"] or not isinstance(r["raw_reply"], str):
            raise ValueError(f"{who} isn't a Gemini answer (error, quoting fallback or no reply)")
        json.loads(r["raw_reply"])  # a reply that isn't JSON would be a hand-made or broken one
        entries.append(_entry(r))
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("the recording has the same question and run twice")
    return entries


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build tests/fixtures/summaries.json.")
    parser.add_argument("--recording", type=Path, default=RECORDING, help="the Day 16 JSON")
    args = parser.parse_args(argv)
    setup_logging()
    if not args.recording.exists():
        sys.exit(f"No recording at {args.recording}. Run scripts/day16_test_summaries.py first.")
    entries = build(json.loads(args.recording.read_text(encoding="utf-8")))
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    # indent=2 and a final newline: a re-recording shows up as a readable diff in a PR.
    FIXTURE.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info("Wrote %d recorded answers to %s", len(entries), FIXTURE)


if __name__ == "__main__":
    main()
