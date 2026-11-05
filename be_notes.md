# BE notes: what's built and how it runs (Days 1–7, FIF-D01-BE … FIF-D07-BE)

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
| D07-BE | Repeatable deploy: Dockerfile, health checks, merge deploys | `Dockerfile`, `.dockerignore`, `tests/test_app.py` | FIF-D07-BE PR |

## 2. What each BE file does

All code is in `src/flame_in_freefall/`.

| File | Job | Status |
|---|---|---|
| `api.py` | The 3 functions everyone calls, with the exact shapes in `docs/contract.md` | `summarize()` is real; `get_table()` reads mock data until **D09-BE**; `search()` returns mock data until **D10-BE** |
| `config.py` | Reads every setting from environment variables into one frozen `Settings` | in use |
| `cache.py` | Remembers answers by question (JSON files, or in memory with `@memo`) | built, **not used yet** (D11-BE "Cache repeats") |
| `store.py` | Saves/loads the search index as `embeddings.npz` + `chunks.json` | used by the AI scripts |
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

- **Two package lists:** `pyproject.toml` + `uv.lock` (laptops, CI, Docker) and
  `app/requirements.txt` (live app). Since D07, a test fails if a `pyproject.toml` package is
  missing from `app/requirements.txt`. Versions can still differ: `requirements.txt` uses `>=`,
  so the live app may get newer versions than our tests ran on. `uv export` could generate it
  from the lock file if that ever causes trouble.
- **PyTorch is huge on Linux:** it pulls in ~4.4 GB of NVIDIA GPU libraries that neither
  Community Cloud nor our Docker image can use (no GPU), and it's most of the ~20 GB Docker
  image. Fine while the app doesn't load PyTorch. Once real search (D10) loads the embedding
  model, watch Community Cloud's 2.7 GB memory limit. A CPU-only PyTorch would help both, but
  it changes `uv.lock` for everyone, so it's a team decision.
- **Contract v1.0 is out of date with `data/master.csv`** (#126): oxygen, pressure and airflow
  are now `_min`/`_max` pairs, `outcome` is new, the experiments are FLEX-2 / Saffire-II / FLEX
  (not BASS), and some cells are empty. That's D09-BE (see `data_notes.md`, "Changes compared to
  contract v1.0").
- **`numpy` and `httpx` are imported but not listed in `pyproject.toml`**; they only arrive
  through other packages. They are listed in `app/requirements.txt`.
- **`summarize()` never sees the user's question**, only the passages. Changing that is a
  contract change.
- **Worst-case wait for a summary is about 95 s** (3 tries × 30 s + waits between them) before the
  fallback.

## 6. Where the next ticket starts (FIF-D08-BE: one command to ingest)

The plan: *1) `make ingest` runs docs → chunks → embeddings. 2) Skip finished steps. Done when:
ingest runs end to end.*

- **The pieces exist** (see `ai_notes.md` §2): `chunking.chunk_document`,
  `embedding.embed_texts` and `store.save_index`. The real documents are in `data/reports/`, with
  their names in `data/sources.csv`, and they make 18 chunks (`ai_notes.md` §6).
- **The AI steps it runs belong to the AI role** (D07-AI chunk the real docs, D08-AI embed them),
  now owned by another teammate. Agree with them where `chunks.jsonl` and the index are saved,
  so the ingest command and their scripts write the same files.
- **`make` isn't installed on Windows by default.** A Python command (e.g.
  `uv run python -m flame_in_freefall.ingest`) works for everyone; a `Makefile` could wrap it.
- **"Skip finished steps"** can compare file times: skip chunking if `chunks.jsonl` is newer
  than every report, and skip embedding if the index is newer than `chunks.jsonl`.

## 7. Rules to keep

- **Run `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q` before
  every PR**, the same steps as CI.
- **No real API keys or network in tests.** `tests/conftest.py` removes `GEMINI_API_KEY` for
  every test, and tests swap in fake clients.
- **Secrets** go in `.env` locally (git-ignored, see `.env.example`) and in Streamlit's Secrets on
  the live app, never in the repo.
- **One ticket = one branch (`feature/<TICKET-ID>`) = one small PR into `main`.** Put
  `Closes #<issue>` in the PR so the issue and Linear close on merge.
