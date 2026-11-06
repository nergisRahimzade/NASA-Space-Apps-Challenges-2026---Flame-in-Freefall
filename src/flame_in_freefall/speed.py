"""Day 11 (BE): time every backend call, keep a speed log, and report the slowest calls.

api.py calls record() after each search(), get_table() and summarize(). Each call becomes a
log line and one JSON line in artifacts/speed.log (git-ignored). To see the slowest:

    uv run python -m flame_in_freefall.speed            # the 5 slowest calls so far
    uv run python -m flame_in_freefall.speed --top 10"""

import argparse
import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from flame_in_freefall.config import setup_logging

SPEED_LOG = Path(__file__).resolve().parents[2] / "artifacts" / "speed.log"
DETAIL_CHARS = 100  # questions are cut to this length, so one long one can't bloat the log

log = logging.getLogger("flame_in_freefall.speed")
# Streamlit runs each visitor in its own thread; one writer at a time keeps lines whole.
_write_lock = threading.Lock()


def record(call: str, detail: str, seconds: float, cached: bool = False) -> None:
    """Log one timed call and add it to the speed log."""
    log.info("%s took %.3f s%s: %s", call, seconds, " (cached)" if cached else "", detail)
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),  # UTC: same clock everywhere
        "call": call,
        "detail": detail[:DETAIL_CHARS],
        "seconds": round(seconds, 4),
        "cached": cached,
    }
    try:
        with _write_lock:
            SPEED_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(SPEED_LOG, "a", encoding="utf-8") as f:  # "a" = add to the end
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Timing is a side job: a full or read-only disk must never break a search.
    except OSError as e:
        log.warning("couldn't write the speed log: %s", e)


def read_log(path: Path | None = None) -> list[dict]:
    # None = the real speed log (read at call time, so tests can point SPEED_LOG elsewhere).
    path = path or SPEED_LOG
    if not path.exists():
        return []  # nothing timed yet
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def slowest(n: int = 5, path: Path | None = None) -> list[dict]:
    """The n slowest calls in the speed log, slowest first."""
    if n <= 0:
        raise ValueError("n must be > 0")
    return sorted(read_log(path), key=lambda e: e["seconds"], reverse=True)[:n]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Report the slowest backend calls.")
    parser.add_argument("--top", type=int, default=5, help="how many to show (default 5)")
    args = parser.parse_args(argv)
    setup_logging()
    entries = read_log()
    if not entries:
        log.info("No speed log yet (%s). Use the app or call api.search() first.", SPEED_LOG)
        return
    searches = [e for e in entries if e["call"] == "search"]
    cached = sum(e["cached"] for e in searches)  # True counts as 1
    log.info(
        "%d calls logged; %d searches, %d answered from cache", len(entries), len(searches), cached
    )
    log.info("Slowest %d:", args.top)
    for e in slowest(args.top):
        note = " (cached)" if e["cached"] else ""
        log.info("%8.3f s  %-9s %s%s  [%s]", e["seconds"], e["call"], e["detail"], note, e["at"])


if __name__ == "__main__":
    main()
