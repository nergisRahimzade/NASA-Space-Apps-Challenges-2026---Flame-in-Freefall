# Day 7 (BE): run the app in a container, as a repeatable deploy and the backup host if
# Streamlit Community Cloud fails (be_notes.md). Installs from uv.lock, the exact versions
# our tests run on.
#   Build:  docker build -t flame-in-freefall .
#   Run:    docker run --rm -p 127.0.0.1:8501:8501 --env-file .env flame-in-freefall
#   Open:   http://localhost:8501
# 127.0.0.1 = only this computer can open it (without it, other devices on the network can).
# Without a .env (no key yet), leave out --env-file; summaries then quote the passages.
# First build: ~14 min and a ~20 GB image (PyTorch's GPU libraries); later builds reuse layers.

FROM python:3.12-slim

# uv from its official image, the same version as on our laptops.
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app
# Compile .py files while building (faster start); copy files instead of linking them,
# because links don't work across Docker's layers.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Packages first, in their own layer: they change rarely, so Docker reuses this slow step
# when only our code changes. --no-dev: pytest and ruff aren't needed to run the app.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Then our code, and install our own package.
COPY . .
RUN uv sync --locked --no-dev

# Put the environment's programs (python, streamlit) first on the PATH.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501
# Docker asks every 30 s whether the app is alive. Inside the container there's no sign-in
# redirect (unlike the live URL), so Streamlit's own health endpoint answers directly.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4)"

# 0.0.0.0: accept connections from outside the container; headless: don't try to open a browser.
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
