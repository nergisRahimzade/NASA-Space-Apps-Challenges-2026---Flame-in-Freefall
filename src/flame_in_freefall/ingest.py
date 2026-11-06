"""Day 8 (BE): one command that builds the search index from the reports.

    uv run python -m flame_in_freefall.ingest          # only the steps that are out of date
    uv run python -m flame_in_freefall.ingest --force  # redo every step

Steps: reports (docs/reports/ + data/sources.csv) -> chunks (data/processed/chunks.jsonl)
-> search index (artifacts/index/). Same files as the AI scripts for Days 7-8, so either way
of building gives the same result. A step is skipped when its output is newer than all of
its inputs, so a second run with nothing changed takes about a second."""

import argparse
import json
import logging
import time
from pathlib import Path

from flame_in_freefall import chunking
from flame_in_freefall.chunking import chunk_reports
from flame_in_freefall.config import setup_logging
from flame_in_freefall.embedding import embed_texts
from flame_in_freefall.store import DEFAULT_FOLDER, _paths, save_index

ROOT = Path(__file__).resolve().parents[2]  # works no matter which folder you run from
SOURCES = ROOT / "data" / "sources.csv"
REPORTS = ROOT / "docs" / "reports"
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
INDEX = DEFAULT_FOLDER  # artifacts/index/ (git-ignored)

# A fixed name: with "python -m", __name__ would be "__main__" and the log lines say that.
log = logging.getLogger("flame_in_freefall.ingest")


def _is_fresh(outputs: list[Path], inputs: list[Path]) -> bool:
    """True when every output exists and is at least as new as the newest input."""
    if not all(p.exists() for p in outputs):
        return False  # never built (or a file was deleted): build it
    # st_mtime = when the file was last changed, in seconds.
    return min(p.stat().st_mtime for p in outputs) >= max(p.stat().st_mtime for p in inputs)


def build_chunks(sources: Path, reports: Path, out: Path) -> int:
    """Chunk every report in sources.csv into out (JSONL); returns the number of chunks."""
    chunks = chunk_reports(sources, reports)
    out.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": the same line endings on Windows and Linux, so Git sees no fake changes.
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return len(chunks)


def build_index(chunks_path: Path, folder: Path) -> tuple[int, int]:
    """Embed the chunks in chunks_path and save the index in folder; returns the vectors' shape."""
    lines = chunks_path.read_text(encoding="utf-8").splitlines()
    chunks = [json.loads(line) for line in lines if line.strip()]
    vectors = embed_texts([c["text"] for c in chunks])
    save_index(vectors, chunks, folder)
    return vectors.shape


def run(
    force: bool = False,
    sources: Path = SOURCES,
    reports: Path = REPORTS,
    chunks: Path = CHUNKS,
    index: Path = INDEX,
) -> dict[str, str]:
    """Run the steps that are out of date (all of them with force=True).
    Returns what happened to each step: {"chunks": "built" | "skipped", "index": ...}."""
    # Chunking also depends on chunking.py itself, so changing the chunk size rebuilds.
    chunk_inputs = [sources, *sorted(reports.glob("*.txt")), Path(chunking.__file__)]
    done = {}

    if not force and _is_fresh([chunks], chunk_inputs):
        done["chunks"] = "skipped"
        log.info("chunks: up to date, skipped (%s)", chunks)
    else:
        start = time.perf_counter()
        count = build_chunks(sources, reports, chunks)
        done["chunks"] = "built"
        log.info("chunks: %d -> %s (%.1f s)", count, chunks, time.perf_counter() - start)

    # Checked after the step above, so freshly built chunks always lead to a new index.
    if not force and _is_fresh(list(_paths(index)), [chunks]):
        done["index"] = "skipped"
        log.info("index: up to date, skipped (%s)", index)
    else:
        start = time.perf_counter()
        shape = build_index(chunks, index)
        done["index"] = "built"
        log.info("index: %s vectors -> %s (%.1f s)", shape, index, time.perf_counter() - start)
    return done


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the search index from the reports.")
    parser.add_argument("--force", action="store_true", help="redo every step")
    args = parser.parse_args(argv)
    setup_logging()
    run(force=args.force)


if __name__ == "__main__":
    main()
