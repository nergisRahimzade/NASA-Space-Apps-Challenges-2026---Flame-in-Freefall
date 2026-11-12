# Retrieval checkpoint (FIF-D14-AI)

The sprint goal for today: relevant top results on **8 of 10** questions. This log re-runs the
tests, records the score, and records what was tried to reach 8. Script:
`scripts/day14_checkpoint.py` (it writes a draft to `artifacts/day14_checkpoint_draft.md`).
Chunks: the real 18 in `data/processed/chunks.jsonl` (150 words, overlap 30). Embedding model:
`all-MiniLM-L6-v2`. Run on CPU (Windows). The run is repeatable.

## Score

| | Score | Fails |
|---|---|---|
| **The app today**, experiment picked or read from the question | **7 / 10** | Q6, Q9, Q10 |
| The app today, "All experiments" (default, nothing read from the question) | 4 / 10 | Q2, Q4, Q5, Q6, Q9, Q10 |
| **Keywords + best sentence** (measured in memory, not in the app yet) | **8 / 10** | Q9, Q10 |

**The app doesn't reach the goal yet: 7 of 10.** One ranking change reaches 8 of 10 in the
measurement. It also scores 10 of 10 on 10 new held-out questions, where today's search scores 8.
It isn't wired into `search()` yet, because that changes what `score` means, which BE owns (see
"What it would take" below).

**Q9 and Q10 can't pass with any search change.** The reports don't answer them, and they score as
high as real answers (below). So 8 of 10 is the most search can reach on this set.

- `pytest` re-run: all tests pass. `ruff` is clean.
- Pass/fail rule: `judge()` from Day 13 (`retrieval_eval.py`, explained in `tests/retest.md`).
  It's strict: a question that names an experiment fails if another experiment's passage comes
  back with the answer.

## New today

- **`experiment_in_question(query, experiments)`** in `retrieval.py` reads the experiment name out
  of a question ("FLEX-2" yes; "FLEX" inside "FLEX-2" no; two experiments named gives `None`).
  With it, a question typed without touching the dropdown scores 7 of 10, the same as with the
  experiment picked. It isn't called by `search()` or the app yet. BE or FE can wire it in (one
  line, see `ai_notes.md` §6).
- **10 held-out questions** (`HELD_OUT` in `retrieval_eval.py`). The ranking changes below were
  chosen by looking at the 10 questions, so a change that only fits those would show up on new
  ones. They're worded differently from the reports, with evidence phrases copied word for word.
  4 name an experiment. A test checks that every answer is in the chunks.

## Ranking changes tried

All in memory, so the app and `artifacts/index/` weren't touched. Same chunks, experiment filter on
when the question names one, top 5, results under 0.30 left out.

| Change | 10 questions | Fails | Held out (new) | Fails |
|---|---|---|---|---|
| Chunk (today's search) | 7 / 10 | Q6, Q9, Q10 | 8 / 10 | H4, H7 |
| Best sentence | 7 / 10 | Q3, Q9, Q10 | 8 / 10 | H7, H9 |
| Keywords + chunk | 7 / 10 | Q6, Q9, Q10 | 8 / 10 | H4, H7 |
| Report title + chunk | 7 / 10 | Q6, Q9, Q10 | 8 / 10 | H4, H7 |
| Experiment name + chunk | 7 / 10 | Q6, Q9, Q10 | 9 / 10 | H7 |
| **Keywords + best sentence** | **8 / 10** | **Q9, Q10** | **10 / 10** | **-** |

- **Best sentence:** a chunk scores as high as its best-matching sentence, instead of one vector
  for the whole chunk.
- **Keywords:** BM25, which ranks chunks by shared rare words (like "cool flames"). It's fused with
  the other ranking by adding `1 / (60 + rank)` from each (reciprocal rank fusion).
- **Title / experiment name + chunk:** that text is embedded together with the chunk.

**Where the first relevant passage ranks** (rank / chunks searched):

| Change | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 |
|---|---|---|---|---|---|---|---|---|
| Chunk (today) | 1/18 | 1/7 | 2/18 | 2/7 | 1/7 | **17/18** | 2/4 | 1/18 |
| Best sentence | 1/18 | 1/7 | **6/18** | 1/7 | 1/7 | 1/18 | 1/4 | 1/18 |
| Keywords + chunk | 1/18 | 1/7 | 1/18 | 2/7 | 2/7 | 9/18 | 2/4 | 1/18 |
| Keywords + best sentence | 1/18 | 1/7 | 1/18 | 2/7 | 2/7 | **1/18** | 2/4 | 1/18 |

## What the results show

- **Q6 was a scoring problem, not a missing answer.** Its answer is one sentence ("determine how
  rapidly a large scale fire grows in low-gravity") in a chunk that's mostly hardware detail. As a
  whole chunk it scores 0.297 and ranks 17th. That sentence alone scores 0.600 and ranks 1st. This
  confirms the Day 9 guess that the hardware detail dilutes the match.
- **Best sentence alone trades Q6 for Q3.** Q3 needs the rare term "cool flames". A likely cause,
  untested: short sentences elsewhere match "flame" better than the long one that mentions cool
  flames. Keywords fix Q3 (rank 2 → 1) but can't lift Q6 past
  9th. Together, each one covers the other's miss.
- **The held-out questions agree.** Today's search misses H4 and H7. H4 ("Which settings did
  FLEX-2 change on purpose?"): its answer chunk scores 0.236 as a whole, so the cutoff removes it,
  but its best sentence scores 0.471. H7 ("Which vehicle carried the fire experiment…"): the Cygnus
  chunk isn't in today's top 6, and the combined ranking puts it 4th. The combination misses none.
- **Not everything gets better.** Q4 and Q7 stay 2nd, and Q5 drops from 1st to 2nd. Each still has
  its answer in the top 5, behind a weaker passage from the right experiment.
- **This is still a small test:** 20 questions, 18 chunks, 3 short reports. The combination was
  chosen after seeing the 10 questions, and only the held-out 10 test it fairly.

## Q9 and Q10, and the cutoff

| | Q9 top | Q10 top | Lowest answer score needed |
|---|---|---|---|
| Chunk (today) | 0.478 | 0.411 | 0.395 (Q4) |
| Keywords + best sentence | 0.538 | 0.434 | 0.424 (Q3); 0.435 (H7) on the held-out set |

"Lowest answer score needed" is the lowest score of the best answer passage any answerable
question returns. A cutoff above it would make that question fail.

No cutoff separates Q9 and Q10 from real answers under either scoring, as on Days 9, 11 and 13.
Their last guard is `summarize()`'s `not_found`, still untested on the real Gemini.

**Best-sentence scores run higher, so the 0.30 cutoff needs retuning if it's adopted.** The
off-topic "How much thrust does a rocket engine produce?" scores 0.2755 as a chunk but **0.3004**
as a sentence, just over 0.30. The other 5 off-topic questions stay at 0.24 or below. With
keywords + best sentence, both question sets keep their full score at every cutoff from 0.30 to
0.42 (the lowest answer is 0.424), so there's room to raise it (0.35, for example). Untested on BE's off-topic questions, which
aren't in the repo.

## What it would take to put keywords + best sentence in the app

Not done today. It touches BE's files and the contract:

1. **Sentence vectors in the index.** 120 sentences for 18 chunks (about 7 times more), built by
   `uv run python -m flame_in_freefall.ingest` (there's no Makefile). Today `store.py` and
   `ingest.py` (BE) save one vector per chunk.
2. **Ranking in `find_passages`** (AI): BM25 over the chunks plus fusion with the sentence ranking.
   The code is in `scripts/day14_checkpoint.py` (`best_sentence`, `bm25`, `fuse`).
3. **`score` changes meaning** from chunk cosine to best-sentence cosine. That needs a contract
   note and a new `MIN_SCORE` (BE).
4. **Re-run** `scripts/day13_retest.py` and this script to check that nothing moved.

## Decisions the team needs

- **Adopt keywords + best sentence?** It's the only change that reaches 8 of 10, and it holds on
  the held-out questions. It needs the BE work above.
- **Do Q9 and Q10 count toward the 8?** Search can't pass them, so with them in, 8 of 10 means
  every answerable question has to pass.
- **Wire `experiment_in_question` into the app?** It makes the default "All experiments" run score
  like a picked experiment (4 → 7 of 10).
