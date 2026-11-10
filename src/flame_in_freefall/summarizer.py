"""Day 5 (BE): the real summarize(): ask Gemini for takeaways that cite their chunk.

Fails safely: with no API key, a timeout after retries, or a broken reply, it quotes the
passages instead (real text, real sources), so the app keeps working and nothing is invented.
The prompt text lives in src/prompts/summary_v1.txt (written by the AI ticket, FIF-D05-AI)."""

import json
import logging
import re
from pathlib import Path

import httpx
from google import genai
from google.genai import errors, types

from flame_in_freefall.config import get_settings
from flame_in_freefall.summary_check import check_summary

# Built from this file's location (up 1 folder = src/), so it works from any folder.
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "summary_v1.txt"
TIMEOUT_MS = 30_000  # give up on one attempt after 30 s (the Gemini client counts milliseconds)
# First try + 2 retries. The client then retries timeouts, rate limits (429) and server errors
# (5xx) itself; without retry options it would never retry.
ATTEMPTS = 3

log = logging.getLogger(__name__)

# Structured output: the model must reply with JSON in exactly this shape.
# It only gives chunk_id; we fill in source ourselves, so a source can't be made up.
# Kept to basic JSON Schema features, because Gemini supports only part of the standard.
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "takeaways": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "chunk_id": {"type": "string"}},
                "required": ["text", "chunk_id"],
            },
        },
        "not_found": {"type": "boolean"},
    },
    "required": ["takeaways", "not_found"],
}


def _get_client(api_key: str) -> genai.Client:
    # Its own function so tests can swap in a fake client (no network, no key, no cost).
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=ATTEMPTS)
        ),
    )


def _format_passages(passages: list[dict]) -> str:
    # Each passage starts with its id in brackets, so the model can cite it.
    return "\n\n".join(
        f"[{p['id']}] ({p['source']}, p. {p['page']})\n{p['text']}" for p in passages
    )


def _first_sentence(text: str) -> str:
    # Split after the first . ! or ? that is followed by a space; no match = keep it all.
    return re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]


def _quote_passages(passages: list[dict]) -> dict:
    # The fallback: real words from each passage with its real source, same shape as a summary.
    takeaways = [
        {"text": _first_sentence(p["text"]), "source": p["source"], "chunk_id": p["id"]}
        for p in passages
    ]
    return {"takeaways": takeaways, "not_found": False}


def _parse_reply(raw: str, passages: list[dict]) -> dict:
    # Any problem here raises, and the caller falls back to quoting the passages.
    data = json.loads(raw)
    # Day 15: "no" or 0 would be read as yes/no below. Only a real true/false is trusted.
    if not isinstance(data["not_found"], bool):
        raise ValueError(f"not_found must be true or false, got {data['not_found']!r}")
    by_id = {p["id"]: p for p in passages}
    takeaways = []
    for t in data["takeaways"]:
        # A citation to a chunk we never sent means the model invented it: don't trust the reply.
        if t["chunk_id"] not in by_id:
            raise ValueError(f"reply cites unknown chunk {t['chunk_id']!r}")
        source = by_id[t["chunk_id"]]["source"]
        takeaways.append({"text": t["text"], "source": source, "chunk_id": t["chunk_id"]})
    # "Not found" or no takeaways at all both mean: nothing useful in these passages.
    if data["not_found"] or not takeaways:
        return {"takeaways": [], "not_found": True}
    return {"takeaways": takeaways, "not_found": False}


def summarize_passages(passages: list[dict]) -> dict:
    """Return {"takeaways": [{"text", "source", "chunk_id"}], "not_found": bool}."""
    # Nothing found -> say so, never invent an answer (contract rule).
    if not passages:
        return {"takeaways": [], "not_found": True}
    settings = get_settings()
    # None = no key set (e.g. in CI), so don't even try to call Gemini.
    if not settings.gemini_api_key:
        log.warning("GEMINI_API_KEY not set; quoting passages instead of summarizing")
        return _quote_passages(passages)
    # Read outside the try: a missing prompt file is our bug, so it should fail loudly.
    instructions = PROMPT_PATH.read_text(encoding="utf-8")
    try:
        response = _get_client(settings.gemini_api_key).models.generate_content(
            model=settings.gemini_model,
            contents=_format_passages(passages),
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                response_mime_type="application/json",  # reply with JSON only, no extra prose
                response_json_schema=REPLY_SCHEMA,
            ),
        )
        summary = _parse_reply(response.text, passages)
        # Day 6 auto-check (summary_check.py): e.g. a takeaway with no text never reaches users.
        problems = check_summary(summary, passages)
        if problems:
            raise ValueError("; ".join(problems))  # caught below, like any other bad reply
        return summary
    # APIError: bad key, unknown model, rate limit or server error after retries.
    # httpx.TransportError: timeout or no connection (Gemini's client is built on httpx).
    # ValueError covers broken JSON, invented chunk ids and failed checks; KeyError/TypeError
    # cover JSON in the wrong shape (TypeError also catches an empty reply, where text is None).
    except (errors.APIError, httpx.TransportError, ValueError, KeyError, TypeError) as e:
        log.warning("summarize fell back to quoting passages: %s", e)
        return _quote_passages(passages)
