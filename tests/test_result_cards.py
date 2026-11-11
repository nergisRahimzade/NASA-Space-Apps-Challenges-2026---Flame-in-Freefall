"""Day 11 (FE): snippet, highlight, source link and score badge for the result cards."""

from flame_in_freefall.result_cards import (
    escape_markdown,
    load_experiments,
    load_source_links,
    query_terms,
    score_badge,
    snippet,
    source_line,
)


def test_query_terms_skip_common_and_short_words_but_keep_o2():
    assert query_terms("What is the effect of O2 on fire suppressants?") == {
        "effect",
        "o2",
        "fire",
        "suppressant",
    }


def test_highlight_matches_plurals_and_keeps_punctuation_outside():
    out = snippet("Suppressants (CO2), were tested.", "suppressant co2")
    assert (
        out
        == r"**:orange-background[Suppressants]** \(**:orange-background[CO2]**\)\, were tested\."
    )


def test_no_matching_words_shows_the_start_of_the_text():
    text = " ".join(f"w{i}" for i in range(50))
    assert snippet(text, "nothing here", size=5) == "w0 w1 w2 w3 w4 …"


def test_snippet_moves_to_where_the_question_words_are():
    words = [f"w{i}" for i in range(30)]
    words[20] = "flame"
    out = snippet(" ".join(words), "flame", size=5)
    assert out.startswith("… ") and out.endswith(" …")
    assert "**:orange-background[flame]**" in out


def test_short_text_has_no_ellipsis():
    assert snippet("Flames spread slowly.", "flame") == (
        r"**:orange-background[Flames]** spread slowly\."
    )


def test_escape_markdown_keeps_dollars_and_stars_literal():
    assert escape_markdown("$5 * 2 [x](y)") == r"\$5 \* 2 \[x\]\(y\)"


def test_plural_forms_match():
    out = snippet("Gases and flames.", "gas flame")
    assert out == r"**:orange-background[Gases]** and **:orange-background[flames]**\."


def test_score_badge_rounds_to_two_places():
    assert score_badge(0.7461) == ":orange-badge[Match 0.75]"


def test_source_line_links_only_known_sources():
    links = {"FLEX report": "https://example.org/a(1)"}
    assert (
        source_line("FLEX report", 1, links)
        == "[FLEX report](https://example.org/a%281%29) · page 1"
    )
    assert source_line("Other_report", 2, links) == r"Other\_report · page 2"


def test_load_source_links_reads_real_sources_csv():
    links = load_source_links()
    assert links["FLEX (Flame Extinguishment Experiment) investigation description"] == (
        "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69"
    )


def test_load_source_links_drops_non_web_links_and_missing_file(tmp_path):
    csv_file = tmp_path / "sources.csv"
    csv_file.write_text(
        "file_name,title,experiment,source_url,retrieved_date\n"
        "a.txt,Good,X,https://example.org,2026-11-01\n"
        "b.txt,Bad,X,javascript:alert(1),2026-11-01\n",
        encoding="utf-8",
    )
    assert load_source_links(csv_file) == {"Good": "https://example.org"}
    assert load_source_links(tmp_path / "missing.csv") == {}


def test_load_experiments_reads_real_sources_csv():
    assert load_experiments() == ["BASS-II", "FLEX", "FLEX-2", "Saffire-II"]


def test_load_experiments_skips_blanks_and_missing_file(tmp_path):
    csv_file = tmp_path / "sources.csv"
    csv_file.write_text(
        "file_name,title,experiment,source_url,retrieved_date\n"
        "a.txt,A,FLEX,https://example.org,2026-11-01\n"
        "b.txt,B, ,https://example.org,2026-11-01\n"
        "c.txt,C,FLEX,https://example.org,2026-11-01\n",
        encoding="utf-8",
    )
    assert load_experiments(csv_file) == ["FLEX"]
    assert load_experiments(tmp_path / "missing.csv") == []
