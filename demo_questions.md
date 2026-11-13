# Demo questions (FIF-D19-DAT)

Five questions for the demo and for the app's example buttons (FIF-D19-FE). Each one is answered
by the reports, finds its answer in the **first** search result with no experiment picked, and got
a summary that matches its source in the Day 16 test (`tests/summaries.md`). Together they cover
all four experiments.

The app reads the numbered lines below: one button per line, showing the text before " — ".
The part after " — " is the expected source, for us, not for the button.

1. What gases were tested as fire suppressants in microgravity? — FLEX
2. How fast could the air blow in the BASS-II wind tunnel? — BASS-II
3. How were fuel droplets deployed and ignited in FLEX-2? — FLEX-2
4. Why run a big fire test on a spacecraft with nobody on board? — Saffire-II
5. How big was each Saffire-II sample? — Saffire-II

## Expected sources

Every source is page 1 of the experiment's investigation description in `docs/reports/`, linked
from `data/sources.csv`. The "evidence" is copied word for word from that passage.

| # | Expected source | Chunk | Evidence in the passage | Search, no filter (2026-11-12) |
|---|---|---|---|---|
| 1 | FLEX investigation description, p. 1 | `flex-p1-c5` | "CO2, He, and SF6" | 1st of 5, score 0.75; the top 3 all hold it |
| 2 | BASS-II investigation description, p. 1 | `bass2-p1-c1` | "airflow speeds up to 40 cm/s" | 1st of 1, score 0.40 |
| 3 | FLEX-2 investigation description, p. 1 | `flex2-p1-c3` | "Deploy the droplet(s)" | 1st of 5, score 0.62 |
| 4 | Saffire-II investigation description, p. 1 | `saffire2-p1-c2` | "without risk to a crew" | 1st of 5, score 0.57 |
| 5 | Saffire-II investigation description, p. 1 | `saffire2-p1-c0` | "each 5 cm x 29 cm" | 1st of 2, score 0.50 |

**Summaries** (real Gemini, Day 16, judged against the passages): all supported. #1 keeps the
report's "aims to" wording, #4 keeps "proposed", and #3 gives the deploy, needle and ignitor steps.

## How they were picked

- **Candidates:** the 22 questions already tested (`QUESTIONS`, `HELD_OUT` and `SUMMARY_EXTRA` in
  `src/flame_in_freefall/retrieval_eval.py`). Re-using them means each one already has evidence
  phrases and a judged summary.
- **Kept:** questions whose evidence is in the **first** result with no experiment picked, since a
  button click searches with the sidebar on "All" by default. Then the ones whose summary was
  fully supported.
- **Left out, with reasons:**
  - "What oxygen levels and pressures were used in the FLEX-2 chamber?": the top result is FLEX's
    passage, with the wrong experiment's pressures; the answer is only 4th.
  - "What airflow speeds were used in Saffire-II?" and "Which materials were burned in
    Saffire-II?": the answer is 2nd or 3rd, not 1st.
  - "Why are normal-gravity fire tests risky for designing spacecraft safety systems?": search
    is right, but the summary writes Saffire-II's hypothesis as a fact (Day 16 wording slip).
  - "What is the Limiting Oxygen Index and how did FLEX measure it?": the summary gives the goal
    but not the steps (under-answers).

## Optional: showing "Not found"

To show that the app doesn't invent answers, ask **"How do you put out a lithium battery fire on
Mars?"** The reports don't cover it, so the summary says "Not found" (checked with the real Gemini
on Day 16). It isn't a button, because a button suggests a question the app can answer. It needs
`GEMINI_API_KEY`; without one the app quotes the passages instead.

## Re-checking before the demo

The tests use a stand-in search model, so they check the file (5 questions, real chunks, evidence
in each chunk) but not the ranking. To check the ranking with the real model:

```bash
uv run --locked python scripts/day19_check_demo_questions.py
```

It searches each question with no filter and prints where the expected chunk ranks. Every line
should say `rank 1`.
