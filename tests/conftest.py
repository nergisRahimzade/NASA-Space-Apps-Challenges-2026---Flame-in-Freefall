"""Shared test setup: pytest runs the fixtures here before every test automatically."""

import pytest


@pytest.fixture(autouse=True)
def _no_real_openai_key(monkeypatch):
    # Even if your shell has a real key, tests never call OpenAI (no network, no cost).
    # Tests that need a key set a fake one themselves.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
