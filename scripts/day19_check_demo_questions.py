"""Day 19 (DAT): check that each demo question finds its expected passage first.

Run from the repo root (uses the real search model, as in the app; no Gemini key needed):
    uv run --locked python scripts/day19_check_demo_questions.py

Searches every question in demo_questions.md with no experiment picked (the app's default) and
prints where the expected chunk ranks. Exits with 1 if any isn't first."""

import sys

from flame_in_freefall import api
from flame_in_freefall.demo_questions import load_demo_questions

# Question number -> the chunk that should come first (demo_questions.md, "Expected sources").
EXPECTED_CHUNK = {
    1: "flex-p1-c5",
    2: "bass2-p1-c1",
    3: "flex2-p1-c3",
    4: "saffire2-p1-c2",
    5: "saffire2-p1-c0",
}


def main() -> None:
    all_first = True
    for number, item in enumerate(load_demo_questions(), start=1):
        results = api.search(item["question"])
        ids = [r["id"] for r in results]
        want = EXPECTED_CHUNK.get(number)
        rank = ids.index(want) + 1 if want in ids else None
        top = f"{results[0]['score']:.2f}" if results else "-"
        where = f"rank {rank or 'missing'} of {len(ids)} (top score {top})"
        print(f"{number}. {where}: {item['question']}")
        all_first &= rank == 1
    sys.exit(0 if all_first else 1)


if __name__ == "__main__":
    main()
