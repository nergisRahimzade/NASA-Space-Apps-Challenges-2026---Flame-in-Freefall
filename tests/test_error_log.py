"""Day 18 (BE): failures are written to the error log, so the team can see why something broke.

conftest.py points error_log.ERROR_LOG at a throwaway file for every test."""

import logging
from types import SimpleNamespace

import pytest
from google.genai import errors

from flame_in_freefall import api, error_log, summarizer
from flame_in_freefall.rate_limit import RateLimiter

PASSAGES = [{"id": "a-1", "text": "Flame spread 2 mm/s.", "source": "S", "page": 1}]


class _FailingClient:
    # Stands in for genai.Client(): every request fails like a Gemini outage.
    def __init__(self):
        self.models = self

    def generate_content(self, **kwargs):
        raise errors.ServerError(503, {"error": {"message": "high demand"}})


# --- the log file ----------------------------------------------------------------------------


def test_record_adds_one_line_with_every_field():
    error_log.record("search", "error", "ValueError", "query must be non-empty text", "flame")
    [entry] = error_log.read_log()
    assert entry["call"] == "search" and entry["kind"] == "error"
    assert entry["error_type"] == "ValueError"
    assert entry["message"] == "query must be non-empty text" and entry["detail"] == "flame"
    assert entry["at"].endswith("+00:00")


def test_a_long_message_is_cut():
    error_log.record("search", "error", "ValueError", "x" * 1000)
    assert len(error_log.read_log()[0]["message"]) == error_log.MESSAGE_CHARS


def test_a_long_detail_is_cut():
    error_log.record("search", "error", "ValueError", "m", "q" * 1000)
    assert len(error_log.read_log()[0]["detail"]) == error_log.DETAIL_CHARS


def test_the_api_key_never_reaches_the_file(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-key-123")
    error_log.record("summarize", "fallback", "ClientError", "bad ?key=secret-key-123 sent", "d")
    entry = error_log.read_log()[0]
    assert "secret-key-123" not in error_log.ERROR_LOG.read_text(encoding="utf-8")
    assert entry["message"] == "bad ?key=<key> sent"


def test_an_unknown_kind_raises():
    with pytest.raises(ValueError, match="kind"):
        error_log.record("search", "oops", "ValueError", "m")


def test_an_unknown_call_raises():
    with pytest.raises(ValueError, match="call"):
        error_log.record("ingest", "error", "ValueError", "m")


def test_an_unwritable_log_does_not_break_the_call(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    monkeypatch.setattr(error_log, "ERROR_LOG", blocker / "errors.log")  # can't make a folder here
    error_log.record("search", "error", "ValueError", "m")  # must not raise


def test_a_damaged_line_is_skipped_not_fatal(caplog):
    error_log.record("search", "error", "ValueError", "first")
    with open(error_log.ERROR_LOG, "a", encoding="utf-8") as f:
        f.write('{"at": "cut off part-way\n')
    error_log.record("search", "error", "ValueError", "second")
    with caplog.at_level(logging.WARNING):
        entries = error_log.read_log()
    assert [e["message"] for e in entries] == ["first", "second"]
    assert "skipped 1 damaged" in caplog.text


# --- the report ------------------------------------------------------------------------------


def test_report_without_a_log_says_so(caplog):
    with caplog.at_level(logging.INFO):
        error_log.main([])
    assert "No errors logged yet" in caplog.text


def test_report_counts_and_lists_the_latest(caplog):
    for message in ("one", "two", "three"):
        error_log.record("search", "error", "ValueError", message)
    with caplog.at_level(logging.INFO):
        error_log.main(["--last", "1"])
    assert "3 events logged" in caplog.text
    assert "three" in caplog.text and "one" not in caplog.text


def test_report_rejects_a_bad_count():
    with pytest.raises(SystemExit):
        error_log.main(["--last", "0"])


# --- what api.py and summarizer.py write -----------------------------------------------------


def test_a_failed_search_is_logged_and_still_raises():
    with pytest.raises(ValueError):
        api.search("")
    [entry] = error_log.read_log()
    assert (entry["call"], entry["kind"], entry["error_type"]) == ("search", "error", "ValueError")


def test_a_failed_get_table_is_logged_and_still_raises():
    with pytest.raises(ValueError):
        api.get_table("FLEX")
    [entry] = error_log.read_log()
    assert (entry["call"], entry["kind"]) == ("get_table", "error")
    assert "FLEX" in entry["detail"]


def test_a_failed_summarize_is_logged_and_still_raises():
    with pytest.raises(ValueError):
        api.summarize("not a list")
    [entry] = error_log.read_log()
    assert (entry["call"], entry["kind"]) == ("summarize", "error")


def test_the_error_also_reaches_the_host_log_with_a_traceback(caplog):
    # On the live host artifacts/ can't be read, so the ERROR line is where the reason shows up.
    with caplog.at_level(logging.ERROR), pytest.raises(ValueError):
        api.search("")
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    message = record.getMessage()
    assert "search() failed with ValueError" in message
    assert "Traceback (most recent call last)" in message


def test_the_key_never_reaches_the_host_log_even_in_a_chained_traceback(monkeypatch, caplog):
    # caplog.text is the fully formatted output, traceback included: what the host would print.
    monkeypatch.setenv("GEMINI_API_KEY", "secret-key-123")
    try:
        try:
            raise KeyError("lookup with secret-key-123")
        except KeyError as inner:
            raise ValueError("call failed: ?key=secret-key-123") from inner
    except ValueError as e:
        with caplog.at_level(logging.ERROR):
            error_log.record_exception("search", "q", e)
    assert "secret-key-123" not in caplog.text
    assert "<key>" in caplog.text and "direct cause" in caplog.text  # the chained part is there


class _Unprintable(Exception):
    # An error whose message can't be turned into text: logging it fails part-way.
    def __str__(self):
        raise RuntimeError("str() broke")


def test_a_problem_while_logging_never_replaces_the_real_error(monkeypatch):
    def failing_search(query, k, experiment):
        raise _Unprintable()

    monkeypatch.setattr(api, "_search", failing_search)
    with pytest.raises(_Unprintable):  # the visitor's real error, not the RuntimeError
        api.search("flame spread")


def test_a_bad_setting_is_logged_because_logging_does_not_read_settings(monkeypatch):
    # GEMINI_CALLS_PER_MINUTE=ten makes get_settings() raise, and search() needs settings. If
    # error_log.record() read settings too, this failure could never be written down.
    monkeypatch.setenv("GEMINI_CALLS_PER_MINUTE", "ten")
    with pytest.raises(ValueError):
        api.search("flame spread")
    [entry] = error_log.read_log()
    assert "GEMINI_CALLS_PER_MINUTE" in entry["message"]


def test_a_gemini_failure_is_logged_as_a_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: _FailingClient())
    summary = api.summarize(PASSAGES, question="How fast?")  # quotes the passage, doesn't raise
    assert summary["takeaways"][0]["text"] == "Flame spread 2 mm/s."
    [entry] = error_log.read_log()
    assert (entry["call"], entry["kind"], entry["error_type"]) == (
        "summarize",
        "fallback",
        "ServerError",
    )
    assert entry["detail"] == "How fast?"


def test_a_reached_call_limit_is_logged(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(summarizer, "_limiter", RateLimiter(1, 60))
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: _FailingClient())
    summarizer.summarize_passages(PASSAGES, "first question")  # uses the one call (and falls back)
    error_log.ERROR_LOG.unlink()
    summarizer.summarize_passages(PASSAGES, "second question")
    [entry] = error_log.read_log()
    assert (entry["kind"], entry["error_type"]) == ("limit", "LimitReached")


def test_no_key_is_not_an_error():
    # It's a setup state, and it would add a line to the log for every summary.
    api.summarize(PASSAGES, question="How fast?")
    assert error_log.read_log() == []


def test_a_normal_call_logs_nothing(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    reply = '{"takeaways": [{"text": "Slow.", "chunk_id": "a-1"}], "not_found": false}'
    fake = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=reply))
    )
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: fake)
    api.search("flame spread")
    api.get_table({"experiment": "FLEX"})
    assert api.summarize(PASSAGES, question="How fast?")["takeaways"][0]["text"] == "Slow."
    assert error_log.read_log() == []
