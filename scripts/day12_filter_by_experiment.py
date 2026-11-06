"""Day 12 (AI): does filtering by experiment before ranking help? Compare with and without it.

Run from the project root:  uv run python scripts/day12_filter_by_experiment.py
No API key needed. Like Day 11, it embeds data/processed/chunks.jsonl in memory, so
artifacts/index/ isn't needed or touched. The filter is the same one find_passages uses
(rows_for_experiment). For each question that names an experiment (NAMED_EXPERIMENT) we
pretend the user picked that experiment in the app; the other questions run unfiltered, as
they would with no experiment picked. Writes artifacts/experiment_filter_draft.md; the judged
copy lives in tests/experiment_filter.md."""

import json
from pathlib import Path

from flame_in_freefall.config import setup_logging
from flame_in_freefall.embedding import embed_texts
from flame_in_freefall.retrieval import rows_for_experiment, top_k
from flame_in_freefall.retrieval_eval import (
    ANSWERABLE,
    NAMED_EXPERIMENT,
    QUESTIONS,
    is_relevant,
    score_results,
)

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
DRAFT = ROOT / "artifacts" / "experiment_filter_draft.md"

KS = [3, 5]

log = setup_logging()

chunks = [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines()]
vectors = embed_texts([c["text"] for c in chunks])
question_vecs = embed_texts(QUESTIONS)


def ranking(q_vec, experiment: str | None) -> list[tuple[dict, float]]:
    """Every kept chunk, best first: the same steps as find_passages, minus loading the index."""
    rows = rows_for_experiment(chunks, experiment)
    return [(chunks[rows[j]], s) for j, s in top_k(q_vec, vectors[rows], k=len(rows))]


plain = {n: ranking(v, None) for n, v in enumerate(question_vecs, start=1)}
filtered = {
    n: ranking(question_vecs[n - 1], NAMED_EXPERIMENT.get(n)) for n in range(1, len(QUESTIONS) + 1)
}


def ids(rankings):
    return {n: [c["id"] for c, _ in r] for n, r in rankings.items()}


summary = [
    "| Search | k | First relevant | Relevant in top k | Relevant / returned | "
    "Wrong experiment / returned | Words to summarize |",
    "|---|---|---|---|---|---|---|",
]
for name, rankings in (("No filter", plain), ("Filter when named", filtered)):
    for k in KS:
        s = score_results(ids(rankings), chunks, k)
        words = sum(len(c["text"].split()) for n in ANSWERABLE for c, _ in rankings[n][:k])
        log.info(
            "%s k=%d: first %d/%d, top%d %d/%d, relevant %d/%d, wrong experiment %d/%d",
            name,
            k,
            s["first"],
            s["answerable"],
            k,
            s["top_k"],
            s["answerable"],
            s["relevant"],
            s["returned"],
            s["wrong_experiment"],
            s["named_returned"],
        )
        summary.append(
            f"| {name} | {k} | {s['first']}/{s['answerable']} | {s['top_k']}/{s['answerable']} | "
            f"{s['relevant']}/{s['returned']} | {s['wrong_experiment']}/{s['named_returned']} | "
            f"{words // len(ANSWERABLE)} |"
        )


def first_hit(n, r):
    hit = next((i for i, (c, _) in enumerate(r, 1) if is_relevant(n, c["text"])), None)
    return f"{hit}/{len(r)}" if hit else "none"


# Only the named questions change, so show them side by side.
per_question = [
    "| # | Experiment | First relevant rank: no filter | with filter | "
    + " | ".join(f"k={k}: relevant / wrong exp., no filter | with filter" for k in KS)
    + " |",
    "|---|---|---|---|" + "---|---|" * len(KS),
]
for n, exp in NAMED_EXPERIMENT.items():
    cells = []
    for k in KS:
        for r in (plain[n], filtered[n]):
            picked = [c for c, _ in r[:k]]
            rel = sum(is_relevant(n, c["text"]) for c in picked)
            wrong = sum(c["experiment"] != exp for c in picked)
            cells.append(f"{rel}/{len(picked)} / {wrong}")
    per_question.append(
        f"| {n} | {exp} | {first_hit(n, plain[n])} | {first_hit(n, filtered[n])} | "
        + " | ".join(cells)
        + " |"
    )

# The filtered top 5 of each named question, to read by hand.
detail = ["| # | Rank | Score | Chunk | Evidence match |", "|---|---|---|---|---|"]
for n in NAMED_EXPERIMENT:
    for r, (c, score) in enumerate(filtered[n][: max(KS)], start=1):
        match = "yes" if is_relevant(n, c["text"]) else "no"
        detail.append(f"| {n} | {r} | {score:.3f} | `{c['id']}` | {match} |")

DRAFT.parent.mkdir(parents=True, exist_ok=True)
DRAFT.write_text(
    "\n\n".join("\n".join(t) for t in (summary, per_question, detail)) + "\n", encoding="utf-8"
)
log.info("Draft -> %s", DRAFT)
