import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant.pairs import action
from views.common import (BLUE, GREEN, GREY, ORANGE, RED, DataError, active, get_pair, get_pair_scan, label, md, money, num,
                          pct, show_chart, ticker_options)

st.title("Pairs trading")
st.write("Two stocks that usually move together sometimes drift apart. The strategy buys the cheap one, sells the expensive one, and closes when the gap is back to normal.")

st.session_state.setdefault("pair_a", "V")
st.session_state.setdefault("pair_b", "MA")


def pick_from_table() -> None:
    rows = st.session_state.pair_table.selection.rows
    if rows:
        row = st.session_state.pair_rows.iloc[rows[0]]
        st.session_state.pair_a, st.session_state.pair_b = row["a"], row["b"]


held = tuple(active()["weights"])
left, middle, right = st.columns([2, 2, 1])
options = ticker_options(st.session_state.pair_a, st.session_state.pair_b, *held)
a = left.selectbox("Stock A", options, key="pair_a", format_func=label, accept_new_options=True)
b = middle.selectbox("Stock B", options, key="pair_b", format_func=label, accept_new_options=True)
amount = right.number_input("Amount on A ($)", min_value=100, value=10_000, step=1000)
a, b = a.strip().upper(), b.strip().upper()

if len(held) >= 2:
    with st.expander("Find the best pairs in my portfolio"):
        rows = get_pair_scan(held)
        st.session_state.pair_rows = rows
        view = pd.DataFrame({"Pair": rows["a"] + " / " + rows["b"], "p-value": rows["p_value"].round(3),
                             "Half-life (days)": rows["half_life"].round(1),
                             "Linked": rows["p_value"].map(lambda p: "Yes" if p < 0.05 else "No")})
        st.dataframe(view, hide_index=True, on_select=pick_from_table, selection_mode="single-row", key="pair_table")
        st.caption("Click a row to load the pair. A p-value under 0.05 means the two stocks are statistically linked.")

try:
    with st.spinner("Loading prices from Yahoo Finance..."):
        res = get_pair(a, b, 2.0)
except DataError as e:
    st.error(str(e))
    st.stop()

p, t, s, S = res["params"], res["tests"], res["stats"], res["series"]
todo = action(res, amount)

# ---------- What to do today ----------
st.header("What to do today")
legs = " and ".join(f"**{side} {money(value)} of {ticker}**" for side, ticker, value in todo["legs"])
if not todo["linked"]:
    st.error(f"Do not trade this pair. {res['verdict']['text']}")
elif todo["state"] == "open":
    st.success(md(f"Position open: {legs}. {todo['text']}"))
else:
    st.info(f"No trade today. {todo['text']}")

# ---------- How to read ----------
long_a, long_b = todo["if_low"]
short_a, short_b = todo["if_high"]
rule = pd.DataFrame({
    "z-score": [f"Below -{p['entry']:g}", f"Above +{p['entry']:g}", f"Back near 0 (within ±{p['exit']:g})", f"Beyond ±{p['stop']:g}"],
    "Meaning": [f"{a} is cheap compared with {b}", f"{a} is expensive compared with {b}", "The gap has closed", "The link may be broken"],
    "What to do": [f"{long_a[0]} {a}, {long_b[0]} {b}", f"{short_a[0]} {a}, {short_b[0]} {b}", "Close both positions", "Close both positions (stop-loss)"],
})
st.dataframe(rule, hide_index=True, width="stretch")
st.caption(md(f"'Long the spread' simply means the first line ({long_a[0].lower()} {a}, {long_b[0].lower()} {b}), and 'short the spread' the second. "
              f"The hedge ratio today is {num(t['beta_latest'])}: for $1 of {a}, trade ${abs(t['beta_latest']):.2f} of {b}."))

# ---------- Chart ----------
st.subheader("Z-score: how far the gap is from normal")
fig = go.Figure()
fig.add_scatter(x=S["dates"], y=S["z"], name="z-score", line=dict(color=BLUE, width=1.5))
marks = [("long", "triangle-up", GREEN, f"{long_a[0].title()} {a} / {long_b[0].lower()} {b}"),
         ("short", "triangle-down", RED, f"{short_a[0].title()} {a} / {short_b[0].lower()} {b}"),
         ("exit", "circle", GREY, "Close"), ("stop", "x", ORANGE, "Stop-loss")]
for key, symbol, colour, name in marks:
    ev = res["events"][key]
    fig.add_scatter(x=ev["dates"], y=ev["z"], mode="markers", name=name, marker=dict(symbol=symbol, size=11, color=colour))
for level, colour in [(p["entry"], RED), (-p["entry"], GREEN)]:
    fig.add_hline(y=level, line=dict(color=colour, dash="dash", width=1))
fig.add_hline(y=0, line=dict(color=GREY, width=1))
show_chart(fig, height=460, last_days=365)

# ---------- Result ----------
st.subheader("Past results of this pair")
c = st.columns(4)
c[0].metric("Link (p-value)", num(t["coint_p"], 3), help="Under 0.05: the two stocks are statistically linked.")
c[1].metric("Half-life", "n/a" if t["half_life"] is None else f"{t['half_life']:.0f} days",
            help="Days the gap takes to close by half. 5 to 30 days is tradeable.")
c[2].metric("Sharpe ratio", num(s["sharpe"]), help="Return per unit of risk, after costs.")
c[3].metric("Trades won", "n/a" if s["win_rate"] is None else f"{s['win_rate']:.0%} of {s['n_trades']}")

fig = go.Figure(go.Scatter(x=S["dates"], y=[v * amount for v in S["equity"]], line=dict(color=BLUE, width=2), name="Strategy"))
fig.update_yaxes(tickprefix="$", tickformat=",.0f")
show_chart(fig, height=300)
st.caption(md(f"Value of {money(amount)} following the signals over 5 years, after costs. Today's price is included."))
