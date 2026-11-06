"""Day 11 (AI): return the top 3, 5 and 8 chunks for the 10 questions, score each k, log failures.

Run from the project root:  uv run python scripts/day11_compare_k.py
No API key needed. Uses the real chunks in data/processed/chunks.jsonl (150 words, overlap 30,
kept on Day 10) and embeds them in memory, so artifacts/index/ isn't needed or touched. Results
are scored with the answer key in retrieval_eval.py and written to artifacts/top_k_draft.md.
The judged copy lives in tests/top_k.md."""

import json
from pathlib import Path

from flame_in_freefall.config import setup_logging
from flame_in_freefall.embedding import embed_texts
from flame_in_freefall.retrieval import top_k
from flame_in_freefall.retrieval_eval import (
    ANSWERABLE,
    NAMED_EXPERIMENT,
    QUESTIONS,
    is_relevant,
    score_results,
)

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
DRAFT = ROOT / "artifacts" / "top_k_draft.md"

KS = [3, 5, 8]

log = setup_logging()

chunks = [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines()]
vectors = embed_texts([c["text"] for c in chunks])
question_vecs = embed_texts(QUESTIONS)

# Rank every chunk once per question; each k is then just the first k of that ranking.
rankings: dict[int, list[tuple[dict, float]]] = {}
for n, q_vec in enumerate(question_vecs, start=1):
    rankings[n] = [(chunks[i], score) for i, score in top_k(q_vec, vectors, k=len(chunks))]
results = {n: [c["id"] for c, _ in ranking] for n, ranking in rankings.items()}

summary = [
    "| k | First relevant | Relevant in top k | Random top k | Relevant / returned | "
    "Wrong experiment / returned | Words to summarize |",
    "|---|---|---|---|---|---|---|",
]
for k in KS:
    s = score_results(results, chunks, k)
    words = sum(len(c["text"].split()) for n in ANSWERABLE for c, _ in rankings[n][:k])
    log.info(
        "k=%d: first %d/%d, top%d %d/%d (random %.1f), relevant %d/%d, wrong experiment %d/%d",
        k,
        s["first"],
        s["answerable"],
        k,
        s["top_k"],
        s["answerable"],
        s["chance_top_k"],
        s["relevant"],
        s["returned"],
        s["wrong_experiment"],
        s["named_returned"],
    )
    summary.append(
        f"| {k} | {s['first']}/{s['answerable']} | {s['top_k']}/{s['answerable']} | "
        f"{s['chance_top_k']:.1f} | {s['relevant']}/{s['returned']} | "
        f"{s['wrong_experiment']}/{s['named_returned']} | {words // len(ANSWERABLE)} |"
    )

# One row per question: where its first relevant chunk ranked, and what each k returns.
per_question = [
    "| # | First relevant rank | "
    + " | ".join(f"k={k}: relevant / wrong exp." for k in KS)
    + " | Top score | Score at rank 8 |",
    "|---|---|" + "---|" * len(KS) + "---|---|",
]
for n, ranking in rankings.items():
    hit = next((r for r, (c, _) in enumerate(ranking, 1) if is_relevant(n, c["text"])), None)
    cells = []
    for k in KS:
        picked = [c for c, _ in ranking[:k]]
        rel = sum(is_relevant(n, c["text"]) for c in picked)
        wrong = (
            sum(c.get("experiment") != NAMED_EXPERIMENT[n] for c in picked)
            if n in NAMED_EXPERIMENT
            else "-"
        )
        cells.append(f"{rel}/{k} / {wrong}")
    rank = f"{hit}/{len(chunks)}" if hit else ("uncovered" if n not in ANSWERABLE else "none")
    per_question.append(
        f"| {n} | {rank} | " + " | ".join(cells) + f" | {ranking[0][1]:.3f} | {ranking[7][1]:.3f} |"
    )

# Every chunk in the top 8, so the failures can be read and judged by hand.
detail = ["| # | Rank | Score | Chunk | Experiment | Evidence match |", "|---|---|---|---|---|---|"]
for n, ranking in rankings.items():
    for r, (c, score) in enumerate(ranking[: max(KS)], start=1):
        match = "yes" if n in ANSWERABLE and is_relevant(n, c["text"]) else "no"
        detail.append(f"| {n} | {r} | {score:.3f} | `{c['id']}` | {c['experiment']} | {match} |")

DRAFT.parent.mkdir(parents=True, exist_ok=True)
DRAFT.write_text(
    "\n\n".join("\n".join(t) for t in (summary, per_question, detail)) + "\n", encoding="utf-8"
)
log.info("Draft -> %s", DRAFT)
