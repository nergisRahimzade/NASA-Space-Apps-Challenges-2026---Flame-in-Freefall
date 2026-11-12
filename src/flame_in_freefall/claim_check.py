"""Day 16 (AI): spot two kinds of slip in a summary: a number, or an experiment name, that the
cited passage doesn't contain.

summary_check.py (Day 6) checks that every takeaway cites a real passage. It can't tell whether
the takeaway says what that passage says. These checks catch two mistakes that matter most here:
- a number the passage doesn't have (a changed value, or one from another passage);
- an experiment name the passage doesn't have (one experiment's numbers given as another's,
  which the D09 search mistake for Q4 could lead to).

It's a report tool (scripts/day16_test_summaries.py, tests/summaries.md), not part of the live
app: how often it raises a false alarm is measured first. Out of scope, on purpose:
- numbers written as words ("nine samples"), and unit conversions ("0.1 mole fraction" vs "10%");
- scientific notation and signs separated from their number by whitespace;
- digits right after a letter or a comma: "5x29" checks only the 5, "1,2,3" only the 1 (a comma
  before 3 digits is read as a thousands separator, "1,000");
- a number with a space before its name: "FLEX 2" reads the 2 as a number (only "FLEX-2" is a name);
- a dash right after a number is read as a range, so "step 2 -5 C" checks 5, not -5;
- meaning: a takeaway can use only the passage's numbers and names and still be wrong. That part
  is the hand check in tests/summaries.md."""

import re

# The experiments in our reports, spelled like the chunks' `experiment` tag.
# tests/test_claim_check.py fails if data/processed/chunks.jsonl gets a new one, so it's added here.
EXPERIMENTS = ("FLEX", "FLEX-2", "Saffire-II", "BASS-II")

# Dashes that writers use in place of "-" (the BASS-II report writes "BASS–II" once).
_DASHES = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-"})

# A number: optional sign, thousands commas ("1,000"), and decimals ("0.5" or ".5").
# (?<![A-Za-z\d.,]) skips digits inside words and formulas: CO2, SF6 and O2 aren't numbers.
_NUMBER = re.compile(
    r"(?<![A-Za-z\d.,])(?P<sign>[+−-]?)(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)"
)


def _normalize(text: str) -> str:
    return text.translate(_DASHES)


def _name_pattern(name: str) -> str:
    # The same rule as retrieval.experiment_in_question: the name must stand alone, so "FLEX"
    # doesn't match inside "FLEX-2" and "BASS" alone doesn't match "BASS-II".
    return rf"(?<![\w-]){re.escape(name)}(?![\w-])"


def _without_experiment_names(text: str) -> str:
    # "FLEX-2" holds a 2 that isn't a measurement, so names are removed before finding numbers.
    for name in sorted(EXPERIMENTS, key=len, reverse=True):  # FLEX-2 before FLEX
        text = re.sub(_name_pattern(name), " ", text, flags=re.IGNORECASE)
    return text


def _numbers(text: str) -> list[tuple[str, float]]:
    # (as written, value): "3.0" and "3" are the same value, "1,000" is 1000.
    text = _without_experiment_names(_normalize(text))
    numbers = []
    for match in _NUMBER.finditer(text):
        written = match.group()
        # A dash after a numeric endpoint separates a range, even with spaces: "0.5 -3.0".
        # A negative endpoint still keeps its sign in "-5 to -1" or "-5--1".
        if match.group("sign") in ("-", "−") and re.search(r"\d\s*$", text[: match.start()]):
            written = written[1:]
        value = float(written.replace(",", "").replace("−", "-"))
        numbers.append((written, value))
    return numbers


def unsupported_numbers(takeaway_text: str, passage_text: str) -> list[str]:
    """Numbers in the takeaway that the passage doesn't contain, as written, without repeats.

    Ranges are read number by number ("0.5–3.0", "0.5 to 3.0"), and units are ignored, so "21%"
    and "21 percent" match. Leading-dot decimals and attached signs are checked.
    Numbers written as words are not checked."""
    in_passage = {value for _, value in _numbers(passage_text)}
    missing = []
    for written, value in _numbers(takeaway_text):
        if value not in in_passage and written not in missing:
            missing.append(written)
    return missing


def _named(text: str) -> list[str]:
    text = _normalize(text)
    return [e for e in EXPERIMENTS if re.search(_name_pattern(e), text, flags=re.IGNORECASE)]


def wrong_experiments(takeaway_text: str, passage: dict) -> list[str]:
    """Experiment names in the takeaway that are neither the passage's experiment tag nor
    written in the passage itself."""
    allowed = set(_named(passage["text"]))
    if passage.get("experiment"):  # an index built before Day 12 has no tag
        allowed.add(passage["experiment"])
    return [name for name in _named(takeaway_text) if name not in allowed]


def check_claims(summary: dict, passages: list[dict]) -> list[str]:
    """Problems found in a summarize() result, one line per problem; an empty list = none found.
    Each takeaway is checked against the passage it cites (its chunk_id)."""
    by_id = {p["id"]: p for p in passages}
    problems = []
    for n, t in enumerate(summary["takeaways"], start=1):  # n counts from 1, like the app
        passage = by_id.get(t["chunk_id"])
        if passage is None:  # check_summary rejects this too; said again so no takeaway is skipped
            problems.append(
                f"takeaway {n} cites {t['chunk_id']!r}, which is not one of the passages"
            )
            continue
        numbers = unsupported_numbers(t["text"], passage["text"])
        if numbers:
            problems.append(
                f"takeaway {n} ({t['chunk_id']}): numbers not in the passage: {', '.join(numbers)}"
            )
        names = wrong_experiments(t["text"], passage)
        if names:
            problems.append(
                f"takeaway {n} ({t['chunk_id']}): experiment not in the passage: {', '.join(names)}"
            )
    return problems
