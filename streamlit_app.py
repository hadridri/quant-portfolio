"""Portfolio risk simulator, Streamlit entry point.

    streamlit run streamlit_app.py

In Spyder: open run_local.py and press F5.
"""
import streamlit as st

from views import common

st.set_page_config(page_title="Portfolio risk simulator", layout="wide")

page = st.navigation([
    st.Page("views/home.py", title="Home", default=True),
    st.Page("views/portfolio.py", title="Portfolio & VaR", url_path="portfolio"),
    st.Page("views/pairs.py", title="Pairs trading", url_path="pairs"),
    st.Page("views/golden.py", title="Golden cross", url_path="golden-cross"),
], position="top")

common.sidebar()
page.run()
