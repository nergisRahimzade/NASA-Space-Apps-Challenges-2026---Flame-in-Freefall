"""FIF-D16-AI, Day 16: partial measurements must preserve the full Gemini recording.

Fake results exercise the command's file handling without a key or network calls.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script() -> ModuleType:
    # scripts/ isn't a package, so the file is loaded by its path.
    spec = importlib.util.spec_from_file_location(
        "day16_test_summaries", ROOT / "scripts" / "day16_test_summaries.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    module = _load_script()
    monkeypatch.setattr(module, "ARTIFACTS", tmp_path / "artifacts")
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key="fake", gemini_model="fake"),
    )

    # No search, model, sleep, or app logging to disk: only the script's output handling runs.
    def fake_run_one(
        label: str, question: str, phrases: list[str], experiment: str | None, run: str, model: str
    ) -> dict:
        return {
            "label": label,
            "run": run,
            "experiment": experiment,
            "question": question,
            "model": model,
            "prompt": module.summarizer.PROMPT_PATH.name,
            "recorded": "2026-11-12",
            "passages": [],
            "summary": None,
            "fallback": False,
            "seconds": 0.0,
            "claims": [],
            "answer": [],
            "error": None,
        }

    monkeypatch.setattr(module, "run_one", fake_run_one)
    # Keep --prompt changes local to this test, including changes made inside main().
    monkeypatch.setattr(module.summarizer, "PROMPT_PATH", tmp_path / "summary_v2.txt")
    return module


@pytest.mark.parametrize("selection", [[], ["typo"], ["Q1", "typo"]])
def test_invalid_selection_stops_before_any_calls_or_output(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, selection: list[str]
):
    def unexpected_settings() -> None:
        pytest.fail("Invalid labels must be rejected before preparing a Gemini run")

    monkeypatch.setattr(script, "get_settings", unexpected_settings)
    with pytest.raises(SystemExit) as exc:
        script.main(["--only", *selection])
    assert exc.value.code == 2
    assert not script.ARTIFACTS.exists()


@pytest.mark.parametrize("prompt", [None, "summary_v3.txt"])
def test_partial_runs_preserve_full_recordings(script: ModuleType, prompt: str | None):
    script.ARTIFACTS.mkdir()
    stem = "day16" + ("_summary_v3" if prompt else "")
    full_reply = script.ARTIFACTS / f"{stem}_replies.json"
    full_draft = script.ARTIFACTS / f"{stem}_summaries_draft.md"
    full_reply.write_text("original full recording", encoding="utf-8")
    full_draft.write_text("original full draft", encoding="utf-8")
    args = ["--only", "Q2"]
    if prompt:
        (script.summarizer.PROMPT_PATH.parent / prompt).touch()
        args += ["--prompt", prompt]

    script.main(args)

    assert full_reply.read_text(encoding="utf-8") == "original full recording"
    assert full_draft.read_text(encoding="utf-8") == "original full draft"
    partial = script.ARTIFACTS / f"{stem}_only_Q2_replies.json"
    records = json.loads(partial.read_text(encoding="utf-8"))
    assert [(r["label"], r["run"]) for r in records] == [("Q2", "picked"), ("Q2", "default")]
    assert (script.ARTIFACTS / f"{stem}_only_Q2_summaries_draft.md").is_file()


def test_full_runs_keep_the_original_output_names(script: ModuleType):
    script.main([])
    records = json.loads((script.ARTIFACTS / "day16_replies.json").read_text(encoding="utf-8"))
    assert len(records) == 32
    assert (script.ARTIFACTS / "day16_summaries_draft.md").is_file()


def _stop_on_call(script: ModuleType, monkeypatch: pytest.MonkeyPatch, n: int) -> None:
    # Like pressing Ctrl+C during the n-th Gemini call.
    finished = []
    fake_run_one = script.run_one

    def stopping_run_one(*args):
        if len(finished) == n - 1:
            raise KeyboardInterrupt
        finished.append(args[0])
        return fake_run_one(*args)

    monkeypatch.setattr(script, "run_one", stopping_run_one)


def test_a_run_that_stops_part_way_saves_what_finished_under_its_own_name(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch
):
    # Every finished answer cost a Gemini call, but a partial run must not replace a full one.
    script.ARTIFACTS.mkdir()
    full_reply = script.ARTIFACTS / "day16_replies.json"
    full_reply.write_text("original full recording", encoding="utf-8")
    _stop_on_call(script, monkeypatch, 3)
    with pytest.raises(KeyboardInterrupt):
        script.main([])
    assert full_reply.read_text(encoding="utf-8") == "original full recording"
    saved = script.ARTIFACTS / "day16_stopped_after_2_replies.json"
    assert [r["label"] for r in json.loads(saved.read_text(encoding="utf-8"))] == ["Q1", "Q2"]
    assert (script.ARTIFACTS / "day16_stopped_after_2_summaries_draft.md").is_file()


def test_a_run_that_stops_before_any_answer_writes_nothing(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch
):
    _stop_on_call(script, monkeypatch, 1)
    with pytest.raises(KeyboardInterrupt):
        script.main([])
    assert not script.ARTIFACTS.exists()


# --- the real run_one, with a fake Gemini (conftest.py gives a fake embedding model) ----------

BASS2_QUESTION = "How fast could the air blow in the BASS-II wind tunnel?"


def _client_citing_the_first_passage(reply_text: str) -> object:
    # Answers like Gemini, citing whichever passage it was sent first, with a made-up number.
    def generate_content(**kwargs):
        first = kwargs["contents"].split("[", 1)[1].split("]", 1)[0]
        text = json.dumps(
            {"takeaways": [{"text": reply_text, "chunk_id": first}], "not_found": False}
        )
        usage = SimpleNamespace(prompt_token_count=900, candidates_token_count=40)
        return SimpleNamespace(text=text, usage_metadata=usage)

    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))


def test_run_one_records_the_exact_reply_tokens_and_claim_flags(monkeypatch: pytest.MonkeyPatch):
    module = _load_script()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = _client_citing_the_first_passage("The tunnel reached 99 cm/s.")
    fake_get_client = lambda key: client  # noqa: E731
    monkeypatch.setattr(module.summarizer, "_get_client", fake_get_client)
    record = module.run_one(BASS2_QUESTION, BASS2_QUESTION, [], "BASS-II", "picked", "test-model")
    assert record["fallback"] is False and record["error"] is None
    assert json.loads(record["raw_reply"])["takeaways"][0]["text"] == "The tunnel reached 99 cm/s."
    assert record["tokens"] == {"input": 900, "output": 40}
    assert record["claims"] and record["claims"][0].endswith("numbers not in the passage: 99")
    assert record["passages"] and all(len(p["sha256"]) == 64 for p in record["passages"])
    assert module.summarizer._get_client is fake_get_client  # the wrapper was taken off again


def test_run_one_records_a_gemini_error_as_a_fallback(monkeypatch: pytest.MonkeyPatch):
    module = _load_script()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def failing_get_client(key):
        def generate_content(**kwargs):
            raise httpx.ReadTimeout("too slow")

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    monkeypatch.setattr(module.summarizer, "_get_client", failing_get_client)
    record = module.run_one(BASS2_QUESTION, BASS2_QUESTION, [], "BASS-II", "picked", "test-model")
    assert record["fallback"] is True  # the passages were quoted, so it isn't judged as Gemini's
    assert record["error"].startswith("ReadTimeout")
    assert record["raw_reply"] is None
    assert module.summarizer._get_client is failing_get_client  # put back even after the error


def test_run_one_puts_the_client_back_even_if_the_call_is_stopped(monkeypatch: pytest.MonkeyPatch):
    # A Gemini error is turned into a fallback inside summarize(), but Ctrl+C isn't: it leaves
    # run_one part-way, and the recording wrapper must still be taken off.
    module = _load_script()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def stopped_get_client(key):
        def generate_content(**kwargs):
            raise KeyboardInterrupt

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    monkeypatch.setattr(module.summarizer, "_get_client", stopped_get_client)
    with pytest.raises(KeyboardInterrupt):
        module.run_one(BASS2_QUESTION, BASS2_QUESTION, [], "BASS-II", "picked", "test-model")
    assert module.summarizer._get_client is stopped_get_client


def test_run_one_records_a_reply_even_when_the_same_question_was_answered_before(
    monkeypatch: pytest.MonkeyPatch,
):
    # Day 17: summarize() remembers answers, and a remembered one makes no Gemini call, so there
    # would be no reply to record. The picked and default runs can send the same passages.
    module = _load_script()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = _client_citing_the_first_passage("Spread was slow.")
    monkeypatch.setattr(module.summarizer, "_get_client", lambda key: client)
    args = (BASS2_QUESTION, BASS2_QUESTION, [], "BASS-II")
    first = module.run_one(*args, "picked", "test-model")
    second = module.run_one(*args, "default", "test-model")
    assert first["raw_reply"] and second["raw_reply"] and second["tokens"] == first["tokens"]
