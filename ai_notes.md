# AI notes: what's built and where to pick up (Days 1–7, FIF-D01-AI … FIF-D07-AI)

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

Related BE pieces the AI code uses: `store.py` saves/loads the index (D04-BE), `summarizer.py`
calls Gemini (D05-BE), and `config.py` reads the settings (D03-BE).

## 2. How the pieces fit

```
report text ──chunk_document()──> chunks {id, text, source, page}      chunking.py
chunks ──embed_texts()──> vectors (384 numbers each, length 1)           embedding.py
vectors + chunks ──save_index()/load_index()──> artifacts/<folder>/      store.py
question ──find_passages()──> top 3 chunks + score                       retrieval.py
top chunks ──summarize_passages()──> takeaways citing chunk_id           summarizer.py + prompt
summary ──check_summary()──> [] if every claim cites a real passage      summary_check.py
```

- **Chunk ids** look like `flex2-p1-c3` (doc, page, chunk number), as in `docs/contract.md` §2.
- **Row i of the vectors always belongs to chunk i.** `store.py` refuses mismatched counts.
- **Where it shows up in the app:** not yet. `api.search()` still returns mock data until
  **FIF-D10-BE** connects `find_passages`. The app's summary box is a placeholder until FE
  calls `summarize()`.

## 3. How to run things

All from the project root. None of these need an API key except the Gemini part of Day 1.

```
uv run pytest -q                                # all tests; a fake model/client, no network
uv run python scripts/day1_check_ai.py           # embeddings work; Gemini part skipped without a key
uv run python scripts/day3_embed_mock.py         # fake docs -> artifacts/mock_index/
uv run python scripts/day4_try_questions.py      # 5 fake questions against the mock index
uv run python scripts/day7_chunk_reports.py      # real reports -> data/processed/chunks.jsonl
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

## 5. Open questions and known issues

- **Embedding model not confirmed by the team.** Nergis tried Gemini embeddings
  (`gemini-embedding-001`) on Day 2. Switching means a key for search too, rebuilding the index,
  and rethinking chunk size. Only `embedding.py` would change; `top_k` refuses vectors of the
  wrong size.
- **Prompt v1 is untested on the real Gemini.** We have no key yet. When there is one, run
  `summarize()` on some passages and check the rules hold (checkbox in #122). Also confirm
  `gemini-flash-latest` accepts our `response_json_schema`.
- **Search misses on the fake questions:** 3/5 ranked first, 4/5 in the top 3. "What is a cool
  flame?" missed completely: a small meaning-based model can lose rare exact terms. Plan B for
  the tuning days: add keyword matching (hybrid BM25).
- **D10-AI wants to compare chunk sizes of 200/400/600 words**, but MiniLM cuts off at about
  200 words. Either keep sizes ≤ 200 or switch to a model that reads longer text.
- **`summarize()` never sees the user's question**, only the passages, so takeaways can't focus
  on what was asked. It's a contract change (BE) if we want it.
- **Worst-case wait for a summary is about 95 s** (3 tries × 30 s timeout + waits between
  retries) before the fallback kicks in. Worth lowering if it feels slow in the app.
- **The corpus is small:** 3 reports, about 2,100 words in total (see §6). Keep that in mind for
  the "8 of 10 relevant" goal in D14-AI.

## 6. Where the next ticket starts (FIF-D08-AI: embed the real chunks)

- **Input:** `data/processed/chunks.jsonl`, 18 chunks, one JSON object per line. To rebuild it, run
  `scripts/day7_chunk_reports.py`. The reports are in `docs/reports/`, not `docs/` as the plan says.
- **D08-AI** embeds the `text` of each chunk with `embed_texts` and saves them with `save_index` to
  the default `artifacts/index/` (time it, as the ticket asks). `artifacts/` is git-ignored, so
  each machine and the live app must build its own index.
- **Check with the D08-BE owner:** `be_notes.md` asks both roles to agree where `chunks.jsonl` and
  the index live, so `make ingest` writes the same files. D07 chose the paths above; that hasn't
  been confirmed with them yet.
- **D09-AI** asks 10 questions with `find_passages` and writes the results to `tests/retrieval.md`.
  `scripts/day4_try_questions.py` is a good starting point: it already pairs each question with
  the chunk expected to win.

## 7. Rules to keep

- **No real API keys or network in tests.** `tests/conftest.py` removes `GEMINI_API_KEY` for
  every test, and tests swap in a fake model or client.
- **Space Apps:** never write "according to NASA"; AI-written summaries must be labelled as
  AI-generated in the app; disclose AI use (our commits carry a `Co-Authored-By` line).
- **Never invent data:** when nothing matches, return "not found" (`not_found: true`), not a guess.
- **Fail loudly on bad input** (empty question, blank text, wrong settings): raise `ValueError`.
