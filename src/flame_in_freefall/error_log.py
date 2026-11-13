"""Day 18 (BE): an error log, so the team can see WHY the live app failed.

Before this, the page caught every failure and showed a red box, and nothing wrote down the
reason. api.py now calls record_exception() when search(), summarize() or get_table() fail, and
summarizer.py calls record() when Gemini fails (the passages are quoted instead) or the
per-minute limit is reached. Each event is one JSON line in artifacts/errors.log (git-ignored):

    uv run python -m flame_in_freefall.error_log            # counts, then the last 10 events
    uv run python -m flame_in_freefall.error_log --last 30

artifacts/ on Streamlit Community Cloud is wiped on every reboot and nobody can open it from
outside, so there the host's own log (the "Manage app" page) is the error log: record_exception()
also writes an ERROR line with a time and the traceback, which reaches it. The Gemini key is
replaced with <key> in both places. Logging must never break a call."""

import argparse
import json
import logging
import os
import threading
import traceback
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ERROR_LOG = Path(__file__).resolve().parents[2] / "artifacts" / "errors.log"
MESSAGE_CHARS = 300  # an error message is cut to this length, so one long one can't bloat the log
DETAIL_CHARS = 100  # same cut as speed.DETAIL_CHARS
# error = an exception left the function (the visitor saw a red box); fallback = Gemini failed and
# the passages were quoted; limit = the per-minute Gemini limit was reached.
KINDS = ("error", "fallback", "limit")
CALLS = ("search", "summarize", "get_table")

log = logging.getLogger("flame_in_freefall.error_log")
# Streamlit runs each visitor in its own thread; one writer at a time keeps lines whole.
_write_lock = threading.Lock()


def _scrub(text: str) -> str:
    # A key can end up inside an error message (e.g. a URL with ?key=...). Read straight from the
    # environment, NOT from get_settings(): a bad setting is one of the errors logged here, and
    # get_settings() would raise again.
    key = os.getenv("GEMINI_API_KEY")
    return text.replace(key, "<key>") if key else text


def record(call: str, kind: str, error_type: str, message: str, detail: str = "") -> None:
    """Add one event to the error log. Never raises, except for a wrong `call` or `kind`
    (that's a bug in our own code, so fail loudly)."""
    if call not in CALLS:
        raise ValueError(f"call must be one of {CALLS}, got {call!r}")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),  # UTC: same clock everywhere
        "call": call,
        "kind": kind,
        "error_type": error_type,
        "message": _scrub(message)[:MESSAGE_CHARS],
        "detail": _scrub(detail)[:DETAIL_CHARS],
    }
    try:
        with _write_lock:
            ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(ERROR_LOG, "a", encoding="utf-8") as f:  # "a" = add to the end
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Logging is a side job: a full or read-only disk must never break a search.
    except OSError as e:
        log.warning("couldn't write the error log: %s", e)


def record_exception(call: str, detail: str, error: Exception) -> None:
    """Log an exception that is about to leave search(), summarize() or get_table().
    Never raises: the caller re-raises the visitor's real error right after this, and a problem
    in here must not replace it with a different one."""
    try:
        # The traceback says where it broke. It's built and scrubbed here, not added by logging
        # (exc_info), because logging would print the exception's message again, unscrubbed.
        # format_exception also includes chained errors ("The above exception was the direct
        # cause..."), and those get scrubbed too.
        trace = _scrub("".join(traceback.format_exception(error))).rstrip()
        # The host's log has no format set up, so the time goes into the message itself.
        log.error(
            "%s: %s() failed with %s:\n%s",
            datetime.now(UTC).isoformat(timespec="seconds"),
            call,
            type(error).__name__,
            trace,
        )
        record(call, "error", type(error).__name__, str(error), detail)
    # Anything at all (even an exception whose text can't be read): only a warning, by type name,
    # because printing the problem itself could fail the same way.
    except Exception as problem:
        log.warning("couldn't log a failed %s() call: %s", call, type(problem).__name__)


def read_log(path: Path | None = None) -> list[dict]:
    # None = the real error log (read at call time, so tests can point ERROR_LOG elsewhere).
    path = path or ERROR_LOG
    if not path.exists():
        return []  # nothing has failed yet
    entries, damaged = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        # A line cut off part-way (the app stopped mid-write) mustn't hide every other event.
        except json.JSONDecodeError:
            damaged += 1
    if damaged:
        log.warning("skipped %d damaged lines in %s", damaged, path)
    return entries


def main(argv: list[str] | None = None) -> None:
    # Imported here so that importing this module (done by api.py on every page run) stays light.
    from flame_in_freefall.config import setup_logging

    parser = argparse.ArgumentParser(description="Report the events in the error log.")
    parser.add_argument("--last", type=int, default=10, help="how many recent events (default 10)")
    args = parser.parse_args(argv)
    if args.last <= 0:
        parser.error("--last must be above 0")
    setup_logging()
    entries = read_log()
    if not entries:
        log.info("No errors logged yet (%s).", ERROR_LOG)
        return
    log.info("%d events logged", len(entries))
    counts = Counter((e["call"], e["kind"], e["error_type"]) for e in entries)
    for (call, kind, error_type), n in counts.most_common():
        log.info("%4d  %-9s %-8s %s", n, call, kind, error_type)
    log.info("Latest %d:", args.last)
    for e in entries[-args.last :]:
        log.info(
            "%s  %s %s %s: %s [%s]",
            e["at"],
            e["call"],
            e["kind"],
            e["error_type"],
            e["message"],
            e["detail"],
        )


if __name__ == "__main__":
    main()
