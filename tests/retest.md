# Re-test log (FIF-D13-AI)

Runs the same 10 questions as Day 9 (`tests/retrieval.md`) again, this time through the real
`api.search()` that the app calls, and gives each one a pass or fail with a reason. Script:
`scripts/day13_retest.py`. Chunks: the real 18 in `data/processed/chunks.jsonl` (150 words,
overlap 30). Embedding model: `all-MiniLM-L6-v2` (unchanged). Run on CPU (Windows). The run is
repeatable.

**Result: 7 of 10 pass when the experiment is picked, 4 of 10 with the app's default "All
experiments".** The 7 match Day 12. The score cutoff added on D13-BE doesn't turn Q9 or Q10 into
"no match". It also drops two of Q2's answer passages.

## What changed since Day 12

Days 10–12 called `find_passages` directly. `search()` now adds three things on top, and this
re-test is the first one that includes them:

- **k = 5 by default** (contract v1.1, from D11-AI).
- **The experiment filter** (`search(query, experiment=...)`, contract v1.4, from D12-AI and
  D12-BE). The app's dropdown defaults to "All experiments", which means no filter.
- **New: a 0.30 score cutoff** (`api.MIN_SCORE`, contract v1.5, from D13-BE). Results scoring
  under 0.30 are left out, so an off-topic question should return `[]` ("no match").

## How pass/fail was decided

The rule is `judge()` in `src/flame_in_freefall/retrieval_eval.py`, tested in
`tests/test_retrieval_eval.py`.

- **Answerable question (Q1–Q8): PASS** if a returned passage contains the answer (the same
  evidence phrases as Days 10–12, which reproduce the Day 9 hand judgments). **Except:** if the
  question names an experiment (Q2, Q4, Q5, Q7) and a passage from *another* experiment comes
  back too, it **FAILS**. That passage's numbers could reach the summary, as FLEX's pressure range
  did for Q4 on Day 9. `summarize()` never sees the question, so it can't tell which numbers were
  asked for.
- **Uncovered question (Q9, Q10): PASS only if search returns nothing.** The reports don't answer
  them, so any passage sent on is unrelated text the summary might try to answer from.
- **Weak passes are marked.** Q3's passage mentions cool flames but never defines them, the same
  as on Day 9.
- **Two runs,** like the app: "All experiments" (no filter for any question), and "Experiment
  picked" (Q2, Q4, Q5 and Q7 filtered to the experiment they name, the rest unfiltered).
- Every returned passage, and every passage the cutoff removed, is listed in the draft the script
  writes to `artifacts/day13_retest_draft.md`. The ones mentioned below were read by hand.

## Pass/fail table

| # | Question | All experiments (default) | Experiment picked | Reason |
|---|---|---|---|---|
| 1 | What gases were tested as fire suppressants in microgravity? | **PASS** | **PASS** (no filter) | Answer at rank 1 (`flex-p1-c5`, names CO2, He and SF6). Ranks 2 and 3 say it too |
| 2 | What is the Limiting Oxygen Index and how did FLEX measure it? | FAIL | **PASS** (FLEX) | Answer at rank 1 (`flex-p1-c1`, LOI procedure steps 1–6). Unfiltered, Saffire-II's `saffire2-p1-c0` (0.320) comes too. Both runs lose the rest of the procedure to the cutoff (below) |
| 3 | What is a cool flame? | **PASS** (weak) | **PASS** (weak, no filter) | `flex-p1-c6` at rank 2 mentions cool flames but never defines them. The reports have no definition |
| 4 | What oxygen levels and pressures were used in the FLEX-2 chamber? | FAIL | **PASS** (FLEX-2) | FLEX-2's "0.5 atm to 3.0 atm" (`flex2-p1-c1`) ranks 4th unfiltered, behind FLEX's 0.5–1.5 atm at rank 1. Filtered it ranks 2nd and FLEX can't come back |
| 5 | How were fuel droplets deployed and ignited in FLEX-2? | FAIL | **PASS** (FLEX-2) | Answer at rank 1 (`flex2-p1-c3`, steps only). Filtered, both detailed passages also come back (ranks 3 and 5). Unfiltered, 2 FLEX chunks come instead |
| 6 | How fast does a large fire grow in low gravity? | FAIL | FAIL (no filter) | None of the 5 contains the answer: 4 are FLEX chunks and 1 is FLEX-2. `saffire2-p1-c0` still ranks 17th of 18, as on Days 9–12 |
| 7 | What airflow speeds were used in Saffire-II? | **PASS** | **PASS** (Saffire-II) | "20 or 30 cm/s" at rank 2 (`saffire2-p1-c1`). Rank 1 still stops just before the values. The cutoff leaves only these 2 |
| 8 | Why are normal-gravity fire tests risky for designing spacecraft safety systems? | **PASS** | **PASS** (no filter) | Answer at rank 1 (`saffire2-p1-c2`) |
| 9 | Which spacecraft materials are the most dangerous at 30 percent oxygen? | FAIL | FAIL (no filter) | 5 unrelated passages returned, top score 0.478. The cutoff removed none |
| 10 | How do you put out a lithium battery fire on Mars? | FAIL | FAIL (no filter) | 5 unrelated passages returned, top score 0.411. The cutoff removed none |
| | **Total** | **4 of 10** | **7 of 10** | |

**How this compares:** Day 9 got 6 of 10 (top 3, no filter, no cutoff). Day 12 got 7 of 10 with the
filter. Days 9–12 counted a question as found even when wrong-experiment passages came with the
answer. Counted that way, "All experiments" would also be 7 of 10 (Q2, Q4 and Q5 have the answer).
The stricter rule is new today, and it's why the default run drops to 4.

## What the results show

**1. The cutoff doesn't catch the uncovered questions.** Q9's 5 results score 0.402–0.478 and
Q10's score 0.387–0.411, all well above 0.30. The D13-BE comment says clearly off-topic questions
scored −0.01 to 0.26. Q9 and Q10 are different: they're *about* fire and spacecraft, so they
share a lot of words with the reports, but the reports don't answer them. A higher cutoff can't
fix this. The lowest-scoring answer passage that a question depends on is Q4's `flex2-p1-c1` at
0.395 (filtered), which is below Q10's top score of 0.411. Any cutoff that drops Q10 also drops
Q4's answer. Days 9 and 11 found the same overlap.

**2. The cutoff drops two of Q2's answer passages.** `flex-p1-c2` (0.295) holds steps 7–8 of the
LOI procedure: lower the oxygen and repeat until the droplet won't ignite. That's the step that
actually finds the LOI. It also gives the variant used when extinction is too small to see.
`flex-p1-c3` (0.281) repeats the end of that variant and adds the slow-flow tests. Q2 still passes on rank 1, but the summary now sees only steps 1–6 and could describe the
method without its key step. In the unfiltered run, the cutoff keeps Saffire-II's
`saffire2-p1-c0` (0.320, wrong experiment) and drops FLEX's own `flex-p1-c2` (0.295).

**3. Fewer passages come back.** Filtered, Q2 returns 1 passage, Q7 returns 2 and Q4 returns 4.
For Q7 and Q4 nothing useful was lost (read by hand: Q7's removed chunks have no airflow values,
and Q4's `flex2-p1-c5` is about bi-component fuels and Earth benefits, with no oxygen or pressure
values). For Q2 something was (point 2).

**4. The filter matters more than any other setting.** Picking the experiment turns 3 fails
(Q2, Q4, Q5) into passes. But the app defaults to "All experiments", so someone who types Q4
without touching the dropdown gets FLEX's 0.5–1.5 atm as the top result. The D12 log recommended
that default, because a wrong pick hides the answer completely.

## Failures and likely causes

These causes are hypotheses unless the row says otherwise.

| Question | Run | What goes wrong | Likely cause |
|---|---|---|---|
| Q2, Q4, Q5 | All experiments | Answer found, but another experiment's chunks come too. For Q4, FLEX's wrong range ranks 1st | Checked on Day 12: filtering removes them all. With no filter picked, nothing reads the experiment name in the question |
| Q6 | Both | Answer chunk ranks 17th of 18. The top 5 are 4 FLEX chunks and 1 FLEX-2 chunk | Unchanged since Day 9. Maybe "large fire" matches FLEX's "relatively large droplets". Untested |
| Q9, Q10 | Both | 5 unrelated passages instead of "no match" | Checked: they score 0.39–0.48, above the 0.30 cutoff and above Q4's answer (0.395). No score cutoff separates them |
| Q2 (passes) | Both | Cutoff drops procedure steps 7–8 (0.295) and 0.281 | Checked: the scores are under 0.30. The cutoff was set from off-topic questions only |

## What's left for the D14-AI checkpoint (8 of 10)

Still 7 of 10, and only with the experiment picked. Three changes could move it. None are built:

- **Read the experiment name from the question** when the dropdown says "All experiments". All 4
  named questions spell it out. That would make the default run match the picked run (7 of 10).
- **Q6 needs a different kind of match,** such as keyword search (BM25) next to the embeddings, or
  embedding each chunk with its experiment name and title.
- **Q9 and Q10 can't be fixed by search.** The last guard is `summarize()`'s `not_found` (prompt
  v1 rule), which is still untested on the real Gemini. D14-AI also has to decide whether these
  two questions count toward the 8.

**For BE (contract v1.5):** the 0.30 cutoff costs Q2 two answer passages and doesn't catch Q9 or
Q10. One option to discuss is 0.27. That would keep Q2's 0.295 and 0.281 passages and still be
above the 0.26 that BE measured for off-topic questions. It's untested, and BE's questions aren't
in the repo. Another option is to leave it at 0.30 and accept the loss.
