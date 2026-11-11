"""Day 14 (FE): the summary box's label and takeaway list."""

from flame_in_freefall.summary_box import (
    AI_LABEL,
    QUOTED_LABEL,
    SKELETON_HTML,
    summary_label,
    takeaway_markdown,
)

RESULTS = [{"id": "flex-p1-c0", "text": "...", "source": "FLEX report", "page": 1, "score": 0.7}]


def test_label_only_says_ai_when_ai_wrote_it():
    assert summary_label(ai_available=True) == AI_LABEL
    assert summary_label(ai_available=False) == QUOTED_LABEL


def test_takeaways_list_text_source_link_and_page():
    summary = {
        "takeaways": [
            {"text": "CO2 and He were tested.", "source": "FLEX report", "chunk_id": "flex-p1-c0"}
        ],
        "not_found": False,
    }
    links = {"FLEX report": "https://example.org/flex"}
    assert takeaway_markdown(summary, RESULTS, links) == (
        r"- CO2 and He were tested\. ([FLEX report](https://example.org/flex) · page 1)"
    )


def test_takeaway_text_is_escaped():
    summary = {
        "takeaways": [{"text": "$5 * 2", "source": "FLEX report", "chunk_id": "flex-p1-c0"}],
        "not_found": False,
    }
    assert takeaway_markdown(summary, RESULTS, {}) == r"- \$5 \* 2 (FLEX report · page 1)"


def test_unknown_chunk_shows_a_question_mark_for_the_page():
    summary = {
        "takeaways": [{"text": "x", "source": "Other", "chunk_id": "missing"}],
        "not_found": False,
    }
    assert takeaway_markdown(summary, RESULTS, {}) == "- x (Other · page ?)"


def test_skeleton_respects_reduced_motion():
    assert "prefers-reduced-motion" in SKELETON_HTML
