"""Day 17 (BE): every Gemini call's tokens go to the usage log (conftest.py points USAGE_LOG at a
throwaway file and removes the price settings from the environment)."""

import json
from types import SimpleNamespace

import pytest

from flame_in_freefall import summarizer, usage
from flame_in_freefall.config import get_settings

PASSAGES = [{"id": "a-1", "text": "Flame spread 2 mm/s.", "source": "S", "page": 1}]
REPLY = json.dumps({"takeaways": [{"text": "Slow.", "chunk_id": "a-1"}], "not_found": False})


def test_a_call_adds_one_line_with_its_token_counts():
    usage.record("model-x", 900, 40)
    [entry] = usage.read_log()
    assert entry["model"] == "model-x"
    assert (entry["input_tokens"], entry["output_tokens"]) == (900, 40)
    assert entry["at"].endswith("+00:00")


def test_no_price_means_no_cost():
    usage.record("model-x", 900, 40)
    assert usage.read_log()[0]["cost_usd"] is None


def test_prices_turn_tokens_into_dollars(monkeypatch):
    monkeypatch.setenv("GEMINI_USD_PER_M_INPUT", "0.5")
    monkeypatch.setenv("GEMINI_USD_PER_M_OUTPUT", "2")
    usage.record("model-x", 2_000_000, 500_000)
    assert usage.read_log()[0]["cost_usd"] == pytest.approx(2.0)  # 2 x 0.5 + 0.5 x 2


def test_one_price_alone_is_not_enough_for_a_cost(monkeypatch):
    monkeypatch.setenv("GEMINI_USD_PER_M_INPUT", "0.5")
    usage.record("model-x", 900, 40)
    assert usage.read_log()[0]["cost_usd"] is None


def test_missing_token_counts_are_kept_as_none_not_zero(monkeypatch):
    monkeypatch.setenv("GEMINI_USD_PER_M_INPUT", "0.5")
    monkeypatch.setenv("GEMINI_USD_PER_M_OUTPUT", "2")
    usage.record("model-x", None, None)
    [entry] = usage.read_log()
    assert (entry["input_tokens"], entry["output_tokens"], entry["cost_usd"]) == (None, None, None)


def test_a_read_only_disk_does_not_break_a_call(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    monkeypatch.setattr(usage, "USAGE_LOG", blocker / "usage.log")  # can't make a folder in a file
    usage.record("model-x", 1, 1)  # must not raise


def test_a_damaged_line_is_skipped_not_fatal(caplog):
    # The app can stop part-way through writing a line; the other calls must still be reported.
    usage.record("model-x", 900, 40)
    with open(usage.USAGE_LOG, "a", encoding="utf-8") as f:
        f.write('{"input_tok')
    with caplog.at_level("INFO", logger="flame_in_freefall.usage"):
        usage.main()
    assert "skipped 1 damaged lines" in caplog.text and "1 Gemini calls" in caplog.text


def test_totals_add_up_and_say_what_is_missing():
    entries = [
        {"input_tokens": 100, "output_tokens": 10, "cost_usd": 0.5},
        {"input_tokens": 200, "output_tokens": 20, "cost_usd": 1.0},
        {"input_tokens": None, "output_tokens": None, "cost_usd": None},
    ]
    assert usage.totals(entries) == {
        "calls": 3,
        "input_tokens": 300,
        "output_tokens": 30,
        "unknown_tokens": 1,
        "cost_usd": 1.5,
        "unpriced": 1,
    }


def test_totals_without_any_price_have_no_cost():
    totals = usage.totals([{"input_tokens": 5, "output_tokens": 1, "cost_usd": None}])
    assert totals["cost_usd"] is None and totals["unpriced"] == 1


def test_the_report_says_the_price_is_not_set(caplog):
    usage.record("model-x", 900, 40)
    with caplog.at_level("INFO", logger="flame_in_freefall.usage"):
        usage.main()
    assert "price not set" in caplog.text and "900 input tokens" in caplog.text


@pytest.mark.parametrize("counts", [(None, None), (900, None), (None, 40)])
def test_the_report_explains_unknown_cost_when_prices_are_set(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, counts: tuple
):
    monkeypatch.setenv("GEMINI_USD_PER_M_INPUT", "0.5")
    monkeypatch.setenv("GEMINI_USD_PER_M_OUTPUT", "2")
    usage.record("model-x", *counts)
    with caplog.at_level("INFO", logger="flame_in_freefall.usage"):
        usage.main()
    assert "Cost: unavailable (price not set or token count missing when calls ran)" in caplog.text


def test_the_report_explains_why_a_cost_sum_is_partial(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    monkeypatch.setenv("GEMINI_USD_PER_M_INPUT", "0.5")
    monkeypatch.setenv("GEMINI_USD_PER_M_OUTPUT", "2")
    usage.record("model-x", 2_000_000, 500_000)
    usage.record("model-x", None, 40)
    with caplog.at_level("INFO", logger="flame_in_freefall.usage"):
        usage.main()
    assert "Cost: $2.0000" in caplog.text
    assert "1 calls lacked prices or token counts when they ran" in caplog.text


def test_the_report_with_no_calls_yet_does_not_crash(caplog):
    with caplog.at_level("INFO", logger="flame_in_freefall.usage"):
        usage.main()
    assert "No usage log yet" in caplog.text


# --- the summarizer writes the log -------------------------------------------------------------


def _fake_gemini(monkeypatch, response) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: response))
    monkeypatch.setattr(summarizer, "_get_client", lambda api_key: client)


def test_a_gemini_summary_logs_the_tokens_google_reported(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "model-x")
    meta = SimpleNamespace(prompt_token_count=900, candidates_token_count=40)
    _fake_gemini(monkeypatch, SimpleNamespace(text=REPLY, usage_metadata=meta))
    summarizer.summarize_passages(PASSAGES, "q")
    [entry] = usage.read_log()
    assert (entry["model"], entry["input_tokens"], entry["output_tokens"]) == ("model-x", 900, 40)


def test_a_reply_without_usage_data_is_still_summarized_and_logged(monkeypatch):
    _fake_gemini(monkeypatch, SimpleNamespace(text=REPLY))  # no usage_metadata at all
    assert summarizer.summarize_passages(PASSAGES, "q")["takeaways"][0]["text"] == "Slow."
    [entry] = usage.read_log()
    assert entry["input_tokens"] is None and entry["output_tokens"] is None


def test_a_paid_call_with_an_unusable_reply_is_still_logged(monkeypatch):
    meta = SimpleNamespace(prompt_token_count=900, candidates_token_count=40)
    _fake_gemini(monkeypatch, SimpleNamespace(text="not json", usage_metadata=meta))
    summarizer.summarize_passages(PASSAGES, "q")  # falls back to quoting
    assert len(usage.read_log()) == 1


def test_a_remembered_answer_is_not_logged_again(monkeypatch):
    meta = SimpleNamespace(prompt_token_count=900, candidates_token_count=40)
    _fake_gemini(monkeypatch, SimpleNamespace(text=REPLY, usage_metadata=meta))
    summarizer.summarize_passages(PASSAGES, "q")
    summarizer.summarize_passages(PASSAGES, "q")
    assert len(usage.read_log()) == 1


def test_quoting_without_a_key_logs_nothing():
    summarizer.summarize_passages(PASSAGES, "q")  # conftest.py removed the key
    assert usage.read_log() == []


# --- the price settings ------------------------------------------------------------------------


def test_prices_default_to_none():
    s = get_settings()
    assert s.gemini_usd_per_m_input is None and s.gemini_usd_per_m_output is None


@pytest.mark.parametrize("blank", ["", "  "])
def test_a_blank_price_means_not_set(monkeypatch, blank):
    monkeypatch.setenv("GEMINI_USD_PER_M_INPUT", blank)
    assert get_settings().gemini_usd_per_m_input is None


@pytest.mark.parametrize("bad", ["free", "-1", "nan", "$0.5"])
def test_a_bad_price_fails_loudly(monkeypatch, bad):
    monkeypatch.setenv("GEMINI_USD_PER_M_OUTPUT", bad)
    with pytest.raises(ValueError, match="GEMINI_USD_PER_M_OUTPUT"):
        get_settings()


@pytest.mark.parametrize("name", ["GEMINI_USD_PER_M_INPUT", "GEMINI_USD_PER_M_OUTPUT"])
@pytest.mark.parametrize("bad", ["inf", "+inf", "Infinity", "1e309"])
def test_an_infinite_price_fails_loudly(monkeypatch: pytest.MonkeyPatch, name: str, bad: str):
    monkeypatch.setenv(name, bad)
    with pytest.raises(ValueError, match=name):
        get_settings()


def test_a_price_of_zero_is_allowed(monkeypatch):
    # A free tier: tokens still count, and the cost is $0.
    monkeypatch.setenv("GEMINI_USD_PER_M_INPUT", "0")
    assert get_settings().gemini_usd_per_m_input == 0.0
