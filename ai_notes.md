
# AI notes: what's built and where to pick up (Days 1–17, FIF-D01-AI … FIF-D17-AI)


For whoever takes over the AI role, and for anyone reviewing AI PRs. Like `data_notes.md`,
this file records what exists, the decisions behind it, and the open questions.

> **Update this file in every AI ticket's PR.** Add the ticket to §1, add any new decision to
> §4, move answered questions out of §5 (and add new ones), and rewrite §6 so it says where the
> next ticket starts. Reviewers: if an AI PR doesn't touch `ai_notes.md`, ask why.

Question the app answers (`docs/the_question.md`): *At what oxygen levels and airflow speed
does a fire in space keep burning or go out, for different materials?* The AI side handles
the text part: find the passages in the reports that match a question, then summarize them
with a citation for every claim.

## 1. Status per ticket

| Ticket | What | Files | PR |
|---|---|---|---|
| D01-AI | Check that the embedding model and the Gemini key work | `scripts/day1_check_ai.py` | #112 |
| D02-AI | Cut text into overlapping chunks that keep source + page; 3 fake docs | `src/flame_in_freefall/chunking.py`, `data/mock/docs.mock.json`, `tests/test_chunking.py` | #114 |
| D03-AI | Turn chunks into vectors (embeddings) and save them | `src/flame_in_freefall/embedding.py`, `scripts/day3_embed_mock.py`, `tests/test_embedding.py` | #120 |
| D04-AI | Find the top 3 chunks for a question (cosine similarity) | `src/flame_in_freefall/retrieval.py`, `scripts/day4_try_questions.py`, `tests/test_retrieval.py` | #121 |
| D05-AI | Summary prompt v1 | `src/prompts/summary_v1.txt`, test in `tests/test_summarizer.py` | #122 |
| D06-AI | Auto-check summaries: every claim cites a real passage | `src/flame_in_freefall/summary_check.py`, `tests/test_summary_check.py`, this file | FIF-D06-AI PR |
| D07-AI | Chunk the real reports and save them | `chunk_reports` in `src/flame_in_freefall/chunking.py`, `scripts/day7_chunk_reports.py`, `data/processed/chunks.jsonl`, `tests/test_chunking.py` | FIF-D07-AI PR |
| D08-AI | Embed the real chunks, save the search index, and time it | `scripts/day8_embed_chunks.py`, `artifacts/index/` (git-ignored) | FIF-D08-AI PR |
| D09-AI | Test real search with 10 questions and judge the top 3 | `scripts/day9_test_search.py`, `tests/retrieval.md` | FIF-D09-AI PR |
| D10-AI | Compare chunk sizes and overlaps, score each, choose one | `src/flame_in_freefall/retrieval_eval.py`, `scripts/day10_compare_chunk_sizes.py`, `tests/chunk_sizes.md`, `tests/test_retrieval_eval.py` | FIF-D10-AI PR |
| D11-AI | Compare top 3, 5 and 8 and log the failures | `scripts/day11_compare_k.py`, `tests/top_k.md`, `NAMED_EXPERIMENT` in `retrieval_eval.py`, `tests/test_retrieval_eval.py` | FIF-D11-AI PR |
| D12-AI | Filter search by experiment before ranking | `rows_for_experiment` and `experiment=` in `src/flame_in_freefall/retrieval.py`, `scripts/day12_filter_by_experiment.py`, `tests/experiment_filter.md`, `tests/test_retrieval.py` | #142 |
| D13-AI | Re-run the 10 questions through the real `search()`, pass/fail with reason | `judge` and `WEAK` in `retrieval_eval.py`, `scripts/day13_retest.py`, `tests/retest.md`, `tests/test_retrieval_eval.py` | #151 |
| D14-AI | Retrieval checkpoint: score recorded, ranking changes tried on the 10 questions and 10 held-out ones | `experiment_in_question` in `retrieval.py`, `HELD_OUT`, `contains_evidence` and `judge_against` in `retrieval_eval.py`, `scripts/day14_checkpoint.py`, `tests/checkpoint.md`, `tests/test_retrieval.py`, `tests/test_retrieval_eval.py` | #152 |
| D15-AI | Summary prompt v2: gets the question, says "not found" when the passages don't answer it; fixed the closed-client crash | `src/prompts/summary_v2.txt`, `question=` in `summarizer.py` and `api.summarize` (contract v1.7), `scripts/day15_compare_prompts.py`, `tests/prompt_v2.md`, `tests/test_summarizer.py`, `tests/test_api_edge_cases.py` | #158 |
| D16-AI | Test summaries on 22 questions with the real Gemini, judge every claim, check "not found"; a number/experiment checker; prompt v3 tried and not adopted | `src/flame_in_freefall/claim_check.py`, `SUMMARY_EXTRA` in `retrieval_eval.py`, `scripts/day16_test_summaries.py`, `tests/summaries.md`, `tests/test_claim_check.py`, `tests/test_day16_script.py`, `tests/test_retrieval_eval.py` | FIF-D16-AI PR |
| D17-AI | Summary accuracy tests in CI: Gemini's real answers replayed (30 recorded, 21 questions), "not found" asserted, a staleness check, and an opt-in live test | `tests/test_summary_accuracy.py`, `tests/fixtures/summaries.json`, `scripts/day17_record_summaries.py`, `tests/test_day17_script.py`, `live` marker in `pyproject.toml` | FIF-D17-AI PR |


Related BE pieces the AI code uses: `store.py` saves/loads the index (D04-BE), `summarizer.py`
calls Gemini (D05-BE), and `config.py` reads the settings (D03-BE).

## 2. How the pieces fit

```
report text ──chunk_document()──> chunks {id, text, source, page}      chunking.py
chunks ──embed_texts()──> vectors (384 numbers each, length 1)           embedding.py
vectors + chunks ──save_index()/load_index()──> artifacts/<folder>/      store.py
question (+ experiment) ──find_passages()──> top 3 chunks + score       retrieval.py
top chunks ──summarize_passages()──> takeaways citing chunk_id           summarizer.py + prompt
summary ──check_summary()──> [] if every claim cites a real passage      summary_check.py
```

- **Chunk ids** look like `flex2-p1-c3` (doc, page, chunk number), as in `docs/contract.md` §2.
- **Row i of the vectors always belongs to chunk i.** `store.py` refuses mismatched counts.
- **Where it shows up in the app:** not yet. `api.search()` still returns mock data until
  **FIF-D10-BE** connects `find_passages`. The app's summary box is a placeholder until FE
  calls `summarize()`.

## 3. How to run things

All from the project root. None of these need an API key except the Gemini part of Day 1 and the
scripts and tests that say "real Gemini".

```
uv run pytest -q                                # all tests; a fake model/client, no network
uv run python scripts/day1_check_ai.py           # embeddings work; Gemini part skipped without a key
uv run python scripts/day3_embed_mock.py         # fake docs -> artifacts/mock_index/
uv run python scripts/day4_try_questions.py      # 5 fake questions against the mock index
uv run python scripts/day7_chunk_reports.py      # real reports -> data/processed/chunks.jsonl
uv run python scripts/day8_embed_chunks.py       # real chunks -> artifacts/index/, prints the time
uv run python scripts/day9_test_search.py        # 10 real questions -> artifacts/retrieval_draft.md
uv run python scripts/day10_compare_chunk_sizes.py  # 15 chunk settings, scored -> artifacts/chunk_sizes_draft.md
uv run python scripts/day11_compare_k.py         # top 3, 5 and 8, scored -> artifacts/top_k_draft.md
uv run python scripts/day12_filter_by_experiment.py  # with/without the filter -> artifacts/experiment_filter_draft.md
uv run python scripts/day13_retest.py           # real search(), pass/fail -> artifacts/day13_retest_draft.md
uv run python scripts/day14_checkpoint.py       # checkpoint score + ranking changes -> artifacts/day14_checkpoint_draft.md
GEMINI_MODEL=gemini-flash-lite-latest uv run --env-file .env python scripts/day15_compare_prompts.py  # prompt v1 vs v2, real Gemini (~20 calls)
GEMINI_MODEL=gemini-flash-lite-latest uv run --env-file .env python scripts/day16_test_summaries.py  # 22 questions, real Gemini (~32 calls, ~6 min)
uv run python scripts/day17_record_summaries.py   # the Day 16 recording -> tests/fixtures/summaries.json (no Gemini)
RUN_LIVE=1 GEMINI_MODEL=gemini-flash-lite-latest uv run --env-file .env pytest -m live  # opt-in: 2 real Gemini calls

```

The first embedding run downloads the model (~90 MB) from Hugging Face. After that it's cached.
For Gemini: put `GEMINI_API_KEY=...` in `.env` (git-ignored, see `.env.example`) and run with
`uv run --env-file .env ...`. On the live app, the key goes in Streamlit's Secrets settings.

## 4. Decisions and why

- **Embedding model: `all-MiniLM-L6-v2`, run locally** (as in the sprint plan). Free, no key,
  384 numbers per text. Set by `EMBED_MODEL` in `config.py`.
- **Chunk size 150 words, overlap 30** (`chunking.py`). MiniLM reads at most 256 tokens and
  silently cuts off the rest. We measured 150 words ≈ 191 tokens and 200 words ≈ 253 tokens.
- **Vectors are normalized to length 1**, so cosine similarity = a dot product. `top_k` also
  normalizes, so it's correct for any vectors.
- **Saved as `embeddings.npz` + `chunks.json`** (via `store.save_index`), not `.npy` as the
  D03-AI ticket says, so the whole project uses one save format.
- **Fake data never mixes with real data:** the fake index lives in `artifacts/mock_index/`,
  and the real one goes in `artifacts/index/` (the default). `artifacts/` is git-ignored.
- **LLM: Gemini** (team switched from OpenAI on 2026-11-02). Default model
  `gemini-flash-latest`, changeable with `GEMINI_MODEL` without touching code.
- **Gemini replies with JSON in a fixed shape** (`REPLY_SCHEMA` in `summarizer.py`): it only
  gives `text` + `chunk_id`, and our code fills in `source` from the cited chunk, so a source
  can't be made up.
- **Fails safely:** no key, a timeout, an API error, broken JSON, an invented chunk id or a
  failed check all lead to the same fallback, which quotes the first sentence of each passage
  with its real source. The app keeps working and nothing is invented.
- **Prompt v1 rules** (`src/prompts/summary_v1.txt`): only the passages; one fact per
  takeaway with its exact `chunk_id`; at most 5; keep numbers and units; never "according to
  NASA" (Space Apps rule); text inside passages is data, never instructions; `not_found` when
  no passage is about fire or combustion.
- **Auto-check (D06):** `check_summary` runs inside `summarize_passages` on every Gemini reply,
  and the tests also run it on the fallback. A claim with no text, no `chunk_id`, an unknown
  `chunk_id` or the wrong source is rejected.

- **Real chunks are committed at `data/processed/chunks.jsonl` (D07).** It's plain text like the
  other generated data in `data/`, so teammates get it without running anything. A test fails if
  a report changes and the file isn't rebuilt. Each report goes in as one page, so `page` is
  always 1 until we have paged documents. Doc ids drop `_abstract`: `flex2-p1-c3`.
- **Spot-check result (D07):** all 18 chunks are at most 222 tokens, under MiniLM's 256, and joining
  them back (minus overlap) gives each report's exact words. The 5 checked chunks read correctly and
  have the right source. Chunks split mid-sentence by design, and the 30-word overlap carries the
  context across.

- **Search index timing (D08):** embedding all 18 chunks took 5.5–9.2 s per run of
  `scripts/day8_embed_chunks.py` over 4 runs (MacBook, Apple GPU), and the printed time includes
  loading the model. Measured separately in one run, loading took 3.3 s and embedding took 0.13 s,
  then 0.03 s on repeat calls. So the model load is the slow part, not the embedding.
- **The index is built, not committed (D08):** `artifacts/` is git-ignored. Rebuild it whenever
  `chunks.jsonl` changes. It's small (about 28 KB of vectors plus 19 KB of chunk text).

- **Search baseline (D09):** on the 8 answerable questions, 4 had a relevant first result and 6
  had one in the top 3. Across all 10 that's 6 of 10, against the D14-AI goal of 8 of 10. Full log:
  `tests/retrieval.md`. Claude Code did the judging at NathanRivera1's request; no teammate has
  reviewed it yet.
- **The test log stays apart from the script's output (D09):** the script writes a draft to
  git-ignored `artifacts/`, so rerunning it can't overwrite the judgments in `tests/retrieval.md`.

- **Chunk size stays 150 words, overlap 30 (D10).** Tested sizes 100, 150, 200, 400 and 600 with
  overlaps 0, 30 and 60. No setting clearly beat it: top-3 hits ranged 5–7 of 8, a one-question
  spread. At 400 and 600, 43–56% of the text falls past MiniLM's limit and the index is so small
  that random picks score nearly as well. Full log and reasons: `tests/chunk_sizes.md`.
- **Search is scored by evidence phrases now (D10)**, not by hand: `EVIDENCE` in
  `retrieval_eval.py` lists phrases from the reports that answer each question. They reproduce all
  30 Day 9 hand judgments (a test checks this), so any chunk setting or `k` can be scored the same
  way. The 10 questions live there too, and the Day 9 script imports them.
- **The comparison runs in memory (D10):** `day10_compare_chunk_sizes.py` doesn't touch
  `chunks.jsonl` or `artifacts/index/`. `chunk_reports` now takes `size` and `overlap`.

- **Recommended k is 5, but the code still defaults to 3 (D11).** At k = 5, 7 of 8 answerable
  questions have a relevant chunk, up from 6 (Q4 is the new one), for about 705 words per
  question instead of 423. k = 8 finds no more questions, sends 1,147 words, and 14 of 32 chunks
  for questions that name an experiment come from the wrong one. Full log: `tests/top_k.md`. The
  default stays 3 until BE agrees, because it's in `docs/contract.md`.

- **Wrong-experiment chunks are counted now (D11):** `NAMED_EXPERIMENT` in `retrieval_eval.py` maps
  Q2, Q4, Q5 and Q7 to the experiment they name, and `score_results` returns `wrong_experiment`
  out of `named_returned`, using each chunk's `experiment` tag.
- **The k comparison uses the committed chunks (D11):** `day11_compare_k.py` reads
  `data/processed/chunks.jsonl` and embeds it in memory, so it needs no built index.

- **The re-test goes through the real `api.search()` (D13)**, not `find_passages`, so it includes
  everything the app does: k = 5, the experiment filter and D13-BE's 0.30 score cutoff. It builds
  `artifacts/index/` if it's missing, like the app. Full log: `tests/retest.md`.
- **Pass/fail rule (D13, `judge` in `retrieval_eval.py`):** an answerable question passes if a
  returned passage holds the answer *and*, when the question names an experiment, no other
  experiment's passage comes with it. An uncovered question passes only on "no match" (`[]`).
  The experiment rule is stricter than Days 9–12, which counted a question as found either way.
- **Re-test result (D13):** 7 of 10 pass with the experiment picked (Q6, Q9, Q10 fail), 4 of 10
  with the app's default "All experiments" (Q2, Q4 and Q5 also fail on wrong-experiment chunks).

- **Checkpoint score (D14): 7 of 10 in the app, goal 8.** Full log: `tests/checkpoint.md`.
  "Keywords + best sentence" ranking reaches 8 of 10 when measured in memory, and 10 of 10 on 10
  held-out questions (today's search: 8 of 10). It's not in the app: it needs sentence vectors in
  the index and a new meaning for `score`, both BE's.
- **Held-out questions (D14):** `HELD_OUT` in `retrieval_eval.py` has 10 new questions that were not
  used to choose any change. Judge every future ranking change on both sets, so a change that only
  fits the 10 original questions shows up.
- **Reading the experiment from the question (D14):** `experiment_in_question` returns the one
  experiment a question names, or `None` (none, or two named). It's built and tested but nothing
  calls it yet. With it, the default run scores 7 instead of 4.

- **Prompt v2 (D15, `src/prompts/summary_v2.txt`):** gets the user's question, keeps only
  takeaways that answer it, and sets `not_found` when no passage does, even if the passages are
  about fire. It also keeps each experiment's numbers with that experiment, and keeps "planned" or
  "studied" from turning into results. v1 stays in the repo for comparison.
- **v2 on the real Gemini (D15, `tests/prompt_v2.md`):** 10 takeaways, all citing a passage with the
  answer; "not found" for Q6, Q9 and Q10 (none of their passages answers them). v1: 34 takeaways,
  10 citing the answer, and it summarized Q9 and Q10 anyway.
- **BASS-II is the 4th report (D16-DAT):** 4 more chunks (22 in all), tagged `BASS-II`, and the
  index was rebuilt. The D14 checkpoint was re-run: same scores on both question sets. Rebuild
  the index after pulling (`scripts/day8_embed_chunks.py` or
  `uv run python -m flame_in_freefall.ingest`; there's no Makefile). The app also rebuilds it by
  itself on the first search when it's out of date.
- **Real Gemini calls crashed before D15:** the client was created inline and cleaned up before the
  request, so it failed with "client has been closed", which the fallback didn't catch. Fixed in
  `summarizer.py`, with a test that fails on the old code.

- **Summaries match their sources (D16, `tests/summaries.md`).** 22 questions (Q1–Q10, the 10
  held out, 2 new BASS-II ones in `SUMMARY_EXTRA`) through the real `search()` and `summarize()`,
  once with the experiment picked and once with nothing picked. 39 takeaways, each read against its
  passage: 38 supported, 1 wording slip (Q8), 0 invented facts or wrong-experiment numbers. "Not
  found" was right for all 4 that said it (Q6, Q9, Q10, H7). With nothing picked, Q4's top passage
  was FLEX's wrong range and the summary still gave only FLEX-2's numbers.
- **The Day 15 slips (D16):** Q1's "aims to measure" is now kept. Q8 ("hypothesizes" written as a
  statement) and Q2 (goal without the procedure) remain. Chunk boundaries contribute, but the
  prompt's effect hasn't been isolated (§5); Q2 also omits steps that are available.
- **Prompt v3 was tried and not adopted (D16).** Two rules (cut-off openings may be hypotheses;
  answer every part of a several-part question) fixed Q2 in one run of two, didn't fix Q8, made Q5
  and H8 thinner, and added a slip. v2 stays; v3's rules are quoted in `tests/summaries.md`.
- **`claim_check.py` (D16)** flags a number or an experiment name a takeaway doesn't get from its
  passage (leading-dot decimals, attached signs, ranges, "%" vs "percent", thousands separators,
  CO2-style formulas and "FLEX-2"'s digit handled; numbers in words, scientific notation, separated
  signs and unit conversions not). 0 flags on 75 real takeaways (v2 and v3), so 0 false alarms.
  It's a report tool, not in the app's path.
- **The summary run records Gemini's exact replies** (`artifacts/day16_replies.json`), with the
  passage ids and a hash of each passage's text, so D17-AI can replay them as tests without a key.
  Partial `--only` runs use separate names (e.g. `day16_only_Q1_Q8_replies.json`); unknown labels
  and empty selections are rejected before any calls, preserving the full recording.
- **Summary accuracy tests replay Gemini's real answers (D17, `tests/test_summary_accuracy.py`).**
  CI has no key, so `tests/fixtures/summaries.json` (committed, 33 KB) holds the 30 answers recorded
  on 2026-11-12: 21 questions asked with the experiment picked, 9 of them again with nothing
  picked. H4 (no passages, so the app never calls Gemini for it) is the 22nd question and has
  nothing to replay. It is built from
  `artifacts/day16_replies.json` by `scripts/day17_record_summaries.py`, which copies the replies
  unchanged and refuses a quoting fallback, a Gemini error, a non-JSON reply or a repeat. Each test
  runs the recorded reply through the real `api.summarize()` and asserts: it is Gemini's answer
  (not the fallback) to the recorded passages and question; a question whose passages hold the
  evidence phrase cites one that does (26 cases); a question whose passages don't gets `not_found`
  with no takeaways (Q6, Q9, Q10, H7); `claim_check` finds nothing (`KNOWN_FALSE_ALARMS` is empty,
  since D16 found no false alarm). "Answerable" is decided from the recorded passages, not
  hard-coded. The replays don't call `search()`, so ranking, filter or cutoff changes require
  re-recording to test their effect on which evidence reaches Gemini.
- **Staleness is checked, and says how to fix it.** `test_the_recorded_passages_are_still_the_chunks`
  fails, naming each question and chunk, if a chunk was removed or its text hash changed or the
  app's prompt file has another name than the recording's; the replays then skip instead of testing
  old passages. Stale entries are excluded from answerability classification during collection;
  the derived coverage count also skips until the recording is current, leaving the dedicated
  staleness test to explain the problem and give the re-record steps (below).
  Four collection regressions cover a removed chunk, an edited chunk, a renamed prompt, and
  removal of all chunks. All four failed before this guard was added. They use a made-up
  recording and made-up chunks in place of the real files' contents (nothing on disk is read or
  changed), plus a control showing the made-up recording is current before it's changed. So when
  the real recording is stale, only the staleness test fails.
- **What the replay tests can't prove:** that Gemini still answers this way. A prompt edited in
  place, a new model, or a change at Google isn't noticed until someone re-records. The opt-in live
  test (`pytest -m live`, needs `RUN_LIVE=1` and a key) asks the real Gemini the same passages for
  Q1 (answerable) and Q9 (not) and asserts the same things, and also fails if the model was
  overloaded and the passages were quoted instead. CI never runs it; it is skipped otherwise.
- **To re-record** (after the chunks, prompt or model change): run `scripts/day16_test_summaries.py`
  with the key (~32 calls, ~6 min), check the new answers by hand as in `tests/summaries.md`, run
  `scripts/day17_record_summaries.py`, and commit the new fixture; its diff shows exactly which
  replies changed. Never write a reply by hand.

## 5. Open questions and known issues

- **Embedding model not confirmed by the team.** Nergis tried Gemini embeddings
  (`gemini-embedding-001`) on Day 2. Switching means a key for search too, rebuilding the index,
  and rethinking chunk size. Only `embedding.py` would change; `top_k` refuses vectors of the
  wrong size.
- **Prompt v2 has only been tested on `gemini-flash-lite-latest` (D15, D16).** The default
  `gemini-flash-latest` was overloaded on 2026-11-10, 11 and 12 (503 or 504 every time), so the app
  shows the quoting fallback with it. The lite model answers in 1–11 s (D16; BE measured 1.2–8.7 s on
  2026-11-11) and accepts our `response_json_schema`. **Team decision:** set
  `GEMINI_MODEL = "gemini-flash-lite-latest"` in the app's Secrets?
- **Two slips remain; chunk boundaries contribute (D16).** Q8: "This investigation hypothesizes" is
  split across `saffire2-p1-c1` and `c2`, and only `c2` is sent, so the hypothesis reads as a plain
  statement. Q2: the LOI procedure runs into `flex-p1-c2` and `c3`, which the 0.30 cutoff drops, and
  `c1` ends mid-step ("until flame exists" for "until flame exists for only a short time after
  ignition"). Several earlier steps are available but omitted by v2; v3 included procedure steps
  in the default run on the same passages. Missing context alone doesn't explain that omission.
  Possible fixes, untested: cut chunks at sentence ends, or send each passage with the
  end of the chunk before it. Either changes the index, so re-run the D14 checkpoint after.
- **Search misses on the fake questions:** 3/5 ranked first, 4/5 in the top 3. "What is a cool
  flame?" missed completely: a small meaning-based model can lose rare exact terms. Plan B for
  the tuning days: add keyword matching (hybrid BM25).
- **Larger chunks would need a different embedding model (D10).** MiniLM cuts off at about 200
  words, so 400 and 600 were measured but can't be used as they are. Not worth it on this corpus:
  big chunks also make the index too small to rank in a useful way.
- **Q6 isn't a chunk-size or k problem (D10, D11).** Its relevant chunk ranked 12th or lower at
  every size up to 200 words, and 17th of 18 at 150/30, so no k up to 8 finds it. 7 of its top 8
  are FLEX droplet chunks; maybe "large fire" matches "relatively large droplets". Untested.
- **Default k is 5 now** (contract v1.1, agreed with BE). 5 passages fit easily: about 1,600 input
  and 80 output tokens per summary, median 1.3 s on the lite model (D16).
- **The 0.30 score cutoff (D13-BE) doesn't catch Q9 or Q10, and drops Q2's answer passages (D13).**
  Q9 and Q10 score 0.39–0.48, which is above Q4's answer at 0.395, so no cutoff separates them. Q2
  loses `flex-p1-c2` (0.295, the LOI procedure's key step) and `flex-p1-c3` (0.281). The log suggests
  discussing 0.27 with BE. That's untested. Details: `tests/retest.md`.
- **"All experiments" is the app's default, and it lets wrong-experiment numbers through (D13).**
  Q2, Q4 and Q5 fail the re-test only because of this. Reading the experiment name from the
  question when nothing is picked would fix all three. Not built.
- **Bigger k sends wrong-experiment numbers to the summary (D11).** At k = 5, Q4 gets FLEX-2's
  pressure range (4th) and FLEX's (1st). `summarize()` never sees the question, so it can't drop
  FLEX's. On paper, filtering chunks by the named experiment puts Q4's answer 2nd with no
  wrong-experiment chunks, even at k = 3 (`tests/top_k.md`). Not built or tested.
- **The evidence phrases miss paraphrases.** They match exact wording, so a passage that
  paraphrases the answer counts as a miss. Hand-check a few results whenever the scores jump. On
  D11 the only one found was Q6's `saffire2-p1-c3` at rank 8 ("flame growth", weak).
- **Overlap repeats inflate "relevant" counts (D11).** Q8's two hits at k = 5 are the same sentence,
  copied by the 30-word overlap. A bigger k looks better on "Relevant / returned" than it is.
- **`summarize()` sees the question now (D15, contract v1.7)**, and the app passes it since
  D14-FE (#159): `summarize(results, question=query)`.
- **Worst-case wait for a summary is about 32 s since D16-BE (#167)** (2 tries × 15 s + a short
  wait), down from about 95 s. Gemini is also limited to 10 summaries a minute for the whole app.
- **Search can return the wrong experiment (D09).** For Q4, about FLEX-2's oxygen and pressure, the
  top result was FLEX with a pressure range that isn't FLEX-2's, and the right chunk ranked 4th of 18.
  A summary could repeat those wrong numbers. Possible cause, untested: that chunk never names FLEX-2,
  and the experiment name isn't embedded with it. With the D12 filter on FLEX-2 it ranks 2nd. On
  D16, prompt v2 left FLEX's range out of the summary even when it was the top passage.
- **A strongly worded match can still rank near the bottom (D09).** For Q6, `saffire2-p1-c0` ranked
  17th of 18. Possible cause, untested: the chunk mixes the objective with a lot of hardware detail.
- **Chunk boundaries can cut off answers (D09).** For Q7, the top result stops just before the airflow
  values. The chunk with the values ranked 2nd.
- **No score cutoff separates good from bad (D09).** Q3's relevant chunk scored 0.427, and Q9's
  irrelevant top result scored 0.478. Search always returns k passages, so "not found" depends on
  `summarize()`.
- **Do Q9 and Q10 count toward "8 of 10"? (D9, still open after D14)** No search change can pass
  them: they score 0.41–0.54, as high as real answers. With them in, 8 of 10 means all 8
  answerable questions must pass. D14 reused the same 10 and added 10 held-out ones.
- **Adopt "keywords + best sentence"? (D14)** It's the only change that reaches 8 of 10, and it
  holds on the held-out set. Needs BE: sentence vectors in the index (120 for 18 chunks),
  `score` becomes the best sentence's score, and `MIN_SCORE` needs retuning. The off-topic "rocket
  thrust" question scores 0.3004 that way. Steps in `tests/checkpoint.md`.
- **The corpus is small:** 3 reports, about 2,100 words in total. Keep that in mind for
  the "8 of 10 relevant" goal in D14-AI.

## 6. Where the next ticket starts (FIF-D18-AI test hallucinations, and the open search work)

The D18 plan (issue #72): *1) Ask out-of-scope questions. 2) Check "not found". Done when: no
invented answers.*

- **What exists to build on:** Q9 (dangerous spacecraft materials at 30 percent oxygen) and
  Q10 ("How do you put out a lithium battery fire on Mars?")
  are the only out-of-scope questions so far, and both give "not found" in the recording and in
  the replay tests. The D18 set should be bigger and nastier: questions about fire that the four
  reports don't cover (other fuels, other stations, numbers the reports never give), questions
  that name a real experiment but ask for something it didn't measure, and questions with a
  false premise. Judge each real answer by hand, as in `tests/summaries.md`.
- **The retrieval side can't help:** no `MIN_SCORE` is safe with today's ranking (§5), so an
  out-of-scope question reaches Gemini with five passages, and "not found" depends on prompt v2.
  That is the thing to test. Record the real answers the same way (`scripts/day16_test_summaries.py`
  takes its questions from `retrieval_eval.py`; add a `SUMMARY_EXTRA`-style list, not new entries
  in `QUESTIONS` or `HELD_OUT`, which the D14 scores depend on), then replay them in CI as D17 did.
- **A failure there is a prompt problem,** not a test problem. Prompt v3 (D16) was rejected, so any
  new prompt needs the same tests as v2 (`tests/summaries.md`) and a new file name, so the staleness
  check notices.
- **Search work still waiting on team decisions** (unchanged since D14): "keywords + best
  sentence" (8 of 10, needs BE's index change and a new `MIN_SCORE`; code in
  `scripts/day14_checkpoint.py`), and calling `experiment_in_question` in `search()` when nothing
  is picked (4 → 7 of 10 in the app's default run; BE's file). Judge every change on both
  question sets (`TUNING` and `HELD` in the D14 script).
- **The missing context contributing to the two slips** (§5) is for whoever owns chunking next;
  Q2's omission of available steps also remains open. Changing the chunks makes the staleness test
  fail until the D16 run is repeated and re-recorded.

## 7. Rules to keep

- **No real API keys or network in tests.** `tests/conftest.py` removes `GEMINI_API_KEY` for
  every test, and tests swap in a fake model or client.
- **Space Apps:** never write "according to NASA"; AI-written summaries must be labelled as
  AI-generated in the app; disclose AI use (our commits carry a `Co-Authored-By` line).
- **Never invent data:** when nothing matches, return "not found" (`not_found: true`), not a guess.
- **Fail loudly on bad input** (empty question, blank text, wrong settings): raise `ValueError`.
