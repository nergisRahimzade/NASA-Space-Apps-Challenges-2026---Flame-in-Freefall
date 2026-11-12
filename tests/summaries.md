# Summary test: 22 questions, every claim checked (FIF-D16-AI)

Do the summaries match their sources? This log runs the real `search()` and `summarize()` on
22 questions with the real Gemini and judges every takeaway against the passage it cites.
Script: `scripts/day16_test_summaries.py` (it writes a draft and Gemini's exact replies to
`artifacts/day16_*`).

- **Run:** 2026-11-12, prompt `summary_v2.txt` (the app's prompt), model
  **`gemini-flash-lite-latest`**. The default `gemini-flash-latest` was overloaded again: a probe
  call ended in `504 DEADLINE_EXCEEDED` after 28.7 s, as on 2026-11-10 and 2026-11-11.
- **Questions:** the 10 from Day 9 (Q1–Q10; Q9 and Q10 aren't answered by the reports), the 10 held
  out on Day 14 (H1–H10) and 2 new BASS-II ones (B1–B2, `SUMMARY_EXTRA` in `retrieval_eval.py`).
- **Two runs:** "picked" asks every question with the experiment picked when it names one (as on
  Days 13 and 15). "default" asks the 10 that name an experiment again with nothing picked (the
  app's default), so passages from other experiments come along. That's the test for prompt rule 3:
  never give one experiment's numbers as another's.
- **Judged by Claude Code** (each takeaway read against the full text of the passage it cites).
  No teammate has reviewed these verdicts yet.

## Result

**Summaries match their sources.** 39 takeaways from 30 Gemini answers:

| Verdict | Takeaways |
|---|---|
| Supported | **38** (2 of them under-answer, 1 is weak; see below) |
| Wording slip | **1** (Q8: a hypothesis written as a statement) |
| Not supported (invented, or a wrong number or experiment) | **0** |

- **"Not found" is right every time:** Q6, Q9, Q10 and H7 say "not found", and none of their
  passages holds the answer. No question that had its answer in the passages said "not found".
- **No wrong-experiment numbers, even when they were offered.** In the default run, Q4's *top*
  passage was FLEX's (0.5–1.5 atm, the mix-up from Day 9), and the summary still gave only
  FLEX-2's 0.5–3.0 atm and 0.1–0.4 mole fraction.
- **No fallbacks:** all 30 calls got a Gemini answer (one 503 was retried by the client and then
  answered). H4 found no passage above the 0.30 cutoff in either run, so no summary was asked for
  (a search issue, known from Day 14).
- **Speed and size** (for FIF-D17-BE's cost log): median 1.3 s per summary (max 11.4 s), about
  1,600 input and 80 output tokens per call (max about 1,900 and 270).

| | Picked | Default |
|---|---|---|
| Gemini answers | 21 (+1 no match) | 9 (+1 no match) |
| Takeaways | 27 | 12 |
| Cite a passage holding the answer | 27 of 27 | 12 of 12 |
| "Not found" | 4 (Q6, Q9, Q10, H7), all correct | 0 |
| `claim_check` flags | 0 | 0 |

## Every takeaway

"Passage words" is the text that settles the verdict, quoted from the cited chunk.

### Picked run

| # | Chunk | Verdict | Passage words / note |
|---|---|---|---|
| Q1 | `flex-p1-c0` | supported | "aims to … measure the effectiveness of various gaseous fire suppressants such as CO2, He, and SF6". **"aims to" is kept**: the Day 15 slip ("measures") didn't come back. |
| Q2 | `flex-p1-c1` | supported, **under-answers** | "to determine the Limiting Oxygen Index (LOI) as a function of ambient pressure". The question also asks *how* FLEX measured it, and the same passage lists the procedure (steps 1–6), which isn't given. |
| Q3 | `flex-p1-c6` | supported, weak | "the study of ''cool flames'' and low-temperature combustion processes … can inform the design of advanced combustion engines". The reports never define a cool flame, and the summary doesn't invent a definition. |
| Q4 | `flex2-p1-c1` | supported | "varied in pressure between 0.5 atm to 3.0 atm" |
| Q4 | `flex2-p1-c1` | supported | "O2 concentration between 0.1 to 0.4 mole fraction with the diluent gas making up the balance" |
| Q5 | `flex2-p1-c3` | supported | "3. Deploy the droplet(s) carefully controlling the droplet diameter." |
| Q5 | `flex2-p1-c1` | supported | "dispensing of a predetermined amount of fuel (based on the target droplet size) onto the support fiber for those tests in which the droplet is not freely deployed" |
| Q5 | `flex2-p1-c2` | supported | "the dispensing needles were retracted and a dwell period of at least 10 seconds was allowed" |
| Q5 | `flex2-p1-c2` | supported | "initiating power to the ignitor for a selectable amount of time ranging from 1 second to 5 seconds" |
| Q6 | – | not found, **correct** | The answer ("how rapidly a large scale fire grows", `saffire2-p1-c0`) wasn't among its 5 passages. |
| Q7 | `saffire2-p1-c1` | supported | "an air flow velocity of either 20 or 30 cm/s, the flow being either concurrent or opposed" |
| Q8 | `saffire2-p1-c2` | **wording slip** | Writes the Saffire-II *hypothesis* as a fact "as stated in the Saffire-II experiment description". The words "This investigation hypothesizes" are at the end of `saffire2-p1-c1`, which wasn't sent; `c2` starts mid-sentence at "that due to large differences…". See "Why the slips happen". |
| Q9 | – | not found, **correct** | The reports don't cover it. |
| Q10 | – | not found, **correct** | The reports don't cover it. |
| H1 | `saffire2-p1-c0` | supported | "added more samples including SIBAL, silicone, structure PMMA, flat PMMA, and PMMA with Nomex" |
| H2 | `saffire2-p1-c0` | supported | "a sample card that contains 9 samples, each 5 cm x 29 cm" |
| H3 | `flex2-p1-c1` | supported | "A settling time of approximately 2 minutes elapsed prior to initiating the test" |
| H4 | – | no match | Search returned nothing above the 0.30 cutoff, so no summary (Day 14: its answer chunk scores 0.236). |
| H5 | `flex-p1-c1` | supported | "2. Select a smaller droplet size (≈ 3 mm)" in the procedure "for the LOI tests" |
| H6 | `saffire2-p1-c1` | supported (×5) | Cameras, thermocouples, radiometers, solid state sensors and anemometers, each as listed in the passage (one keeps the report's typo "mole faction"). |
| H7 | – | not found, **correct** | The answer ("Cygnus resupply vehicle", `saffire2-p1-c0`) wasn't among its 5 passages. |
| H8 | `flex-p1-c6` | supported | The same "cool flames … advanced combustion engines" sentence as Q3. |
| H8 | `flex2-p1-c5` | supported | "Insights gained from these studies can lead to more efficient and cleaner combustion technologies"; "these studies" are FLEX-2's droplet combustion studies, which the takeaway names. |
| H9 | `flex-p1-c4` | supported, **hypothesis kept** | "The primary hypothesis of the FLEX mission is that microgravity conditions fundamentally alter…" |
| H9 | `flex-p1-c4` | supported, **hypothesis kept** | "the hypothesis posits that the lack of buoyant convection in microgravity will lead to significant differences…" |
| H10 | `saffire2-p1-c2` | supported, **"proposed" kept** | "this investigation proposed to conduct large-scale fire safety experiments in an expendable spacecraft without risk to a crew" |
| B1 | `bass2-p1-c1` | supported | "could impose airflow speeds up to 40 cm/s" |
| B2 | `bass2-p1-c1` | supported | "oxygen varied below 21% by adding nitrogen" |

### Default run (nothing picked)

| # | Experiments in the passages | Verdict | Note |
|---|---|---|---|
| Q2 | FLEX, Saffire-II | supported, **under-answers** | Same takeaway as the picked run; the Saffire-II passage wasn't used. |
| Q4 | BASS-II, FLEX, FLEX-2, Saffire-II | supported (×2) | FLEX-2's pressure and oxygen ranges from `flex2-p1-c1`. FLEX's 0.5–1.5 atm was the top passage and was left out. |
| Q5 | FLEX, FLEX-2 | supported (×3) | Deploy, "Allow the droplet to stabilize", "Ignite the droplet in a uniform and controlled fashion" (`flex2-p1-c3`); no FLEX steps. |
| Q7 | Saffire-II | supported | Same as the picked run. |
| H1 | BASS-II, Saffire-II | supported | Saffire-II's samples; the BASS-II passage wasn't used. |
| H2 | Saffire-II | supported | Same as the picked run. |
| H3 | FLEX, FLEX-2, Saffire-II | supported | FLEX-2's settling time, named as FLEX-2. |
| H4 | – | no match | As in the picked run. |
| B1 | BASS-II | supported | Same as the picked run. |
| B2 | BASS-II, FLEX | supported | BASS-II's nitrogen; the FLEX passage wasn't used. |

## The Day 15 slips, re-checked

| Day 15 slip | Today |
|---|---|
| Q1: "aims to measure" written as "measures" | **Fixed**: "aims to … measure" is kept. |
| Q8: "hypothesizes" written as "states" | **Still there**; a contributing factor is that the word isn't in the passage Gemini gets (below). |
| Q2: gives the LOI goal but not the procedure steps | **Still there** in both runs. |

## Why the slips happen

Chunk boundaries contribute to the slips (150 words, 30-word overlap, cut mid-sentence by design),
but this run doesn't isolate the prompt's effect from missing context:

- **Q8:** the sentence "This investigation hypothesizes that …" is split across two chunks.
  Search sends only the second half (`saffire2-p1-c2`), which reads like a plain statement. Where the
  word "hypothesis" is inside the passage (H9), the prompt keeps it every time.
- **Q2:** the procedure runs from `flex-p1-c1` into `flex-p1-c2` and `flex-p1-c3`, and the 0.30
  score cutoff drops `c2` and `c3` (Day 13), so only the first half of the procedure reaches
  Gemini. `c1` itself also ends mid-sentence: step 6 reads "until flame exists" there, but the full
  step is "until flame exists for only a short time after ignition". However, several earlier
  steps are available in `c1` and v2 omits them. v3 includes procedure steps in the default run
  on the same passages, so missing context alone doesn't explain the under-answering.

## Prompt v3: tried, not adopted

The plan allows a prompt v3 only for slips the run shows. v3 was v2 with two changes:

- **Rule 4, added:** a passage can start in the middle of a sentence, so "hypothesizes", "aims to" or
  "proposed" may be missing; a takeaway from that opening may be a hypothesis or a goal, so write it
  as something the report puts forward ("the report argues that …"), not as a finding.
- **Rule 7, changed:** if the question asks more than one thing, answer every part the passages
  cover, each in its own takeaway.

Same 32 searches, same passages (the first Q2 call met a 503 and was asked again):

| | v2 | v3 |
|---|---|---|
| Q2 (both parts?) | goal only, both runs | procedure added in the default run only; picked run still goal only |
| Q2 default, new problem | – | quotes step 6 as "until flame exists" (cut off by the chunk), which changes its meaning |
| Q8 (hypothesis) | "as stated in…" | "**states** that…": not fixed |
| Q5 (deployed and ignited) | 4 detailed steps (dispensing, needles, 10 s dwell, 1–5 s ignitor) | 2 vaguer takeaways, one reading "deployed by deploying the droplet" |
| H8 | 2 relevant takeaways | 1 |
| H10 | 1 | 2 (better) |
| "Not found" for Q6, Q9, Q10, H7 | correct | correct |
| Takeaways / `claim_check` flags | 39 / 0 | 36 / 0 |

**Decision: keep v2.** v3 fixed Q2 in one run of two, didn't fix Q8, made Q5 and H8 thinner, and
added a new slip. The "each in its own takeaway" wording seems to make Gemini squeeze a two-part
question into exactly one takeaway per part. A prompt can't restore missing source text, but it
can affect whether available steps are included and how uncertain claims are worded. The v3 file
isn't committed; its two rules are quoted here.

## `claim_check`: false alarms

`claim_check.check_claims` (new today) flags numbers and experiment names a takeaway doesn't get from
its passage. On the 39 real takeaways it raised **0 flags, so 0 false alarms** (and 0 on v3's 36).
There was also nothing of its kind to catch: no takeaway had a wrong number or experiment. Its unit
tests show what it catches. It stays a report tool for now; wiring it into the app is a separate
decision (`ai_notes.md` §6).

## Limits

- **One run per prompt, on the lite model.** Gemini's answers vary between runs (v2 and v3 differed
  on questions the rule change shouldn't touch), and the app's default model wasn't usable today.
- **22 questions on 4 short reports.** Every verdict above is one reader's.
- **The default run's Q5 and Q2** use different passages from the picked run, so their takeaways
  differ for that reason too.
