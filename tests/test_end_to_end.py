"""Day 14 (BE): the whole backend in a row: ingest -> search -> table.

The other test files check each piece alone; these check that one piece's output works as the
next piece's input. They use the real reports, sources.csv and master.csv, and write only to
tmp_path. conftest.py supplies the fake embedding model, so CI needs no download.
scripts/day14_end_to_end.py runs the same path with the real model.

Row counts and scores are left out on purpose: the data role can add rows and the fake model
ranks differently, and neither of those means the path is broken."""

import json
from pathlib import Path

import pytest

from flame_in_freefall import api, ingest

QUESTION = "What oxygen levels and pressures were used in the FLEX-2 chamber?"


def _chunks_in(path: Path) -> list[dict]:
    # chunks.jsonl has one JSON object per line.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def built(monkeypatch, tmp_path) -> dict:
    # Step 1 of every test: build chunks and index from the real reports, in a throwaway folder.
    chunks = tmp_path / "processed" / "chunks.jsonl"
    index = tmp_path / "built_index"
    # force=True: both steps must really run here, not get skipped as "up to date".
    done = ingest.run(force=True, chunks=chunks, index=index)
    # Point search() at what was just built, like the app reading artifacts/index/.
    monkeypatch.setattr(api, "CHUNKS", chunks)
    monkeypatch.setattr(api, "INDEX", index)
    return {"done": done, "chunks": chunks}


def test_ingest_builds_both_steps_from_the_real_reports(built):
    assert built["done"] == {"chunks": "built", "index": "built"}
    assert _chunks_in(built["chunks"])  # at least one chunk came out


def test_search_uses_the_index_ingest_built(built, monkeypatch):
    # If search() decided to build its own index, the link between the two steps is broken.
    def fail_if_called(chunks, folder):
        raise AssertionError("search() rebuilt the index instead of using ingest's")

    monkeypatch.setattr(ingest, "build_index", fail_if_called)
    results = api.search(QUESTION)
    ingested_ids = {c["id"] for c in _chunks_in(built["chunks"])}
    assert results and {r["id"] for r in results} <= ingested_ids


def test_top_result_leads_to_table_rows_for_its_experiment(built):
    # The path a visitor takes: ask a question, then see the numbers for that experiment.
    top = api.search(QUESTION)[0]
    rows = api.get_table({"experiment": top["experiment"]})
    assert rows and all(row["experiment"] == top["experiment"] for row in rows)


def test_every_experiment_in_the_reports_has_table_rows(built):
    # Chunks get their experiment name from sources.csv, the table from master.csv. Two files,
    # so a name changed in only one (FLEX-2 vs FLEX2) would break the link between them.
    experiments = {c["experiment"] for c in _chunks_in(built["chunks"])}
    without_rows = [e for e in sorted(experiments) if not api.get_table({"experiment": e})]
    assert experiments and without_rows == []


def test_every_experiment_can_be_searched_on_its_own(built):
    experiments = {c["experiment"] for c in _chunks_in(built["chunks"])}
    for experiment in sorted(experiments):
        results = api.search(QUESTION, experiment=experiment)
        assert results and all(r["experiment"] == experiment for r in results)
