from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from flame_in_freefall.api import search

st.set_page_config(page_title="Flame in Freefall", layout="wide")
st.title("Flame in Freefall")
st.write("Explore microgravity combustion experiments.")

query = st.text_input("Search the research reports")

if not query.strip():
    st.caption("Try a question like: Which materials burn fastest in microgravity?")
else:
    try:
        with st.spinner("Searching the reports..."):
            results = search(query)
    except Exception:
        st.error("Search isn't working right now. Please try again in a moment.")
    else:
        st.subheader("Summary")
        st.info("Summary coming soon. This will show cited takeaways from summarize().")

        st.subheader(f"Results ({len(results)})")
        if not results:
            st.info("No matching passages found. Try different words.")
        for r in results:
            with st.container(border=True):
                st.write(r["text"])
                st.caption(f"{r['source']} · page {r['page']} · score {r['score']:.2f}")

st.divider()
st.subheader("Experiment data")

# Build the path from this file's location so the app runs from any folder (and when deployed)
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "mock" / "master.mock.csv"
try:
    table = pd.read_csv(DATA_FILE)
except FileNotFoundError:
    st.error(f"Experiment data is missing: {DATA_FILE.name} was not found.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    experiments = st.multiselect(
        "Experiment", sorted(table["experiment"].unique()), placeholder="All"
    )
    materials = st.multiselect("Material", sorted(table["material"].unique()), placeholder="All")
    oxygen_min, oxygen_max = st.slider("Oxygen %", 15.0, 30.0, (15.0, 30.0), step=0.5)

# An empty multiselect means "no filter", so keep every row
if experiments:
    table = table[table["experiment"].isin(experiments)]
if materials:
    table = table[table["material"].isin(materials)]
table = table[table["oxygen_pct"].between(oxygen_min, oxygen_max)]

st.caption(f"{len(table)} rows")
if table.empty:
    st.info("No experiments match these filters. Try widening them in the sidebar.")
else:
    st.dataframe(table, hide_index=True, width="stretch")

    st.subheader("Flame spread vs. oxygen")
    fig = px.scatter(
        table,
        x="oxygen_pct",
        y="spread_rate_mm_s",
        color="material",
        hover_data=["experiment", "pressure_kpa", "flow_cm_s"],
        labels={
            "oxygen_pct": "Oxygen (%)",
            "spread_rate_mm_s": "Flame spread rate (mm/s)",
            "material": "Material",
        },
    )
    st.plotly_chart(fig)

st.subheader("Flame spread by material and oxygen")
st.caption("Fake numbers for building the layout. Real data replaces them on Day 9.")

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
if materials:
    fake = fake[fake["material"].isin(materials)]
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
