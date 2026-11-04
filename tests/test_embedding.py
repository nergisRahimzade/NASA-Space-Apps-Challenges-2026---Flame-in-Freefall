"""Day 3 (AI): embed_texts gives unit-length rows; the fake docs embed and save.

A fake model stands in for all-MiniLM-L6-v2, so tests need no download or network."""

import json
from pathlib import Path

import numpy as np
import pytest

from flame_in_freefall import embedding
from flame_in_freefall.chunking import chunk_document
from flame_in_freefall.store import load_index, save_index

MOCK_DOCS = Path(__file__).resolve().parents[1] / "data" / "mock" / "docs.mock.json"


class FakeModel:
    """Returns one fixed 384-number row per text and remembers how it was called."""

    def __init__(self):
        self.name = None  # None = embed_texts hasn't asked for a model yet
        self.kwargs = {}

    def encode(self, texts, **kwargs):
        self.kwargs = kwargs
        return np.full((len(texts), 384), 1 / np.sqrt(384), dtype=np.float32)


@pytest.fixture
def fake_model(monkeypatch):
    model = FakeModel()

    def fake_get_model(name):
        model.name = name  # remember which model was asked for
        return model

    monkeypatch.setattr(embedding, "_get_model", fake_get_model)
    return model


def test_one_row_per_text(fake_model):
    assert embedding.embed_texts(["flame", "oxygen"]).shape == (2, 384)


def test_asks_for_unit_length_vectors(fake_model):
    embedding.embed_texts(["flame"])
    assert fake_model.kwargs["normalize_embeddings"] is True  # so cosine = dot product


def test_uses_model_from_settings(fake_model, monkeypatch):
    monkeypatch.setenv("EMBED_MODEL", "some/other-model")
    embedding.embed_texts(["flame"])
    assert fake_model.name == "some/other-model"


def test_empty_list_rejected(fake_model):
    with pytest.raises(ValueError):
        embedding.embed_texts([])


def test_blank_text_rejected(fake_model):
    with pytest.raises(ValueError):
        embedding.embed_texts(["flame", "  "])


def test_mock_docs_embed_and_save(fake_model, tmp_path):
    docs = json.loads(MOCK_DOCS.read_text(encoding="utf-8"))
    chunks = [c for d in docs for c in chunk_document(d["pages"], d["source"], d["doc_id"])]
    save_index(embedding.embed_texts([c["text"] for c in chunks]), chunks, tmp_path)
    vectors, loaded = load_index(tmp_path)
    assert vectors.shape == (len(chunks), 384)
    assert [c["id"] for c in loaded] == [c["id"] for c in chunks]  # row i still = chunk i
