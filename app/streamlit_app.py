import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make src/ importable when the package isn't installed (e.g. Streamlit Community Cloud).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flame_in_freefall.api import get_table, search  # noqa: E402
from flame_in_freefall.glossary import column_help, load_glossary  # noqa: E402
from flame_in_freefall.result_cards import (  # noqa: E402
    SNIPPET_WORDS,
    load_experiments,
    load_source_links,
    score_badge,
    snippet,
    source_line,
)

st.set_page_config(page_title="Flame in Freefall", layout="wide")
st.title("Flame in Freefall")
st.write("Explore microgravity combustion experiments.")

ALL = "All"

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

experiment = ALL
if not all_rows.empty:
    # Widen the slider if the data goes past 15-30%, so no rows are hidden by default.
    # master.csv stores oxygen as a range per row (FIF-D09-BE), so use the lowest min and highest
    # max.
    oxygen_low = min(15.0, float(all_rows["oxygen_pct_min"].min()))
    oxygen_high = max(30.0, float(all_rows["oxygen_pct_max"].max()))

    with st.sidebar:
        st.header("Filters")
        # Single choice, because the contract's get_table() and search() take one experiment
        experiment = st.selectbox(
            "Experiment",
            [ALL, *sorted(all_rows["experiment"].unique())],
            help=" ".join(
                [
                    tooltip.get("experiment", ""),
                    "Filters the search results and the experiment data.",
                ]
            ).strip(),
        )
        material = st.selectbox(
            "Material",
            [ALL, *sorted(all_rows["material"].unique())],
            help=tooltip.get("material"),
        )
        oxygen_min, oxygen_max = st.slider(
            "Oxygen %",
            oxygen_low,
            oxygen_high,
            (oxygen_low, oxygen_high),
            step=0.5,
            help=tooltip.get("oxygen_pct_min"),
        )

query = st.text_input("Search the research reports")
# Only experiments with reports can be searched; search() rejects any other name
searchable = experiment in load_experiments()
if experiment != ALL:
    if searchable:
        st.caption(f"Searching {experiment} reports only. Choose All in the sidebar to search all.")
    else:
        st.caption(f"There are no {experiment} reports to search, so search covers all of them.")
search_experiment = experiment if searchable else None

if not query.strip():
    st.caption("Try a question like: What gases were tested as fire suppressants in microgravity?")
else:
    try:
        with st.spinner("Searching the reports..."):
            start = time.perf_counter()
            if search_experiment is None:
                results = search(query)
            else:
                results = search(query, experiment=search_experiment)
            seconds = time.perf_counter() - start  # FIF-D11-BE: shown under "Results"
    except Exception:
        st.error("Search isn't working right now. Please try again in a moment.")
    else:
        st.subheader("Summary")
        st.info("Summary coming soon. This will show cited takeaways from summarize().")

        from_text = f" from {search_experiment}" if search_experiment else ""
        st.subheader(f"Results ({len(results)}){from_text}")
        # FIF-D11-BE: the first search after a deploy takes ~15 s (model + index), later ones ~0.1 s
        st.caption(f"Searched in {seconds:.2f} s")
        if not results and search_experiment:
            st.info(
                f"No {search_experiment} passages match. "
                "Try different words, or choose All in the sidebar."
            )
        elif not results:
            st.info("No matching passages found. Try different words.")
        else:
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

filters = {"oxygen_min": oxygen_min, "oxygen_max": oxygen_max}
if experiment != ALL:
    filters["experiment"] = experiment
if material != ALL:
    filters["material"] = material
table = pd.DataFrame(get_table(filters))

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
    st.caption(
        "Ranked by fastest flame spread. Fake numbers for building the layout. "
        "Real data replaces them on Day 13."
    )
    # One bar per material; a material can have several test rows, so keep its fastest
    ranking = (
        table.groupby("material", as_index=False)
        .agg(
            spread_rate_mm_s=("spread_rate_mm_s", "max"),
            experiment=("experiment", lambda names: ", ".join(sorted(set(names)))),
            tests=("material", "size"),
        )
        .sort_values("spread_rate_mm_s")  # Plotly draws the last row on top, so riskiest goes first
    )
    fig = px.bar(
        ranking,
        x="spread_rate_mm_s",
        y="material",
        orientation="h",
        text="spread_rate_mm_s",
        color="spread_rate_mm_s",
        color_continuous_scale="YlOrRd",
        hover_data={"experiment": True, "tests": True},
        labels={
            "spread_rate_mm_s": "Fastest flame spread (mm/s)",
            "material": "Material",
            "experiment": "Experiment",
            "tests": "Tests",
        },
    )
    # Labels sit outside the bars so a 0 (no spread) still shows a number
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig)

st.subheader("Flame spread by material and oxygen")
st.caption("Fake numbers for building the layout. Real data replaces them once master.csv lands.")

# Made-up grid, not NASA data: each material spreads faster as oxygen rises
base_rate = {
    "cotton": 0.8,
    "PMMA": 0.3,
    "cotton-fiberglass": 1.6,
    "Nomex": 0.1,
    "heptane": 0.5,
}
fake = pd.DataFrame(
    [
        {"material": m, "oxygen_pct": o, "spread_rate_mm_s": round(rate * (o - 15) / 6, 2)}
        for m, rate in base_rate.items()
        for o in [16, 18, 21, 25, 30]
    ]
)

# Reuse the sidebar filters so the heatmap matches the table
if experiment != ALL:
    in_experiment = all_rows.loc[all_rows["experiment"] == experiment, "material"]
    fake = fake[fake["material"].isin(in_experiment)]
if material != ALL:
    fake = fake[fake["material"] == material]
fake = fake[fake["oxygen_pct"].between(oxygen_min, oxygen_max)]

if fake.empty:
    st.info("No data for these filters.")
else:
    grid = fake.pivot(index="material", columns="oxygen_pct", values="spread_rate_mm_s")
    grid.columns = [f"{o}%" for o in grid.columns]
    fig = px.imshow(
        grid,
        color_continuous_scale="YlOrRd",
        text_auto=True,
        aspect="auto",
        labels={"x": "Oxygen", "y": "Material", "color": "Spread (mm/s)"},
    )
    # Plotly reads "16%" as a number, so force labels to keep the cells evenly spaced
    fig.update_xaxes(type="category")
    st.plotly_chart(fig)
