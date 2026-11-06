# Experiment filter test log (FIF-D12-AI)

Day 11 checked on paper what filtering by experiment would do (`tests/top_k.md`). Day 12 builds
the filter and measures it on the same 10 questions with `scripts/day12_filter_by_experiment.py`.
Chunks: the real 18 in `data/processed/chunks.jsonl` (150 words, overlap 30), tagged by DAT on
Day 12: 7 FLEX, 7 FLEX-2, 4 Saffire-II. Embedding model: `all-MiniLM-L6-v2` (unchanged). Run on
CPU (Windows). The run is repeatable.

**Result: the filter works and does what Day 11 predicted.** With it, k = 3 finds 7 of 8
answerable questions (up from 6) and returns no wrong-experiment chunks (down from 4 of 12). That
matches k = 5 without the filter, for about 280 fewer words per question.

## What was built

- `find_passages(query, k=5, folder=..., experiment=None)` (default k is 5 since D11; this log passes k explicitly) in `src/flame_in_freefall/retrieval.py`.
  With an experiment (`"FLEX-2"`, `"Saffire-II"` or `"FLEX"`), it keeps only that experiment's
  chunks **before** ranking, so all k results come from it. `None` searches everything, as before.
- `rows_for_experiment(chunks, experiment)` does the filtering. It fails loudly (`ValueError`) on an
  experiment no chunk has, such as a typo, `"flex-2"` or the old `"BASS"`, and on chunks with no tag
  (an index built before Day 12), instead of quietly returning nothing.
- Scores don't change: a kept chunk gets the same cosine score as without the filter. Only the
  competition is removed.
- If an experiment has fewer than k chunks, fewer results come back (Saffire-II has 4).
- Tests: 6 new cases in `tests/test_retrieval.py` (filter order, results only from that
  experiment, fewer than k, unknown experiment, untagged index, no filter unchanged).

## How it was scored

- Same answer key and scoring as Days 10–11 (`EVIDENCE` and `score_results` in
  `retrieval_eval.py`). Without the filter the numbers match `tests/top_k.md` exactly.
- **Filter when named:** Q2, Q4, Q5 and Q7 name an experiment (`NAMED_EXPERIMENT`), so they run
  as if the user had picked it in the app. The other questions run unfiltered, as with no pick.
- Only the 8 answerable questions are scored. Q9 and Q10 aren't answered by the reports.

## Results

| Search | k | First relevant | Relevant in top k | Relevant / returned | Wrong experiment / returned (Q2, Q4, Q5, Q7) | Words to summarize, per question |
|---|---|---|---|---|---|---|
| No filter | 3 | 4/8 | 6/8 | 9/24 (38%) | 4/12 (33%) | 423 |
| No filter | 5 | 4/8 | 7/8 | 13/40 (33%) | 8/20 (40%) | 705 |
| **Filter when named** | **3** | **4/8** | **7/8** | **12/24 (50%)** | **0/12** | **423** |
| Filter when named | 5 | 4/8 | 7/8 | 14/39 (36%) | 0/19 | 686 |

At k = 5, Q7 gets only 4 chunks back, because Saffire-II has only 4, hence 39 returned instead of 40.

**The four named questions** (relevant returned / wrong-experiment returned):

| # | Question | Filter | First relevant rank: no filter → filter | k = 3: no filter → filter | k = 5: no filter → filter |
|---|---|---|---|---|---|
| 2 | LOI and how FLEX measured it | FLEX | 1/18 → 1/7 | 2 / 1 → 3 / 0 | 3 / 2 → 3 / 0 |
| 4 | FLEX-2 oxygen levels and pressures | FLEX-2 | 4/18 → **2/7** | **0** / 2 → **1** / 0 | 1 / 3 → 1 / 0 |
| 5 | How FLEX-2 droplets were deployed and ignited | FLEX-2 | 1/18 → 1/7 | 1 / 1 → 2 / 0 | 2 / 2 → 3 / 0 |
| 7 | Saffire-II airflow speeds | Saffire-II | 2/18 → 2/4 | 1 / 0 → 1 / 0 | 1 / 1 → 1 / 0 |

The filtered top 5 with scores is in the draft the script writes to `artifacts/experiment_filter_draft.md`.

## What the results show (read by hand)

- **Q4 is fixed at k = 3.** FLEX-2's values (`flex2-p1-c1`, "0.5 atm to 3.0 atm", "0.1 to 0.4
  mole fraction") move from 4th to 2nd. FLEX's 0.5–1.5 atm, which ranked 1st on Days 9 and 11, can
  no longer reach the summary. The new 1st, `flex2-p1-c3`, lists pressure as a test parameter
  but gives no values. It's weak, not wrong.
- **Q5 gets both detailed passages at k = 5.** `flex2-p1-c1` (dispensing needles retracted) and
  `flex2-p1-c2` (ignitor timing) rank 3rd and 5th. Without the filter, k = 8 was needed for the
  second one.
- **Q2's extra hit is mostly a repeat.** `flex-p1-c3` gets in on the 30-word overlap with
  `flex-p1-c2` ("...to determine the LOI"). It adds a little, the slow-flow tests, but
  "Relevant / returned" overstates the gain, as on Day 11.
- **Q7 doesn't change:** the top result still stops just before the airflow values. The 2nd result
  has them.
- **First relevant stays at 4/8.** The filter removes the wrong experiment's chunks but doesn't
  reorder the right experiment's chunks, so the chunk boundary problems stay.

## What the filter can't do

- **It only helps when the experiment is known.** 4 of the 10 questions name one. Q3, Q6 and
  the uncovered Q9 and Q10 are unchanged. Q6's answer (`saffire2-p1-c0`) still ranks 17th of 18
  without a filter. With Saffire-II picked by hand it would be among only 4 chunks. Not measured,
  because Q6 doesn't name an experiment.
- **Something has to supply the experiment.** The plan has the user pick it from a dropdown
  (FIF-D12-FE) and BE pass it through `search(query, experiment=...)` (FIF-D12-BE, contract v1.2).
  Reading the name out of the question is not built.
- **A wrong pick hides the answer.** If the user picks FLEX for a FLEX-2 question, none of the
  FLEX-2 chunks can come back. The app should make "All experiments" (no filter) the default.

## Where this leaves the D14-AI goal (8 of 10)

Still 7 of 10. The filter gets there at k = 3 instead of 5, and with no wrong-experiment
numbers. The remaining answerable miss is Q6, as on Day 11.
