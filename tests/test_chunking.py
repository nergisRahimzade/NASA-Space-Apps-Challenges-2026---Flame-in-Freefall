"""Day 2 (AI): chunk_text splits words with overlap; chunk_document keeps source and page."""

import json
from pathlib import Path

import pytest

from flame_in_freefall.chunking import chunk_document, chunk_reports, chunk_text

ROOT = Path(__file__).resolve().parents[1]
MOCK_DOCS = ROOT / "data" / "mock" / "docs.mock.json"
SOURCES = ROOT / "data" / "sources.csv"
REPORTS = ROOT / "docs" / "reports"
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"


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


def test_real_reports_make_contract_chunks():
    chunks = chunk_reports(SOURCES, REPORTS)
    for c in chunks:
        assert set(c) == {"id", "text", "source", "page"}
        assert c["page"] == 1 and c["text"]  # plain-text reports have no pages
    assert len({c["id"] for c in chunks}) == len(chunks)
    assert {c["id"].split("-")[0] for c in chunks} == {"flex", "flex2", "saffire2"}
    assert all(c["source"].split(" ")[0] in {"FLEX", "FLEX-2", "Saffire-II"} for c in chunks)


def test_blank_report_fails_loudly(tmp_path):
    sources = tmp_path / "sources.csv"
    sources.write_text("file_name,title\nblank.txt,Blank report\n")
    (tmp_path / "blank.txt").write_text("   ")
    with pytest.raises(ValueError):
        chunk_reports(sources, tmp_path)


def test_saved_chunks_match_the_reports():
    # Fails if a report changes without re-running scripts/day7_chunk_reports.py
    lines = CHUNKS.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == chunk_reports(SOURCES, REPORTS)
