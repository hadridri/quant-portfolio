"""Shared helpers for the Streamlit pages: cached data, sidebar, charts, saved portfolios."""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant import data, montecarlo, pairs, portfolio, sma
from quant.data import DataError
from quant.universe import NAMES, PEA, UNIVERSE, label

REFRESH_SECONDS = 15 * 60
SCAN_URL = "https://raw.githubusercontent.com/hadridri/quant-portfolio/alerts-data/scan.json"
DEFAULT_PORTFOLIO = {"AAPL": 0.2, "MSFT": 0.2, "JPM": 0.2, "XOM": 0.2, "GLD": 0.2}
GREEN, RED, BLUE, ORANGE, GREY = "#16a34a", "#dc2626", "#2563eb", "#ea580c", "#9ca3af"


# ---------- Cached computations (15 minutes, cleared by the Refresh button) ----------
@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_returns(tickers: tuple, period: str = "5y") -> pd.DataFrame:
    return portfolio.daily_returns(list(tickers), period)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_var(tickers: tuple, weights: tuple, notional: float, horizon: int, alpha: float) -> dict:
    return montecarlo.run(list(tickers), list(weights), horizon=horizon, alpha=alpha, notional=notional)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_pair(a: str, b: str, entry: float) -> dict:
    return pairs.run(a, b, entry=entry)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_pair_scan(tickers: tuple) -> pd.DataFrame:
    return pairs.scan_pairs(data.get_prices(list(tickers), period="5y"))


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_sma(ticker: str) -> dict:
    return sma.run(ticker)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_sma_portfolio(tickers: tuple, weights: tuple) -> dict:
    value = (1 + portfolio.daily_returns(list(tickers), "10y") @ np.array(weights)).cumprod() * 100
    return sma.run("My portfolio", execution="next_close", df=pd.DataFrame({"Open": value, "Close": value}))


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_scan() -> pd.DataFrame:
    return pd.DataFrame(sma.scan(data.get_closes(UNIVERSE)))


@st.cache_data(ttl=300, show_spinner=False)
def get_alert_status() -> dict | None:
    """Last run of the e-mail job, published on the alerts-data branch."""
    try:
        with urllib.request.urlopen(SCAN_URL, timeout=10) as r:
            return json.load(r)
    except Exception:
        return None


# ---------- Portfolios ----------
def active() -> dict:
    return st.session_state.setdefault("active", {"name": "Sample portfolio", "weights": DEFAULT_PORTFOLIO,
                                                  "notional": 100_000.0})


def set_active(name: str, weights: dict, notional: float) -> None:
    st.session_state.active = {"name": name, "weights": weights, "notional": notional}


# Saved portfolios live in the visitor's own browser (localStorage), so each person
# keeps theirs and a public visitor cannot change anyone else's.
_STORE_JS = """
export default function(component) {
  const { data, setStateValue } = component;
  const key = "saved_portfolios";
  if (data && data.write) localStorage.setItem(key, data.write);
  const value = localStorage.getItem(key) || "{}";
  if (window.__savedPortfolios !== value) {
    window.__savedPortfolios = value;
    setStateValue("saved", value);
  }
}
"""
_store = st.components.v2.component("browser_store", js=_STORE_JS)


def sync_saved() -> dict:
    loaded = "saved" in st.session_state
    write = json.dumps(st.session_state.saved) if loaded else None
    result = _store(key="browser_store", data={"write": write}, on_saved_change=lambda: None)
    if not loaded and result.saved:
        st.session_state.saved = json.loads(result.saved)
    return st.session_state.get("saved", {})


def save_portfolio(name: str, weights: dict, notional: float) -> None:
    st.session_state.setdefault("saved", {})[name] = {"weights": weights, "notional": notional}


# ---------- Sidebar ----------
def refresh() -> None:
    st.cache_data.clear()
    data.clear_cache()
    st.session_state.fetched_at = time.time()


@st.fragment(run_every="5m")
def _auto_refresh() -> None:
    if time.time() - st.session_state.fetched_at > REFRESH_SECONDS:
        st.session_state.fetched_at = time.time()
        st.rerun()


def sidebar() -> None:
    st.session_state.setdefault("fetched_at", time.time())
    with st.sidebar:
        if st.button("Refresh data", type="primary", width="stretch"):
            refresh()
            st.rerun()
        fetched = datetime.fromtimestamp(st.session_state.fetched_at, timezone.utc)
        st.caption(f"Yahoo Finance prices, loaded {fetched:%d %b %H:%M} UTC. Updates by itself every 15 minutes.")
        _auto_refresh()

        st.divider()
        pf = active()
        st.markdown(f"**Active portfolio:** {pf['name']}")
        st.caption(" · ".join(f"{t} {w:.0%}" for t, w in pf["weights"].items()))

        saved = sync_saved()
        if saved:
            choice = st.selectbox("Saved portfolios", list(saved), index=None, placeholder="Open a portfolio")
            if choice:
                left, right = st.columns(2)
                if left.button("Open", width="stretch"):
                    set_active(choice, saved[choice]["weights"], saved[choice]["notional"])
                    st.rerun()
                if right.button("Delete", width="stretch"):
                    del st.session_state.saved[choice]
                    st.rerun()


# ---------- Widgets ----------
def ticker_options(*extra: str) -> list[str]:
    return list(dict.fromkeys([*extra, *UNIVERSE]))


def show_chart(fig: go.Figure, height: int = 420, last_days: int | None = None, selector: bool = True) -> None:
    """Plotly chart: scroll or drag to zoom, double-click to reset."""
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                      legend=dict(orientation="h", y=1.08, x=0), dragmode="zoom")
    if selector:
        fig.update_xaxes(rangeselector=dict(y=1.16, buttons=[
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(count=6, label="6M", step="month", stepmode="backward"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=2, label="2Y", step="year", stepmode="backward"),
            dict(step="all", label="All")]))
        fig.update_layout(margin=dict(t=70))
    if last_days:
        end = pd.Timestamp(fig.data[0].x[-1])
        fig.update_xaxes(range=[end - pd.Timedelta(days=last_days), end + pd.Timedelta(days=5)])
    st.plotly_chart(fig, width="stretch", config={"scrollZoom": True, "displaylogo": False})


def pct(v, digits: int = 1) -> str:
    return "n/a" if v is None or not np.isfinite(v) else f"{v:.{digits}%}"


def num(v, digits: int = 2) -> str:
    return "n/a" if v is None or not np.isfinite(v) else f"{v:.{digits}f}"


def money(v) -> str:
    return "n/a" if v is None or not np.isfinite(v) else f"${v:,.0f}"


def md(text: str) -> str:
    """Escape dollars, otherwise Streamlit reads them as LaTeX."""
    return text.replace("$", "\\$")


__all__ = ["DataError", "NAMES", "label"]
