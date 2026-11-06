"""Day 9 (AI): ask 10 questions against the real index and write a draft log to judge by hand.

Run from the project root, after building the index with scripts/day8_embed_chunks.py:
    uv run python scripts/day9_test_search.py
No API key needed. Copy the draft into tests/retrieval.md, then fill in the Relevant column."""

from pathlib import Path

from flame_in_freefall.config import setup_logging
from flame_in_freefall.retrieval import find_passages
from flame_in_freefall.retrieval_eval import QUESTIONS  # the last 2 aren't covered by the reports

DRAFT = Path(__file__).resolve().parents[1] / "artifacts" / "retrieval_draft.md"

log = setup_logging()

lines = [
    "| # | Question | Rank | Score | Chunk | Relevant? (yes/no) |",
    "|---|---|---|---|---|---|",
]
for n, question in enumerate(QUESTIONS, start=1):
    log.info("Q%d: %s", n, question)
    for rank, r in enumerate(find_passages(question, k=3), start=1):
        log.info("  %d. %.3f  %s\n     %s", rank, r["score"], r["id"], r["text"][:200])
        lines.append(f"| {n} | {question} | {rank} | {r['score']:.3f} | `{r['id']}` | |")
DRAFT.parent.mkdir(parents=True, exist_ok=True)
DRAFT.write_text("\n".join(lines) + "\n", encoding="utf-8")
log.info("Draft log -> %s", DRAFT)
