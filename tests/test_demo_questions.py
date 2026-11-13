"""Day 19 (FIF-D19-DAT): demo_questions.md lists 5 usable questions with real expected sources.

CI uses a stand-in search model, so these tests check the file and the passages, not the ranking.
scripts/day19_check_demo_questions.py checks the ranking with the real model."""

import importlib.util
import json
from pathlib import Path

from flame_in_freefall import api
from flame_in_freefall.demo_questions import DEMO_FILE, load_demo_questions

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = {
    c["id"]: c
    for c in (
        json.loads(line)
        for line in (ROOT / "data" / "processed" / "chunks.jsonl").read_text().splitlines()
        if line.strip()
    )
}
# Same table as the card's "Expected sources": chunk and the evidence copied from it.
EVIDENCE = {
    1: ("flex-p1-c5", "CO2, He, and SF6"),
    2: ("bass2-p1-c1", "airflow speeds up to 40 cm/s"),
    3: ("flex2-p1-c3", "Deploy the droplet(s)"),
    4: ("saffire2-p1-c2", "without risk to a crew"),
    5: ("saffire2-p1-c0", "each 5 cm x 29 cm"),
}


def _check_script():
    spec = importlib.util.spec_from_file_location(
        "day19_check", ROOT / "scripts" / "day19_check_demo_questions.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_file_has_five_questions():
    items = load_demo_questions()
    assert len(items) == 5
    assert all(item["question"].endswith("?") for item in items)
    assert len({item["question"] for item in items}) == 5  # no repeats


def test_questions_fit_the_search_box():
    # BE rejects questions over MAX_QUERY_CHARS (contract v1.9); a demo button must never hit it
    assert all(len(item["question"]) <= api.MAX_QUERY_CHARS for item in load_demo_questions())


def test_every_experiment_with_a_report_is_covered():
    sources = {item["source"] for item in load_demo_questions()}
    assert sources == {"FLEX", "FLEX-2", "Saffire-II", "BASS-II"}


def test_expected_chunks_exist_hold_the_evidence_and_match_the_source():
    items = load_demo_questions()
    for number, (chunk_id, phrase) in EVIDENCE.items():
        chunk = CHUNKS[chunk_id]
        assert phrase in chunk["text"], (number, chunk_id)
        assert chunk["experiment"] == items[number - 1]["source"], number
        assert f"`{chunk_id}`" in DEMO_FILE.read_text(encoding="utf-8")


def test_check_script_expects_the_same_chunks():
    assert _check_script().EXPECTED_CHUNK == {n: chunk for n, (chunk, _) in EVIDENCE.items()}


def test_parser_reads_numbered_lines_only(tmp_path):
    md = tmp_path / "demo.md"
    md.write_text(
        "# Title\n\nIntro text.\n\n1. First question? — FLEX\n2. Second question?\n"
        "- a bullet, not a question\n| 1 | table row |\n10. Tenth question? – BASS-II\n",
        encoding="utf-8",
    )
    assert load_demo_questions(md) == [
        {"question": "First question?", "source": "FLEX"},
        {"question": "Second question?", "source": ""},
        {"question": "Tenth question?", "source": "BASS-II"},
    ]


def test_missing_file_gives_no_questions(tmp_path):
    assert load_demo_questions(tmp_path / "missing.md") == []
