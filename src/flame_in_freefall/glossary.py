"""Day 15 (DAT): plain-word tooltips for the app, read from data/glossary.json.

Each term has an id, the term as shown, a short tooltip, and the data columns it explains
(master.csv or ranking.csv). The app shows a column's tooltip on its table header, and lists
every term under "What do these words mean?". Rules for the text: data_notes.md section 11."""

import json
from pathlib import Path

GLOSSARY = Path(__file__).resolve().parents[2] / "data" / "glossary.json"
MAX_TOOLTIP_CHARS = 250  # a tooltip is a hover box: about 2 short sentences
FIELDS = {"id", "term", "tooltip", "columns"}


def load_glossary(path: str | Path = GLOSSARY) -> list[dict]:
    """The terms in file order. Raises ValueError if the file breaks the rules above, so a
    mistake fails in the tests instead of showing a broken tooltip."""
    terms = json.loads(Path(path).read_text(encoding="utf-8"))["terms"]
    ids, columns = set(), set()
    for n, t in enumerate(terms, start=1):
        if set(t) != FIELDS:
            raise ValueError(f"term {n} must have exactly the fields {sorted(FIELDS)}")
        for key in ("id", "term", "tooltip"):
            if not isinstance(t[key], str) or not t[key].strip():
                raise ValueError(f"term {n} needs a non-empty {key}")
        if len(t["tooltip"]) > MAX_TOOLTIP_CHARS:
            raise ValueError(f"{t['id']}: tooltip is over {MAX_TOOLTIP_CHARS} characters")
        if t["id"] in ids:
            raise ValueError(f"{t['id']} is listed twice")
        ids.add(t["id"])
        # One tooltip per column, or the app would have to pick one.
        repeated = columns & set(t["columns"])
        if repeated:
            raise ValueError(f"{t['id']}: column(s) {sorted(repeated)} already have a tooltip")
        columns |= set(t["columns"])
    return terms


def column_help(terms: list[dict]) -> dict[str, str]:
    """Column name -> tooltip, for the table headers."""
    return {col: t["tooltip"] for t in terms for col in t["columns"]}
