# Chunk size test log (FIF-D10-AI)

Compares chunk sizes and overlaps on the same 10 questions as Day 9 (`tests/retrieval.md`), using
`scripts/day10_compare_chunk_sizes.py`. Embedding model: `all-MiniLM-L6-v2` (unchanged).

**Decision: keep 150 words with 30 words of overlap.** No setting clearly beats it, and every
larger size either cuts off text the model can't read or barely beats picking at random.

## How it was scored

Day 9 judged results by hand, but chunk ids change with the settings, so those judgments can't be
reused. Instead, each answerable question has a few **evidence phrases** copied from the reports
(`EVIDENCE` in `src/flame_in_freefall/retrieval_eval.py`). A returned chunk counts as relevant
if it contains one of them.

- **Checked against Day 9:** at 150/30 the phrases give the same answer as all 30 hand judgments
  in `tests/retrieval.md`. `tests/test_retrieval_eval.py` fails if that ever stops being true.
- **Same rule as Day 9:** a chunk from the wrong experiment, or one that only shares topic words,
  doesn't count. Q3 (cool flames) and Q5 (droplet steps) are still weak matches, as on Day 9.
- **Only the 8 answerable questions are scored.** Q9 and Q10 aren't answered by the reports.
- **The run is repeatable:** same chunks, same model, same scores. Run on CPU (Windows).

## Why sizes over 200 words can't work with this model

MiniLM reads at most 256 tokens and silently drops the rest. The ticket's 400 and 600 were still
tested so the effect is measured, not assumed:

- **At 400 and 600 words, 43–56% of the text is never seen by search.** Search ranks a chunk on its
  first ~200 words only. The rest is still passed to the summary, but it can't help the chunk rank.
- **At 200 words, 7–10 chunks are cut off**, losing 2–3% of the text.
- **Big chunks make the index tiny**, so a "hit" means less. With 5 chunks (600 words), picking 3 at
  random would already find a relevant one for 5.1 of 8 questions on average; search got 5–6. At
  150/30, random picking would get 2.3 and search gets 6. The "Random top 3" column shows this.
- **Big chunks also send 2–3× more text to the summary** (900–1,300 words vs about 420).

## Results

"Text never seen" is the share of the corpus's tokens that fall past the model's 254-token limit.
"Random top 3" is how many of the 8 questions 3 random chunks would answer, on average.

| Size | Overlap | Chunks | Max tokens | Chunks cut off | Text never seen | First relevant | Relevant in top 3 | Random top 3 | Relevant / returned | Words in top 3 |
|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 0 | 23 | 157 | 0 | 0% | 4/8 | 6/8 | 1.4 | 8/24 | 286 |
| 100 | 30 | 31 | 157 | 0 | 0% | 4/8 | 6/8 | 1.4 | 8/24 | 294 |
| 100 | 60 | 49 | 157 | 0 | 0% | 4/8 | 5/8 | 1.5 | 10/24 | 296 |
| 150 | 0 | 16 | 220 | 0 | 0% | 2/8 | 6/8 | 2.0 | 8/24 | 428 |
| **150** | **30** | **18** | **220** | **0** | **0%** | **4/8** | **6/8** | **2.3** | **9/24** | **423** |
| 150 | 60 | 23 | 220 | 0 | 0% | 5/8 | 6/8 | 1.9 | 8/24 | 435 |
| 200 | 0 | 13 | 288 | 8 | 3% | 4/8 | 5/8 | 2.4 | 7/24 | 530 |
| 200 | 30 | 13 | 288 | 7 | 2% | 4/8 | 6/8 | 2.6 | 9/24 | 558 |
| 200 | 60 | 15 | 288 | 10 | 2% | 3/8 | 7/8 | 2.7 | 12/24 | 567 |
| 400 | 0 | 8 | 526 | 5 | 49% | 4/8 | 5/8 | 3.5 | 6/24 | 990 |
| 400 | 30 | 8 | 526 | 5 | 46% | 4/8 | 5/8 | 4.1 | 7/24 | 931 |
| 400 | 60 | 8 | 526 | 5 | 43% | 4/8 | 5/8 | 4.0 | 7/24 | 899 |
| 600 | 0 | 5 | 778 | 5 | 53% | 4/8 | 6/8 | 5.1 | 7/24 | 1335 |
| 600 | 30 | 5 | 778 | 5 | 55% | 4/8 | 5/8 | 5.1 | 6/24 | 1286 |
| 600 | 60 | 5 | 778 | 5 | 56% | 4/8 | 5/8 | 5.1 | 6/24 | 1324 |

The bold row is the current setting. It reproduces the Day 9 hand-judged numbers exactly
(4/8 first, 6/8 top 3, 9/24 relevant).

**Where the first relevant chunk ranked** (rank / chunks in the index):

| Size | Overlap | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 0 | 1/23 | 1/23 | 2/23 | 18/23 | 2/23 | 12/23 | 1/23 | 1/23 |
| 100 | 30 | 1/31 | 1/31 | 2/31 | 2/31 | 4/31 | 18/31 | 1/31 | 1/31 |
| 100 | 60 | 1/49 | 1/49 | 5/49 | 7/49 | 2/49 | 27/49 | 1/49 | 1/49 |
| 150 | 0 | 1/16 | 1/16 | 3/16 | 2/16 | 5/16 | 13/16 | 2/16 | 3/16 |
| **150** | **30** | **1/18** | **1/18** | **2/18** | **4/18** | **1/18** | **17/18** | **2/18** | **1/18** |
| 150 | 60 | 1/23 | 1/23 | 2/23 | 15/23 | 1/23 | 22/23 | 1/23 | 1/23 |
| 200 | 0 | 1/13 | 1/13 | 3/13 | 6/13 | 4/13 | 12/13 | 1/13 | 1/13 |
| 200 | 30 | 1/13 | 1/13 | 2/13 | 8/13 | 2/13 | 12/13 | 1/13 | 1/13 |
| 200 | 60 | 1/15 | 1/15 | 2/15 | 3/15 | 2/15 | 14/15 | 1/15 | 2/15 |
| 400 | 0 | 1/8 | 1/8 | 5/8 | 3/8 | 1/8 | 7/8 | 1/8 | 4/8 |
| 400 | 30 | 1/8 | 1/8 | 3/8 | 5/8 | 1/8 | 7/8 | 1/8 | 4/8 |
| 400 | 60 | 1/8 | 1/8 | 2/8 | 5/8 | 1/8 | 7/8 | 1/8 | 4/8 |
| 600 | 0 | 1/5 | 1/5 | 2/5 | 4/5 | 1/5 | 5/5 | 1/5 | 3/5 |
| 600 | 30 | 1/5 | 1/5 | 4/5 | 4/5 | 1/5 | 5/5 | 1/5 | 3/5 |
| 600 | 60 | 1/5 | 1/5 | 4/5 | 5/5 | 1/5 | 5/5 | 1/5 | 3/5 |

## What the results show

- **No setting is clearly better.** "Relevant in top 3" stays between 5 and 7 of 8 everywhere. With
  8 questions, a difference of one question is within what chunk boundaries alone can change.
- **Why not 200/60 (the only 7 of 8)?** Its first result is the worst of the small sizes (3/8),
  10 of its 15 chunks are cut off, and the extra hit is Q4, whose rank swings from 2nd to 18th
  depending on where boundaries fall. That looks like luck, not a better setting.
- **Why not 150/60 (5 of 8 first)?** Q4 drops from 4th to 15th, and the index grows by 5 chunks
  for one better first result.
- **No overlap hurts.** At 150 words, overlap 0 drops first results from 4/8 to 2/8: Q5 falls to
  5th and Q8 to 3rd. Why isn't tested.
- **Keeping 150/30 means nothing else changes:** `data/processed/chunks.jsonl`, the index, and the
  Day 9 hand judgments in `tests/retrieval.md` all stay valid.

## Failures chunk size doesn't fix

- **Q6 (how fast a large fire grows) is never found.** Its one relevant chunk ranks 12th or lower
  at every size up to 200, and last at 400 and 600. This is a different problem from chunk size.
- **Q4 (FLEX-2's oxygen and pressure) is unstable**, from 2nd to 18th. FLEX's own pressure range
  keeps outranking it. This fits the Day 9 guess that the experiment name isn't embedded with the
  chunk. That guess is still untested.
- **The D14-AI goal (8 of 10) isn't reachable by chunk size.** The best setting found is 7 of 8
  answerable, and Q9 and Q10 can't be answered at all. Other changes are needed (see `ai_notes.md`).
