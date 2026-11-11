"""Day 16 (FE): what the page says when there are no results, something fails, or it's slow.

Goal of FIF-D16-FE: no blank screens. Every case gets a plain message that says what happened
and what to try next."""

# --- Slow -----------------------------------------------------------------------------------
# FIF-D11-BE measured ~15 s for the first search after a deploy (the model and index load),
# then ~0.1 s. Gemini gives up after 30 s (summarizer.TIMEOUT_MS).
SEARCH_SPINNER = "Searching the reports... The first search after the app starts can take ~15 s."
# Local first searches took ~5 s, so 3 s catches them; normal searches take ~0.1-0.6 s.
SLOW_SEARCH_SECONDS = 3.0
SLOW_SEARCH_NOTE = "That took a while because the search was starting up. Next searches are faster."

# --- No results -----------------------------------------------------------------------------
NO_RESULTS_TIPS = [
    "Try different or fewer words.",
    "Ask about something the reports cover, such as fire suppressants, flame spread or oxygen.",
    "Try: What gases were tested as fire suppressants in microgravity?",
]
ALL_EXPERIMENTS_TIP = "Choose All in the sidebar to search every experiment."

# --- Failures -------------------------------------------------------------------------------
SEARCH_FAILED = "Search isn't working right now. Please try again in a moment."
SUMMARY_FAILED = "The summary isn't working right now. The passages below still are."
TRY_AGAIN = "Try again"


def slow_search_note(seconds: float) -> str | None:
    """A short explanation when a search was slow, or None when it wasn't."""
    return SLOW_SEARCH_NOTE if seconds >= SLOW_SEARCH_SECONDS else None


def no_results_title(experiment: str | None) -> str:
    """The headline of the empty state, naming the experiment when a filter is on."""
    where = f"the {experiment} reports" if experiment else "the reports"
    return f"Nothing in {where} matches this question."


def no_results_tips(experiment: str | None) -> str:
    """Markdown bullet list of what to try. Mentions the sidebar only when a filter is on."""
    tips = [*NO_RESULTS_TIPS]
    if experiment:
        tips.insert(0, ALL_EXPERIMENTS_TIP)
    return "\n".join(f"- {t}" for t in tips)
