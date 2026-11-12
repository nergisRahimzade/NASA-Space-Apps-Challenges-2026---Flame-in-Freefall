"""Day 7 (BE): health check for the app before it deploys.

Every merge to main redeploys the live app (be_notes.md §3), and the live URL can't be checked
from CI (it redirects automated requests to a sign-in page). So we check the app here instead:
run the real app/streamlit_app.py with Streamlit's test tool (no browser or server needed) and
fail if the page crashes or shows an error box. Also check that the live app's package list
(app/requirements.txt) still covers our pyproject.toml dependencies."""

import re
import tomllib
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from flame_in_freefall.api import get_table
from flame_in_freefall.page_states import SLOW_SEARCH_NOTE
from flame_in_freefall.summary_box import AI_LABEL, NOT_FOUND_TEXT, QUOTED_LABEL

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "streamlit_app.py"


@pytest.fixture
def app() -> AppTest:
    # The first run imports pandas and plotly, which can take a few seconds.
    return AppTest.from_file(str(APP), default_timeout=30).run()


def _assert_healthy(at: AppTest) -> None:
    # at.exception = the script crashed; at.error = it showed a red st.error box.
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_start_page_loads(app):
    _assert_healthy(app)
    assert app.title[0].value == "Flame in Freefall"


def test_search_shows_results(app):
    app.text_input[0].input("Which materials burn fastest in microgravity?").run()
    _assert_healthy(app)
    assert any(h.value.startswith("Results") for h in app.subheader)


def test_search_shows_how_long_it_took(app):
    # Day 11: the speed is visible to everyone on the page, not only in the logs.
    app.text_input[0].input("flame spread").run()
    assert any(c.value.startswith("Searched in ") for c in app.caption)


PASSAGE = "Spread was 0.3 mm/s * at 21% O2, and cost rose from $5 to $10."
RESULT = {
    "id": "bass-001-p3-c0",
    "text": PASSAGE,
    "source": "BASS report",
    "page": 3,
    "score": 0.81,
}


GLOSSARY_LABEL = "What do these words mean?"  # FIF-D15-DAT, always on the page


def _result_expanders(at: AppTest) -> list[str]:
    # Expanders that belong to the result cards, leaving out the glossary.
    return [e.label for e in at.expander if e.label != GLOSSARY_LABEL]


def _run_search(**patch) -> AppTest:
    with mock.patch("flame_in_freefall.api.search", **patch):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.text_input[0].input("flame spread").run()
    return at


def test_result_card_shows_badge_source_and_snippet():
    at = _run_search(return_value=[RESULT])
    _assert_healthy(at)
    cards = [m.value for m in at.markdown]
    # An unknown source gets no link, just its name and page
    assert ":gray-badge[Match 0.81] BASS report · page 3" in cards
    # "spread" from the question is highlighted, and $ and * are escaped
    assert any("**:blue-background[Spread]**" in c and r"\$5" in c for c in cards)
    # The snippet already shows this short passage in full, so there's no "Full passage"
    assert _result_expanders(at) == []
    assert not at.text


def test_long_passage_offers_the_full_text_exactly():
    long_text = PASSAGE + " " + " ".join(f"word{i}" for i in range(50))
    at = _run_search(return_value=[{**RESULT, "text": long_text}])
    _assert_healthy(at)
    assert _result_expanders(at) == ["Full passage"]
    assert [t.value for t in at.text] == [long_text]


def test_known_source_links_to_its_report():
    flex = {**RESULT, "source": "FLEX (Flame Extinguishment Experiment) investigation description"}
    at = _run_search(return_value=[flex])
    _assert_healthy(at)
    link = "](https://psi.nasa.gov/physci/repo/data/investigations/PSI-69)"
    assert any(link in m.value for m in at.markdown)


def test_no_results_shows_one_clear_empty_state():
    # FIF-D16-FE: a headline and tips, and no empty summary box or skeleton
    at = _run_search(return_value=[])
    _assert_healthy(at)
    texts = [m.value for m in at.markdown]
    assert ":material/search_off: **Nothing in the reports matches this question.**" in texts
    assert any(t.startswith("- Try different or fewer words.") for t in texts)
    assert "Summary" not in [h.value for h in at.subheader]
    assert not any("fif-skeleton" in t for t in texts)


def test_search_failure_shows_an_error_not_a_crash():
    at = _run_search(side_effect=RuntimeError("index missing"))
    assert not at.exception
    assert len(at.error) == 1
    assert [b.label for b in at.main.button] == ["Try again"]


def test_try_again_searches_again():
    # The first search fails, the retry works
    with mock.patch(
        "flame_in_freefall.api.search", side_effect=[RuntimeError("index missing"), [RESULT]]
    ):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.text_input[0].input("flame spread").run()
        at.main.button[0].click().run()
    _assert_healthy(at)
    assert "Results (1)" in [h.value for h in at.subheader]


def test_slow_search_explains_why():
    # The 3 s threshold is tested in test_page_states.py; here, check the page shows the note.
    # (Faking the clock would also slow Streamlit's own timers, so the check is faked instead.)
    with mock.patch(
        "flame_in_freefall.page_states.slow_search_note", return_value=SLOW_SEARCH_NOTE
    ) as check:
        at = _run_search(return_value=[RESULT])
    _assert_healthy(at)
    check.assert_called()
    # FIF-D18-FE: the note is part of the single caption line above the cards
    assert any(SLOW_SEARCH_NOTE in c.value for c in at.caption)


def test_fast_search_has_no_slow_note():
    at = _run_search(return_value=[RESULT])
    assert not any(SLOW_SEARCH_NOTE in c.value for c in at.caption)


# FIF-D12-FE: the sidebar's Experiment choice filters search as well as the table.


def _search_in(experiment: str, **patch) -> tuple[AppTest, mock.MagicMock]:
    with mock.patch("flame_in_freefall.api.search", **patch) as fake_search:
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.sidebar.selectbox[0].select(experiment).run()
        at.text_input[0].input("flame spread").run()
    return at, fake_search


def test_experiment_dropdown_lists_the_real_experiments(app):
    box = app.sidebar.selectbox[0]
    assert box.label == "Experiment"
    assert box.options == ["All", "BASS-II", "FLEX", "FLEX-2", "Saffire-II"]


def test_chosen_experiment_is_passed_to_search():
    at, fake_search = _search_in("FLEX-2", return_value=[{**RESULT, "experiment": "FLEX-2"}])
    _assert_healthy(at)
    fake_search.assert_called_with("flame spread", experiment="FLEX-2")
    assert "Results (1) from FLEX-2" in [h.value for h in at.subheader]
    assert any(c.value.startswith("Searching FLEX-2 reports only") for c in at.caption)


def test_chosen_experiment_also_filters_the_table():
    at, _ = _search_in("Saffire-II", return_value=[RESULT])
    assert set(at.dataframe[0].value["experiment"]) == {"Saffire-II"}


def test_all_searches_every_experiment():
    at, fake_search = _search_in("All", return_value=[RESULT])
    _assert_healthy(at)
    fake_search.assert_called_with("flame spread")
    assert "Results (1)" in [h.value for h in at.subheader]


def test_no_results_in_one_experiment_suggests_all():
    at, _ = _search_in("FLEX", return_value=[])
    texts = [m.value for m in at.markdown]
    assert ":material/search_off: **Nothing in the FLEX reports matches this question.**" in texts
    assert any(t.startswith("- Choose All in the sidebar") for t in texts)


def test_experiment_without_reports_searches_everything():
    # search() rejects an experiment no chunk has, so the app mustn't pass one along
    with mock.patch("flame_in_freefall.result_cards.load_experiments", return_value=["FLEX"]):
        at, fake_search = _search_in("FLEX-2", return_value=[RESULT])
    _assert_healthy(at)
    fake_search.assert_called_with("flame spread")
    assert any(c.value.startswith("There are no FLEX-2 reports") for c in at.caption)


def test_search_still_works_when_the_table_fails():
    with (
        mock.patch("flame_in_freefall.api.get_table", side_effect=RuntimeError("no csv")),
        mock.patch("flame_in_freefall.api.search", return_value=[RESULT]) as fake_search,
    ):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.text_input[0].input("flame spread").run()
    assert not at.exception
    fake_search.assert_called_with("flame spread")
    assert "Results (1)" in [h.value for h in at.subheader]
    assert [e.value for e in at.error] == [
        "Experiment data isn't available right now. Please try again in a moment."
    ]


# FIF-D13-FE: the riskiness charts read data/ranking.csv and follow the sidebar filters.
SAFFIRE_HEADING = "**Saffire-II: solid materials, ranked by how fast the flame spread**"
FLEX_HEADING = "**FLEX: fuel droplets, how often the flame kept burning at each oxygen level**"


def _markdown(at: AppTest) -> list[str]:
    return [m.value for m in at.markdown]


def test_ranking_shows_one_chart_per_experiment(app):
    _assert_healthy(app)
    assert SAFFIRE_HEADING in _markdown(app)
    assert FLEX_HEADING in _markdown(app)
    assert not any("Fake numbers" in c.value and "Day 13" in c.value for c in app.caption)


def test_ranking_follows_the_experiment_filter(app):
    app.sidebar.selectbox[0].select("Saffire-II").run()
    _assert_healthy(app)
    assert SAFFIRE_HEADING in _markdown(app)
    assert FLEX_HEADING not in _markdown(app)


def test_experiment_without_results_explains_why(app):
    app.sidebar.selectbox[0].select("FLEX-2").run()
    _assert_healthy(app)
    assert "No ranking for FLEX-2: its tests have no recorded results." in [
        i.value for i in app.info
    ]


def test_bass2_explains_why_it_has_no_ranking(app):
    # FIF-D16-DAT: BASS-II has results, so the FLEX-2 wording ("no recorded results") is wrong.
    app.sidebar.selectbox[0].select("BASS-II").run()
    _assert_healthy(app)
    infos = [i.value for i in app.info]
    assert any(i.startswith("No ranking for BASS-II: its crews lowered the airflow") for i in infos)
    assert app.dataframe and len(app.dataframe[0].value) == 129  # its rows are in the table


def test_missing_ranking_file_shows_a_message():
    with mock.patch("flame_in_freefall.ranking_view.load_ranking", return_value=pd.DataFrame()):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
    _assert_healthy(at)
    assert "The riskiness ranking hasn't been built yet." in [i.value for i in at.info]


def _package_names(lines: list[str]) -> set[str]:
    # "sentence-transformers>=6.2.0" -> "sentence-transformers". Lowercase and - vs _ don't
    # matter in package names, so both are normalized.
    names = set()
    for line in lines:
        line = line.split("#")[0].strip()  # drop comments and blank lines
        if line:
            names.add(re.split(r"[<>=!~;\[ ]", line)[0].lower().replace("_", "-"))
    return names


def test_live_app_package_list_covers_pyproject():
    # Community Cloud installs from app/requirements.txt, not uv.lock. A package added only
    # to pyproject.toml would work on our laptops and break the live app.
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ours = _package_names(pyproject["project"]["dependencies"])
    live = _package_names((ROOT / "app" / "requirements.txt").read_text().splitlines())
    assert ours <= live, f"missing from app/requirements.txt: {sorted(ours - live)}"


def test_glossary_explains_the_words(app):
    # FIF-D15-DAT: the glossary is on the page, including LOI (in the reports, not the table).
    _assert_healthy(app)
    assert [e.label for e in app.expander] == [GLOSSARY_LABEL]
    texts = [m.value for m in app.markdown]
    assert any(t.startswith("**LOI (Limiting Oxygen Index)**: The lowest oxygen") for t in texts)
    assert any(t.startswith("**Flame spread rate**:") for t in texts)


def test_page_works_without_the_glossary():
    # A missing or broken glossary.json only removes the tooltips and the glossary box.
    with mock.patch(
        "flame_in_freefall.glossary.load_glossary", side_effect=ValueError("broken file")
    ):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
    _assert_healthy(at)
    assert GLOSSARY_LABEL not in [e.label for e in at.expander]
    assert at.dataframe  # the table still shows


# FIF-D14-FE: the summary box, filled from summarize(results, question=query).
AI_SUMMARY = {
    "takeaways": [
        {"text": "Spread rose to $5 * 2.", "source": "BASS report", "chunk_id": RESULT["id"]}
    ],
    "not_found": False,
}


def _run_summary(**patch) -> tuple[AppTest, mock.MagicMock]:
    with (
        mock.patch("flame_in_freefall.api.search", return_value=[RESULT]),
        mock.patch("flame_in_freefall.api.summarize", **patch) as fake_summarize,
    ):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.text_input[0].input("flame spread").run()
    return at, fake_summarize


def test_summary_shows_takeaways_with_sources(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    at, fake_summarize = _run_summary(return_value=AI_SUMMARY)
    _assert_healthy(at)
    fake_summarize.assert_called_once_with([RESULT], question="flame spread")
    assert AI_LABEL in [c.value for c in at.caption]
    # FIF-D15-FE: the source is a chip; mock results have no experiment, so the short title shows
    chip = r":gray-badge[BASS report · p\. 3]"
    assert rf"- Spread rose to \$5 \* 2\. {chip}" in [m.value for m in at.markdown]
    # The skeleton is replaced once the summary is ready
    assert not any("fif-skeleton" in m.value for m in at.markdown)


def test_summary_says_not_found():
    at, _ = _run_summary(return_value={"takeaways": [], "not_found": True})
    _assert_healthy(at)
    assert NOT_FOUND_TEXT in [i.value for i in at.info]


def test_without_a_key_the_quotes_are_not_called_ai():
    # conftest removes GEMINI_API_KEY, so the real summarize() quotes the passages
    with mock.patch("flame_in_freefall.api.search", return_value=[RESULT]):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.text_input[0].input("flame spread").run()
    _assert_healthy(at)
    captions = [c.value for c in at.caption]
    assert QUOTED_LABEL in captions and AI_LABEL not in captions


def test_summary_failure_keeps_the_result_cards():
    at, _ = _run_summary(side_effect=RuntimeError("Gemini down"))
    assert not at.exception
    assert [e.value for e in at.error] == [
        "The summary isn't working right now. The passages below still are."
    ]
    assert "Results (1)" in [h.value for h in at.subheader]
    # FIF-D16-FE: a retry button for the summary
    assert [b.label for b in at.main.button] == ["Try again"]


# FIF-D17-FE: one filter state for search, the table and every chart.


def _sidebar_box(at: AppTest, label: str):
    return next(b for b in at.sidebar.selectbox if b.label == label)


def _chart_specs(at: AppTest) -> list[str]:
    # Each Plotly chart's figure as JSON text, to check which materials it draws
    return [c.proto.spec for c in at.get("plotly_chart")]


def test_material_list_follows_the_experiment(app):
    _sidebar_box(app, "Experiment").select("FLEX").run()
    _assert_healthy(app)
    assert _sidebar_box(app, "Material").options == ["All", "Heptane", "Methanol"]


def test_material_from_another_experiment_goes_back_to_all(app):
    _sidebar_box(app, "Material").select("PMMA").run()
    _sidebar_box(app, "Experiment").select("FLEX").run()
    _assert_healthy(app)
    assert _sidebar_box(app, "Material").value == "All"
    assert "No experiments match these filters." not in " ".join(i.value for i in app.info)


def test_showing_line_and_every_chart_follow_one_choice(app):
    _sidebar_box(app, "Experiment").select("Saffire-II").run()
    _assert_healthy(app)
    assert "**Showing:** Saffire\\-II · all materials · 12–34\\% oxygen" in [
        m.value for m in app.markdown
    ]
    assert set(app.dataframe[0].value["experiment"]) == {"Saffire-II"}
    specs = _chart_specs(app)
    assert specs and all("Heptane" not in s and "Methanol" not in s for s in specs)
    assert any("Silicone" in s for s in specs)


def test_reset_filters_puts_everything_back(app):
    _sidebar_box(app, "Experiment").select("FLEX").run()
    _sidebar_box(app, "Material").select("Heptane").run()
    next(b for b in app.sidebar.button if b.label == "Reset filters").click().run()
    _assert_healthy(app)
    assert _sidebar_box(app, "Experiment").value == "All"
    assert _sidebar_box(app, "Material").value == "All"
    # Every row is back (compared with get_table(), so new data like BASS-II doesn't break this)
    assert len(app.dataframe[0].value) == len(get_table())
