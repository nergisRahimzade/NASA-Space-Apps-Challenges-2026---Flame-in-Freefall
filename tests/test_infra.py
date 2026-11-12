import pytest

from flame_in_freefall.cache import QueryCache, memo, normalize
from flame_in_freefall.config import get_settings


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    assert get_settings().gemini_model == "test-model"


def test_gemini_call_limit_defaults_to_10_a_minute():
    # conftest.py removes GEMINI_CALLS_PER_MINUTE from the environment for every test.
    assert get_settings().gemini_calls_per_minute == 10


def test_gemini_call_limit_reads_env(monkeypatch):
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "25")
    assert get_settings().gemini_calls_per_minute == 25


@pytest.mark.parametrize("bad", ["0", "-3", "ten", "2.5", ""])
def test_gemini_call_limit_must_be_a_whole_number_above_zero(monkeypatch, bad):
    # A typo in the app's Secrets should be an obvious error, not a quietly different limit.
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", bad)
    with pytest.raises(ValueError, match="GEMINI_CALLS_PER_MINUTE"):
        get_settings()


def test_normalize():
    assert normalize("  Which MATERIAL  burns? ") == "which material burns?"


def test_file_cache_round_trip(tmp_path):
    cache = QueryCache(tmp_path)
    assert cache.get("q") is None
    cache.set("Which material?", {"answer": 1})
    assert cache.get("  which MATERIAL? ") == {"answer": 1}


def test_memo_calls_once():
    calls = []

    @memo
    def slow(query):
        calls.append(query)
        return len(query)

    slow("Hello"), slow("hello "), slow("HELLO")
    assert len(calls) == 1


def test_memo_knows_what_is_cached():
    @memo
    def slow(query, k=3):
        return query

    assert not slow.is_cached("Hello")
    slow("Hello")
    assert slow.is_cached(" hello ")  # same cleaned-up question
    assert not slow.is_cached("hello", 5)  # other arguments are remembered separately
