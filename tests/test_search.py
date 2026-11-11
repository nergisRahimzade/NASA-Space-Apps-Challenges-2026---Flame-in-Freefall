"""Day 10 (BE): search() ranks the real report chunks and builds the index on first use.

conftest.py swaps in a fake embedding model and a throwaway index folder (api.INDEX), so
these tests search the committed chunks.jsonl with no download and no files left behind."""

import os
import shutil
import threading
import time

import pytest

from flame_in_freefall import api, ingest, speed

KEYS = {"id", "text", "source", "page", "score", "experiment"}


@pytest.fixture
def builds(monkeypatch) -> list:
    # Count index builds while still building for real.
    calls = []
    real_build = ingest.build_index

    def counting_build(chunks, folder):
        calls.append(folder)
        return real_build(chunks, folder)

    monkeypatch.setattr(ingest, "build_index", counting_build)
    return calls


def test_returns_real_passages_in_contract_shape():
    results = api.search("What gases were used to put out fires?")
    assert 0 < len(results) <= 5  # contract v1.1 default k
    assert all(set(r) == KEYS for r in results)
    assert all(r["experiment"] in {"FLEX", "FLEX-2", "Saffire-II", "BASS-II"} for r in results)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)  # best first


def test_k_limits_the_results():
    assert len(api.search("flame", k=1)) == 1


def test_blank_query_is_rejected():
    with pytest.raises(ValueError):
        api.search("   ")


def test_first_search_builds_the_index_and_later_ones_reuse_it(builds):
    assert not api.INDEX.exists()  # like a fresh deploy
    api.search("flame")
    api.search("oxygen")
    assert len(builds) == 1


def test_index_older_than_the_chunks_is_rebuilt(builds, monkeypatch, tmp_path):
    # Use a copy of chunks.jsonl, so marking it as changed doesn't touch the committed file.
    chunks = tmp_path / "chunks.jsonl"
    shutil.copy(api.CHUNKS, chunks)
    monkeypatch.setattr(api, "CHUNKS", chunks)
    api.search("flame")
    later = time.time() + 10  # file times can be too coarse to tell two writes apart
    os.utime(chunks, (later, later))
    api.search("flame")
    assert len(builds) == 2


def test_two_searches_at_once_build_the_index_only_once(builds, monkeypatch):
    # Two visitors searching at the same moment on a fresh deploy. The fake model builds in
    # milliseconds, so slow the build down: the second search then always arrives mid-build,
    # and without the lock in api.py both would build (checked: this test then fails).
    counting_build = ingest.build_index  # the `builds` fixture's version

    def slow_build(chunks, folder):
        time.sleep(0.3)
        return counting_build(chunks, folder)

    monkeypatch.setattr(ingest, "build_index", slow_build)
    threads = [threading.Thread(target=api.search, args=("flame",)) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(builds) == 1


# --- Day 12 (BE): the experiment filter -----------------------------------------------------


def test_experiment_filter_returns_only_that_experiment():
    results = api.search("flame", experiment="FLEX-2")
    assert results and all(r["experiment"] == "FLEX-2" for r in results)


def test_no_experiment_searches_every_experiment():
    experiments = {r["experiment"] for r in api.search("flame", k=22)}  # 22 = every chunk
    assert experiments == {"FLEX", "FLEX-2", "Saffire-II", "BASS-II"}


def test_unknown_experiment_is_rejected():
    # A typo would otherwise look like "no results"; the error lists the valid names.
    with pytest.raises(ValueError, match="unknown experiment"):
        api.search("flame", experiment="Flex2")


@pytest.mark.parametrize("bad", ["", "  ", 5])
def test_blank_or_non_text_experiment_is_rejected(bad):
    with pytest.raises(ValueError):
        api.search("flame", experiment=bad)


def test_filtered_and_unfiltered_are_cached_separately():
    # The filter is part of the cache key, so the unfiltered answer is never reused for it.
    api.search("flame")
    filtered = api.search("flame", experiment="FLEX")
    assert all(r["experiment"] == "FLEX" for r in filtered)
    assert [e["cached"] for e in speed.read_log()] == [False, False]
