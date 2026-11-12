# BE notes: what's built and how it runs (Days 1–15, FIF-D01-BE … FIF-D15-BE)

For anyone reviewing BE PRs, and for teammates whose code calls the backend. Like
`data_notes.md` and `ai_notes.md`, this file records what exists, the decisions behind it, and
the open questions.

> **Update this file in every BE ticket's PR.** Add the ticket to §1, update §2 if a file's
> job changes, add any new decision to §4, move answered questions out of §5 (and add new
> ones), and rewrite §6 so it says where the next ticket starts. Reviewers: if a BE PR doesn't
> touch `be_notes.md`, ask why.

## 1. Status per ticket

| Ticket | What | Files | PR |
|---|---|---|---|
| D01-BE | Repo setup and the agreed shapes (contract v1.0), mock data | `docs/contract.md`, `data/mock/`, `pyproject.toml`, CI | came in with #6 |
| D02-BE | The 3 contract functions as stubs returning mock data | `src/flame_in_freefall/api.py`, `tests/test_contract.py` | came in with #6 |
| D03-BE | Settings, cache and logging | `config.py`, `cache.py`, `tests/test_infra.py` | #104 |
| D04-BE | Save/load the search index (vectors + chunks) | `store.py`, `tests/test_store.py` | #107 |
| D05-BE | Real `summarize()`: timeout, retry, fallback, mocked client in tests | `summarizer.py`, `tests/test_summarizer.py`, `tests/conftest.py` | #108, then Gemini in #111 |
| D06-BE | First deploy on Streamlit Community Cloud | `app/requirements.txt`, `app/streamlit_app.py` (Nergis, #123); this file | #123 + #128 |
| D07-BE | Repeatable deploy: Dockerfile, health checks, merge deploys | `Dockerfile`, `.dockerignore`, `tests/test_app.py` | #129 |
| D08-BE | One command to ingest: reports → chunks → index, skipping finished steps | `ingest.py`, `tests/test_ingest.py` | #139 |
| D09-BE | Real `get_table()` from `data/master.csv`; contract v1.2 | `api.py`, `docs/contract.md`, `tests/test_get_table.py`, `tests/test_contract.py`, 2 small edits in `app/streamlit_app.py` (FE's file) | #143 |
| D10-BE | Real `search()`; builds the index on first search; contract v1.3 | `api.py`, `docs/contract.md`, `tests/test_search.py`, `tests/conftest.py` (fake model for all tests) | #144 |
| D11-BE | Measure speed: every call timed, repeated questions cached, slowest-calls report | `speed.py`, `api.py`, `cache.py` (`is_cached`), `tests/test_speed.py`, 3 lines in `app/streamlit_app.py` (FE's file) | #145 |
| D12-BE | `search()` takes an `experiment` filter; contract v1.4 | `api.py`, `docs/contract.md`, `tests/test_search.py` | #146 |
| D13-BE | Edge cases for all three functions; `search()` "no match" (min score 0.30); contract v1.5 | `api.py`, `docs/contract.md`, `tests/test_api_edge_cases.py`, `tests/conftest.py` | #148 |
| D14-BE | End-to-end check: ingest → search → table | `tests/test_end_to_end.py`, `scripts/day14_end_to_end.py` | #149 |
| D15-BE | Sources in output: `summarize()` checks its answer's shape on every path; contract v1.6 | `api.py`, `summarizer.py`, `summary_check.py` (D06-AI's file), `docs/contract.md`, `tests/test_summary_shape.py`, `tests/test_summary_check.py` | #154 |
| fix (D08) | New chunks always rebuild the index, so the flaky ingest test is deterministic | `ingest.py`, `tests/test_ingest.py` | #155 |
| fix (D05) | The quoting fallback quotes the first full sentence, not a fragment | `summarizer.py`, `tests/test_summarizer.py` | FIF-D05-BE fallback PR |

## 2. What each BE file does

All code is in `src/flame_in_freefall/`.

| File | Job | Status |
|---|---|---|
| `api.py` | The 3 functions everyone calls, with the exact shapes in `docs/contract.md` | all 3 are real (`search()` since D10) |
| `config.py` | Reads every setting from environment variables into one frozen `Settings` | in use |
| `cache.py` | Remembers answers by question (JSON files, or in memory with `@memo`) | `@memo` used by `search()` since D11; `QueryCache` (files) not used |
| `speed.py` | Times every backend call into `artifacts/speed.log`; `uv run python -m flame_in_freefall.speed` lists the slowest | in use since D11 |
| `store.py` | Saves/loads the search index as `embeddings.npz` + `chunks.json` | used by the AI scripts and `ingest.py` |
| `ingest.py` | One command builds the search index: `uv run python -m flame_in_freefall.ingest` (`--force` redoes every step) | in use; same files as the AI scripts for Days 7–8 |
| `summarizer.py` | Calls Gemini for takeaways; falls back to quoting passages on any failure | in use through `api.summarize()` |

The app (`app/streamlit_app.py`) belongs to FE and only calls `api.py`.

## 3. How the deploy works (D06)

- **Live app:** https://crc-flame-in-freefall.streamlit.app
- **Host:** Streamlit Community Cloud (free), deployed from `main`, entry file
  `app/streamlit_app.py`, Python 3.12.
- **Who can manage it:** only Nergis. Community Cloud lets only a repo **admin** deploy, and in a
  personal-account repo that's the owner. Teammates with write access can read the build logs.
- **Every merge to `main` redeploys automatically.** A broken `main` means a broken live app, so
  CI (ruff + pytest) must pass before merging.
- **Packages:** Community Cloud looks for a dependency file in the entry file's folder first, so
  it installs from **`app/requirements.txt`**, not from our `uv.lock` in the repo root.
- **Our code is importable** because `streamlit_app.py` adds `src/` to Python's search path
  (`sys.path`). On Community Cloud our package isn't installed the way `uv sync` installs it.
- **Secrets:** none yet. When there's a Gemini key, Nergis pastes `GEMINI_API_KEY = "..."` into
  the app's Secrets settings. Streamlit turns top-level secrets into environment variables, so
  `config.get_settings()` reads it with no code change. Keys never go in the repo.
- **Sleep:** the app sleeps after a while without visitors. The first visitor clicks "Yes, get
  this app back up!" and waits about a minute.
- **Checked on 2026-11-04:** page loads, search shows the mock results and the summary
  placeholder, the table and sidebar filters work, and all 3 charts draw.
- **Health check (D07):** the live URL can't be checked from CI. `/_stcore/health` redirects
  automated requests to a Streamlit sign-in page, and `/healthz` answers `{"status":"ok"}` even
  for an app name that doesn't exist (it's the hosting platform, not our app). So the app is
  checked **before** it can reach `main`: `tests/test_app.py` runs the real
  `app/streamlit_app.py` with Streamlit's `AppTest` in CI and fails on a crash or a red error
  box. Tried on purpose: a failing `get_table()` and renamed `master.csv` columns both fail it.

### Docker (backup host, D07)

- `Dockerfile` installs from `uv.lock` (the exact versions our tests use) and runs the app on
  port 8501. Commands are at the top of the file. Secrets are passed in when it starts
  (`--env-file .env`) and never built into the image (`.dockerignore` keeps `.env` out).
- Its `HEALTHCHECK` asks `/_stcore/health` every 30 s; inside the container there's no sign-in
  redirect, so `docker ps` shows `(healthy)` or `(unhealthy)` for the real app.
- **Tested on 2026-11-04:** built in ~14 min, image ~20 GB, container `(healthy)`, health
  endpoint and main page answer HTTP 200.
- Run it with `-p 127.0.0.1:8501:8501` so only your own computer can open it.
- Needs Docker (on Windows: Docker Desktop with WSL integration for Ubuntu turned on). If
  `docker` says "permission denied", restart WSL once (`wsl --shutdown`) so your user's new
  `docker` group applies.

## 4. Decisions and why

- **Contract first:** `docs/contract.md` fixes the function names and return shapes, and mocks
  return exactly those shapes. FE could build the app before any real data existed. Shapes
  change only by PR, with a version bump.
- **Fail loudly on bad input:** an empty question, an unknown filter key (e.g. a typo like
  `"colour"`) or mismatched index files raise an error instead of quietly returning something.
- **Never invent data:** no passages means `not_found: true`; a failed Gemini call quotes the
  real passages instead of making something up.
- **Gemini instead of OpenAI** (team decision, 2026-11-02): `google-genai`, with a 30 s timeout
  and 3 attempts, so the client retries timeouts, rate limits and server errors.
- **Settings are read fresh on every call** (`get_settings()`), so tests can change them with
  `monkeypatch`, and a `frozen` dataclass means nothing changes a setting by accident.
- **The index is saved as `.npz` + JSON** and loaded with `allow_pickle=False`, so a tampered
  file can't run code. Row i of the vectors always belongs to chunk i, and mismatches raise.
- **Generated files go in `artifacts/`** (git-ignored): the index and the cache.

## 5. Open questions and known issues

- **The live app keeps running old backend code after merges** (found 2026-11-06): the page was
  new, but `search()` still gave the mock results and `get_table()` the mock table, so the page
  crashed with `KeyError: 'oxygen_pct_min'`. Community Cloud updates the files in place, but
  Python modules already loaded (our `src/` code) stay in memory. **A reboot fixed it**
  (confirmed 2026-11-06), so **after merging changes to `src/`, Nergis reboots the app**
  (Manage app → ⋮ → Reboot app). A lasting fix, so a merge alone is enough, is still open.
- **Memory on the live app is fine:** after the reboot, the first real search took 43.6 s on
  Community Cloud (model download + index build) and the app didn't crash. Later searches are
  fast.
- **Two package lists:** `pyproject.toml` + `uv.lock` (laptops, CI, Docker) and
  `app/requirements.txt` (live app). Since D07, a test fails if a `pyproject.toml` package is
  missing from `app/requirements.txt`. Versions can still differ: `requirements.txt` uses `>=`,
  so the live app may get newer versions than our tests ran on. `uv export` could generate it
  from the lock file if that ever causes trouble.
- **PyTorch is huge on Linux:** it pulls in ~4.4 GB of NVIDIA GPU libraries that neither
  Community Cloud nor our Docker image can use (no GPU), and it's most of the ~20 GB Docker
  image. Since D10 the live app loads PyTorch for search, so watch Community Cloud's 2.7 GB
  memory limit. A CPU-only PyTorch would help both, but it changes `uv.lock` for everyone, so
  it's a team decision.
- **The app's charts are built for the old mock data** (FE's file). Since D09 they get real rows,
  but `spread_rate_mm_s` is filled for only 2 of 290 rows, so "Flame spread vs. oxygen" and
  "Riskiest materials" are nearly empty, and the "Riskiest materials" caption still says "Fake
  numbers". The real data is mostly in `outcome` (273 FLEX tests). A chart redesign is FE's call.
- **`numpy` and `httpx` are imported but not listed in `pyproject.toml`**; they only arrive
  through other packages. They are listed in `app/requirements.txt`.
- **`summarize()` never sees the user's question**, only the passages. Changing that is a
  contract change.
- **Worst-case wait for a summary is about 95 s** (3 tries × 30 s + waits between them) before the
  fallback.
- **The 0.30 cutoff has no safe value with today's ranking** (2026-11-10, real model). It drops two
  of Q2's answer passages (0.295, 0.281; `tests/retest.md`). Lowering it to 0.27 (suggested in #151)
  lets "How much thrust does a rocket engine produce?" (0.2755) through, and the short query "rocket
  thrust" already gets through at 0.3267. Q9 and Q10 (not answered by the reports) score above real
  answers, so no cutoff stops them. Waiting on the team's decision about the new ranking below,
  since it would change every score.
- **Team decisions from D14-AI (#152), each needing BE work:** (1) the "keywords + best sentence"
  ranking (8 of 10): sentence vectors in the index (`store.py`, `ingest.py`), `score` becomes the
  best sentence's (contract), and a new `MIN_SCORE`. (2) Calling `experiment_in_question()` in
  `search()` when no experiment is picked (4 → 7 of 10 in the app's default run): about one line
  plus a contract note. Neither is in the sprint plan.
- **Our off-topic test questions aren't in the repo,** so the AI role can't retune the cutoff
  against them (#152). They should be committed with the next cutoff change.

### Ingest (D08)

- **Steps:** reports (`docs/reports/` + `data/sources.csv`) → `data/processed/chunks.jsonl`
  (committed) → `artifacts/index/` (git-ignored). These are the same files the AI scripts
  `scripts/day7_chunk_reports.py` and `scripts/day8_embed_chunks.py` write, so either way of
  building gives the same result.
- **Skip finished steps:** a step is skipped when its output is newer than all of its inputs
  (file times). Chunking's inputs include `chunking.py` itself, so changing the chunk size
  rebuilds. Changing the embedding model (`EMBED_MODEL`) is **not** detected: run with `--force`.
- **Not `make ingest`** as the plan says: `make` isn't installed on Windows (or in our WSL) by
  default, and a Python command works for everyone.
- **Tested on 2026-11-05 with the real reports:** 18 chunks, then 18 × 384 vectors in ~7–12 s
  (mostly loading the model). A second run skips both steps, and touching a report rebuilds both.
  Rebuilding `chunks.jsonl` gives the same content, so Git sees no change.

### Real `get_table()` (D09)

- **Reads `data/master.csv` with pandas** on every call (290 rows, so it's fast). The columns are
  in `docs/contract.md` §3 (v1.2).
- **Filters:** `experiment`, `material` and the new `material_category` match exactly. For oxygen,
  a row matches when its range overlaps the filter's range, so FLEX-2's 17–30 % rows still show for
  a 20–25 % filter.
- **Validated:** unknown keys, blank text, a non-number oxygen value (`True` included) and
  `oxygen_min > oxygen_max` raise `ValueError`. An unknown value (e.g. `"BASS"`) just gives `[]`.
- **Empty cells come back as `None`**, never `NaN`.
- **The app had to change in the same PR:** it read `oxygen_pct`, which no longer exists, and
  `tests/test_app.py` would have failed. Only the slider range and the scatter chart's column names
  changed (FE's file, agreed with FE). Chart design stays with FE (§5).

### Real `search()` (D10)

- **`search()` calls `retrieval.find_passages`** on `artifacts/index/` and returns the top 5
  (contract v1.3), each with its chunk's `experiment`.
- **The index is built on first search** (team decision): if it's missing (every fresh deploy,
  since `artifacts/` isn't in Git) or older than `chunks.jsonl`, `search()` embeds the committed
  `chunks.jsonl` once. Nothing generated is committed, and the index can't fall behind the chunks.
- **A lock makes sure two visitors searching at once build it only once.** The test for it was
  checked: without the lock it fails every time.
- **Timing (2026-11-06, real model, fresh index):** first search 14.4 s (loading the model +
  building the index), the next one 0.1 s. The app shows its "Searching the reports..." spinner
  meanwhile.
- **Tests never load the real model:** `tests/conftest.py` gives every test a small fake model
  (word counts) and a throwaway index folder, so CI needs no download and writes nothing into the
  repo. Checked by running the suite offline with an empty model cache.

### Speed (D11)

- **Every backend call is timed:** `search()`, `get_table()` and `summarize()` each call
  `speed.record()`, which writes a log line and one JSON line to `artifacts/speed.log`
  (git-ignored). Questions are cut to 100 characters there. A broken log file never breaks a call.
- **Visible to everyone (team decision):** the app shows "Searched in 0.12 s" under the results
  (3 lines in FE's file). The report command lists the slowest calls:
  `uv run python -m flame_in_freefall.speed` (`--top 10` for more).
- **Repeated questions come from memory:** `search()` uses `cache.memo` (from D03), keyed by the
  cleaned-up question (capitals and spaces ignored) and `k`. Callers get a copy, so changing one
  result can't change what's remembered. The index check still runs first (a few file-time
  comparisons), and a rebuild empties the cache, so an out-of-date answer is never served.
- **The cache lives in memory** until the app restarts (every deploy). It isn't size-limited, which
  is fine for a hackathon's traffic.
- **Measured on 2026-11-06 (real model, existing index):** first search 8.6 s (loading the model),
  another question 0.7 s, the same question again 0.000 s (cached), `get_table()` 0.014 s.

### Experiment filter (D12)

- **`search(query, k=5, experiment=None)`** (contract v1.4) passes the filter to Nathan's
  `find_passages`, which keeps only that experiment's chunks *before* ranking, so all k results
  come from it. Without a filter it works exactly as before.
- **An unknown experiment raises `ValueError`** and lists the valid names (from `retrieval.py`), so
  a typo like `"Saffire"` doesn't look like "no results". `get_table()` returns `[]` for unknown
  values instead, because "no rows" is a normal table answer. Blank or non-text values raise too.
- **The filter is part of the cache key**, so filtered and unfiltered answers are remembered
  separately (checked in `tests/test_search.py` with the speed log).
- **The app uses it since D12-FE (#147):** the sidebar's Experiment choice also filters search.

### Edge cases and "no match" (D13)

- **Probing found crashes instead of clear errors:** `search(5)` gave `AttributeError`,
  `search(k="3")` a `TypeError`, `search(k=True)` was accepted as k=1, `summarize(None)` or a
  passage without `"text"` gave `TypeError`/`KeyError`, and `get_table("FLEX")` complained about
  unknown filters `E`, `F`, `L`, `X`. All now raise `ValueError` with a plain message.
- **"No match" for search (team decision):** `search()` leaves out results scoring under
  `api.MIN_SCORE = 0.30`, so an off-topic question returns `[]` and the app says "No matching
  passages found". Measured with the real model on 16 questions: answerable ones scored 0.42–0.69,
  clearly off-topic ones −0.01–0.26 (pizza, World Cup, rocket thrust…). "How do batteries catch
  fire in phones" scored 0.39 and still gets results, which is fine (it's about fire). **Retune
  `MIN_SCORE` if the embedding model or the chunking changes**, since the scores move with them.
- **Tests turn the cutoff off** (`tests/conftest.py`), because the fake test model scores
  differently. The "no match" tests turn it on themselves.
- **All edge cases in one place:** `tests/test_api_edge_cases.py`, grouped by function.

### End-to-end check (D14)

- **Two versions of the same path.** `tests/test_end_to_end.py` runs in CI with the fake model.
  `uv run python scripts/day14_end_to_end.py` uses the real model (about 18 s once the model is
  downloaded) and is the only one that exercises `MIN_SCORE`. Both write only to temporary folders.
- **What the tests guard is the joins between steps:** `search()` uses the index ingest built
  instead of building its own, and every experiment name in `sources.csv` has rows in
  `master.csv`, so renaming one in only one file now fails CI.
- **No row counts or scores in the tests,** so DAT can add rows without breaking them.
- **Each check was confirmed to fail when broken** (on a scratch copy): an experiment renamed only
  in `master.csv`, `search()` always rebuilding, and the script with the cutoff turned off.
- **Known, not a BE bug:** "What oxygen levels and pressures were used in the FLEX-2 chamber?"
  ranks a FLEX chunk first with no filter, so following its experiment shows FLEX rows. It's Q4 in
  `tests/retrieval.md` (AI's retrieval work, D14-AI). The check only proves the path works, not
  that the top passage is the right one.

### Sources in output (D15)

- **The shape was already right on the normal paths;** probing found the edges where it wasn't. A
  passage with blank text came back as a takeaway with no text, a number as text crashed with
  `AttributeError`, `source: None` was shown as the source, a Gemini reply with a number as `text`
  went straight through, and `not_found: "no"` counted as *yes*, throwing a real answer away.
  `check_summary` itself crashed on a takeaway that wasn't a dict.
- **Three layers now:** passages are checked on the way in (`api._check_passages`), Gemini's reply
  is checked in `summarizer.py` (a bad one falls back to quoting), and `api.summarize()` checks its
  own answer with `check_summary` before returning it. That last check only fails on a bug in our
  code, so it raises `RuntimeError` instead of showing a broken summary.
- **`check_summary` (D06-AI's file) got stricter:** exactly `text`, `source`, `chunk_id`, all text.
- **Shape tested:** `tests/test_summary_shape.py` runs every path (Gemini answer, nothing useful,
  timeout, two bad replies, no key, no passages) through one shape check. Each new rule was
  confirmed to fail its test when removed (on a scratch copy).
- **Plan vs contract:** the plan asks for `{takeaways: [{text, source}]}`. We keep `chunk_id` and
  `not_found` (contract v1.0), so nothing that calls `summarize()` has to change.

### Fixes after D15: the ingest test and the quoting fallback

- **Flaky ingest test (#155).** `ingest.run()` decided whether to rebuild the index by comparing
  file times. The test failed about half the time on Nergis's laptop (Windows) but passed 400 of
  400 runs on WSL. Most likely cause (never reproduced): Windows file times move in steps of about
  16 ms, so in a fast test the old index and the freshly rebuilt chunks could get the same time,
  and the index looked up to date. Now, if the chunks were rebuilt
  in this run, the index is rebuilt too, whatever the file times say. A new test pushes the old
  index's time ahead, so the tie happens on every run.
- **The quoting fallback showed fragments** (reported by Nathan in #160). With no key, or when
  Gemini fails, `summarize()` quotes one sentence per passage. Chunks overlap by 30 words, so 17 of
  the 22 chunks start in the middle of a sentence, and the old code quoted that first piece:
  "the experiment module.", "of the experiment.". Now `_first_sentence` skips a piece that starts
  with a lowercase letter, skips pieces under 4 words (list numbers, "Fig. 5."), and only takes a
  piece that ends in `.`, `!` or `?`, so the chunk's own cut-off end isn't quoted as a whole
  sentence. If a passage has no whole sentence, it's quoted as it is: never empty, never reworded.
  Checked on the real chunks: 17 fragments before, 0 after, every quote a word-for-word piece of
  its chunk, and no passage needed the whole-text case.
- **The label under the summary** (`summary_box.QUOTED_LABEL`, FE's file) says the quotes are
  "from the start of each passage", which isn't exactly true any more. Left for FE to reword.

## 6. Where the next ticket starts (FIF-D16-BE: protect the app)

**Still open from D14:** tag #149's merge commit (`bf28918`) `v0.2` once the team agrees
(`git tag v0.2 bf28918`, then `git push origin v0.2`). Pushing a tag is visible to everyone.

The D16 plan: *1) Reject empty/very long queries. 2) Rate limit. 3) Timeouts. Done when: bad input
handled.*

- **Already done:** empty, blank and non-text queries raise `ValueError` (D13), and Gemini calls
  time out after 30 s with 3 tries, then fall back (D05).
- **Still to do:** a maximum query length in `search()` (no limit today), a rate limit (one per
  visitor session would fit Streamlit), and deciding what
  "timeout" means for `search()`, whose first call after a deploy takes 15–45 s.

## 7. Rules to keep

- **Run `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q` before
  every PR**, the same steps as CI.
- **No real API keys or network in tests.** `tests/conftest.py` removes `GEMINI_API_KEY` and
  swaps in a fake embedding model for every test, and tests swap in fake clients.
- **Secrets** go in `.env` locally (git-ignored, see `.env.example`) and in Streamlit's Secrets on
  the live app, never in the repo.
- **One ticket = one branch (`feature/<TICKET-ID>`) = one small PR into `main`.** Put
  `Closes #<issue>` in the PR so the issue and Linear close on merge.
