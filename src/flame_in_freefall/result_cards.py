"""Day 11 (FE): helpers for the search result cards.

A card shows a short snippet of the passage with the question's words highlighted, a link to
the source report, and the search score as a badge. These helpers build that text; the app
draws it with st.markdown."""

import csv
import re
from pathlib import Path

SOURCES_CSV = Path(__file__).resolve().parents[2] / "data" / "sources.csv"
SNIPPET_WORDS = 40

# Common words that would highlight almost everything, so they're never highlighted.
STOPWORDS = {
    "and", "are", "can", "did", "does", "for", "from", "has", "have", "how", "into", "its",
    "not", "that", "the", "their", "them", "then", "there", "these", "they", "this", "those",
    "through", "was", "were", "what", "when", "where", "which", "while", "who", "why", "will",
    "with", "you", "your",
}  # fmt: skip

# Splits a word like "(CO2)," into "(", "CO2" and ")," so only the middle part is highlighted.
_WORD = re.compile(r"^(\W*)([\w-]*\w)?(\W*)$")
# In Markdown any ASCII punctuation can be shown as-is by putting a backslash before it.
_MARKDOWN_SPECIAL = re.compile(r"([!-/:-@\[-`{-~])")


def _stem(word: str) -> str:
    # Crude, but enough to match "flame" with "flames" and "gas" with "gases".
    word = word.lower()
    if len(word) > 4 and word.endswith(("ses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def query_terms(query: str) -> set[str]:
    """The question's words worth highlighting, stemmed. Short words are skipped, except ones
    with a digit like "O2"."""
    words = re.findall(r"\w[\w-]*", query)
    return {
        _stem(w)
        for w in words
        if w.lower() not in STOPWORDS and (len(w) >= 3 or any(c.isdigit() for c in w))
    }


def escape_markdown(text: str) -> str:
    """Show text exactly as written: $ would start math and * would start bold otherwise."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def _is_match(word: str, terms: set[str]) -> bool:
    core = _WORD.match(word)
    return bool(core and core.group(2) and _stem(core.group(2)) in terms)


def _highlight(word: str, terms: set[str]) -> str:
    if not _is_match(word, terms):
        return escape_markdown(word)
    before, core, after = _WORD.match(word).groups()
    # Bold as well as the color, so the highlight doesn't rely on color alone.
    return (
        f"{escape_markdown(before)}**:blue-background[{escape_markdown(core)}]**"
        f"{escape_markdown(after)}"
    )


def snippet(text: str, query: str, size: int = SNIPPET_WORDS) -> str:
    """Markdown for the size-word stretch of text with the most question words in it,
    with those words highlighted and "…" where text was cut off."""
    words = text.split()
    terms = query_terms(query)
    matches = [_is_match(w, terms) for w in words]
    # Slide a size-word window along the text and keep the first one with the most matches.
    start = 0
    if len(words) > size:
        counts = [sum(matches[i : i + size]) for i in range(len(words) - size + 1)]
        start = counts.index(max(counts))
    shown = words[start : start + size]
    body = " ".join(_highlight(w, terms) for w in shown)
    prefix = "… " if start > 0 else ""
    suffix = " …" if start + size < len(words) else ""
    return f"{prefix}{body}{suffix}"


def score_badge(score: float) -> str:
    # One color for every score: Day 9 found scores can't tell good results from bad ones yet,
    # so a green "good" badge would promise more than the number means. Neutral grey since
    # FIF-D18-FE: orange is kept for fire-risk data.
    return f":gray-badge[Match {score:.2f}]"


def load_source_links(path: str | Path = SOURCES_CSV) -> dict[str, str]:
    """Map each report title (a chunk's "source") to its web page. Only http(s) links are kept,
    so a bad row can't turn into a javascript: link."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return {}
    return {
        r["title"]: r["source_url"]
        for r in rows
        if r.get("title") and (r.get("source_url") or "").startswith(("https://", "http://"))
    }


def load_experiments(path: str | Path = SOURCES_CSV) -> list[str]:
    """The experiments that have reports, so they can be searched (FIF-D12-FE). Read from the
    `experiment` column of sources.csv, which is where the chunks get their tag."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return []
    return sorted({r["experiment"].strip() for r in rows if (r.get("experiment") or "").strip()})


def source_line(source: str, page: int, links: dict[str, str]) -> str:
    """Markdown for "Source title · page N", with the title linked when we know its page."""
    title = escape_markdown(source)
    url = links.get(source)
    if url:
        # Parentheses in a URL would end the Markdown link early, so encode them.
        url = url.replace("(", "%28").replace(")", "%29")
        # The icon says the link leaves the app for the report's page (FIF-D18-FE)
        title = f"[{title} :material/open_in_new:]({url})"
    return f"{title} · page {page}"
