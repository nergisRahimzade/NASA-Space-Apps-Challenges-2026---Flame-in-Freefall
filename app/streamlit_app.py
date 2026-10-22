import streamlit as st

st.set_page_config(page_title="Flame in Freefall", layout="wide")
st.title("Flame in Freefall")
st.write("Explore microgravity combustion experiments.")
query = st.text_input("Search the research reports")
