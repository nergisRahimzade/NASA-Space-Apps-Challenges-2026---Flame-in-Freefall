"""Day 14 (AI): retrieval checkpoint. Score the 10 questions, and record what was tried for 8/10.

Run from the project root:  uv run python scripts/day14_checkpoint.py
No API key needed. Writes artifacts/day14_checkpoint_draft.md; the judged copy lives in
tests/checkpoint.md. Pass/fail is retrieval_eval's judge rule, the same as Day 13.

Part 1, the score: the real api.search() (k = 5, experiment filter, 0.30 cutoff), three ways:
  - "Experiment picked": the user picks the experiment the question names (as on Day 13).
  - "All experiments": the app's default, no filter (as on Day 13).
  - "Name read from question": no pick, but experiment_in_question() supplies the filter.
Part 2, ranking changes tried to reach 8/10, in memory (artifacts/index/ isn't touched). Each ranks
the same 18 chunks a different way; experiment filter on when the question names one, top 5,
results under 0.30 left out. Scored on the 10 questions and on the 10 held-out ones (HELD_OUT),
which weren't used to choose the changes:
  - chunk: today's search, one vector per chunk.
  - best sentence: a chunk scores as high as its best-matching sentence.
  - keywords + chunk: BM25 keyword ranks fused with today's ranks (reciprocal rank fusion).
  - title + chunk / experiment + chunk: the report title or experiment name embedded with the text.
  - keywords + best sentence: BM25 ranks fused with best-sentence ranks; the cutoff uses the
    best-sentence score.
Part 3: the top score of a few off-topic questions under "chunk" and "best sentence", since the
0.30 cutoff (D13-BE) was tuned on chunk scores."""

import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

from flame_in_freefall import api
from flame_in_freefall.config import setup_logging
from flame_in_freefall.embedding import embed_texts
from flame_in_freefall.retrieval import experiment_in_question, rows_for_experiment
from flame_in_freefall.retrieval_eval import (
    EVIDENCE,
    HELD_OUT,
    NAMED_EXPERIMENT,
    QUESTIONS,
    WEAK,
    contains_evidence,
    judge,
    judge_against,
)

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
DRAFT = ROOT / "artifacts" / "day14_checkpoint_draft.md"
K = 5
OFF_TOPIC = [
    "pizza recipes",
    "Who won the World Cup?",
    "How much thrust does a rocket engine produce?",
    "What is the capital of France?",
    "How do I bake sourdough bread?",
    "Best laptop for programming",
]
# Both question sets in one shape: (question, evidence phrases, experiment named, weak note).
TUNING = [
    (q, EVIDENCE[n], NAMED_EXPERIMENT.get(n), WEAK.get(n)) for n, q in enumerate(QUESTIONS, 1)
]
HELD = [(q, phrases, named, None) for q, phrases, named in HELD_OUT]

log = setup_logging()
chunks = [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines()]
experiments = sorted({c["experiment"] for c in chunks})
lines = []

# ---- Part 1: the score, through the real search() ----
RUNS = {
    "Experiment picked": lambda n, q: NAMED_EXPERIMENT.get(n),
    "All experiments": lambda n, q: None,
    "Name read from question": lambda n, q: experiment_in_question(q, experiments),
}
lines += ["## Score (real search)", "", "| Run | Pass | Fails |", "|---|---|---|"]
for run, pick in RUNS.items():
    verdicts = [
        judge(n, api.search(q, k=K, experiment=pick(n, q))) for n, q in enumerate(QUESTIONS, 1)
    ]
    fails = [f"Q{n}" for n, (ok, _) in enumerate(verdicts, 1) if not ok]
    lines.append(f"| {run} | {10 - len(fails)}/10 | {', '.join(fails)} |")
    log.info("%s: %d/10 pass, fails %s", run, 10 - len(fails), fails)
    for n, (ok, reason) in enumerate(verdicts, 1):
        log.info("  Q%d %s: %s", n, "PASS" if ok else "FAIL", reason)


# ---- Part 2: ranking changes, in memory ----
def sentences(text: str) -> list[str]:
    # Split after . ! or ?; skip fragments under 4 words (list numbers like "2." etc.).
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 4]


SENT_OWNER = [i for i, c in enumerate(chunks) for _ in sentences(c["text"])]
SENT_VECS = embed_texts([s for c in chunks for s in sentences(c["text"])])
CHUNK_VECS = embed_texts([c["text"] for c in chunks])
TITLE_VECS = embed_texts([f"{c['source']}. {c['text']}" for c in chunks])
EXP_VECS = embed_texts([f"{c['experiment']}: {c['text']}" for c in chunks])


def best_sentence(query_vecs: np.ndarray) -> np.ndarray:
    """(questions, chunks): each chunk's score is its best sentence's cosine score."""
    per_sentence = query_vecs @ SENT_VECS.T
    out = np.full((len(query_vecs), len(chunks)), -1.0)
    for j, i in enumerate(SENT_OWNER):
        out[:, i] = np.maximum(out[:, i], per_sentence[:, j])
    return out


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25(queries: list[str], k1: float = 1.2, b: float = 0.75) -> np.ndarray:
    """Classic BM25 keyword scores, (questions, chunks). Question words like 'what' are skipped."""
    stop = {"a", "and", "are", "at", "do", "does", "for", "how", "in", "is", "of", "on", "the"}
    stop |= {"to", "used", "was", "were", "what", "which", "why", "you"}
    docs = [Counter(words(c["text"])) for c in chunks]
    lengths = [sum(d.values()) for d in docs]
    avg = sum(lengths) / len(docs)
    df = Counter(w for d in docs for w in d)
    out = np.zeros((len(queries), len(chunks)))
    for qi, q in enumerate(queries):
        for w in set(words(q)) - stop:
            idf = math.log(1 + (len(docs) - df[w] + 0.5) / (df[w] + 0.5))
            for i, d in enumerate(docs):
                tf = d[w]
                out[qi, i] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * lengths[i] / avg))
    return out


def fuse(*score_tables: np.ndarray, c: int = 60) -> np.ndarray:
    """Reciprocal rank fusion: add 1 / (c + rank) from each ranking. Only the order counts."""
    out = np.zeros_like(score_tables[0])
    for table in score_tables:
        for row in range(table.shape[0]):
            ranks = np.empty(table.shape[1])
            ranks[np.argsort(-table[row], kind="stable")] = np.arange(1, table.shape[1] + 1)
            out[row] += 1 / (c + ranks)
    return out


def rankings(queries: list[str]) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Change name -> (scores to rank by, scores the 0.30 cutoff applies to). Fused ranks aren't
    cosine scores, so fused rows are cut on a cosine score, as api.search() would have to."""
    q = embed_texts(queries)
    chunk, best, keywords = q @ CHUNK_VECS.T, best_sentence(q), bm25(queries)
    return {
        "chunk (today)": (chunk, chunk),
        "best sentence": (best, best),
        "keywords + chunk": (fuse(chunk, keywords), chunk),
        "title + chunk": (q @ TITLE_VECS.T, q @ TITLE_VECS.T),
        "experiment + chunk": (q @ EXP_VECS.T, q @ EXP_VECS.T),
        "keywords + best sentence": (fuse(best, keywords), best),
    }


def evaluate(qset, tables) -> tuple[list[str], list[str]]:
    """Fails ("Q6" or "H3") and the first relevant rank of each answerable question."""
    fails, firsts = [], []
    for n, (_, phrases, named, weak) in enumerate(qset):
        rank_by, cut_by = tables[0][n], tables[1][n]
        order = sorted(rows_for_experiment(chunks, named), key=lambda i: -rank_by[i])  # stable
        if phrases:
            hit = next(
                (
                    r
                    for r, i in enumerate(order, 1)
                    if contains_evidence(phrases, chunks[i]["text"])
                ),
                None,
            )
            firsts.append(f"{hit}/{len(order)}" if hit else "-")
        kept = [i for i in order[:K] if cut_by[i] >= api.MIN_SCORE]
        ok, _ = judge_against(
            phrases, named, [{**chunks[i], "score": float(cut_by[i])} for i in kept], weak
        )
        fails += [] if ok else [f"{'Q' if qset is TUNING else 'H'}{n + 1}"]
    return fails, firsts


tuning, held = rankings([q for q, *_ in TUNING]), rankings([q for q, *_ in HELD])
lines += [
    "",
    "## Ranking changes (filter when named, top 5, 0.30 cutoff)",
    "",
    "| Change | 10 questions | Fails | First relevant rank, Q1-Q8 | Held out | Fails "
    "| Q9 top | Q10 top |",
    "|---|---|---|---|---|---|---|---|",
]
for name in tuning:
    t_fails, t_firsts = evaluate(TUNING, tuning[name])
    h_fails, _ = evaluate(HELD, held[name])
    cut = tuning[name][1]
    lines.append(
        f"| {name} | {10 - len(t_fails)}/10 | {', '.join(t_fails)} | {', '.join(t_firsts)} | "
        f"{10 - len(h_fails)}/10 | {', '.join(h_fails) or '-'} | "
        f"{cut[8].max():.3f} | {cut[9].max():.3f} |"
    )
    log.info(
        "%s: %d/10 (fails %s), held out %d/10 (fails %s)",
        name,
        10 - len(t_fails),
        t_fails,
        10 - len(h_fails),
        h_fails,
    )

# ---- Part 3: off-topic questions vs the cutoff ----
off_vecs = embed_texts(OFF_TOPIC)
off_chunk = (off_vecs @ CHUNK_VECS.T).max(axis=1)
off_best = best_sentence(off_vecs).max(axis=1)
lines += [
    "",
    "## Off-topic top scores",
    "",
    "| Question | chunk | best sentence |",
    "|---|---|---|",
]
for q, a, b in zip(OFF_TOPIC, off_chunk, off_best, strict=True):
    lines.append(f"| {q} | {a:.4f} | {b:.4f} |")

DRAFT.parent.mkdir(parents=True, exist_ok=True)
DRAFT.write_text("\n".join(lines) + "\n", encoding="utf-8")
log.info("Draft -> %s", DRAFT)
