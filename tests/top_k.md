# Top-k test log (FIF-D11-AI)

Compares returning the top **3, 5 and 8** chunks for the same 10 questions as Day 9
(`tests/retrieval.md`), using `scripts/day11_compare_k.py`. Chunks: the real 18 in
`data/processed/chunks.jsonl` (150 words, overlap 30, kept on Day 10). Embedding model:
`all-MiniLM-L6-v2` (unchanged). Run on CPU (Windows). The run is repeatable.

**Recommendation: k = 5.** It finds one more question than k = 3 (Q4), for about 280 more words
per question. k = 8 finds no more questions than 5. It adds 440 more words, and nearly half of
what it returns comes from the wrong experiment.

**Not changed in code yet:** `search(query, k=3)` in `docs/contract.md` and `api.search` both
default to 3. Changing the default is a contract change, so it needs the BE owner's agreement
(see `ai_notes.md` §5).

## How it was scored

- **Same answer key as Day 10:** a chunk is relevant if it contains one of the evidence phrases in
  `EVIDENCE` (`src/flame_in_freefall/retrieval_eval.py`). At k = 3 it gives the Day 9 hand
  judgments exactly (4/8 first, 6/8 top 3, 9/24 relevant).
- **Every new chunk at ranks 4–8 was also read by hand**, since the phrases miss paraphrases.
  Only one disagreement was found (Q6, below).
- **New: wrong-experiment chunks.** Q2, Q4, Q5 and Q7 name one experiment. A returned chunk from
  another experiment can't answer them and may carry its numbers into the summary, which is what
  happened with Q4 on Day 9. The count uses the `experiment` tag on each chunk (Day 12 DAT).
- **Only the 8 answerable questions are scored.** Q9 and Q10 aren't answered by the reports.

## Results

| k | First relevant | Relevant in top k | Random top k | Relevant / returned | Wrong experiment / returned (Q2, Q4, Q5, Q7) | Words to summarize, per question |
|---|---|---|---|---|---|---|
| 3 | 4/8 | 6/8 | 2.3 | 9/24 (38%) | 4/12 (33%) | 423 |
| **5** | **4/8** | **7/8** | **3.5** | **13/40 (33%)** | **8/20 (40%)** | **705** |
| 8 | 4/8 | 7/8 | 5.0 | 14/64 (22%) | 14/32 (44%) | 1147 |

"Random top k" is how many of the 8 questions k random chunks would answer, on average. With 18
chunks, 8 random picks are almost half the index, so at k = 8 search beats random by only 2
questions (7 vs 5.0). At k = 3 and 5 the margin is about 3.5.

**Per question** (relevant chunks returned / wrong-experiment chunks returned; "-" means the
question names no experiment):

| # | Question | First relevant rank | k = 3 | k = 5 | k = 8 |
|---|---|---|---|---|---|
| 1 | Gases tested as fire suppressants | 1/18 | 3 / - | 3 / - | 3 / - |
| 2 | LOI and how FLEX measured it | 1/18 | 2 / 1 | 3 / 2 | 3 / 3 |
| 3 | What is a cool flame? | 2/18 | 1 / - | 1 / - | 1 / - |
| 4 | FLEX-2 oxygen levels and pressures | 4/18 | **0** / 2 | 1 / 3 | 1 / 4 |
| 5 | How FLEX-2 droplets were deployed and ignited | 1/18 | 1 / 1 | 2 / 2 | 3 / 3 |
| 6 | How fast a large fire grows | 17/18 | **0** / - | **0** / - | **0** / - |
| 7 | Saffire-II airflow speeds | 2/18 | 1 / 0 | 1 / 1 | 1 / 4 |
| 8 | Why normal-gravity fire tests are risky | 1/18 | 1 / - | 2 / - | 2 / - |
| 9 | Most dangerous materials at 30% oxygen (uncovered) | - | 0 | 0 | 0 |
| 10 | Lithium battery fire on Mars (uncovered) | - | 0 | 0 | 0 |

The full top-8 ranking with scores is in the draft the script writes to `artifacts/top_k_draft.md`.

## What the results show

- **k = 5 adds Q4, and that's the only new question.** FLEX-2's values (`flex2-p1-c1`,
  "0.5 atm to 3.0 atm") rank 4th. But FLEX's own pressure range still ranks 1st, so the summary
  gets both the right and the wrong numbers. Each takeaway would cite its real source, but
  `summarize()` never sees the question, so it can't tell that FLEX's range wasn't asked for.
- **k = 5 also adds Q5's detailed passage.** `flex2-p1-c1` (5th) starts the deploy-and-ignite
  steps. Day 9 noted that the detailed Q5 passages ranked 5th and 8th, and k = 8 picks up the
  other one (`flex2-p1-c2`, with needle retraction and ignitor timing).
- **k = 8 adds nothing else useful.** Apart from that one Q5 passage, the 3 extra chunks per
  question are off-topic or from the wrong experiment: Q7 goes from 0 wrong-experiment chunks to 4,
  all scoring 0.273 or below.
- **Some "relevant" chunks are repeats.** Q8's second hit at k = 5 (`saffire2-p1-c1`) is the same
  sentence as its first hit, copied by the 30-word overlap. Q1's 3 hits overlap the same way. So
  "Relevant / returned" overstates how much new information a bigger k brings.
- **First relevant stays at 4/8 at every k.** A bigger k can't fix the order. It only reaches further
  down the list.

## Failures

These causes are hypotheses unless the row says otherwise.

| Question | k = 3 | k = 5 | k = 8 | What goes wrong | Likely cause |
|---|---|---|---|---|---|
| Q4 | miss | hit (4th) | hit (4th) | FLEX's 0.5–1.5 atm ranks 1st at every k, so a wrong range always reaches the summary | `flex2-p1-c1` never names FLEX-2, and the experiment name isn't embedded with it |
| Q6 | miss | miss | miss (weak by hand) | 7 of the top 8 are FLEX or FLEX-2 droplet chunks. The key chunk `saffire2-p1-c0` ranks 17th of 18 | Maybe "large fire" matches FLEX's "relatively large droplets". Untested |
| Q6, by hand | | | rank 8 | `saffire2-p1-c3` says Saffire-II measures "flame growth" and how oxygen affects "flame size". No speed. The evidence phrase misses it | A paraphrase. It counts as weak at best, like Q3 |
| Q3 | weak | weak | weak | Only `flex-p1-c6` mentions cool flames, and it never defines them. Nothing else in the top 8 does | The reports don't define a cool flame. k can't fix this |
| Q7 | hit (2nd) | hit | hit | The top result stops just before the airflow values (as on Day 9). Bigger k only adds noise | Chunk boundary. Fixed by the 2nd result already |
| Q9, Q10 | 3 returned | 5 returned | 8 returned | Search never says "not found". It returns k chunks anyway, so a bigger k sends more unrelated text to the summary | No score cutoff works (below). Only `summarize()`'s `not_found` stops a made-up answer |

**A score cutoff still can't separate good from bad, at any k.** Q2's relevant chunk at rank 4
scores 0.281 and Q3's relevant chunk scores 0.427, while Q9's irrelevant top result scores 0.478 and
Q10's 8th result scores 0.337.

## Checked from the rankings above: filtering by experiment

This is a check on paper, not tested code. If search kept only chunks whose `experiment` tag
matches the experiment named in the question, the rankings above would give:

| Question | Filter | First relevant rank, unfiltered | First relevant rank, filtered |
|---|---|---|---|
| Q2 | FLEX | 1 | 1 |
| Q4 | FLEX-2 | 4 | **2** |
| Q5 | FLEX-2 | 1 | 1 (and the 2 detailed passages move to 3rd and 5th) |
| Q7 | Saffire-II | 2 | 2 |

So with a filter, **k = 3 would already find Q4 with no wrong-experiment chunks** (7/8 top 3,
0/12 wrong experiment). That would fix Q4 better than a bigger k does. It needs a way to know the
experiment: the user picks it in the app, or the code spots the name in the question. Only 4 of the
10 questions name one, so it doesn't help Q6, Q3 or the uncovered questions.

## Where this leaves the D14-AI goal (8 of 10)

The best result is 7 of 8 answerable, at k = 5 or 8. Across all 10 questions that's 7 of 10, since
Q9 and Q10 can't be answered. k alone doesn't reach 8 of 10. Q6 is the remaining answerable miss,
and neither chunk size (Day 10) nor k (Day 11) moves it.
