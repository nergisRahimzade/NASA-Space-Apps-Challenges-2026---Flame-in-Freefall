# Retrieval test log (FIF-D09-AI)

Tests real search on the 18 chunks from the 3 reports, using `find_passages` and
`scripts/day9_test_search.py`. Chunk settings: 150 words with 30 words of overlap.

**Judged by:** Claude Code, at NathanRivera1's request, reading each returned chunk in full.
No teammate has reviewed these judgments yet.

**Rule used:** a result is relevant if the passage itself helps answer the question. A passage
from the wrong experiment, or one that only shares topic words, is not relevant.

## Summary

| Measure | Result |
|---|---|
| Relevant **first** result, 8 answerable questions | **4 of 8** (Q1, Q2, Q5, Q8) |
| Relevant result in the **top 3**, 8 answerable questions | **6 of 8** (Q1, Q2, Q3, Q5, Q7, Q8) |
| Relevant results overall, 8 answerable questions | 9 of 24 |
| Questions with no relevant result | Q4 and Q6, plus uncovered Q9 and Q10 |
| Same top-3 measure across all 10 questions | 6 of 10 (the D14-AI checkpoint aims for 8 of 10) |

Two of those passes are weak: Q3's chunk mentions cool flames but doesn't define them, and Q5's
chunk only lists the steps. The detailed Q5 passages ranked 5th and 8th.

**Uncovered questions:** Q9 and Q10 aren't answered by the reports. Search still returned 3
passages for each, with top scores of 0.478 and 0.411, so it never reports "nothing found" itself.

## Failures and likely causes

These causes are hypotheses. They haven't been tested.

| Question | What went wrong | Where the best chunk ranked | Likely cause |
|---|---|---|---|
| Q4 | The top result is from FLEX, not FLEX-2, and its 0.5–1.5 atm range is for the wrong experiment | `flex2-p1-c1`: 4th of 18 (0.395) | That chunk never names FLEX-2, and the experiment name isn't embedded with it |
| Q6 | All 3 results are from FLEX | `saffire2-p1-c0`: 17th of 18 (0.297) | That chunk covers the objective and a lot of hardware detail, which may dilute its match |
| Q7 | The top result stops just before the airflow values | `saffire2-p1-c1`: 2nd of 18 (0.541) | The chunk boundary falls in the middle of the sentence |

**Scores can't separate good from bad results yet.** Q3's relevant chunk scored 0.427, while Q9's
irrelevant top result scored 0.478. A simple score cutoff would drop some good results and keep
some bad ones.

**The test set is small:** there are only 18 chunks from 3 short reports, and the reports don't
hold every answer. Q6 asks how fast fire grows, but the best passage only says that measuring this
is an objective.

## Results

| # | Question | Rank | Score | Chunk | Relevant? | Why |
|---|---|---|---|---|---|---|
| 1 | What gases were tested as fire suppressants in microgravity? | 1 | 0.746 | `flex-p1-c5` | yes | Names CO2, He and SF6 |
| 1 | | 2 | 0.738 | `flex-p1-c6` | yes | Names CO2, He and SF6 |
| 1 | | 3 | 0.696 | `flex-p1-c0` | yes | Names CO2, He and SF6 |
| 2 | What is the Limiting Oxygen Index and how did FLEX measure it? | 1 | 0.515 | `flex-p1-c1` | yes | Starts the LOI procedure |
| 2 | | 2 | 0.320 | `saffire2-p1-c0` | no | Flammability limits in a different experiment; no LOI |
| 2 | | 3 | 0.295 | `flex-p1-c2` | yes | Continues the LOI procedure |
| 3 | What is a cool flame? | 1 | 0.430 | `flex-p1-c0` | no | Doesn't mention cool flames |
| 3 | | 2 | 0.427 | `flex-p1-c6` | yes (weak) | Mentions cool flames with low-temperature combustion, but gives no definition |
| 3 | | 3 | 0.413 | `saffire2-p1-c3` | no | Doesn't mention cool flames |
| 4 | What oxygen levels and pressures were used in the FLEX-2 chamber? | 1 | 0.509 | `flex-p1-c1` | no | FLEX values, not FLEX-2 |
| 4 | | 2 | 0.453 | `flex2-p1-c3` | no | Says these were varied, but gives no values |
| 4 | | 3 | 0.400 | `saffire2-p1-c0` | no | Different experiment |
| 5 | How were fuel droplets deployed and ignited in FLEX-2? | 1 | 0.618 | `flex2-p1-c3` | yes (weak) | Lists deploy and ignite steps, with little detail |
| 5 | | 2 | 0.618 | `flex-p1-c1` | no | FLEX procedure, not FLEX-2 |
| 5 | | 3 | 0.617 | `flex2-p1-c0` | no | Objectives; stops as the approach begins |
| 6 | How fast does a large fire grow in low gravity? | 1 | 0.529 | `flex-p1-c0` | no | Droplet burning, not large fires |
| 6 | | 2 | 0.485 | `flex-p1-c5` | no | Suppressants and benefits |
| 6 | | 3 | 0.480 | `flex-p1-c4` | no | Droplet flow and hypothesis |
| 7 | What airflow speeds were used in Saffire-II? | 1 | 0.574 | `saffire2-p1-c0` | no | Stops at "conducted at an air", before the values |
| 7 | | 2 | 0.541 | `saffire2-p1-c1` | yes | Gives 20 or 30 cm/s |
| 7 | | 3 | 0.287 | `saffire2-p1-c3` | no | No airflow values |
| 8 | Why are normal-gravity fire tests risky for designing spacecraft safety systems? | 1 | 0.738 | `saffire2-p1-c2` | yes | States the risk and why |
| 8 | | 2 | 0.690 | `flex-p1-c5` | no | Doesn't address normal-gravity testing |
| 8 | | 3 | 0.640 | `saffire2-p1-c3` | no | Benefits of the experiment, not the risk |
| 9 | Which spacecraft materials are the most dangerous at 30 percent oxygen? | 1 | 0.478 | `saffire2-p1-c3` | no | Says limits are measured; no ranking |
| 9 | | 2 | 0.426 | `flex-p1-c5` | no | Suppressants and benefits |
| 9 | | 3 | 0.413 | `flex-p1-c6` | no | Suppressants and benefits |
| 10 | How do you put out a lithium battery fire on Mars? | 1 | 0.411 | `flex-p1-c5` | no | Not about batteries or Mars |
| 10 | | 2 | 0.409 | `flex-p1-c6` | no | Not about batteries or Mars |
| 10 | | 3 | 0.406 | `flex-p1-c0` | no | Not about batteries or Mars |

Q9 and Q10 are the 2 uncovered questions. They don't count toward the "answerable" results.
