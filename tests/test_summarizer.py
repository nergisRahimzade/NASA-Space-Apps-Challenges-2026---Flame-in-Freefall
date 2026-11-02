"""Day 5 (BE): summarize_passages with a fake OpenAI client (no network, no key)."""

import json
from types import SimpleNamespace

import openai
import pytest

from flame_in_freefall import summarizer
from flame_in_freefall.summarizer import summarize_passages

PASSAGES = [
    {"id": "bass-001-p3-c0", "text": "Spread was 1.2 mm/s. More.", "source": "BASS", "page": 3},
    {"id": "flex-002-p1-c0", "text": "Droplet burned 2 s.", "source": "FLEX", "page": 1},
]


class FakeClient:
    """Stands in for OpenAI(): remembers each request and replies with text or an error."""

    def __init__(self, reply: str = "", error: Exception | None = None):
        self.calls = []
        self.reply, self.error = reply, error
        self.responses = self  # so fake.responses.create(...) works like the real client

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(output_text=self.reply)


@pytest.fixture
def use_fake(monkeypatch):
    # Set a fake key and swap in the fake client; returns a helper that installs one.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def install(**kwargs) -> FakeClient:
        fake = FakeClient(**kwargs)
        monkeypatch.setattr(summarizer, "_get_client", lambda api_key: fake)
        return fake

    return install


def _reply(takeaways: list[dict], not_found: bool = False) -> str:
    return json.dumps({"takeaways": takeaways, "not_found": not_found})


def test_model_reply_gets_real_source(use_fake):
    use_fake(reply=_reply([{"text": "Spread is slow.", "chunk_id": "bass-001-p3-c0"}]))
    out = summarize_passages(PASSAGES)
    assert out == {
        "takeaways": [{"text": "Spread is slow.", "source": "BASS", "chunk_id": "bass-001-p3-c0"}],
        "not_found": False,
    }


def test_sends_prompt_and_passage_ids(use_fake):
    fake = use_fake(reply=_reply([], not_found=True))
    summarize_passages(PASSAGES)
    sent = fake.calls[0]
    assert sent["instructions"] == summarizer.PROMPT_PATH.read_text(encoding="utf-8")
    assert "[bass-001-p3-c0]" in sent["input"] and "[flex-002-p1-c0]" in sent["input"]


def test_not_found_reply(use_fake):
    use_fake(reply=_reply([], not_found=True))
    assert summarize_passages(PASSAGES) == {"takeaways": [], "not_found": True}


def test_no_passages_skips_openai(use_fake):
    fake = use_fake(reply="unused")
    assert summarize_passages([]) == {"takeaways": [], "not_found": True}
    assert fake.calls == []


def test_no_key_quotes_passages():
    # conftest.py already removed OPENAI_API_KEY, so this is the "no key" case.
    out = summarize_passages(PASSAGES)
    assert out["not_found"] is False
    assert out["takeaways"][0] == {
        "text": "Spread was 1.2 mm/s.",
        "source": "BASS",
        "chunk_id": "bass-001-p3-c0",
    }


def test_timeout_falls_back(use_fake):
    # request=None: the error normally carries the HTTP request, but a fake doesn't need one.
    use_fake(error=openai.APITimeoutError(request=None))
    out = summarize_passages(PASSAGES)
    assert [t["chunk_id"] for t in out["takeaways"]] == ["bass-001-p3-c0", "flex-002-p1-c0"]


def test_broken_json_falls_back(use_fake):
    use_fake(reply="not json")
    assert summarize_passages(PASSAGES)["takeaways"][1]["text"] == "Droplet burned 2 s."


def test_invented_chunk_id_falls_back(use_fake):
    use_fake(reply=_reply([{"text": "Made up.", "chunk_id": "nope-999"}]))
    texts = [t["text"] for t in summarize_passages(PASSAGES)["takeaways"]]
    assert "Made up." not in texts
