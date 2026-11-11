import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make src/ importable when the package isn't installed (e.g. Streamlit Community Cloud).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flame_in_freefall.api import get_table, search, summarize  # noqa: E402
from flame_in_freefall.config import get_settings  # noqa: E402
from flame_in_freefall.filters import (  # noqa: E402
    ALL,
    Filters,
    from_choices,
    material_options,
    material_oxygen_test_counts,
)
from flame_in_freefall.glossary import column_help, load_glossary  # noqa: E402
from flame_in_freefall.page_states import (  # noqa: E402
    SEARCH_FAILED,
    SEARCH_SPINNER,
    SUMMARY_FAILED,
    TRY_AGAIN,
    no_results_tips,
    no_results_title,
    slow_search_note,
)
from flame_in_freefall.ranking_view import axis_label, filter_ranking, load_ranking  # noqa: E402
from flame_in_freefall.result_cards import (  # noqa: E402
    SNIPPET_WORDS,
    escape_markdown,
    load_experiments,
    load_source_links,
    score_badge,
    snippet,
    source_line,
)
from flame_in_freefall.summary_box import (  # noqa: E402
    LOADING_TEXT,
    NOT_FOUND_TEXT,
    SKELETON_HTML,
    summary_label,
    takeaway_markdown,
)

st.set_page_config(page_title="Flame in Freefall", layout="wide")
st.title("Flame in Freefall")
st.write("Explore microgravity combustion experiments.")


# FIF-D15-DAT: plain-word tooltips from data/glossary.json. A missing or broken glossary only
# removes the tooltips; the rest of the page still works.
try:
    glossary = load_glossary()
except Exception:
    glossary = []
tooltip = column_help(glossary)  # column name -> tooltip

# The table loads first: its experiments fill the sidebar, and search reads the same Experiment
# choice (FIF-D12-FE). If it fails, search still works, unfiltered.
try:
    # The unfiltered rows fill the sidebar, so its choices don't shrink as filters change
    all_rows = pd.DataFrame(get_table())
    table_error = False
except Exception:
    all_rows = pd.DataFrame()
    table_error = True

# FIF-D17-FE: one filter state for the whole page. The sidebar widgets keep their values in
# st.session_state (under these keys), and everything below reads the single `f` built from them.
FILTER_KEYS = ("f_experiment", "f_material", "f_oxygen")


def reset_filters() -> None:
    # Removing the saved values puts every widget back to its default on the next run
    for key in FILTER_KEYS:
        st.session_state.pop(key, None)


f = Filters(experiment=None, material=None, oxygen_min=0.0, oxygen_max=100.0)
if not all_rows.empty:
    # Widen the slider if the data goes past 15-30%, so no rows are hidden by default.
    # master.csv stores oxygen as a range per row (FIF-D09-BE), so use the lowest min and highest
    # max.
    oxygen_low = min(15.0, float(all_rows["oxygen_pct_min"].min()))
    oxygen_high = max(30.0, float(all_rows["oxygen_pct_max"].max()))

    with st.sidebar:
        st.header("Filters")
        st.caption("These filters apply to search, the table and every chart.")
        # Single choice, because the contract's get_table() and search() take one experiment
        experiment = st.selectbox(
            "Experiment",
            [ALL, *sorted(all_rows["experiment"].unique())],
            key="f_experiment",
            help=" ".join(
                [
                    tooltip.get("experiment", ""),
                    "Filters the search results and the experiment data.",
                ]
            ).strip(),
        )
        # Only offer materials from the chosen experiment. A material left over from another
        # experiment would empty every chart, so it goes back to All.
        materials = material_options(all_rows, experiment)
        if st.session_state.get("f_material", ALL) not in materials:
            st.session_state["f_material"] = ALL
        material = st.selectbox(
            "Material", materials, key="f_material", help=tooltip.get("material")
        )
        oxygen = st.slider(
            "Oxygen %",
            oxygen_low,
            oxygen_high,
            (oxygen_low, oxygen_high),
            step=0.5,
            key="f_oxygen",
            help=tooltip.get("oxygen_pct_min"),
        )
        st.button("Reset filters", on_click=reset_filters)
    f = from_choices(experiment, material, oxygen)

query = st.text_input("Search the research reports")
# Only experiments with reports can be searched; search() rejects any other name
searchable = f.experiment in load_experiments()
if f.experiment:
    if searchable:
        st.caption(
            f"Searching {f.experiment} reports only. Choose All in the sidebar to search all."
        )
    else:
        st.caption(f"There are no {f.experiment} reports to search, so search covers all of them.")
search_experiment = f.experiment if searchable else None

if not query.strip():
    st.caption("Try a question like: What gases were tested as fire suppressants in microgravity?")
else:
    try:
        with st.spinner(SEARCH_SPINNER):
            start = time.perf_counter()
            if search_experiment is None:
                results = search(query)
            else:
                results = search(query, experiment=search_experiment)
            seconds = time.perf_counter() - start  # FIF-D11-BE: shown under "Results"
    except Exception:
        st.error(SEARCH_FAILED)
        # FIF-D16-FE: clicking reruns the page, which searches again
        st.button(TRY_AGAIN, key="retry_search")
    else:
        from_text = f" from {search_experiment}" if search_experiment else ""
        if not results:
            # FIF-D16-FE: one clear empty state instead of an empty summary and an empty list.
            # Since contract v1.5, off-topic questions find nothing (scores under 0.30).
            st.subheader(f"Results (0){from_text}")
            st.caption(f"Searched in {seconds:.2f} s")
            with st.container(border=True):
                st.markdown(f"**{no_results_title(search_experiment)}**")
                st.markdown(no_results_tips(search_experiment))
        else:
            st.subheader("Summary")
            # FIF-D14-FE: show a skeleton now, so the result cards below appear while
            # summarize() works. The box is filled in after the cards.
            summary_box = st.empty()
            with summary_box.container():
                st.caption(LOADING_TEXT)
                st.markdown(SKELETON_HTML, unsafe_allow_html=True)

            st.subheader(f"Results ({len(results)}){from_text}")
            # FIF-D11-BE: the first search after a deploy takes ~15 s, later ones ~0.1 s
            st.caption(f"Searched in {seconds:.2f} s")
            note = slow_search_note(seconds)
            if note:
                st.caption(note)
            st.caption(
                "The closest passages, best first. They may not answer your question. "
                "Match is how close the wording and meaning are, from 0 to 1."
            )
            links = load_source_links()
            for r in results:
                with st.container(border=True):
                    st.markdown(
                        f"{score_badge(r['score'])} {source_line(r['source'], r['page'], links)}"
                    )
                    # The snippet is escaped, so $ or * in a report can't turn into math or bold
                    st.markdown(snippet(r["text"], query))
                    # Only offer the full passage when the snippet had to cut some of it off
                    if len(r["text"].split()) > SNIPPET_WORDS:
                        with st.expander("Full passage"):
                            # st.text, not st.write: shows the passage exactly as written
                            st.text(r["text"])

            try:
                # FIF-D15-AI (contract v1.7): passing the question keeps only takeaways that
                # answer it, and gives "not found" when none do.
                summary = summarize(results, question=query)
            except Exception:
                with summary_box.container():
                    st.error(SUMMARY_FAILED)
                    # FIF-D16-FE: clicking reruns the page, which asks for the summary again
                    st.button(TRY_AGAIN, key="retry_summary")
            else:
                with summary_box.container():
                    if summary["not_found"]:
                        st.info(NOT_FOUND_TEXT)
                    else:
                        ai = bool(get_settings().gemini_api_key)
                        st.caption(summary_label(ai_available=ai))
                        st.markdown(takeaway_markdown(summary, results, links))

# FIF-D15-DAT: words like LOI come up in the reports but not in the table, so list them all here.
if glossary:
    with st.expander("What do these words mean?"):
        for t in glossary:
            st.markdown(f"**{t['term']}**: {t['tooltip']}")

st.divider()
st.subheader("Experiment data")

if table_error:
    st.error("Experiment data isn't available right now. Please try again in a moment.")
    st.stop()
if all_rows.empty:
    st.info("No experiment data has been loaded yet.")
    st.stop()

# FIF-D17-FE: every chart below uses this one filter state
st.markdown(f"**Showing:** {escape_markdown(f.describe())}")
table = pd.DataFrame(get_table(f.table_filters()))

st.caption(f"{len(table)} rows")
if table.empty:
    st.info("No experiments match these filters. Try widening them in the sidebar.")
else:
    # Hovering a column header shows its plain-word tooltip (FIF-D15-DAT)
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            col: st.column_config.Column(help=tooltip[col]) for col in table if col in tooltip
        },
    )

    st.subheader("Flame spread vs. oxygen")
    fig = px.scatter(
        table,
        # The low end of each row's oxygen range (FIF-D09-BE: master.csv has min/max columns)
        x="oxygen_pct_min",
        y="spread_rate_mm_s",
        color="material",
        hover_data=["experiment", "oxygen_pct_max", "pressure_kpa_min", "flow_cm_s_min"],
        labels={
            "oxygen_pct_min": "Oxygen (%)",
            "spread_rate_mm_s": "Flame spread rate (mm/s)",
            "material": "Material",
        },
    )
    st.plotly_chart(fig)

st.subheader("Riskiest materials")
# FIF-D13-FE: real ranking from data/ranking.csv (FIF-D13-DAT). Each experiment is ranked on
# its own measure, so each gets its own chart; their ranks can't be compared.
ranking = load_ranking()
if ranking.empty:
    st.info("The riskiness ranking hasn't been built yet.")
else:
    ranked = filter_ranking(
        ranking,
        experiment=f.experiment,
        material=f.material,
        oxygen_min=f.oxygen_min,
        oxygen_max=f.oxygen_max,
    )
    if f.experiment and f.experiment not in set(ranking["experiment"]):
        st.info(f"No ranking for {f.experiment}: its tests have no recorded results.")
    elif ranked.empty:
        st.info("No ranked materials match these filters. Try widening them in the sidebar.")

    sheets = ranked[ranked["experiment"] == "Saffire-II"]
    if not sheets.empty:
        st.markdown("**Saffire-II: solid materials, ranked by how fast the flame spread**")
        st.caption(
            "Average spread over the whole burn (burn length ÷ burn time). All samples were "
            "tested at about 22% oxygen and 20 cm/s airflow, so this ranks materials but says "
            "nothing about oxygen. Burn time may include ignition, so speeds may read a bit low."
        )
        # Plotly draws the last row on top, so sorting low to high puts the riskiest first
        sheets = sheets.sort_values("risk_value")
        fig = px.bar(
            sheets,
            x="risk_value",
            y="material",
            orientation="h",
            text="risk_value",
            hover_data={"risk_rank": True, "tests": True, "oxygen_pct": True, "risk_value": False},
            labels={
                "risk_value": axis_label(sheets),
                "material": "Material",
                "risk_rank": "Rank",
                "tests": "Samples",
                "oxygen_pct": "Oxygen (%)",
            },
        )
        # One color: the bar length already shows the value. Labels sit outside the bars so
        # Silicone's 0 (never spread) still shows a number.
        fig.update_traces(
            marker_color="#F77F00", texttemplate="%{x:.2f} mm/s", textposition="outside",
            cliponaxis=False,
        )  # fmt: skip
        # Leave room past the longest bar so its label isn't cut off
        fig.update_xaxes(range=[0, max(sheets["risk_value"].max(), 0.1) * 1.3])
        st.plotly_chart(fig)

    droplets = ranked[ranked["experiment"] == "FLEX"].sort_values(["material", "oxygen_pct"])
    if not droplets.empty:
        st.markdown(
            "**FLEX: fuel droplets, how often the flame kept burning at each oxygen level**"
        )
        st.caption(
            "Of the tests that finished, the share where the flame burned until the fuel was "
            "gone instead of going out. Tests cut short (disruptions) are left out. Some points "
            "rest on very few tests, so hover to see the counts."
        )
        fig = px.line(
            droplets,
            x="oxygen_pct",
            y="risk_value",
            color="material",
            markers=True,
            hover_data={
                "tests": True,
                "completion": True,
                "extinction": True,
                "disruption": True,
                "risk_rank": True,
            },
            labels={
                "oxygen_pct": "Oxygen (%)",
                "risk_value": axis_label(droplets),
                "material": "Fuel",
                "tests": "Tests",
                "completion": "Kept burning",
                "extinction": "Went out",
                "disruption": "Cut short",
                "risk_rank": "Rank",
            },
        )
        fig.update_yaxes(range=[-0.05, 1.05], tickformat=".0%")
        st.plotly_chart(fig)

st.subheader("Tests run by material and oxygen level")
# FIF-D17-FE: real counts from the same filtered table, replacing the made-up grid, so this chart
# follows the sidebar like the others.
st.caption(
    "How many tests were run for each material at each oxygen level, so you can see where the "
    "data is thin. FLEX-2 is left out: its rows are planned ranges, one per fuel, not tests."
)
grid = material_oxygen_test_counts(table) if not table.empty else pd.DataFrame()
if grid.empty:
    st.info("No tests match these filters. Try widening them in the sidebar.")
else:
    fig = px.imshow(
        grid,
        color_continuous_scale="Oranges",
        text_auto=True,
        aspect="auto",
        labels={"x": "Oxygen", "y": "Material", "color": "Tests"},
    )
    # Plotly reads "16%" as a number, so force labels to keep the cells evenly spaced
    fig.update_xaxes(type="category")
    st.plotly_chart(fig)
