# Days 1–3: AI + Backend guide, with the "why" for every step

For the team repo, on Ubuntu (WSL) + VS Code. New files: `day1-3-ai-backend-files.zip`.

## First, the idea behind Days 1–3

```
Day 1  BE: contract + fake data + CI        AI: prove the model and the key work
Day 2  BE: fake versions of the 3 functions  AI: cut text into chunks
Day 3  BE: settings, cache, logging          AI: turn chunks into numbers
                     │
                     ▼
Days 4–11: fake pieces get swapped for real ones, one at a time
```

**Why work like this?** Four people can't wait on each other. Real NASA data won't be clean until about Day 9. If Backend publishes the *shape* of the data on Day 1, plus fake data in that shape, then AI, Frontend and Data can all build at the same time. Later the real thing drops in, and nobody else has to change their code.

## Tools in this repo, and why each one is there

| Tool | What it does | Why we use it |
|---|---|---|
| **uv** | Installs Python and packages, and runs commands inside the project's environment | One command (`uv sync --locked`) gives every teammate *exactly* the same versions, recorded in `uv.lock`. That ends "it works on my machine". |
| **`uv run ...`** | Runs a command using the project's `.venv` | You don't have to remember to activate the venv, so you can't accidentally use the wrong Python. |
| **Git branches + pull requests** | Each ticket goes on its own branch, then gets reviewed | `main` always works, and a second pair of eyes catches mistakes before everyone pulls them. |
| **pytest** | Runs automatic checks | It proves the code still does what the contract promises after every change. |
| **Ruff** | A linter (finds bugs and unused imports) and a formatter (one code style) | Clean diffs: pull requests show real changes, not spacing arguments. |
| **CI (GitHub Actions)** | Runs Ruff and pytest on GitHub for every push | It catches problems even when someone forgets to run the tests locally. |

---

## Day 1

### FIF-D01-BE: Repo and contract

**Step 1. Clone with SSH, sync, and open in VS Code.**
```bash
cd ~
git clone git@github.com:<owner>/<repo>.git flame-in-freefall
cd flame-in-freefall
uv sync --locked
code .
```
- `cd ~`: WSL is much faster with files in your Linux home folder than under `/mnt/c` (Microsoft's own advice).
- **SSH URL:** GitHub stopped accepting passwords for Git. Once your SSH key is added, pushing just works.
- `uv sync --locked`: builds `.venv` from `uv.lock`. `--locked` refuses to run if `pyproject.toml` and `uv.lock` disagree, so you never end up with versions that are silently different.
- `code .` from Ubuntu: VS Code runs *inside* Linux (the "WSL: Ubuntu" label at the bottom left), so it uses the same Python and files as your terminal.

**Step 2. Unzip the new files into the repo root.**
- They are placed exactly where the repo expects them: `src/flame_in_freefall/`, `tests/`, `docs/`, `data/mock/`, `.github/workflows/`.

| File | Why it exists |
|---|---|
| `docs/contract.md` | The team's agreement on function inputs and outputs. It's what lets four people build in parallel. Changing it needs a pull request, so nobody breaks others by surprise. |
| `data/mock/chunks.mock.jsonl` | Fake report pieces, so AI and FE can build search screens before real reports exist. JSONL (one JSON object per line) can be read line by line and appended to easily. |
| `data/mock/master.mock.csv` | Fake experiment table, so FE can build charts and filters now. It uses the real column names, so the swap on Day 9 is painless. |
| `.github/workflows/ci.yml` | Makes GitHub check every push. |
| `.env.example` | Shows teammates *which* settings exist, without containing a real key. |

**Step 3. `uv add --dev ruff`**
- CI runs Ruff, so it must be in the project.
- `--dev` means it's a tool for developers, not something the app needs to run.
- `uv add` updates both `pyproject.toml` and `uv.lock`, so teammates get it on their next `uv sync`.

**Step 4. Paste the pytest and Ruff settings into `pyproject.toml`.**
- `pythonpath = ["src"]` lets tests `import flame_in_freefall` straight from the `src/` folder.
- `testpaths = ["tests"]` means pytest only looks in `tests/`, which is faster and won't pick up random notebook files.
- `line-length = 100` and `target-version = "py312"` match the team's Python 3.12. `extend-exclude = ["notebooks"]` skips experimental notebooks.
- `select = ["E", "F", "I"]` turns on three rule groups:
  - **E**: style errors
  - **F**: real bugs, such as undefined names and unused imports
  - **I**: import sorting

  That catches the important things without nagging.

**Step 5. `uv run ruff format .`, then `ruff check .`, then `pytest -q`.**
- **Format first**, so the CI "format check" step passes on day one.
- `app/streamlit_app.py` changes slightly: Ruff removes an invisible byte-order mark at the top. It's harmless, but tell FE so they understand the diff.
- `pytest -q` should print `19 passed`. That proves the files landed in the right places and imports work.

**Step 6. Branch → commit → push → pull request.**
```bash
git switch -c feature/FIF-D01-BE
git add .
git status
git commit -m "FIF-D01-BE: contract, mocks, CI, ruff"
git push -u origin feature/FIF-D01-BE
```
- **A branch per ticket** keeps `main` working. The name ties the work to the ticket on the board.
- **`git status` before committing** is your last chance to spot `.env`. A leaked key can be found and abused within minutes of being pushed to a public repo.
- **`-u origin ...`** links your local branch to GitHub, so later you just type `git push`.
- **A pull request** gives a teammate a chance to review, and makes CI run *before* the merge.

**Step 7. Protect `main`.**
- **Require a pull request:** nobody, including you, can push broken code straight to `main` by accident.
- **1 approval:** every change gets a second reader.
- **Require the `test` status check:** a red CI blocks the merge, so `main` always passes its tests.
- This is free on public repos. Private repos need GitHub Pro or Team.

**Step 8. (Team decision) Use CPU-only PyTorch.**
- sentence-transformers needs PyTorch. On Linux, the default PyTorch from PyPI includes GPU (CUDA) libraries, which are several GB.
- A WSL laptop won't use the GPU for this project, so that download just wastes time and disk space, and it slows CI too.
- Pointing `torch` at PyTorch's CPU index gets a far smaller build.
- It's a team decision because it changes `uv.lock` for everyone.

**Done when:** CI is green, and the contract, mocks and CI are merged to `main`.

### FIF-D01-AI: Prove the AI tools work

**Step 1. `cp .env.example .env`, then paste your key.**
- The OpenAI key is a password that costs money. It lives only in `.env` on your machine.
- `.gitignore` already lists `.env`, so Git never uploads it.
- Copying the example means you get every setting name right.

**Step 2. `uv run --env-file .env python scripts/day1_check_ai.py`**
- `--env-file .env` makes uv load your key into the environment for that one command. The code reads it with `os.getenv`, so no extra package is needed.
- **Embedding check:** `(2, 384)` means 2 sentences each became 384 numbers. The `all-MiniLM-L6-v2` model always outputs 384 numbers. Seeing that number proves the model downloaded and runs.
- **Similarity score:** two sentences about the same idea should score clearly above zero. This is the core trick behind search.
- **One test prompt:** proves your key, your account credit and your network all work, *before* you build anything on top of them.
- **Why `all-MiniLM-L6-v2`?** It's small and fast on a laptop CPU, it's free, and it's good enough for searching reports.
- **Why `gpt-5-mini` as the default?** Summaries don't need the biggest model, and a small one keeps hackathon costs low. You can change it in `.env` without touching code.

**Done when:** both checks print without errors.

---

## Day 2

### FIF-D02-BE: Fake versions of the three functions

**What:** `src/flame_in_freefall/api.py` contains `search()`, `summarize()` and `get_table()`. They return fake data in the exact shape the contract promises.

**Why:**
- **Stubs unblock everyone.** FE can wire the search bar to `search()` today, before real search exists on Day 10.
- **Fixing the shape now prevents rework.** If FE builds against `{"id", "text", "source", "page", "score"}`, real search must return that too.
- **Each design detail has a reason:**

| Detail | Why |
|---|---|
| `score` is included and sorted best-first | FE can show a relevance badge, and the user sees the best match first. |
| An empty query raises `ValueError` | Fail loudly on bad input instead of spending money on a blank search. |
| No passages gives `{"takeaways": [], "not_found": True}` | The AI must say "not found" instead of making things up. Here the rule is built into the data shape. |
| Every takeaway carries a `chunk_id` | Every claim can be traced to a source, which is the plan's anti-hallucination rule. |
| An unknown filter raises `ValueError` | A typo like `"colour"` fails right away instead of silently returning the whole table. |

**Check:** `uv run pytest tests/test_contract.py -q`
- These tests are the contract in code form. When you write the real `search()` on Day 10, the same tests must still pass. That's how you know you didn't break FE.

### FIF-D02-AI: The chunker

**What:** `chunk_text(text, size=200, overlap=40)` and `chunk_document(pages, source, doc_id)`.

**Why cut text into chunks at all?**
1. **Model limit:** MiniLM only reads the first 256 word pieces of any input and silently drops the rest. A whole report would be mostly ignored.
2. **Precision:** one vector for a 40-page report blurs every topic together. A 200-word chunk is about one idea, so it matches questions much more sharply.
3. **Cost:** you send the LLM only the 3–5 best chunks, not whole reports. That's cheaper, faster, and less room for it to make things up.

**Why overlap?**
```
chunk 0: w0 w1 w2 w3
chunk 1:          w3 w4 w5 w6
chunk 2:                   w6 w7 w8 w9
```
If a key sentence falls on a boundary, the overlap means it still appears whole in at least one chunk.

**Why keep `source`, `page` and `id` on every chunk?** So every summary claim can say exactly where it came from ("BASS report, p. 3"). Judges can check it, and the Day 6 automatic citation test depends on it.

**Why test on fake docs first?** With fake text you know exactly what the chunks *should* be, so bugs are obvious. Real PDFs add messy problems (headers, broken lines) that you'd mix up with chunker bugs.

**Your part:** write 3 short fake docs and run `chunk_document` on them in a notebook. Look at the IDs, pages and overlaps.

**Check:** `uv run pytest tests/test_chunking.py -q`. It tests exact overlap, short text, empty text, that no words are lost, and that bad settings are rejected.

---

## Day 3

### FIF-D03-BE: Config, cache and logging

**`config.py`: settings in one place**
- **Why:** if five files each call `os.getenv("OPENAI_MODEL")` with their own default, they'll drift apart. With one `get_settings()`, a change happens once.
- **Why environment variables?** The same code runs on your laptop (from `.env`) and on the deployed site (from Streamlit Secrets) without edits, and keys never sit in code.

**`cache.py`: remember answers**
- **Why:** every summary costs money and takes seconds. Judges and demo viewers ask the same questions over and over. A cache makes repeats instant and free.
- **Why clean up the query first?** `"  Which MATERIAL?"` and `"which material?"` are the same question, so they should share one saved answer.
- **Why two kinds of cache?**
  - `@memo` (in memory) is the fastest, but it's lost when the app restarts.
  - `QueryCache` (JSON files in `artifacts/cache/`) survives restarts. It lives in `artifacts/` because that folder is git-ignored: cached answers are generated files, not source code.

**Logging**
- **Why:** `print` disappears in a deployed app, and you can't tell how serious a message is. `log.info` and `log.error` add a timestamp and a level.
- On Day 11 you need timing logs ("search took 0.8s") to find what's slow.

**Check:** `uv run pytest tests/test_infra.py -q`

### FIF-D03-AI: Turn chunks into numbers

**What:** `uv run python scripts/day3_embed_mock.py` saves `artifacts/mock_embeddings.npy` with shape (3, 384), plus `mock_ids.json`.

**Why:**
- **Embed once, search many times.** Embedding is the slow step. Doing it ahead of time and saving the result makes every search fast: only the question gets embedded at search time.
- **Why `.npy`?** It's NumPy's own format. It loads in milliseconds with the exact numbers, which CSV can't promise.
- **Why a separate `mock_ids.json`?** Row 0 of the vectors must map back to chunk 0's text and source. The IDs file is that link.
- **Why `normalize_embeddings=True`?** It scales every vector to length 1, which makes cosine similarity equal to a plain dot product. One matrix multiplication then scores every chunk at once.
- **Why save to `artifacts/`?** It's generated output, which anyone can rebuild with one command, so it doesn't belong in Git.

**Head start:** `retrieval.py` already has a tested `top_k()` function. Day 4 becomes: embed the question → `top_k` → look up the chunks.

---

## Every work session, and why

```bash
cd ~/flame-in-freefall
git switch main
git pull
uv sync --locked
git switch -c feature/<ticket-id>
code .
```

| Command | Why |
|---|---|
| `git switch main` + `git pull` | Start from the team's latest work, which avoids merge conflicts later. |
| `uv sync --locked` | Picks up any package a teammate added. |
| New branch per ticket | Small, separate pull requests are quick to review and easy to undo. |

## Troubleshooting

| You see | Cause → fix |
|---|---|
| `ModuleNotFoundError: flame_in_freefall` | Not running from the repo root, or the `pythonpath` setting is missing → `cd` to the root, use `uv run` |
| `ModuleNotFoundError: dotenv` | An old script from the first starter → use the new zip's scripts |
| `openai.AuthenticationError` | The key didn't load → add `--env-file .env` and check the key |
| "lockfile is out of date" | `pyproject.toml` changed without the lock → `uv lock`, commit both files |
| CI fails at "Check formatting" | Code isn't Ruff-formatted → `uv run ruff format .`, commit |
| VS Code import errors | Wrong interpreter → **Python: Select Interpreter** → `./.venv/bin/python` |
