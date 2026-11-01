import pandas as pd
import plotly.express as px
import streamlit as st

from flame_in_freefall.api import search

st.set_page_config(page_title="Flame in Freefall", layout="wide")
st.title("Flame in Freefall")
st.write("Explore microgravity combustion experiments.")

query = st.text_input("Search the research reports")

# search() raises ValueError on a blank query, so only call it once something is typed
if query.strip():
    results = search(query)

    st.subheader("Summary")
    st.info("Summary coming soon. This will show cited takeaways from summarize().")

    st.subheader(f"Results ({len(results)})")
    for r in results:
        with st.container(border=True):
            st.write(r["text"])
            st.caption(f"{r['source']} · page {r['page']} · score {r['score']:.2f}")

st.divider()
st.subheader("Experiment data")

table = pd.read_csv("data/mock/master.mock.csv")

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
