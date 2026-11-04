"""Day 3 (AI): chunk the 3 fake docs, turn the chunks into numbers and save them.

Run from the project root:  uv run python scripts/day3_embed_mock.py
No API key needed. The first run downloads the embedding model (~90 MB); later runs reuse it."""

import json
from pathlib import Path

from flame_in_freefall.chunking import chunk_document
from flame_in_freefall.config import setup_logging
from flame_in_freefall.embedding import embed_texts
from flame_in_freefall.store import load_index, save_index

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
MOCK_DOCS = ROOT / "data" / "mock" / "docs.mock.json"
# Its own folder, not the real artifacts/index, so fake chunks can never show up as real answers.
MOCK_INDEX = ROOT / "artifacts" / "mock_index"

log = setup_logging()

docs = json.loads(MOCK_DOCS.read_text(encoding="utf-8"))
chunks = [c for d in docs for c in chunk_document(d["pages"], d["source"], d["doc_id"])]
vectors = embed_texts([c["text"] for c in chunks])
save_index(vectors, chunks, MOCK_INDEX)
log.info("Saved %s vectors for %d chunks -> %s", vectors.shape, len(chunks), MOCK_INDEX)

# Read it back to prove the save worked (done when: embeddings saved).
loaded, loaded_chunks = load_index(MOCK_INDEX)
log.info("Loaded back %s; first chunk: %s", loaded.shape, loaded_chunks[0]["id"])
