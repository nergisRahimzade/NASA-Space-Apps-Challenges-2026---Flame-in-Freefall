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