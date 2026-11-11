# Summary prompt v2 log (FIF-D15-AI)

Prompt v2 (`src/prompts/summary_v2.txt`) compared with v1 on the real Gemini, using the 10
questions from Day 9. Script: `scripts/day15_compare_prompts.py` (it writes every takeaway to
`artifacts/day15_prompts_draft.md`). Every takeaway below was read by hand against its passage.

**Result: v2 says "not found" for the 3 questions the passages don't answer, and every v2
takeaway answers the question from its cited passage.** v1 summarized all 10 questions, including
Q9 and Q10, which the reports don't answer.

## What changed from v1

The ticket asks for 3 things. v1 already did the first two. The third needed the question:

| Ticket asks | v1 | v2 |
|---|---|---|
| A source for each takeaway | Yes (`chunk_id`; the code fills in `source`) | Same |
| Use only the passages | Yes | Same, plus: one experiment's numbers never go to another; "planned" or "studied" stays planned or studied; a result isn't applied to conditions the passage doesn't cover (another planet, oxygen level, material) |
| "Not found" when the answer is missing | Only when no passage is about fire at all | When no passage helps **answer the question**, even if the passages are about fire |

**Why v2 needs the question:** `summarize()` used to get only the passages. Search always returns
fire passages, so v1 could never say "not found" for an on-topic question the reports don't answer.
Q9 and Q10 showed this on Days 13 and 14. Now:

- `summarize(passages, question=None)` (contract **v1.7**). With a question, Gemini gets
  `Question: ...` and then `Passages: ...`.
- Without a question it works as before (v2's rule 9 keeps v1's fire-topic rule).
- The question is treated as material, not instructions (rule 12), the same as passage text.

## Results (real Gemini)

Passages: `search()` with the experiment picked (as on Day 13), the same passages for v1 and v2.
"Cite the answer" means the cited passage holds the Day 10 evidence phrase.

| # | Question | v1 | v2 |
|---|---|---|---|
| 1 | Gases tested as fire suppressants | 4 takeaways, 2 cite the answer | 1 takeaway, cites the answer |
| 2 | What is LOI and how did FLEX measure it | 2, both cite the answer | 1, cites the answer |
| 3 | What is a cool flame | 3, **none** cite the answer | 1, cites the answer |
| 4 | FLEX-2 oxygen levels and pressures | 3, 1 cites the answer | 2, both cite the answer, both values |
| 5 | How FLEX-2 droplets were deployed and ignited | 3, 1 cites the answer | 3, all cite the answer |
| 6 | How fast a large fire grows | 5, **none** cite the answer | **not found** |
| 7 | Saffire-II airflow speeds | 5, 2 cite the answer | 1, cites the answer |
| 8 | Why normal-gravity tests are risky | 5, 2 cite the answer | 1, cites the answer |
| 9 | Most dangerous materials at 30% oxygen (uncovered) | 4, **none** answer it | **not found** |
| 10 | Lithium battery fire on Mars (uncovered) | 4, **none** answer it | **not found** |
| | **Total** | 34 takeaways, 10 cite the answer; 0 not found | 10 takeaways, 10 cite the answer; 3 not found |

**Q6 "not found" is correct.** Its answer chunk isn't among the 5 passages search returned (it ranks
17th, Day 14), and none of the 5 says how fast a fire grows.

## Read by hand

- **No invented facts in v2.** Every takeaway matches its passage. Numbers and experiment names are
  kept: Q4 gives FLEX-2's 0.5–3.0 atm and 0.1–0.4 mole fraction, both labelled FLEX-2.
- **v2 drops what doesn't answer the question.** v1's extra takeaways were true but off-topic
  (Q8: the cameras, the sample size). One v1 takeaway was also wrong. Q9: "Terrestrial fires …
  differ largely from fire behavior in normal and reduced gravity", where the passage contrasts
  normal and reduced gravity, not terrestrial and normal.
- **Two small wording slips in v2** (rule 4 asks to keep "planned" as planned):
  - Q1: "The FLEX investigation **measures** the effectiveness of … suppressants". The passage
    says it "**aims to** … measure".
  - Q8: "The Saffire-II investigation **states** …". The passage says it "**hypothesizes**".
- **v2 can under-answer.** Q2's passage has steps 1–6 of the LOI procedure, but v2 gave only the
  goal ("determine the LOI as a function of ambient pressure"). Q1 and Q7 also got 1 takeaway each,
  which is enough there.
- **Q3 is honest but thin:** the passages never define a cool flame, so v2 says only what they say
  (cool flames were studied). It didn't make up a definition.

## Limits of this test

- **Run on `gemini-flash-lite-latest`, not the app's default `gemini-flash-latest`.** On
  2026-11-10 the default model was overloaded: every call ended in `503 UNAVAILABLE` ("high
  demand") or `504 DEADLINE_EXCEEDED`, so the app would have shown its quoting fallback. The lite
  model answered in under a second. Run with
  `GEMINI_MODEL=gemini-flash-lite-latest uv run --env-file .env python scripts/day15_compare_prompts.py`.
- **One run.** Gemini's answers vary between runs, so counts can move by a takeaway or two.
- **10 questions.** D16-AI ("test 8+ questions, check each claim") should add more, including the
  held-out ones (`HELD_OUT` in `retrieval_eval.py`), and repeat the run on the default model.

## Bug found and fixed: every real Gemini call crashed

`summarizer.py` created the Gemini client inline (`_get_client(key).models.generate_content(...)`).
Nothing kept the client, so Python cleaned it up as soon as `.models` was read, and cleanup closes
its connection. Every real call failed with `RuntimeError: Cannot send a request, as the client has
been closed`. That error isn't one the fallback catches, so `summarize()` crashed instead of quoting.

The tests never caught it because their fake client is always kept alive by the test. Fix: keep the
client in a variable for the whole call. The new test `test_client_stays_open_for_the_whole_call`
uses a fake that closes itself when cleaned up, like the real one. It fails on the old code.
