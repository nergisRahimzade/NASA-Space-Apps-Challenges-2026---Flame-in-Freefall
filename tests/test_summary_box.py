"""Day 14 (FE): the summary box's label and takeaway list."""

from flame_in_freefall.summary_box import (
    AI_LABEL,
    QUOTED_LABEL,
    SKELETON_HTML,
    short_source,
    source_chip,
    summary_label,
    takeaway_markdown,
)

RESULTS = [
    {
        "id": "flex-p1-c0",
        "text": "...",
        "source": "FLEX (Flame Extinguishment Experiment) investigation description",
        "page": 1,
        "score": 0.7,
        "experiment": "FLEX",
    }
]
FLEX_TITLE = RESULTS[0]["source"]


def _summary(text: str, source: str = FLEX_TITLE, chunk_id: str = "flex-p1-c0") -> dict:
    return {
        "takeaways": [{"text": text, "source": source, "chunk_id": chunk_id}],
        "not_found": False,
    }


def test_label_only_says_ai_when_ai_wrote_it():
    assert summary_label(ai_available=True) == AI_LABEL
    assert summary_label(ai_available=False) == QUOTED_LABEL


def test_chip_names_the_experiment_and_page_and_links_to_the_report():
    links = {FLEX_TITLE: "https://example.org/flex"}
    chip = source_chip(_summary("x")["takeaways"][0], RESULTS, links)
    # Hovering the link shows the full report title
    assert chip == (rf'[:orange-badge[FLEX · p\. 1]](https://example.org/flex "{FLEX_TITLE}")')


def test_chip_without_a_link_is_just_the_badge():
    assert source_chip(_summary("x")["takeaways"][0], RESULTS, {}) == r":orange-badge[FLEX · p\. 1]"


def test_chip_falls_back_to_a_short_title_and_unknown_page():
    takeaway = _summary("x", source="BASS report (mock)", chunk_id="missing")["takeaways"][0]
    assert source_chip(takeaway, RESULTS, {}) == r":orange-badge[BASS report · p\. \?]"


def test_short_source_keeps_the_name_before_the_description():
    assert short_source(FLEX_TITLE) == "FLEX"
    assert short_source("Plain title") == "Plain title"


def test_each_takeaway_is_a_bullet_with_its_chip():
    two = {
        "takeaways": [
            {"text": "One.", "source": FLEX_TITLE, "chunk_id": "flex-p1-c0"},
            {"text": "Two.", "source": FLEX_TITLE, "chunk_id": "flex-p1-c0"},
        ],
        "not_found": False,
    }
    assert takeaway_markdown(two, RESULTS, {}).splitlines() == [
        r"- One\. :orange-badge[FLEX · p\. 1]",
        r"- Two\. :orange-badge[FLEX · p\. 1]",
    ]


def test_takeaway_text_is_escaped():
    assert takeaway_markdown(_summary("$5 * 2"), RESULTS, {}).startswith(r"- \$5 \* 2 ")


def test_skeleton_respects_reduced_motion():
    assert "prefers-reduced-motion" in SKELETON_HTML
