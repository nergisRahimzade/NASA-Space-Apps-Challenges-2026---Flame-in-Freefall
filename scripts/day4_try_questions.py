"""Day 4 (AI): ask 5 fake questions and check the top 3 chunks make sense.

Run from the project root, after building the fake index with scripts/day3_embed_mock.py:
    uv run python scripts/day4_try_questions.py
No API key needed."""

from pathlib import Path

from flame_in_freefall.config import setup_logging
from flame_in_freefall.retrieval import find_passages

MOCK_INDEX = Path(__file__).resolve().parents[1] / "artifacts" / "mock_index"

# Each question with the chunk that should come first, so "sensible" is a count, not a feeling.
QUESTIONS = [
    ("Why do flames spread slowly in microgravity?", "bass-mock-p2-c0"),
    ("What happens to a flame when the airflow is turned down?", "bass-mock-p3-c0"),
    ("What is a cool flame?", "flex-mock-p2-c0"),
    ("How large were the fires tested in space?", "saffire-mock-p1-c0"),
    ("Does faster airflow make a flame spread faster?", "saffire-mock-p2-c0"),
]

log = setup_logging()

first = in_top3 = 0
for question, expected in QUESTIONS:
    results = find_passages(question, k=3, folder=MOCK_INDEX)
    ids = [r["id"] for r in results]
    first += ids[0] == expected  # True counts as 1
    in_top3 += expected in ids  # the app shows all 3, so this is what the user would see
    log.info("%s %s", "OK  " if ids[0] == expected else "MISS", question)
    for r in results:
        log.info("     %.3f  %s  (%s, p. %d)", r["score"], r["id"], r["source"], r["page"])
log.info("Expected chunk ranked first: %d of %d", first, len(QUESTIONS))
log.info("Expected chunk in the top 3: %d of %d", in_top3, len(QUESTIONS))
