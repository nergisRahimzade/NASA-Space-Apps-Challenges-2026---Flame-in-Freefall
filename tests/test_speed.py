"""Day 11 (BE): backend calls are timed into the speed log, repeated questions come from the
cache, and the report lists the slowest calls.

conftest.py points speed.SPEED_LOG at a throwaway file and empties the search cache per test."""

import logging

import pytest

from flame_in_freefall import api, speed


@pytest.fixture
def finds(monkeypatch) -> list:
    # Count real searches (not answered from the cache) while still searching for real.
    calls = []
    real_find = api.find_passages

    def counting_find(query, k, folder, experiment=None):
        calls.append(query)
        return real_find(query, k, folder=folder, experiment=experiment)

    monkeypatch.setattr(api, "find_passages", counting_find)
    return calls


def test_record_adds_a_line_to_the_speed_log():
    speed.record("search", "flame", 0.25)
    [entry] = speed.read_log()
    assert entry["call"] == "search" and entry["seconds"] == 0.25 and entry["cached"] is False


def test_long_questions_are_cut_in_the_log():
    speed.record("search", "x" * 500, 0.1)
    assert len(speed.read_log()[0]["detail"]) == speed.DETAIL_CHARS


def test_a_broken_speed_log_never_breaks_the_call(monkeypatch, tmp_path):
    monkeypatch.setattr(speed, "SPEED_LOG", tmp_path)  # a folder, so writing to it fails
    speed.record("search", "flame", 0.1)  # logs a warning instead of raising


def test_repeated_question_comes_from_the_cache(finds):
    api.search("Flame spread")
    api.search("  flame SPREAD ")  # same question after cleaning up capitals and spaces
    assert len(finds) == 1
    assert [e["cached"] for e in speed.read_log()] == [False, True]


def test_different_k_is_searched_again(finds):
    api.search("flame", k=1)
    api.search("flame", k=2)
    assert len(finds) == 2


def test_cached_results_are_copies():
    first = api.search("flame")
    first[0]["text"] = "changed by a caller"
    assert api.search("flame")[0]["text"] != "changed by a caller"


def test_get_table_and_summarize_are_timed():
    api.get_table({"experiment": "FLEX-2"})
    api.summarize([])
    calls = [e["call"] for e in speed.read_log()]
    assert calls == ["get_table", "summarize"]


def test_slowest_comes_first():
    for seconds in (0.2, 3.0, 0.5):
        speed.record("search", f"took {seconds}", seconds)
    assert [e["seconds"] for e in speed.slowest(2)] == [3.0, 0.5]


def test_slowest_rejects_a_bad_count():
    with pytest.raises(ValueError):
        speed.slowest(0)


def test_report_without_a_log_says_so(caplog):
    with caplog.at_level(logging.INFO):
        speed.main([])
    assert "No speed log yet" in caplog.text


def test_report_lists_the_slowest(caplog):
    speed.record("search", "slow question", 2.5)
    speed.record("search", "quick question", 0.1, cached=True)
    with caplog.at_level(logging.INFO):
        speed.main(["--top", "1"])
    assert "2 searches, 1 answered from cache" in caplog.text
    assert "slow question" in caplog.text and "quick question" not in caplog.text
