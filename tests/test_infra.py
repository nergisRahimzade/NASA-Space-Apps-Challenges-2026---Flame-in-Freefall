from flame_in_freefall.cache import QueryCache, memo, normalize
from flame_in_freefall.config import get_settings


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    assert get_settings().gemini_model == "test-model"


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
