"""Day 10 (AI): try several chunk sizes and overlaps, score search for each, and compare.

Run from the project root:  uv run python scripts/day10_compare_chunk_sizes.py
No API key needed. Each setting is chunked and embedded in memory, so the real index in
artifacts/index/ and data/processed/chunks.jsonl are left alone. Results are scored with the
answer key in retrieval_eval.py (it matches the Day 9 hand judgments) and written to
artifacts/chunk_sizes_draft.md. The judged copy lives in tests/chunk_sizes.md."""

from pathlib import Path

from flame_in_freefall.chunking import chunk_reports
from flame_in_freefall.config import get_settings, setup_logging
from flame_in_freefall.embedding import _get_model, embed_texts
from flame_in_freefall.retrieval import top_k
from flame_in_freefall.retrieval_eval import ANSWERABLE, QUESTIONS, is_relevant, score_results

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
SOURCES = ROOT / "data" / "sources.csv"
REPORTS = ROOT / "docs" / "reports"
DRAFT = ROOT / "artifacts" / "chunk_sizes_draft.md"

SIZES = [100, 150, 200, 400, 600]  # 200/400/600 from the ticket, plus smaller ones
OVERLAPS = [0, 30, 60]
K = 3

log = setup_logging()

model = _get_model(get_settings().embed_model)
# MiniLM adds 2 special tokens and reads 256 in total, so 254 tokens of text get through.
VISIBLE = model.max_seq_length - 2


def n_tokens(text: str) -> int:
    return len(model.tokenizer(text, add_special_tokens=False)["input_ids"])


question_vecs = embed_texts(QUESTIONS)

summary = [
    "| Size | Overlap | Chunks | Max tokens | Chunks cut off | Text never seen | "
    f"First relevant | Relevant in top {K} | Random top {K} | Relevant / returned | "
    f"Words in top {K} |",
    "|---|---|---|---|---|---|---|---|---|---|---|",
]
ranks = [
    "| Size | Overlap | " + " | ".join(f"Q{n}" for n in ANSWERABLE) + " |",
    "|---|---|" + "---|" * len(ANSWERABLE),
]
for size in SIZES:
    for overlap in OVERLAPS:
        if overlap >= size:
            continue
        chunks = chunk_reports(SOURCES, REPORTS, size, overlap)
        vectors = embed_texts([c["text"] for c in chunks])
        tokens = [n_tokens(c["text"]) for c in chunks]
        unseen = sum(max(0, t - VISIBLE) for t in tokens) / sum(tokens)

        results, first_ranks, words = {}, [], 0
        for n, q_vec in enumerate(question_vecs, start=1):
            # Rank every chunk, so we also see where the best relevant one landed.
            ranking = [chunks[i] for i, _ in top_k(q_vec, vectors, k=len(chunks))]
            results[n] = [c["id"] for c in ranking]
            if n in ANSWERABLE:
                words += sum(len(c["text"].split()) for c in ranking[:K])
                hit = next((r for r, c in enumerate(ranking, 1) if is_relevant(n, c["text"])), None)
                first_ranks.append(f"{hit}/{len(chunks)}" if hit else "none")
        s = score_results(results, chunks, K)
        log.info(
            "size %d overlap %d: %d chunks, first %d/%d, top%d %d/%d (random %.1f)",
            size,
            overlap,
            len(chunks),
            s["first"],
            s["answerable"],
            K,
            s["top_k"],
            s["answerable"],
            s["chance_top_k"],
        )
        summary.append(
            f"| {size} | {overlap} | {len(chunks)} | {max(tokens)} | "
            f"{sum(t > VISIBLE for t in tokens)} | {unseen:.0%} | "
            f"{s['first']}/{s['answerable']} | {s['top_k']}/{s['answerable']} | "
            f"{s['chance_top_k']:.1f} | {s['relevant']}/{s['returned']} | "
            f"{words // len(ANSWERABLE)} |"
        )
        ranks.append(f"| {size} | {overlap} | " + " | ".join(first_ranks) + " |")

DRAFT.parent.mkdir(parents=True, exist_ok=True)
DRAFT.write_text("\n".join(summary) + "\n\n" + "\n".join(ranks) + "\n", encoding="utf-8")
log.info("Draft -> %s", DRAFT)
