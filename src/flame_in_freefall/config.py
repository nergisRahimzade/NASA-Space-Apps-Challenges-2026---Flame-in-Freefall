"""Day 3 (BE): one place that reads settings from environment variables.

Locally, put them in .env and launch with:  uv run --env-file .env <command>
On Streamlit Community Cloud they come from the app's Secrets settings."""

import logging
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # One object holds every setting, so other files read settings from here
    # instead of each calling os.getenv with its own default.
    # frozen=True: a setting can't be changed by accident while the app runs.
    openai_api_key: str | None  # None when no key is set (e.g. in CI, which doesn't need one)
    openai_model: str
    embed_model: str
    log_level: str


def get_settings() -> Settings:
    # Read fresh on every call, so a changed environment (or a test's monkeypatch) is picked up.
    # Each os.getenv default below is what you get when that variable isn't set.
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        embed_model=os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def setup_logging() -> logging.Logger:
    # Unlike print, every log line gets a time and a level (INFO, ERROR...),
    # and LOG_LEVEL decides which levels are shown.
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("flame_in_freefall")
