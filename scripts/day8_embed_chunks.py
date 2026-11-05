"""Day 8 (AI): turn the real chunks into numbers, save them as the search index, and time it.

Run from the project root, after scripts/day7_chunk_reports.py:
    uv run python scripts/day8_embed_chunks.py
No API key needed. The first run downloads the embedding model (~90 MB); later runs reuse it."""

import json
import time
from pathlib import Path

from flame_in_freefall.config import setup_logging
from flame_in_freefall.embedding import embed_texts
from flame_in_freefall.store import DEFAULT_FOLDER, load_index, save_index

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"

log = setup_logging()

lines = CHUNKS.read_text(encoding="utf-8").splitlines()
chunks = [json.loads(line) for line in lines if line.strip()]
log.info("Embedding %d chunks...", len(chunks))

start = time.perf_counter()
vectors = embed_texts([c["text"] for c in chunks])
seconds = time.perf_counter() - start
log.info("Embedded %s in %.2f s, including loading the model", vectors.shape, seconds)

save_index(vectors, chunks, DEFAULT_FOLDER)
log.info("Saved -> %s", DEFAULT_FOLDER)

# Read it back to prove the save worked (done when: embeddings file saved).
loaded, loaded_chunks = load_index(DEFAULT_FOLDER)
log.info("Loaded back %s; first chunk: %s", loaded.shape, loaded_chunks[0]["id"])
