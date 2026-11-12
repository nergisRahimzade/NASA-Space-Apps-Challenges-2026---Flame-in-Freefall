"""Shared test setup: pytest runs the fixtures here before every test automatically."""

import zlib

import numpy as np
import pytest

from flame_in_freefall import api, embedding, speed, summarizer, usage


@pytest.fixture(autouse=True)
def _no_real_gemini_key(monkeypatch):
    # Even if your shell has a real key, tests never call Gemini (no network, no cost).
    # Tests that need a key set a fake one themselves.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Same for the call limit: a GEMINI_CALLS_PER_MINUTE in your shell must not change the tests.
    monkeypatch.delenv("GEMINI_CALLS_PER_MINUTE", raising=False)
    # Day 17: and for the prices, so a shell's price can't change a cost in the tests.
    monkeypatch.delenv("GEMINI_USD_PER_M_INPUT", raising=False)
    monkeypatch.delenv("GEMINI_USD_PER_M_OUTPUT", raising=False)


@pytest.fixture(autouse=True)
def _fresh_gemini_limiter(monkeypatch):
    # Day 16: the call limit lives for the whole process, so without this the 11th test that
    # reaches Gemini would be told "limit reached". None = the next summary makes a new one.
    monkeypatch.setattr(summarizer, "_limiter", None)


class _WordCountModel:
    """Stands in for all-MiniLM-L6-v2: each word bumps one of 384 numbers, so texts that share
    words point in similar directions. Crude, but it ranks, and it needs no download."""

    def encode(self, texts, **kwargs):
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in text.lower().split():
                # crc32 gives the same number for a word in every run (hash() doesn't).
                vectors[row, zlib.crc32(word.encode()) % 384] += 1
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)  # length 1, like the real model


@pytest.fixture(autouse=True)
def _no_real_embedding_model(monkeypatch, tmp_path):
    # Real search (D10) would download the embedding model (~90 MB) in CI and write
    # artifacts/index/ in the repo. Tests get the fake model and a throwaway index folder.
    # Tests that fake the model themselves (e.g. test_embedding.py) still override this.
    monkeypatch.setattr(embedding, "_get_model", lambda name: _WordCountModel())
    monkeypatch.setattr(api, "INDEX", tmp_path / "index")
    # Day 13: MIN_SCORE was measured on the real model; the fake one scores differently, so the
    # cutoff is off by default. Tests about "no match" set it themselves.
    monkeypatch.setattr(api, "MIN_SCORE", float("-inf"))


@pytest.fixture(autouse=True)
def _fresh_speed_log_and_cache(monkeypatch, tmp_path):
    # Day 11: timings go to a throwaway speed log, not artifacts/speed.log in the repo. The
    # search cache lives for the whole test run, so empty it: each test starts with nothing
    # remembered, and answers from another test's index can't leak in.
    monkeypatch.setattr(speed, "SPEED_LOG", tmp_path / "speed.log")
    api._find.cache.clear()


@pytest.fixture(autouse=True)
def _fresh_summary_cache_and_usage_log(monkeypatch, tmp_path):
    # Day 17: a remembered summary would let one test's answer leak into another (and skip its
    # fake Gemini), and token counts go to a throwaway log, not artifacts/usage.log in the repo.
    summarizer.clear_summary_cache()
    monkeypatch.setattr(usage, "USAGE_LOG", tmp_path / "usage.log")
