"""Day 4 (BE): save and load the search index (chunk vectors + chunk metadata).

The embedding step is slow, so it runs once and saves here; search then just loads the files.
Row i of the vectors always belongs to chunks[i] (fields in docs/contract.md, section 2)."""

import json
from pathlib import Path

import numpy as np

# Built from this file's location, so it works no matter which folder you run from.
# artifacts/ is git-ignored, so the generated index never gets committed.
DEFAULT_FOLDER = Path(__file__).resolve().parents[2] / "artifacts" / "index"


def _paths(folder: str | Path) -> tuple[Path, Path]:
    # .npz holds the numbers compactly; .json keeps the text readable if you open it.
    folder = Path(folder)
    return folder / "embeddings.npz", folder / "chunks.json"


def save_index(
    vectors: np.ndarray, chunks: list[dict], folder: str | Path = DEFAULT_FOLDER
) -> None:
    """Write vectors to embeddings.npz and chunks to chunks.json in folder."""
    # One row per chunk is expected: a 1-D array would mean a single vector or a mistake.
    if vectors.ndim != 2:
        raise ValueError(f"vectors must be 2-D (one row per chunk), got {vectors.ndim}-D")
    # A count mismatch would pair vectors with the wrong source, so stop instead of saving.
    if len(vectors) != len(chunks):
        raise ValueError(f"{len(vectors)} vectors but {len(chunks)} chunks; they must match")
    npz_path, json_path = _paths(folder)
    npz_path.parent.mkdir(parents=True, exist_ok=True)  # create it if missing, fine if it exists
    np.savez(npz_path, vectors=vectors)
    # ensure_ascii=False keeps characters like ° or µ readable instead of \u escapes.
    json_path.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")


def load_index(folder: str | Path = DEFAULT_FOLDER) -> tuple[np.ndarray, list[dict]]:
    """Read back (vectors, chunks) saved by save_index."""
    npz_path, json_path = _paths(folder)
    # Fail loudly: no index means the embedding step hasn't been run yet.
    for p in (npz_path, json_path):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found; build the index with save_index first")
    # allow_pickle=False (the default, written out on purpose): only plain numbers are loaded,
    # never Python objects, so a tampered file can't run code.
    with np.load(npz_path, allow_pickle=False) as data:
        vectors = data["vectors"]
    chunks = json.loads(json_path.read_text(encoding="utf-8"))
    # The two files could come from different runs; refuse a mismatched pair.
    if len(vectors) != len(chunks):
        raise ValueError(f"{len(vectors)} vectors but {len(chunks)} chunks in {folder}")
    return vectors, chunks
