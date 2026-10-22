# Flame in Freefall

A Python project for exploring microgravity combustion experiments, with a Streamlit dashboard. The planned features include report search, AI summaries, and interactive charts.

The current app displays a title and search input. Search, summaries, and data loading are not implemented yet. You can run this starter without datasets or an API key.

## First-time setup

### 1. Install Git and uv

Install [Git](https://git-scm.com/downloads) if it is not already available. We use [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage Python, dependencies, and the virtual environment.

Install uv using the command for your operating system.

**Windows PowerShell:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS or Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reopen your terminal after installation, then check:

```text
git --version
uv --version
```

### 2. Clone the repository

On the GitHub repository page, select **Code** and copy the HTTPS clone URL. Replace `REPOSITORY_URL` below with that URL:

```text
git clone REPOSITORY_URL flame-in-freefall
cd flame-in-freefall
```

If you already cloned the repository, open a terminal in that folder and run `git pull` instead. Run all remaining commands from the project root, where `pyproject.toml` is located.

### 3. Install Python and the project dependencies

```text
uv python install 3.12
uv sync --locked
```

The project selects Python 3.12 through `.python-version`. Syncing creates your local `.venv`, installs the project and its dependencies, and includes the development tools `pytest` and `ipykernel`. `--locked` checks that `uv.lock` agrees with `pyproject.toml` and uses the recorded dependency versions. See the [uv syncing documentation](https://docs.astral.sh/uv/concepts/projects/sync/).

The first installation can take a while because the machine-learning dependencies are large. You do not need to run `uv init`, install each package separately, or manually activate the environment when using `uv run`.

### 4. Create the empty working folders

Git tracks files, so empty folders do not arrive with a clone. Also, `artifacts/` is intentionally ignored. Run this command in PowerShell, macOS, or Linux to create the working folders; existing folders and files are preserved:

```text
uv run --locked python -c "from pathlib import Path; folders = ['data/raw', 'data/processed', 'data/reports', 'artifacts', 'notebooks', 'scripts', 'tests', 'evaluation', 'docs']; [Path(folder).mkdir(parents=True, exist_ok=True) for folder in folders]"
```

This creates directories only. NASA data, reports, and generated embeddings will need to be downloaded or built separately when those workflows are implemented.

### 5. Start the dashboard

```text
uv run --locked streamlit run app/streamlit_app.py
```

Open the local URL printed in the terminal, usually `http://localhost:8501`. You should see **Flame in Freefall** and a search input. Stop the app with **Ctrl+C**.

## After pulling team changes

From the project root, run:

```text
git pull
uv sync --locked
uv run --locked streamlit run app/streamlit_app.py
```

Sync after pulling so your environment picks up dependency changes. If a new empty working folder is added, follow its setup instructions; Git will not create it until it contains a tracked file.

## Project structure

```text
flame-in-freefall/
|-- app/streamlit_app.py       # Streamlit dashboard entry point
|-- src/flame_in_freefall/    # Reusable Python package
|-- data/
|   |-- raw/                 # Original experiment datasets
|   |-- processed/           # Cleaned tables
|   `-- reports/             # Source reports and abstracts
|-- artifacts/               # Generated chunks, embeddings, and indexes
|-- notebooks/               # Exploratory analysis
|-- scripts/                 # Future download and processing commands
|-- tests/                   # Automated tests as they are added
|-- evaluation/              # Retrieval and summary test questions
|-- docs/                    # Glossary, data notes, and demo materials
|-- .python-version          # Python version selected for development
|-- pyproject.toml           # Project metadata and dependency declarations
|-- uv.lock                  # Resolved dependency versions
`-- README.md
```

## Adding dependencies

When your work requires a new package, use:

```text
uv add PACKAGE_NAME
```

For a development-only tool, use `uv add --dev PACKAGE_NAME`. Commit both `pyproject.toml` and `uv.lock` so teammates receive the update on their next pull and sync. Commit `.python-version` too when intentionally changing the team's Python version. See the [uv project guide](https://docs.astral.sh/uv/guides/projects/).

Keep `.venv/`, API keys, and generated artifacts out of Git. The existing `.gitignore` excludes `.venv`, `.env` files, `.streamlit/secrets.toml`, and `artifacts/`. The starter does not load `.env` files; future AI integration should document how to configure its required environment variables.

## Troubleshooting

| Problem | Action |
| --- | --- |
| `uv` or `git` is not recognized | Finish installing the tool and reopen your terminal, including any terminal inside your editor. |
| `pyproject.toml` or `app/streamlit_app.py` cannot be found | Change into the `flame-in-freefall` repository root before running commands. |
| A Python package cannot be imported | Run `uv sync --locked`, then launch commands with `uv run --locked` to use the project environment. |
| `uv sync --locked` says the lockfile is out of date | Pull the latest changes. If it still fails, the teammate who changed dependencies should run `uv lock` and commit the matching `pyproject.toml` and `uv.lock`. |
| Your editor reports missing imports | Select the interpreter at `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on macOS/Linux. |
| Some folders are missing after cloning | Run the working-folder command in step 4. Empty directories are not stored in Git. |
