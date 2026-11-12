"""Day 14 (FE): the summary box above the result cards.

The app shows a loading skeleton while summarize() works, then the takeaways, each followed by
a chip naming its experiment and page (FIF-D15-FE). Takeaway text is escaped, like the
snippets, so $ or * can't turn into math or bold."""

from flame_in_freefall.result_cards import escape_markdown

# Three grey lines that shimmer while the summary is being written. Fixed HTML with no user
# text in it, so it's safe to show with unsafe_allow_html. Motion stops for people who ask
# their system for reduced motion.
SKELETON_HTML = """
<div class="fif-skeleton" aria-hidden="true"><div></div><div></div><div></div></div>
<style>
.fif-skeleton div {
  height: 12px; margin: 12px 0; border-radius: 6px;
  background: linear-gradient(90deg, #2A2F37 25%, #3A4049 50%, #2A2F37 75%);
  background-size: 200% 100%; animation: fif-shimmer 1.2s ease-in-out infinite;
}
.fif-skeleton div:nth-child(1) { width: 92%; }
.fif-skeleton div:nth-child(2) { width: 78%; }
.fif-skeleton div:nth-child(3) { width: 85%; }
@keyframes fif-shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}
@media (prefers-reduced-motion: reduce) { .fif-skeleton div { animation: none; } }
</style>
"""
# FIF-D16-FE: says how long it can take, since Gemini gives up after 30 s
LOADING_TEXT = "Writing a summary from these passages. This can take up to 30 seconds..."

AI_LABEL = "AI-generated from the passages below. Check each source before relying on it."
# Says "word for word", not where in the passage: the fallback quotes the first full sentence
# (FIF-D05-BE, #165), which isn't always at the start.
QUOTED_LABEL = (
    "The AI summary isn't available, so these are quoted word for word from the passages below."
)
NOT_FOUND_TEXT = (
    "Not found: the passages below don't answer this question. Try different words, "
    "or check the result cards for related information."
)


def summary_label(ai_available: bool) -> str:
    """The caption over the takeaways. Without a Gemini key, summarize() quotes the passages
    instead, so the box must not call that text AI-generated."""
    return AI_LABEL if ai_available else QUOTED_LABEL


def short_source(source: str) -> str:
    """A report title without its description: "FLEX (Flame Extinguishment ...) investigation
    description" -> "FLEX". Used when a result has no experiment tag."""
    return source.split(" (")[0].strip() or source


def source_chip(takeaway: dict, results: list[dict], links: dict[str, str]) -> str:
    """A small badge naming the experiment and page a takeaway came from, e.g. "FLEX · p. 1".
    It links to the report when we know its page; hovering the link shows the full title."""
    result = {r["id"]: r for r in results}.get(takeaway["chunk_id"], {})
    name = result.get("experiment") or short_source(takeaway["source"])
    page = result.get("page", "?")
    chip = f":gray-badge[{escape_markdown(f'{name} · p. {page}')}]"
    url = links.get(takeaway["source"])
    if not url:
        return chip
    # Parentheses or quotes would break the Markdown link, so they're encoded or dropped.
    url = url.replace("(", "%28").replace(")", "%29")
    title = takeaway["source"].replace('"', "")
    return f'[{chip}]({url} "{title}")'


def takeaway_markdown(summary: dict, results: list[dict], links: dict[str, str]) -> str:
    """A bullet list: each takeaway, then a chip for its source (FIF-D15-FE)."""
    return "\n".join(
        f"- {escape_markdown(t['text'])} {source_chip(t, results, links)}"
        for t in summary["takeaways"]
    )
