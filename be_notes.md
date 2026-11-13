# BE notes: what's built and how it runs (Days 1–18, FIF-D01-BE … FIF-D18-BE)

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
| fix (D05) | The quoting fallback quotes the first full sentence, not a fragment | `summarizer.py`, `tests/test_summarizer.py` | #165 |
| D16-BE | Protect the app: 300-character question limit, Gemini calls limited to 10 a minute, a summary that never comes ends in ~32 s; contract v1.9 | `api.py`, `rate_limit.py`, `summarizer.py`, `config.py`, `docs/contract.md`, `tests/test_rate_limit.py`, `tests/test_api_edge_cases.py`, `tests/test_summarizer.py`, `tests/test_infra.py`, `tests/conftest.py`, 2 lines in `app/streamlit_app.py` (FE's file) | #167 |
| D17-BE | Cache summaries (a repeat is instant, free and not counted by the limit); log every Gemini call's tokens and cost; contract v1.10 | `summarizer.py`, `usage.py`, `api.py`, `config.py`, `docs/contract.md`, `.env.example`, `tests/test_summary_cache.py`, `tests/test_usage.py`, `tests/test_summarizer.py`, `tests/test_day16_script.py`, `tests/conftest.py`, `scripts/day16_test_summaries.py` (AI's, 1 line) | #169 |
| D18-BE | Monitoring: an error log (why a call failed) and an uptime check run on a schedule by GitHub | `error_log.py`, `uptime.py`, `.github/workflows/uptime.yml`, `api.py`, `summarizer.py`, `tests/test_error_log.py`, `tests/test_uptime.py`, `tests/test_app.py`, `tests/conftest.py` | FIF-D18-BE PR |

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
| `summarizer.py` | Calls Gemini for takeaways; falls back to quoting passages on any failure, or when the call limit is reached; remembers the answers Gemini gave (D17) | in use through `api.summarize()` |
| `usage.py` | Logs the tokens (and cost, if a price is set) of every Gemini call to `artifacts/usage.log`; `uv run python -m flame_in_freefall.usage` reports the total | in use since D17 |
| `error_log.py` | Writes every failed call to `artifacts/errors.log` (`error`, `fallback`, `limit`); `uv run python -m flame_in_freefall.error_log` reports them | in use since D18 |
| `uptime.py` | Asks the live app's health address whether it is up, asleep or down; the exit code feeds the scheduled GitHub job | run by `.github/workflows/uptime.yml` since D18 |
| `rate_limit.py` | `RateLimiter`: at most N calls in any window, safe with many visitors at once | used by `summarizer.py` since D16 (10 a minute) |

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
- **Health check (D07; partly outdated, see the D18 measurement below):** the live URL can't be
  checked from CI the way the Docker image is. `/_stcore/health` redirects
  automated requests to a Streamlit sign-in page, and `/healthz` answers `{"status":"ok"}` even
  for an app name that doesn't exist (it's the hosting platform, not our app). So the app is
  checked **before** it can reach `main`: `tests/test_app.py` runs the real
  `app/streamlit_app.py` with Streamlit's `AppTest` in CI and fails on a crash or a red error
  box. Tried on purpose: a failing `get_table()` and renamed `master.csv` columns both fail it.
- **Measured again on 2026-11-13 (D18):** the *app's own* health address does work from outside,
  but under `/~/+/`: `https://crc-flame-in-freefall.streamlit.app/~/+/_stcore/health` answered the
  plain text `ok` in 0.4 s while the app was awake. Without `/~/+/`, `/_stcore/health` answers the
  platform's wrapper page (HTTP 200, HTML), as found in D07. An app name that doesn't exist answers
  404. That `ok` means Streamlit's server runs, **not** that the page works (D18 below), so
  `tests/test_app.py` stays the check for the page. **Not observed:** what a sleeping app answers;
  we could not make it sleep.

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
- **Worst-case wait for a summary is about 32 s since D16** (2 tries × 15 s + a 1–2 s wait
  between them) before the fallback; it was about 95 s. **Measured with a real key on
  2026-11-11:** `gemini-flash-lite-latest` answered 3 real summaries in 1.2, 6.0 and 8.7 s, inside
  15 s. The default `gemini-flash-latest` answered every call with `503 UNAVAILABLE` ("high
  demand") or `504`, and each summary fell back to quotes after 8–18 s, the same overload the AI
  role saw on 2026-11-10. If that keeps happening, the team may want `GEMINI_MODEL =
  "gemini-flash-lite-latest"` in the app's Secrets (an open question in `ai_notes.md` too).
- **Every widget change re-runs `summarize()`** (checked with AppTest): Streamlit re-runs the whole
  page when a visitor moves a slider, and with a question in the box that's another Gemini call.
  Before D17 a visitor adjusting filters spent a call each time and could use up the 10-a-minute
  limit on their own. **Fixed in D17:** the repeats are answered from the summary cache
  (`tests/test_summary_cache.py` moves the slider in the real page and counts Gemini calls: 1).
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
- **The page never calls `setup_logging()`** (FE's file, found in D18). Streamlit leaves Python's
  logging alone, so on the live host only WARNING and ERROR lines reach the log (no time), and every
  INFO line (the speed and usage lines) is dropped. D18's ERROR line carries its own time, so the
  error log works anyway. One line in the page would fix the rest; it's Nathan's call.
- **A sleeping app fails the uptime check** (D18). Until someone visits, the check reports "asleep"
  and every scheduled run fails: up to 48 emails a day if the check's own requests don't count as
  traffic (Streamlit's docs don't say). Counting "asleep" as a pass with a warning is a one-line
  change; it's the team's call. A sleeping app's real answer was never observed (D18 section).

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

### Protect the app (D16)

Plan: *1) Reject empty/very long queries. 2) Rate limit. 3) Timeouts. Done when: bad input
handled.* Empty queries already raised since D13.

- **Long questions:** `api.MAX_QUERY_CHARS = 300`, counted after trimming spaces. `search()` and
  `summarize(question=...)` raise `ValueError("query is too long: 412 characters, the limit is
  300")`. Our longest test question is under 100 characters, and MiniLM reads only about 200 words,
  so a longer text would be silently cut off. The app's search box has `max_chars=300` (2 lines in
  FE's file), so visitors can't type past it and never see the error.
- **Rate limit:** `rate_limit.RateLimiter(max_calls, per_seconds)` is a sliding window behind a
  lock, because Streamlit runs each visitor in its own thread. `summarizer.py` keeps one for the
  whole process: **10 Gemini summaries a minute, shared by every visitor** (`GEMINI_CALLS_PER_MINUTE`,
  a whole number above 0 or `get_settings()` raises). All visitors use one free-tier key, so this
  protects the key's quota. Over the limit, `summarize()` doesn't fail: it quotes the passages, the
  same path as "no key". Calls that never reach Gemini (no passages, no key) don't count, and a
  call counts once even if the client then retries it.
- **The limit is per process, not per visitor.** One person clicking fast can use up the minute for
  everyone else. A per-visitor limit belongs in the page (FE's file, `st.session_state`), and
  `RateLimiter` can be reused there. Community Cloud runs one process per app, so the limit
  isn't multiplied by several copies.
- **Search has no limit and no timeout.** It runs locally and repeated questions are cached, and
  its only slow case is the one-time index build after a deploy (15–45 s), which can't be stopped
  half-way safely; the page already explains that wait (D16-FE).
- **Timeouts:** Gemini calls now give up after 15 s per try with 2 tries (`TIMEOUT_MS`, `ATTEMPTS`),
  so the worst case is about 32 s, as the page says ("up to 30 seconds"). The SDK waits 1–2 s
  between tries. Measured with a real key: answers came in 1.2–8.7 s on the lite model (§5).
- **A wrong `GEMINI_CALLS_PER_MINUTE` fails loudly, and widely.** Every `get_settings()` call
  raises, and `embedding.py` uses it too, so **search** breaks as well as summaries: the page shows
  "search failed" and the log says `GEMINI_CALLS_PER_MINUTE must be a whole number above 0, got
  'ten'`. On purpose (a wrong limit should be noticed at once, not run quietly), but whoever edits
  the app's Secrets should know a typo there takes the whole search down.
- **Tests:** `tests/test_rate_limit.py` (fake clock; also a thread test that fails every time if
  the lock is removed), plus limit, setting and search-box tests. `conftest.py` gives every test a
  fresh limiter, because the real one lives for the whole process and the 11th test that reached
  Gemini would otherwise be told "limit reached".
- **Since D15, from teammates:** BASS-II is the 4th experiment (419 rows, 22 chunks, contract
  v1.8) and `master.csv` is frozen as data v1.0 (`data/freeze.json`, checked by CI). `summarize()`
  takes the user's `question` (v1.7, prompt v2).
- **Seen while building this, not fixed (needs a contract change):** the page labels a summary
  "AI-generated" whenever a key is set (`bool(get_settings().gemini_api_key)`), not by what
  `summarize()` did. When Gemini fails or the call limit is reached, quoted text gets the AI label.
  Fixing it needs a new field in `summarize()`'s result, so the team should agree first.

### Summary cache and usage log (D17)

Plan: *1) Cache by query. 2) Log cost per call. Done when: repeat is instant.* `search()` has been
cached since D11; this adds the slow, paid call.

- **What is remembered:** the answers Gemini gave, including a real "not found". **Never the
  quoting fallback**: after a short outage or a limit hit, the next visitor should get a real
  summary, not stuck quotes. A reply that fails our checks is a fallback too, so it isn't
  remembered.
- **The key:** the question (`cache.normalize`: capitals and spaces ignored, as for `search()`),
  every passage's **id, text, source and page** (as text, the way Gemini sees it) in order, the prompt file's name, and the model.
  The plan said ids; text also matters because a re-ingested report keeps its ids but not its words.
  Source and page are sent to Gemini too. Including them prevents a corrected source from reusing
  a stale citation and failing `api.summarize()`'s contract check.
  Editing a prompt file without renaming it does *not* change the key: a prompt change needs a new
  file name (v3, as before) or a reboot, which empties the cache.
- **A hit is free and instant:** it returns before the rate limiter, so it counts nothing, and it
  works even when the minute's limit is used up. It comes *after* the "no key" check: the page
  labels a summary by whether a key is set, so with no key a remembered Gemini answer would be
  shown as "quoted word for word". With no key, the passages are really quoted. `api.summarize()` marks it `cached` in the speed
  log, like `search()`.
- **Size and safety:** at most 256 answers, the oldest dropped first, behind a lock (Streamlit
  runs each visitor in its own thread). A caller gets a copy, so changing its answer can't change
  the memory. It lives in the app's process, so a reboot empties it. Two visitors asking something
  new at the same moment both go to Gemini (the lock guards the memory, not the call); the second
  answer replaces the first, which is harmless.
- **Questions that differ only in capitals share an answer**, though Gemini would see slightly
  different text. Same rule as `search()`; fine for these reports.
- **Usage log:** `usage.record()` writes one JSON line per real Gemini reply to
  `artifacts/usage.log` (git-ignored): time, model, `input_tokens`, `output_tokens` (from
  `usage_metadata`; `None` when Google sends none, never 0) and `cost_usd`. It's written even when
  the reply turns out to be unusable, because that call was paid for. Cache hits and quoted
  summaries are not logged: they cost nothing.
- **Cost needs a price, and the code has none** (prices change): set `GEMINI_USD_PER_M_INPUT` and
  `GEMINI_USD_PER_M_OUTPUT` (US dollars per million tokens, from Google's pricing page; leaving
  them out is fine, and "0" is allowed for a free tier). Without both, `cost_usd` is `None` and the
  report says cost is unavailable because a price or token count was missing when calls ran.
  Log entries don't store which cause applies, so the report doesn't guess from today's settings.
  A price that isn't a finite number, or is negative, fails loudly in
  `get_settings()`, so, as with the call limit in D16, a typo in the Secrets takes search down too.
  The cost is worked out when the call is logged, with the prices of that moment. Rejecting infinite
  prices (including numeric overflow such as `1e309`) prevents `inf` or `nan` costs in the log.
- **A damaged line in `usage.log`** (the app stopped mid-write) is skipped with a warning, so the
  report still covers every other call.
- **`artifacts/` on the live app is wiped on every reboot**, so `usage.log` there only covers the
  time since the last one. To keep a total, read it from the host before rebooting.
- **For the AI role:** `scripts/day16_test_summaries.py` clears the summary cache before each
  question (1 line), because a remembered answer would make no Gemini call and leave no reply to
  record. Its two runs per question can send identical passages.
- **Tests:** `tests/test_summary_cache.py` (28) and `tests/test_usage.py`. 26 deliberate
  breakages of the new code were each caught by a test; the first run missed 5 (an id-only key,
  remembering before the checks, dropping an entry on a re-store, the size constant and the
  lock), so those got their own tests. `conftest.py` empties the cache and points `USAGE_LOG` at
  a throwaway file for every test. Three old limit tests in `test_summarizer.py` now send
  different questions, because a repeat is no longer counted.
- **Review regressions:** 14 additional cases failed before the review fixes: source and page
  corrections, unknown or partial costs with configured prices, and infinite prices in either
  setting. They cover the stale-source crash, misleading report messages, and non-finite costs.
  A second review added tests for: a remembered answer with no key set, a page value that isn't a
  plain number, a damaged usage-log line, and threads filling the cache past its limit.

### Monitoring (D18)

Plan: *1) Error log. 2) Uptime check. Done when: Alerts work.*

- **Why an error log:** the page catches every failure of `search()` and `summarize()` and shows a
  red box, and nothing wrote the reason down. Now `api.py` records an exception before it leaves
  `search()`, `summarize()` or `get_table()`, then raises it unchanged (the three signatures and
  the page's behaviour are the same). Each public function calls a private body (`_search`,
  `_summarize`, `_get_table`) inside a `try/except`.
- **Three kinds of event** in `artifacts/errors.log` (one JSON line each: `at`, `call`, `kind`,
  `error_type`, `message` cut to 300 characters, `detail` cut to 100): `error` (an exception left
  the function: the visitor saw a red box), `fallback` (Gemini failed and the passages were
  quoted instead) and `limit` (the 10-a-minute limit was reached). "No key set" is **not** logged:
  it's a setup state and would add a line to every summary.
- **It must never make things worse.** `record()` never raises (a full disk is a warning, like
  `speed.py`); it does **not** read `get_settings()`, because a bad setting such as
  `GEMINI_CALLS_PER_MINUTE=ten` is one of the failures it has to write down (a test covers this);
  and it replaces the Gemini key with `<key>` if one ever shows up in a message. A wrong `call` or
  `kind` raises, because that's a bug in our code. `record_exception()` (the one `api.py` calls)
  never raises at all: if logging itself fails, it writes a warning and the visitor's real error
  is raised as before, never a different one.
- **On the live host** `artifacts/` is wiped on every reboot and nobody can open it, so the host's
  own log ("Manage app") is the error log there: `record_exception()` also writes an ERROR line
  with the time, the reason and the traceback. The traceback is built and scrubbed by our code,
  not added by Python's logging (`exc_info`), because logging would print the exception's message
  again with the key still in it; chained errors ("the direct cause...") are scrubbed too.
  Checked on the laptop with **no** logging set up (as on the host): the line and traceback
  appeared on stderr, the caller still got the `ValueError`, and the report listed the event.
- **Uptime states.** `uptime.check()` asks the app's health address first. `ok` = **up**. If that
  isn't `ok` but the page still answers 200 = **asleep** (or starting). A server error (5xx) from the
  health address = **down**, with that status, even if the platform's page in front still answers.
  Anything else (404, no answer, timeout, a broken reply) = **down**. **Asleep is unverified:** it
  is "the address exists but the app isn't saying ok", not something we saw (if a sleeping app's
  health address answers a 5xx, it shows as down). Run on 2026-11-13: the live app was UP (0.55 s,
  exit 0), a made-up app name was DOWN (404, exit 1).
- **"Up" does not mean the page works.** In Streamlit 1.66.1 the health address answers `ok`
  whenever the server is running (`Runtime.is_ready_for_browser_connection`); it never runs the
  page. A page that crashes for every visitor, like the `KeyError` on 2026-11-06, still shows as
  up. The page is checked before each merge by `tests/test_app.py`, not by this check.
- **The scheduled job** (`.github/workflows/uptime.yml`) runs the check at minutes 7 and 37 of every
  hour, by hand from the Actions tab (with an optional `url`, to prove an alert), and on PRs that
  touch the check. It uses only the standard library, so it needs no `uv sync`. A run that isn't
  *up* fails, which is what sends the email. Limits: scheduled runs can be late or skipped when
  GitHub is busy; the check shows the server answers, not that the page works or runs the newest
  code; and a sleeping app counts as a failure. Streamlit's docs say an app sleeps after 12 hours
  without traffic, and don't say whether this check's requests count as traffic. If they don't,
  every run fails while the app sleeps: **up to 48 failure emails a day** until someone visits.
- **Alerts work: not yet proven.** Two separate things to show after the merge (a workflow can only
  be started by hand once it is on `main`):
  1. *The check fails when it should:* Actions → Uptime → Run workflow with `url` set to a made-up
     address. The run must fail. Its email most likely goes to whoever clicked "Run workflow"
     (GitHub's docs say you get notified about runs you trigger), so it doesn't show who gets the
     *scheduled* alerts.
  2. *Who gets the scheduled alerts:* GitHub's docs disagree. The "Events that trigger workflows"
     page says notifications go to "the user who last modified the cron syntax in the workflow
     file"; the "Notifications for workflow runs" page says "the user who initially created the
     workflow". With the file added in our PR and merged by Nergis, which of us that is isn't
     known. Watch the first real scheduled failure (e.g. while the app sleeps) and ask Nergis
     whether she got it. Both need Settings → Notifications → Actions → "failed workflows only".
  Record the dates and who got the email here when done.
- **Tests:** `tests/test_error_log.py` (22) and `tests/test_uptime.py` (14), plus one page test
  (`tests/test_app.py`: the visitor sees the generic box *and* the log has the reason).
  `conftest.py` points the error log at a throwaway file for every test.
- **Deliberate breakages:** 30, each caught by a test. In the first round (25), 22 were caught at
  first: one breakage never ran (the mutation script's search text no longer matched the
  reformatted code), one was badly designed, and one showed a real gap (a broken HTTP reply wasn't
  tested), which got its own test. Two reviews then found three real problems, each fixed with a
  test: the Gemini key could reach the host's log through the traceback (also in a chained error),
  a problem while logging could replace the visitor's real error, and a server error from the
  health address showed as "asleep". The breakages were updated for that code (one old one no
  longer applied; six new ones).

## 6. Where the next ticket starts (FIF-D19-BE: auto deploy)

**Still open from D14:** tag #149's merge commit (`bf28918`) `v0.2` once the team agrees
(`git tag v0.2 bf28918`, then `git push origin v0.2`). Pushing a tag is visible to everyone.

**Open from D17, for the team:** future calls need `GEMINI_USD_PER_M_INPUT` and
`GEMINI_USD_PER_M_OUTPUT` (from Google's pricing page, in the app's Secrets and in `.env`) and
reported token counts to have a cost. Old entries without costs remain unknown.

**Open from D18:** Nergis reboots the app after the D18 PR (it changes `src/`, as every backend merge
did so far). After that PR is on `main`, prove the alert by hand (D18 section: "Alerts work: not yet
proven") and write the dates there.

**After the hackathon:** in a public repo, GitHub turns off scheduled workflows after 60 days
without repository activity (GitHub's docs), so the Uptime job stops by itself then. Turn it off
sooner (Actions → Uptime → "Disable workflow") if the emails aren't wanted.

The D19 plan: auto deploy (*1) CI deploy on merge. 2) Smoke test. Done when: Deploy automatic*). What
exists, and the gap:

- **Community Cloud already redeploys on every merge**, and `tests/test_app.py` is the smoke
  test that runs before a merge. The gap: the live app keeps running the *old backend code* until
  someone reboots it (§5). Streamlit only reloads modules in the page's own folder (or on
  `PYTHONPATH`), and our code is in `src/`.
- **After a merge, nothing looks at the live app.** `uptime.py` and the Uptime workflow (D18) can be
  run after each merge to `main`.

## 7. Rules to keep

- **Run `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q` before
  every PR**, the same steps as CI.
- **No real API keys or network in tests.** `tests/conftest.py` removes `GEMINI_API_KEY` and
  swaps in a fake embedding model for every test, and tests swap in fake clients.
- **Secrets** go in `.env` locally (git-ignored, see `.env.example`) and in Streamlit's Secrets on
  the live app, never in the repo.
- **One ticket = one branch (`feature/<TICKET-ID>`) = one small PR into `main`.** Put
  `Closes #<issue>` in the PR so the issue and Linear close on merge.
