"""Day 5 (BE): the real summarize(): ask Gemini for takeaways that cite their chunk.

Fails safely: with no API key, a timeout after retries, or a broken reply, it quotes the
passages instead (real text, real sources), so the app keeps working and nothing is invented.
Day 16 (BE): the quote is the first full sentence of each passage, not a fragment. Gemini calls
are also limited per minute (rate_limit.py), and a call that never answers ends in about 32 s.
The prompt text lives in src/prompts/ (written by the AI tickets: v1 FIF-D05-AI, v2 FIF-D15-AI).
Day 15 (AI): prompt v2 also gets the user's question, so it can say "not found" when the
passages are about fire but don't answer it (Q9 and Q10 in tests/retest.md).
Day 17 (BE): an answer Gemini gave is remembered, so the same question about the same passages
is instant and free, and every Gemini call's token count goes to usage.py."""

import copy
import json
import logging
import re
import threading
from pathlib import Path

import httpx
from google import genai
from google.genai import errors, types

from flame_in_freefall import usage
from flame_in_freefall.cache import normalize
from flame_in_freefall.config import get_settings
from flame_in_freefall.rate_limit import RateLimiter
from flame_in_freefall.summary_check import check_summary

# Built from this file's location (up 1 folder = src/), so it works from any folder.
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "summary_v2.txt"
# Day 16: 15 s per attempt, 2 attempts (the first try + 1 retry), so a summary that never comes
# back ends after about 32 s (15 + a 1-2 s wait + 15) instead of about 95 s (3 x 30 s + waits).
# The page tells visitors a summary "can take up to 30 seconds" (summary_box.LOADING_TEXT).
# The Gemini client counts milliseconds, and retries timeouts, rate limits (429) and server
# errors (5xx) itself; without retry options it would never retry.
TIMEOUT_MS = 15_000
ATTEMPTS = 2
# Day 16: the quoting fallback skips "sentences" shorter than this many words (see _first_sentence).
MIN_QUOTE_WORDS = 4

log = logging.getLogger(__name__)

# Day 16: one limiter for the whole app (every visitor shares one Gemini key). None until the
# first summary needs it, so GEMINI_CALLS_PER_MINUTE is read then, not when the file is imported.
# Tests set it back to None, which gives the next test a fresh, empty limiter.
_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def _gemini_call_allowed() -> bool:
    # Counts one call against the limit when it returns True.
    global _limiter
    with _limiter_lock:  # two visitors arriving together must not each create a limiter
        if _limiter is None:
            _limiter = RateLimiter(get_settings().gemini_calls_per_minute, per_seconds=60)
    return _limiter.allow()


# Day 17: answers Gemini gave, so a repeat is instant and free. Only real answers go in (a
# quoted fallback would keep showing quotes after a short outage). Oldest out first when full.
MAX_CACHED_SUMMARIES = 256
_summary_cache: dict[tuple, dict] = {}
_summary_cache_lock = threading.Lock()  # visitors run in separate threads


def _cache_key(passages: list[dict], question: str | None, model: str) -> tuple:
    # Everything that can change the answer: the question (capitals and spaces ignored, like
    # search()), the passages in order, the prompt file and the model. Source and page are sent
    # to Gemini too; keeping them in the key prevents stale citations after metadata corrections.
    # The page goes in as text, the way Gemini sees it ("p. 3"), so any page value can be a key.
    return (
        None if question is None else normalize(question),
        tuple((p["id"], p["text"], p["source"], str(p["page"])) for p in passages),
        PROMPT_PATH.name,
        model,
    )


def summary_is_cached(passages: list[dict], question: str | None = None) -> bool:
    """True when summarize_passages() would answer from memory (api.py logs it as "cached")."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return False  # with no key, summarize_passages() quotes before looking in memory
    key = _cache_key(passages, question, settings.gemini_model)
    with _summary_cache_lock:
        return key in _summary_cache


def clear_summary_cache() -> None:
    # For tests, and for scripts that must see every real Gemini reply.
    with _summary_cache_lock:
        _summary_cache.clear()


def _remember(key: tuple, summary: dict) -> None:
    with _summary_cache_lock:
        if len(_summary_cache) >= MAX_CACHED_SUMMARIES and key not in _summary_cache:
            del _summary_cache[next(iter(_summary_cache))]  # dicts keep insertion order: the oldest
        # A copy, so the caller changing the answer it gets can't change what's remembered.
        _summary_cache[key] = copy.deepcopy(summary)


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


def _build_contents(passages: list[dict], question: str | None) -> str:
    # The layout prompt v2 describes: the question (if any), then the passages.
    body = "Passages:\n\n" + _format_passages(passages)
    return body if question is None else f"Question: {question.strip()}\n\n{body}"


def _first_sentence(text: str) -> str:
    # Day 16: the first sentence that is whole. Chunks are cut every 150 words with a 30-word
    # overlap (chunking.py), so a passage can start or end in the middle of a sentence, and
    # quoting its first piece showed fragments like "the experiment module."
    text = text.strip()
    pieces = re.split(r"(?<=[.!?])\s+", text)  # split after a . ! or ? followed by a space
    # A lowercase first letter means the passage starts mid-sentence, so the first piece is only
    # the end of someone else's sentence. Skip it.
    if text[:1].islower():
        pieces = pieces[1:]
    for piece in pieces:
        # Ending in . ! or ? means the chunk didn't cut it off; a few words is a list number or
        # a heading ("2.", "Fig. 5."), not a sentence worth quoting.
        if len(piece.split()) >= MIN_QUOTE_WORDS and piece.endswith((".", "!", "?")):
            return piece
    # No whole sentence in this passage: quote it as it is. Never empty, never reworded.
    return text


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


def summarize_passages(passages: list[dict], question: str | None = None) -> dict:
    """Return {"takeaways": [{"text", "source", "chunk_id"}], "not_found": bool}.

    With a question, only takeaways that help answer it are kept, and not_found is True when
    no passage does. Without one, takeaways cover anything about fire (prompt v2, rule 9)."""
    # Nothing found -> say so, never invent an answer (contract rule).
    if not passages:
        return {"takeaways": [], "not_found": True}
    settings = get_settings()
    # None = no key set (e.g. in CI), so don't even try to call Gemini.
    # Checked before the memory: the page labels the summary by whether a key is set, so with no
    # key a remembered Gemini answer would be shown as "quoted word for word".
    if not settings.gemini_api_key:
        log.warning("GEMINI_API_KEY not set; quoting passages instead of summarizing")
        return _quote_passages(passages)
    # Day 17: asked before, with the same passages, prompt and model? Answer from memory: no
    # Gemini call and nothing counted against the per-minute limit below.
    key = _cache_key(passages, question, settings.gemini_model)
    with _summary_cache_lock:
        remembered = _summary_cache.get(key)
    if remembered is not None:
        return copy.deepcopy(remembered)  # a copy, as search() does
    # Day 16: over the limit, quote the passages like the "no key" case. The app keeps working,
    # and the key's quota is left for the visitors who come next. A call counts here once, even
    # if the client then retries it.
    if not _gemini_call_allowed():
        log.warning(
            "Gemini limit of %d calls a minute reached; quoting passages instead of summarizing",
            settings.gemini_calls_per_minute,
        )
        return _quote_passages(passages)
    # Read outside the try: a missing prompt file is our bug, so it should fail loudly.
    instructions = PROMPT_PATH.read_text(encoding="utf-8")
    try:
        # Day 15 (AI): keep the client in a variable for the whole call. Written inline, nothing
        # held the client, so Python cleaned it up as soon as .models was read, and cleanup
        # closes its connection: every real call failed with "client has been closed".
        client = _get_client(settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=_build_contents(passages, question),
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                response_mime_type="application/json",  # reply with JSON only, no extra prose
                response_json_schema=REPLY_SCHEMA,
            ),
        )
        # Day 17: the call is paid for, even if the reply turns out to be unusable, so log it now.
        usage_info = getattr(response, "usage_metadata", None)  # None if Google sent none
        usage.record(
            settings.gemini_model,
            getattr(usage_info, "prompt_token_count", None),
            getattr(usage_info, "candidates_token_count", None),
        )
        summary = _parse_reply(response.text, passages)
        # Day 6 auto-check (summary_check.py): e.g. a takeaway with no text never reaches users.
        problems = check_summary(summary, passages)
        if problems:
            raise ValueError("; ".join(problems))  # caught below, like any other bad reply
        _remember(key, summary)  # only here: a real, checked answer from Gemini
        return summary
    # APIError: bad key, unknown model, rate limit or server error after retries.
    # httpx.TransportError: timeout or no connection (Gemini's client is built on httpx).
    # ValueError covers broken JSON, invented chunk ids and failed checks; KeyError/TypeError
    # cover JSON in the wrong shape (TypeError also catches an empty reply, where text is None).
    except (errors.APIError, httpx.TransportError, ValueError, KeyError, TypeError) as e:
        log.warning("summarize fell back to quoting passages: %s", e)
        return _quote_passages(passages)
