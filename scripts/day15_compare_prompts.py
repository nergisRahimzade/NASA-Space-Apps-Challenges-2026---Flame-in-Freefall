"""Day 15 (AI): compare summary prompt v1 and v2 on the real Gemini, for the 10 questions.

Run from the project root (needs GEMINI_API_KEY in .env, about 20 Gemini calls):
    uv run --env-file .env python scripts/day15_compare_prompts.py

For each question: search() with the experiment picked (as on Day 13), then summarize the same
passages twice. v1 gets only the passages, as before Day 15. v2 also gets the question. Writes
every takeaway to artifacts/day15_prompts_draft.md to read by hand; the judged copy lives in
tests/prompt_v2.md. "fallback" means Gemini failed and the passages were quoted instead.
A takeaway is marked "answer" when its cited passage holds the evidence phrase (retrieval_eval)."""

import sys
import time
from pathlib import Path

from flame_in_freefall import api, summarizer
from flame_in_freefall.config import get_settings, setup_logging
from flame_in_freefall.retrieval_eval import EVIDENCE, NAMED_EXPERIMENT, QUESTIONS, is_relevant

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "artifacts" / "day15_prompts_draft.md"
PROMPTS = ROOT / "src" / "prompts"
PAUSE_S = 5  # stay under the free tier's requests-per-minute limit

log = setup_logging()
if not get_settings().gemini_api_key:
    sys.exit("No GEMINI_API_KEY: run with  uv run --env-file .env python " + __file__)


def summarize(version: str, passages: list[dict], question: str | None) -> dict:
    summarizer.PROMPT_PATH = PROMPTS / f"summary_{version}.txt"
    time.sleep(PAUSE_S)
    out = summarizer.summarize_passages(passages, question)
    out["fallback"] = out == {**summarizer._quote_passages(passages)}
    return out


lines = [
    "| # | Question | Passages | v1 not found | v1 takeaways | v2 not found | v2 takeaways |",
    "|---|---|---|---|---|---|---|",
]
detail = []
for n, question in enumerate(QUESTIONS, start=1):
    passages = api.search(question, experiment=NAMED_EXPERIMENT.get(n))
    if not passages:
        lines.append(f"| {n} | {question} | 0 | - | - | - | - |")
        continue
    by_id = {p["id"]: p for p in passages}
    row = [str(n), question, str(len(passages))]
    detail += [f"## Q{n}: {question}", "", f"Passages: {', '.join(by_id)}", ""]
    for version, q in (("v1", None), ("v2", question)):
        out = summarize(version, passages, q)
        flag = " (fallback)" if out["fallback"] else ""
        answers = sum(
            is_relevant(n, by_id[t["chunk_id"]]["text"]) for t in out["takeaways"] if EVIDENCE[n]
        )
        row += [f"{out['not_found']}{flag}", f"{len(out['takeaways'])} ({answers} cite an answer)"]
        detail.append(f"**{version}**: not_found={out['not_found']}{flag}")
        for t in out["takeaways"]:
            mark = (
                " [answer]" if EVIDENCE[n] and is_relevant(n, by_id[t["chunk_id"]]["text"]) else ""
            )
            detail.append(f"- `{t['chunk_id']}`{mark}: {t['text']}")
        detail.append("")
        log.info(
            "Q%d %s: not_found=%s, %d takeaways%s",
            n,
            version,
            out["not_found"],
            len(out["takeaways"]),
            flag,
        )
    lines.append("| " + " | ".join(row) + " |")

DRAFT.parent.mkdir(parents=True, exist_ok=True)
DRAFT.write_text("\n".join(lines) + "\n\n" + "\n".join(detail) + "\n", encoding="utf-8")
log.info("Draft -> %s", DRAFT)
