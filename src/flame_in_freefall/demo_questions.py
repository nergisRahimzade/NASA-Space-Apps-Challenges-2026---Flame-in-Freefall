"""Day 19 (FIF-D19-DAT): read demo_questions.md.

The file lists the demo questions as numbered lines: "1. Question — expected source". The app's
example buttons (FIF-D19-FE) use the question part; the expected source is for the team."""

import re
from pathlib import Path

DEMO_FILE = Path(__file__).resolve().parents[2] / "demo_questions.md"

# "1. What gases ... microgravity? — FLEX" -> question, source. Only numbered lines count, so the
# tables and notes in the file are ignored.
_LINE = re.compile(r"^\s*\d+\.\s+(?P<question>.+?)(?:\s+[—–-]\s+(?P<source>.+?))?\s*$")


def load_demo_questions(path: str | Path = DEMO_FILE) -> list[dict]:
    """[{"question": ..., "source": ...}] in file order, or [] if the file doesn't exist."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    items = []
    for line in lines:
        match = _LINE.match(line)
        if match:
            items.append({"question": match["question"], "source": match["source"] or ""})
    return items
