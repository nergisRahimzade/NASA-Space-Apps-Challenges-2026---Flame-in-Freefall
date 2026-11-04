"""Day 2 (AI): chunk_text splits words with overlap; chunk_document keeps source and page."""

import json
from pathlib import Path

import pytest

from flame_in_freefall.chunking import chunk_document, chunk_text

MOCK_DOCS = Path(__file__).resolve().parents[1] / "data" / "mock" / "docs.mock.json"


def test_chunks_have_right_size_and_overlap():
    words = [f"w{i}" for i in range(10)]
    chunks = chunk_text(" ".join(words), size=4, overlap=1)
    assert chunks == ["w0 w1 w2 w3", "w3 w4 w5 w6", "w6 w7 w8 w9"]


def test_short_text_is_one_chunk():
    assert chunk_text("just three words") == ["just three words"]


def test_empty_text():
    assert chunk_text("   ") == []


def test_no_words_lost():
    text = " ".join(f"w{i}" for i in range(1000))
    seen = set(" ".join(chunk_text(text, size=200, overlap=40)).split())
    assert seen == set(text.split())


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1)])
def test_bad_settings(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("a b c", size=size, overlap=overlap)


def test_document_keeps_source_and_page():
    chunks = chunk_document(["page one text", "page two text"], "BASS report", "bass-001")
    assert [c["page"] for c in chunks] == [1, 2]
    assert chunks[1]["id"] == "bass-001-p2-c0"
    assert all(c["source"] == "BASS report" for c in chunks)


def test_document_rejects_empty_source():
    with pytest.raises(ValueError):
        chunk_document(["text"], source=" ", doc_id="bass-001")


def test_mock_docs_make_contract_chunks():
    docs = json.loads(MOCK_DOCS.read_text(encoding="utf-8"))
    assert len(docs) == 3  # the plan asks for 3 short fake docs
    chunks = [c for d in docs for c in chunk_document(d["pages"], d["source"], d["doc_id"])]
    for c in chunks:
        assert set(c) == {"id", "text", "source", "page"}  # chunk fields in docs/contract.md
        assert isinstance(c["page"], int) and c["text"]
    assert len({c["id"] for c in chunks}) == len(chunks)  # every id is unique
