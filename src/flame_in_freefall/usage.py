"""Day 17 (BE): log the tokens (and cost) of every Gemini call, and report the total.

summarizer.py calls record() after each real Gemini reply. A call answered from the summary
cache never reaches Gemini, so it isn't logged here. Each call becomes one JSON line in
artifacts/usage.log (git-ignored). To see the totals:

    uv run python -m flame_in_freefall.usage

The cost needs a price. Set GEMINI_USD_PER_M_INPUT and GEMINI_USD_PER_M_OUTPUT (US dollars per
million tokens, from Google's pricing page); with no price set, the report says so instead of
guessing. artifacts/ on Streamlit Community Cloud is wiped when the app reboots, so the log
there only covers the time since the last reboot."""

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from flame_in_freefall.config import get_settings, setup_logging

USAGE_LOG = Path(__file__).resolve().parents[2] / "artifacts" / "usage.log"

log = logging.getLogger("flame_in_freefall.usage")
# Streamlit runs each visitor in its own thread; one writer at a time keeps lines whole.
_write_lock = threading.Lock()


def _cost_usd(input_tokens: int | None, output_tokens: int | None) -> float | None:
    # None = can't say: no price set, or Google sent no token count for this call.
    settings = get_settings()
    in_price, out_price = settings.gemini_usd_per_m_input, settings.gemini_usd_per_m_output
    if in_price is None or out_price is None or input_tokens is None or output_tokens is None:
        return None
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


def record(model: str, input_tokens: int | None, output_tokens: int | None) -> None:
    """Log one Gemini call. A token count Google didn't send stays None (not 0: 0 would claim
    the call was free)."""
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),  # UTC: same clock everywhere
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": _cost_usd(input_tokens, output_tokens),
    }
    log.info(
        "Gemini call: %s input tokens, %s output tokens (%s)", input_tokens, output_tokens, model
    )
    try:
        with _write_lock:
            USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(USAGE_LOG, "a", encoding="utf-8") as f:  # "a" = add to the end
                f.write(json.dumps(entry) + "\n")
    # Logging is a side job: a full or read-only disk must never break a summary.
    except OSError as e:
        log.warning("couldn't write the usage log: %s", e)


def read_log(path: Path | None = None) -> list[dict]:
    # None = the real usage log (read at call time, so tests can point USAGE_LOG elsewhere).
    path = path or USAGE_LOG
    if not path.exists():
        return []  # no Gemini call yet
    entries, damaged = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        # A line cut off part-way (the app stopped mid-write) mustn't hide every other call.
        except json.JSONDecodeError:
            damaged += 1
    if damaged:
        log.warning("skipped %d damaged lines in %s", damaged, path)
    return entries


def totals(entries: list[dict]) -> dict:
    """Calls, tokens and cost over the entries. Tokens Google didn't report count as 0 here, so
    `unknown_tokens` says how many calls had none. `cost_usd` adds only the calls that have a cost
    (None when none does), and `unpriced` counts the calls that don't."""
    costs = [e["cost_usd"] for e in entries if e["cost_usd"] is not None]
    return {
        "calls": len(entries),
        "input_tokens": sum(e["input_tokens"] or 0 for e in entries),
        "output_tokens": sum(e["output_tokens"] or 0 for e in entries),
        "unknown_tokens": sum(
            e["input_tokens"] is None or e["output_tokens"] is None for e in entries
        ),
        "cost_usd": sum(costs) if costs else None,
        "unpriced": len(entries) - len(costs),
    }


def main() -> None:
    setup_logging()
    entries = read_log()
    if not entries:
        log.info("No usage log yet (%s). A Gemini summary has to run first.", USAGE_LOG)
        return
    t = totals(entries)
    log.info(
        "%d Gemini calls: %d input tokens, %d output tokens",
        t["calls"],
        t["input_tokens"],
        t["output_tokens"],
    )
    if t["unknown_tokens"]:
        log.info("%d calls had no token count from Google (counted as 0)", t["unknown_tokens"])
    if t["cost_usd"] is None:
        # Older entries store only a missing cost, not its cause. Current prices can't tell us
        # whether a historical call lacked prices, token counts, or both.
        log.info("Cost: unavailable (price not set or token count missing when calls ran)")
    else:
        log.info("Cost: $%.4f", t["cost_usd"])
        if t["unpriced"]:
            log.info(
                "%d calls lacked prices or token counts when they ran, so they aren't in that sum",
                t["unpriced"],
            )


if __name__ == "__main__":
    main()
