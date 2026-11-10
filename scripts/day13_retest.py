"""Day 13 (AI): run the 10 Day 9 questions again through the real search() and record pass/fail.

Run from the project root:  uv run python scripts/day13_retest.py
No API key needed. Unlike Days 10-12, this calls api.search() itself, exactly as the app does
since D13-BE: k = 5, the experiment filter, and the 0.30 score cutoff (api.MIN_SCORE). It builds
artifacts/index/ first if it's missing or out of date, like the app does.

Two runs, matching the app's experiment dropdown:
  - "All experiments" (the app's default): every question runs unfiltered.
  - "Experiment picked": Q2, Q4, Q5 and Q7 run as if the user picked the experiment they name
    (NAMED_EXPERIMENT); the others stay unfiltered.
Pass/fail comes from retrieval_eval.judge(). To explain each result, the script also asks
find_passages() for the same top 5 *before* the cutoff and notes what the cutoff removed.
Writes artifacts/day13_retest_draft.md; the judged copy lives in tests/retest.md."""

from pathlib import Path

from flame_in_freefall import api
from flame_in_freefall.config import setup_logging
from flame_in_freefall.retrieval import find_passages
from flame_in_freefall.retrieval_eval import NAMED_EXPERIMENT, QUESTIONS, is_relevant, judge

ROOT = Path(__file__).resolve().parents[1]  # works no matter which folder you run from
DRAFT = ROOT / "artifacts" / "day13_retest_draft.md"
K = 5  # search()'s default since contract v1.1

log = setup_logging()

RUNS = {
    "All experiments": lambda n: None,
    "Experiment picked": lambda n: NAMED_EXPERIMENT.get(n),
}

lines = []
for run, pick in RUNS.items():
    lines += [
        f"## {run}",
        "",
        "| # | Question | Filter | Returned | Result | Reason | Removed by the cutoff |",
        "|---|---|---|---|---|---|---|",
    ]
    passed = 0
    for n, question in enumerate(QUESTIONS, start=1):
        experiment = pick(n)
        results = api.search(question, k=K, experiment=experiment)
        ok, reason = judge(n, results)
        passed += ok
        # The same search without the cutoff, to see what MIN_SCORE took away.
        before = find_passages(question, K, folder=api.INDEX, experiment=experiment)
        kept = {r["id"] for r in results}
        removed = [
            f"`{p['id']}` {p['score']:.3f}{' (answer!)' if is_relevant(n, p['text']) else ''}"
            for p in before
            if p["id"] not in kept
        ]
        lines.append(
            f"| {n} | {question} | {experiment or 'none'} | {len(results)} | "
            f"{'PASS' if ok else 'FAIL'} | {reason} | {', '.join(removed) or '-'} |"
        )
        log.info("%s Q%d: %s, %s", run, n, "PASS" if ok else "FAIL", reason)
    lines += ["", f"**{run}: {passed} of {len(QUESTIONS)} pass.**", ""]
    log.info("%s: %d of %d pass", run, passed, len(QUESTIONS))

# Every passage search() returned in the "Experiment picked" run, to read by hand.
lines += ["## Returned passages (Experiment picked)", "", "| # | Rank | Score | Chunk | Answer? |"]
lines.append("|---|---|---|---|---|")
for n, question in enumerate(QUESTIONS, start=1):
    for r, p in enumerate(api.search(question, k=K, experiment=NAMED_EXPERIMENT.get(n)), start=1):
        match = "yes" if is_relevant(n, p["text"]) else "no"
        lines.append(f"| {n} | {r} | {p['score']:.3f} | `{p['id']}` | {match} |")

DRAFT.parent.mkdir(parents=True, exist_ok=True)
DRAFT.write_text("\n".join(lines) + "\n", encoding="utf-8")
log.info("Draft -> %s", DRAFT)
