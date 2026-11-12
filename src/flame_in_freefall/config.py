"""Day 3 (BE): one place that reads settings from environment variables.

Locally, put them in .env and launch with:  uv run --env-file .env <command>
On Streamlit Community Cloud they come from the app's Secrets settings."""

import logging
import math
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # One object holds every setting, so other files read settings from here
    # instead of each calling os.getenv with its own default.
    # frozen=True: a setting can't be changed by accident while the app runs.
    gemini_api_key: str | None  # None when no key is set (e.g. in CI, which doesn't need one)
    gemini_model: str
    # Day 16: how many summaries per minute may go to Gemini (all visitors share one key).
    gemini_calls_per_minute: int
    # Day 17: US dollars per million tokens, from Google's pricing page. None = the team hasn't
    # set a price, so usage.py reports tokens but no cost. No price is written in the code:
    # prices change.
    gemini_usd_per_m_input: float | None
    gemini_usd_per_m_output: float | None
    embed_model: str
    log_level: str


def _whole_number_above_zero(name: str, default: str) -> int:
    # Fail loudly: "ten" or "0" in a Secrets box should be an obvious error, not a silent default.
    raw = os.getenv(name, default)
    try:
        number = int(raw)
    except ValueError:
        number = 0  # reported below, with the same message as 0 or a negative
    if number <= 0:
        raise ValueError(f"{name} must be a whole number above 0, got {raw!r}")
    return number


def _optional_price(name: str) -> float | None:
    # Unset or blank = no price (None). A typo like "free" or a negative price fails loudly.
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        price = float(raw)
    except ValueError:
        price = -1.0  # reported below, with the same message as a negative
    # Infinity (including float overflow) would turn logged costs into inf or nan.
    if not math.isfinite(price) or price < 0:
        raise ValueError(f"{name} must be a finite number of US dollars, 0 or more, got {raw!r}")
    return price


def get_settings() -> Settings:
    # Read fresh on every call, so a changed environment (or a test's monkeypatch) is picked up.
    # Each os.getenv default below is what you get when that variable isn't set.
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        # "latest" alias: follows Google's newest Flash model until the team picks a fixed one.
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        gemini_calls_per_minute=_whole_number_above_zero("GEMINI_CALLS_PER_MINUTE", "10"),
        gemini_usd_per_m_input=_optional_price("GEMINI_USD_PER_M_INPUT"),
        gemini_usd_per_m_output=_optional_price("GEMINI_USD_PER_M_OUTPUT"),
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
