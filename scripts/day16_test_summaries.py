"""Day 16 (AI): test summaries on 22 questions with the real Gemini, and check every claim.

Run from the project root (needs GEMINI_API_KEY in .env; about 32 Gemini calls, ~5 minutes):
    uv run --env-file .env python scripts/day16_test_summaries.py
If the default model only answers 503 ("high demand"), set GEMINI_MODEL=gemini-flash-lite-latest
in front of the command; the model is recorded either way.

Two runs, through the real search() and summarize(), like the app:
- "picked": all 22 questions (Q1-Q10, the 10 held out as H1-H10, the 2 BASS-II ones as B1-B2),
  with the experiment picked when the question names one (as on Days 13 and 15).
- "default": only the questions that name an experiment, with none picked (the app's default),
  so passages from other experiments come along. That tests prompt rule 3: never give one
  experiment's numbers as another's.
For every takeaway: the passage it cites, whether that passage holds the evidence phrase, and
what claim_check found. Writes artifacts/day16_summaries_draft.md (judged by hand into
tests/summaries.md) and artifacts/day16_replies.json (Gemini's exact replies, which
FIF-D17-AI turns into replay tests).

--prompt summary_v3.txt runs another prompt file from src/prompts/, and --only Q1 Q8 runs just
those questions (both runs), to compare prompts on the same passages. Partial runs add
_only_Q1_Q8 to their output names so they can't overwrite the full recording. A run that stops
part-way (Ctrl+C, a crash) still saves what finished, as ..._stopped_after_N_*."""

import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

from flame_in_freefall import api, summarizer
from flame_in_freefall.claim_check import check_claims
from flame_in_freefall.config import get_settings, setup_logging
from flame_in_freefall.retrieval_eval import (
    EVIDENCE,
    HELD_OUT,
    NAMED_EXPERIMENT,
    QUESTIONS,
    SUMMARY_EXTRA,
    contains_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
# 7 s between calls keeps us at about 8 a minute, under summarizer's limit of 10 (FIF-D16-BE),
# which would otherwise quote some of the summaries instead of asking Gemini.
PAUSE_S = 7

log = setup_logging()

# Every question once: (label, question, evidence phrases, experiment it names or None).
ITEMS = (
    [(f"Q{n}", q, EVIDENCE[n], NAMED_EXPERIMENT.get(n)) for n, q in enumerate(QUESTIONS, 1)]
    + [(f"H{n}", q, phrases, named) for n, (q, phrases, named) in enumerate(HELD_OUT, 1)]
    + [(f"B{n}", q, phrases, named) for n, (q, phrases, named) in enumerate(SUMMARY_EXTRA, 1)]
)


class _RecordingClient:
    """Wraps the real Gemini client and keeps the exact reply text and token counts of the call.

    It holds the real client for the whole call, so the Day 15 "client has been closed" bug
    can't come back through here."""

    def __init__(self, client, record: dict):
        self._client, self._record = client, record
        self.models = self  # so .models.generate_content(...) works like the real client

    def generate_content(self, **kwargs):
        try:
            response = self._client.models.generate_content(**kwargs)
        except Exception as e:  # recorded, then raised again so summarize() falls back as usual
            self._record["error"] = f"{type(e).__name__}: {e}"
            raise
        self._record["raw_reply"] = response.text
        usage = response.usage_metadata
        self._record["tokens"] = {
            "input": usage.prompt_token_count if usage else None,
            "output": usage.candidates_token_count if usage else None,
        }
        return response


def _sha256(text: str) -> str:
    # Lets the replay tests notice a passage whose text changed after this recording.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_one(label, question, phrases, filter_name, run, model) -> dict:
    record = {
        "label": label,
        "run": run,
        "question": question,
        "experiment": filter_name,
        "evidence": phrases,
        "model": model,
        "prompt": summarizer.PROMPT_PATH.name,
        "recorded": datetime.date.today().isoformat(),
        "raw_reply": None,
        "error": None,
        "tokens": None,
    }
    passages = api.search(question, experiment=filter_name)
    record["passages"] = [
        {"id": p["id"], "experiment": p.get("experiment"), "sha256": _sha256(p["text"])}
        for p in passages
    ]
    if not passages:  # "no match": the app shows its empty state and never calls summarize()
        record.update(summary=None, fallback=False, seconds=0.0, claims=[], answer=[])
        return record
    # Day 17: a remembered answer makes no Gemini call, so there'd be no reply to record.
    summarizer.clear_summary_cache()
    real_get_client = summarizer._get_client
    summarizer._get_client = lambda key: _RecordingClient(real_get_client(key), record)
    try:
        start = time.perf_counter()
        summary = api.summarize(passages, question=question)
        record["seconds"] = round(time.perf_counter() - start, 2)
    finally:
        summarizer._get_client = real_get_client
    by_id = {p["id"]: p for p in passages}
    record["summary"] = summary
    # A quoted fallback is word for word from the passages, so it can't be judged as Gemini's.
    record["fallback"] = summary == summarizer._quote_passages(passages)
    record["claims"] = check_claims(summary, passages)
    record["answer"] = [
        bool(phrases) and contains_evidence(phrases, by_id[t["chunk_id"]]["text"])
        for t in summary["takeaways"]
    ]
    return record


def _draft(records: list[dict]) -> str:
    lines = [
        f"Model: {records[0]['model']} · prompt: {records[0]['prompt']} · {records[0]['recorded']}",
        "",
        "| Label | Run | Filter | Passages | Not found | Takeaways | Cite answer | Claim flags "
        "| Fallback | Seconds |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        s = r["summary"]
        lines.append(
            f"| {r['label']} | {r['run']} | {r['experiment'] or 'all'} | {len(r['passages'])} | "
            f"{'no match' if s is None else s['not_found']} | "
            f"{0 if s is None else len(s['takeaways'])} | {sum(r['answer'])} | "
            f"{len(r['claims'])} | {r['fallback']} | {r['seconds']} |"
        )
    for r in records:
        lines += ["", f"## {r['label']} ({r['run']}): {r['question']}", ""]
        lines.append(f"Passages: {', '.join(p['id'] for p in r['passages']) or 'none'}")
        if r["error"]:
            lines.append(f"Gemini error: {r['error']}")
        for t, hit in zip(r["summary"]["takeaways"] if r["summary"] else [], r["answer"]):
            lines.append(f"- `{t['chunk_id']}`{' [answer]' if hit else ''}: {t['text']}")
        lines += [f"- claim_check: {c}" for c in r["claims"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Test summaries on the real Gemini.")
    parser.add_argument("--prompt", help="prompt file in src/prompts/, e.g. summary_v3.txt")
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[item[0] for item in ITEMS],
        help="labels to run, e.g. Q1 Q8 (default: all)",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    if not settings.gemini_api_key:
        sys.exit("No GEMINI_API_KEY: run with  uv run --env-file .env python " + __file__)
    if args.prompt:
        summarizer.PROMPT_PATH = summarizer.PROMPT_PATH.parent / args.prompt
        if not summarizer.PROMPT_PATH.exists():
            sys.exit(f"No prompt file {summarizer.PROMPT_PATH}")
    items = [i for i in ITEMS if not args.only or i[0] in args.only]
    jobs = [(*i[:3], i[3], "picked") for i in items]
    jobs += [(*i[:3], None, "default") for i in items if i[3]]  # named ones, nothing picked
    log.info(
        "%d searches, up to %d Gemini calls, model %s", len(jobs), len(jobs), settings.gemini_model
    )

    stem = "day16" + (f"_{Path(args.prompt).stem}" if args.prompt else "")
    if args.only:
        # Keep the complete, costly recording available for Day 17 replay fixtures.
        stem += "_only_" + "_".join(item[0] for item in items)

    records = []
    finished = False
    try:
        for label, question, phrases, filter_name, run in jobs:
            record = run_one(label, question, phrases, filter_name, run, settings.gemini_model)
            records.append(record)
            s = record["summary"]
            log.info(
                "%s %s: %s, %d takeaways, %d claim flags%s",
                label,
                run,
                "no match" if s is None else f"not_found={s['not_found']}",
                0 if s is None else len(s["takeaways"]),
                len(record["claims"]),
                " (FALLBACK)" if record["fallback"] else "",
            )
            if s is not None:
                time.sleep(PAUSE_S)
        finished = True
    finally:
        # Every answer cost a Gemini call, so save what finished even if the run stops part-way
        # (Ctrl+C, a crash). Under another name, so a partial run never replaces a complete one.
        if records:
            _save(records, stem if finished else f"{stem}_stopped_after_{len(records)}")


def _save(records: list[dict], stem: str) -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / f"{stem}_replies.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / f"{stem}_summaries_draft.md").write_text(_draft(records), encoding="utf-8")
    fallbacks = sum(r["fallback"] for r in records)
    log.info("Saved %d records, %d fallbacks -> artifacts/%s_*", len(records), fallbacks, stem)


if __name__ == "__main__":
    main()
