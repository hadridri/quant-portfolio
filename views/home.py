import streamlit as st

st.title("Portfolio risk simulator")
st.write("A portfolio simulator to measure and manage risk. Personal project in Python by Hadrien Bonhomme, "
         "with market data from Yahoo Finance.")

left, middle, right = st.columns(3)
with left:
    st.subheader("Portfolio & VaR")
    st.write("Build a portfolio, backtest it, measure how much it could lose, and find the allocation with the best Sharpe ratio.")
    st.page_link("views/portfolio.py", label="Open")
with middle:
    st.subheader("Pairs trading")
    st.write("Check whether two stocks move together, and see which one to buy and which one to sell today.")
    st.page_link("views/pairs.py", label="Open")
with right:
    st.subheader("Golden cross")
    st.write("See which stocks have just crossed their 200-day average, with e-mail alerts on each new cross.")
    st.page_link("views/golden.py", label="Open")

st.divider()
st.markdown("[E-mail](mailto:h.bonhomme@hotmail.com) · [LinkedIn](https://www.linkedin.com/in/hadrien-bonhomme) · "
            "[Code on GitHub](https://github.com/hadridri/quant-portfolio)")
st.caption("Educational project, not investment advice.")
