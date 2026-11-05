"""Day 7 (AI): cut the real reports into chunks, save them, and print 5 to spot-check.

Run from the project root:  uv run python scripts/day7_chunk_reports.py
No API key or model download needed."""

import json
from pathlib import Path

from flame_in_freefall.chunking import chunk_reports
from flame_in_freefall.config import setup_logging

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
SOURCES = ROOT / "data" / "sources.csv"
REPORTS = ROOT / "docs" / "reports"
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"

log = setup_logging()

chunks = chunk_reports(SOURCES, REPORTS)
CHUNKS.parent.mkdir(parents=True, exist_ok=True)
with open(CHUNKS, "w", encoding="utf-8", newline="\n") as f:
    for c in chunks:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
log.info("Saved %d chunks -> %s", len(chunks), CHUNKS)

# Evenly spaced from first to last, so the spot-check reaches every report.
for i in range(5):
    c = chunks[i * (len(chunks) - 1) // 4]
    log.info(
        "%s | %s | page %d | %d words\n%s\n",
        c["id"],
        c["source"],
        c["page"],
        len(c["text"].split()),
        c["text"],
    )
