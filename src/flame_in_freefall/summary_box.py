"""Day 14 (FE): the summary box above the result cards.

The app shows a loading skeleton while summarize() works, then the takeaways, each followed by
its source and page. Takeaway text is escaped, like the snippets, so $ or * can't turn into
math or bold."""

from flame_in_freefall.result_cards import escape_markdown, source_line

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
LOADING_TEXT = "Writing a summary from these passages..."

AI_LABEL = "AI-generated from the passages below. Check each source before relying on it."
QUOTED_LABEL = (
    "The AI summary isn't available, so these are quoted from the start of each passage below."
)
NOT_FOUND_TEXT = (
    "Not found: the passages below don't answer this question. Try different words, "
    "or check the result cards for related information."
)


def summary_label(ai_available: bool) -> str:
    """The caption over the takeaways. Without a Gemini key, summarize() quotes the passages
    instead, so the box must not call that text AI-generated."""
    return AI_LABEL if ai_available else QUOTED_LABEL


def takeaway_markdown(summary: dict, results: list[dict], links: dict[str, str]) -> str:
    """A bullet list: each takeaway, then its source (linked when known) and page."""
    pages = {r["id"]: r["page"] for r in results}
    lines = []
    for t in summary["takeaways"]:
        source = source_line(t["source"], pages.get(t["chunk_id"], "?"), links)
        lines.append(f"- {escape_markdown(t['text'])} ({source})")
    return "\n".join(lines)
