"""Day 5 (BE): the real summarize(): ask OpenAI for takeaways that cite their chunk.

Fails safely: with no API key, a timeout after retries, or a broken reply, it quotes the
passages instead (real text, real sources), so the app keeps working and nothing is invented.
The prompt text lives in src/prompts/summary_v1.txt (written by the AI ticket, FIF-D05-AI)."""

import json
import logging
import re
from pathlib import Path

from openai import OpenAI, OpenAIError

from flame_in_freefall.config import get_settings

# Built from this file's location (up 1 folder = src/), so it works from any folder.
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "summary_v1.txt"
TIMEOUT_S = 30.0  # give up on one attempt after this many seconds
MAX_RETRIES = 2  # the OpenAI client retries timeouts, rate limits and server errors itself

log = logging.getLogger(__name__)

# Structured output: the model must reply with JSON in exactly this shape.
# It only gives chunk_id; we fill in source ourselves, so a source can't be made up.
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "takeaways": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "chunk_id": {"type": "string"}},
                "required": ["text", "chunk_id"],
                "additionalProperties": False,
            },
        },
        "not_found": {"type": "boolean"},
    },
    "required": ["takeaways", "not_found"],
    "additionalProperties": False,
}


def _get_client(api_key: str) -> OpenAI:
    # Its own function so tests can swap in a fake client (no network, no key, no cost).
    return OpenAI(api_key=api_key, timeout=TIMEOUT_S, max_retries=MAX_RETRIES)


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
    # None = no key set (e.g. in CI), so don't even try to call OpenAI.
    if not settings.openai_api_key:
        log.warning("OPENAI_API_KEY not set; quoting passages instead of summarizing")
        return _quote_passages(passages)
    # Read outside the try: a missing prompt file is our bug, so it should fail loudly.
    instructions = PROMPT_PATH.read_text(encoding="utf-8")
    try:
        response = _get_client(settings.openai_api_key).responses.create(
            model=settings.openai_model,
            instructions=instructions,
            input=_format_passages(passages),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "summary",
                    "schema": REPLY_SCHEMA,
                    "strict": True,
                }
            },
        )
        return _parse_reply(response.output_text, passages)
    # OpenAIError: no connection, timeout after retries, bad key... ValueError covers broken
    # JSON and invented chunk ids; KeyError/TypeError cover JSON in the wrong shape.
    except (OpenAIError, ValueError, KeyError, TypeError) as e:
        log.warning("summarize fell back to quoting passages: %s", e)
        return _quote_passages(passages)
