"""Day 8 (BE): the ingest command builds chunks and the index, and skips finished steps.

Uses two small fake reports in tmp_path and a fake embedding, so no model or network is needed."""

import os
import time

import numpy as np
import pytest

from flame_in_freefall import ingest
from flame_in_freefall.store import load_index


@pytest.fixture
def paths(tmp_path, monkeypatch) -> dict:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "alpha_abstract.txt").write_text("Flames spread slowly in microgravity.")
    (reports / "beta_abstract.txt").write_text("Droplets burned for two seconds.")
    sources = tmp_path / "sources.csv"
    # Same columns chunk_reports reads from the real data/sources.csv (experiment is required).
    sources.write_text(
        "file_name,title,experiment\n"
        "alpha_abstract.txt,Alpha report,FLEX\n"
        "beta_abstract.txt,Beta report,FLEX-2\n"
    )
    # Fake embedding: one 384-number row per text, so no model is downloaded.
    monkeypatch.setattr(ingest, "embed_texts", lambda texts: np.ones((len(texts), 384)))
    return {
        "sources": sources,
        "reports": reports,
        "chunks": tmp_path / "processed" / "chunks.jsonl",
        "index": tmp_path / "index",
    }


def _touch_later(path) -> None:
    # Mark a file as changed 10 s in the future: file times can be too coarse to tell apart
    # two writes in the same moment.
    later = time.time() + 10
    os.utime(path, (later, later))


def test_first_run_builds_everything(paths):
    assert ingest.run(**paths) == {"chunks": "built", "index": "built"}
    vectors, chunks = load_index(paths["index"])
    assert len(vectors) == len(chunks) == 2  # one short chunk per fake report
    assert {c["source"] for c in chunks} == {"Alpha report", "Beta report"}


def test_second_run_skips_everything(paths):
    ingest.run(**paths)
    assert ingest.run(**paths) == {"chunks": "skipped", "index": "skipped"}


def test_changed_report_rebuilds_both_steps(paths):
    ingest.run(**paths)
    _touch_later(paths["reports"] / "alpha_abstract.txt")
    assert ingest.run(**paths) == {"chunks": "built", "index": "built"}


def test_changed_chunks_rebuild_only_the_index(paths):
    ingest.run(**paths)
    _touch_later(paths["chunks"])
    assert ingest.run(**paths) == {"chunks": "skipped", "index": "built"}


def test_deleted_index_is_rebuilt(paths):
    ingest.run(**paths)
    (paths["index"] / "embeddings.npz").unlink()
    assert ingest.run(**paths)["index"] == "built"


def test_force_rebuilds_everything(paths):
    ingest.run(**paths)
    assert ingest.run(force=True, **paths) == {"chunks": "built", "index": "built"}
