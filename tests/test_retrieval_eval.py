"""Day 10 (AI): the answer key reproduces the Day 9 hand judgments, and scoring adds up.
Day 11 (AI): wrong-experiment chunks are counted for questions that name an experiment.
Day 13 (AI): judge() gives the right pass/fail and reason.
Day 14 (AI): the held-out questions are answerable and their experiment names are real.

No model needed: these tests only read text."""

import re
from pathlib import Path

import pytest

from flame_in_freefall.chunking import chunk_reports
from flame_in_freefall.retrieval_eval import (
    ANSWERABLE,
    HELD_OUT,
    NAMED_EXPERIMENT,
    QUESTIONS,
    SUMMARY_EXTRA,
    chance_of_a_hit,
    contains_evidence,
    is_relevant,
    judge,
    score_results,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.csv"
REPORTS = ROOT / "docs" / "reports"
DAY9_LOG = ROOT / "tests" / "retrieval.md"


def _day9_judgments() -> list[tuple[int, str, bool]]:
    """(question number, chunk id, judged relevant) for every row of the Day 9 results table."""
    rows = []
    for line in DAY9_LOG.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| (\d+) \|.*?\| \d \| [\d.]+ \| `([\w-]+)` \| (yes|no)", line)
        if m:
            rows.append((int(m[1]), m[2], m[3] == "yes"))
    return rows


def test_answer_key_matches_day9_hand_judgments():
    # Day 9 was judged with 150-word chunks and 30 words of overlap.
    text_by_id = {c["id"]: c["text"] for c in chunk_reports(SOURCES, REPORTS, 150, 30)}
    rows = _day9_judgments()
    assert len(rows) == 30  # 10 questions x top 3
    for n, chunk_id, judged in rows:
        assert is_relevant(n, text_by_id[chunk_id]) == judged, (n, chunk_id)


def test_every_answerable_question_has_an_answer_in_the_reports():
    # A phrase with a typo would never match, and the question would always look like a miss.
    chunks = chunk_reports(SOURCES, REPORTS, 150, 30)
    assert len(QUESTIONS) == 10 and ANSWERABLE == [1, 2, 3, 4, 5, 6, 7, 8]
    for n in ANSWERABLE:
        assert any(is_relevant(n, c["text"]) for c in chunks), n


def test_relevance_ignores_line_breaks():
    assert is_relevant(7, "an air flow velocity of either 20 or\n30   cm/s")
    assert not is_relevant(7, "an air flow velocity of 25 cm/s")
    assert not is_relevant(9, "CO2, He, and SF6")  # uncovered: nothing is relevant


def test_unknown_question_fails_loudly():
    with pytest.raises(ValueError):
        is_relevant(11, "some text")


def test_chance_of_a_hit():
    assert chance_of_a_hit(10, 0) == 0
    assert chance_of_a_hit(5, 1, k=5) == 1  # every chunk is picked
    assert chance_of_a_hit(10, 1) == pytest.approx(0.3)  # 3 picks from 10, 1 relevant


def test_score_results_counts_first_and_top_k():
    chunks = [
        {"id": "a", "text": "the gases were CO2, He, and SF6"},  # answers Q1
        {"id": "b", "text": "nothing useful here"},
    ]
    # Q1's best result is relevant; the other answerable questions get nothing relevant.
    results = {n: ["a", "b"] if n == 1 else ["b", "a"] for n in range(1, 11)}
    s = score_results(results, chunks, k=1)
    assert (s["first"], s["top_k"], s["relevant"], s["returned"]) == (1, 1, 1, 8)
    s = score_results(results, chunks, k=2)
    assert (s["first"], s["top_k"], s["relevant"]) == (1, 1, 1)


def test_named_experiments_match_the_chunk_tags():
    # A misspelled name would count every returned chunk as the wrong experiment.
    tags = {c["experiment"] for c in chunk_reports(SOURCES, REPORTS)}
    assert set(NAMED_EXPERIMENT.values()) <= tags
    for n, name in NAMED_EXPERIMENT.items():
        assert name.lower() in QUESTIONS[n - 1].lower(), n


def test_score_results_counts_wrong_experiment_chunks():
    chunks = [
        {"id": "a", "text": "nothing useful", "experiment": "FLEX"},
        {"id": "b", "text": "nothing useful", "experiment": "FLEX-2"},
        {"id": "c", "text": "nothing useful"},  # no tag: not counted either way
    ]
    results = {n: ["a", "b", "c"] for n in range(1, 11)}
    s = score_results(results, chunks, k=3)
    # Q2 names FLEX (b is wrong), Q4 and Q5 name FLEX-2 (a is wrong), Q7 names Saffire-II (both).
    assert (s["wrong_experiment"], s["named_returned"]) == (5, 8)
    s = score_results(results, chunks, k=1)
    assert (s["wrong_experiment"], s["named_returned"]) == (3, 4)


def _passage(chunk_id: str, text: str, experiment: str, score: float = 0.5) -> dict:
    return {"id": chunk_id, "text": text, "experiment": experiment, "score": score}


def test_judge_answerable_question():
    answer = _passage("flex2-p1-c1", "from 0.5 atm to 3.0 atm", "FLEX-2")
    other = _passage("flex2-p1-c3", "nothing useful", "FLEX-2")
    ok, reason = judge(4, [other, answer])
    assert ok and reason == "answer at rank 2 (flex2-p1-c1)"
    ok, reason = judge(4, [other])
    assert not ok and "none of the 1 returned" in reason
    ok, reason = judge(4, [])
    assert not ok and "under the cutoff" in reason


def test_judge_fails_a_named_question_with_wrong_experiment_chunks():
    # Q4 names FLEX-2; FLEX's pressure range alongside the right answer could reach the summary.
    answer = _passage("flex2-p1-c1", "from 0.5 atm to 3.0 atm", "FLEX-2")
    flex = _passage("flex-p1-c1", "0.5 to 1.5 atm", "FLEX")
    ok, reason = judge(4, [flex, answer])
    assert not ok and "answer at rank 2" in reason and "flex-p1-c1" in reason
    # Q1 names no experiment, so any experiment is fine.
    results = [_passage("x", "nothing", "Saffire-II"), _passage("y", "CO2, He, and SF6", "FLEX")]
    assert judge(1, results)[0]


def test_judge_marks_weak_passes():
    ok, reason = judge(3, [_passage("flex-p1-c6", "cool flames", "FLEX")])
    assert ok and "weak" in reason


def test_judge_uncovered_question_passes_only_on_no_match():
    ok, reason = judge(9, [])
    assert ok and reason.startswith("no match returned")
    ok, reason = judge(10, [_passage("flex-p1-c5", "nothing", "FLEX", score=0.411)])
    assert not ok and "0.411" in reason


def test_judge_unknown_question_fails_loudly():
    with pytest.raises(ValueError):
        judge(11, [])


def test_held_out_questions_are_answerable_and_new():
    # Like the 10 questions: a phrase with a typo, or split across 2 chunks, would never match.
    chunks = chunk_reports(SOURCES, REPORTS, 150, 30)
    tags = {c["experiment"] for c in chunks}
    assert len(HELD_OUT) == 10
    for question, phrases, named in HELD_OUT:
        assert phrases and question not in QUESTIONS, question
        assert any(contains_evidence(phrases, c["text"]) for c in chunks), question
        if named:
            assert named in tags and named.lower() in question.lower(), question


def test_bass2_summary_questions_are_answerable_and_new():
    # Day 16: every phrase must sit whole inside one real chunk, or no passage could ever match.
    chunks = chunk_reports(SOURCES, REPORTS, 150, 30)
    held = {q for q, _, _ in HELD_OUT}
    assert len(SUMMARY_EXTRA) == 2
    for question, phrases, named in SUMMARY_EXTRA:
        assert named == "BASS-II" and named.lower() in question.lower(), question
        assert question not in QUESTIONS and question not in held, question
        for phrase in phrases:
            assert any(contains_evidence([phrase], c["text"]) for c in chunks), phrase
