"""Project 3 - SMA 50/200 crossover backtest vs buy & hold.

Rules
    signal_t = 1 if SMA_fast > SMA_slow at the close of day t, else 0 (long / flat).
    The signal is only known after the close, so it is executed on day t+1:
      - "next_open":  fill at the next open (overnight gap kept at the old position)
      - "next_close": fill at the next close
    A transaction cost (fees + slippage, in bps) is charged on every change.

The module also re-runs the strategy with look-ahead (same-day close) and
without costs, to measure how much each shortcut would flatter the backtest.
Run in Spyder (F5) for a report on SPY.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import DataError, dates, get_ohlc, perf_stats, to_json_safe


def backtest(df: pd.DataFrame, signal: pd.Series, execution: str, cost_bps: float) -> tuple[pd.Series, pd.Series]:
    """Return (daily strategy returns, position held during the session)."""
    c, o = df["Close"], df["Open"]
    if execution == "same_close":           # look-ahead: trades at the close that created the signal
        held = signal
        ret = held.shift(1).fillna(0) * c.pct_change().fillna(0)
        change = held.diff().abs().fillna(held.abs())
        ret = ret - change * cost_bps / 1e4
        return ret, held
    if execution == "next_close":
        held = signal.shift(1).fillna(0)
        ret = held.shift(1).fillna(0) * c.pct_change().fillna(0)
        change = held.diff().abs().fillna(0)
    elif execution == "next_open":
        overnight = (o / c.shift(1) - 1).fillna(0)
        intraday = (c / o - 1).fillna(0)
        pos_night = signal.shift(2).fillna(0)   # position carried from before the signal
        pos_day = signal.shift(1).fillna(0)     # position after the open fill
        ret = (1 + pos_night * overnight) * (1 + pos_day * intraday) - 1
        held = pos_day
        change = pos_day.diff().abs().fillna(0)
    else:
        raise DataError("execution must be 'next_open', 'next_close' or 'same_close'.")
    return ret - change * cost_bps / 1e4, held


def run(ticker: str = "SPY", years: int = 20, fast: int = 50, slow: int = 200,
        cost_bps: float = 10.0, execution: str = "next_open") -> dict:
    fast, slow = int(fast), int(slow)
    if not 2 <= fast < slow <= 400:
        raise DataError("Need 2 <= fast < slow <= 400.")
    df = get_ohlc(ticker, period="max", min_obs=slow + 260)
    full = df.copy()
    full["sma_fast"] = full["Close"].rolling(fast).mean()
    full["sma_slow"] = full["Close"].rolling(slow).mean()
    full = full.dropna()
    if years and years > 0:
        full = full[full.index >= full.index[-1] - pd.DateOffset(years=int(years))]
    if len(full) < 252:
        raise DataError("Not enough history after the warm-up period.")

    signal = (full["sma_fast"] > full["sma_slow"]).astype(float)
    strat, held = backtest(full, signal, execution, cost_bps)
    bh = full["Close"].pct_change().fillna(0)

    variants = {
        "Strategy (realistic)": strat,
        "No transaction costs": backtest(full, signal, execution, 0.0)[0],
        "Look-ahead (same close)": backtest(full, signal, "same_close", cost_bps)[0],
        "Buy & hold": bh,
    }
    comparison = []
    for name, r in variants.items():
        s = perf_stats(r)
        s["name"] = name
        comparison.append(s)

    s_stats = perf_stats(strat)
    s_stats["exposure"] = held.mean()
    s_stats["n_trades"] = int(held.diff().abs().fillna(0).sum())
    s_stats["cost_drag"] = comparison[1]["cagr"] - comparison[0]["cagr"]
    s_stats["lookahead_bias"] = comparison[2]["cagr"] - comparison[0]["cagr"]
    b_stats = perf_stats(bh)

    diff = np.sign(full["sma_fast"] - full["sma_slow"])
    cross = diff.diff().fillna(0)
    crosses = [{"date": d, "type": "golden" if v > 0 else "death", "price": full["Close"].loc[d]}
               for d, v in cross[cross != 0].items()]

    eq_s = (1 + strat).cumprod()
    eq_b = (1 + bh).cumprod()
    dd_s = eq_s / eq_s.cummax() - 1
    dd_b = eq_b / eq_b.cummax() - 1

    yearly = pd.DataFrame({"strategy": (1 + strat).groupby(full.index.year).prod() - 1,
                           "buy_hold": (1 + bh).groupby(full.index.year).prod() - 1})
    # Market regime per year: trending if |return| / vol is large, choppy otherwise
    yr_vol = bh.groupby(full.index.year).std() * np.sqrt(252)
    yearly["regime"] = np.where((yearly["buy_hold"].abs() / yr_vol) > 0.75, "trending", "choppy")

    last = full.iloc[-1]
    gap = last["sma_fast"] / last["sma_slow"] - 1
    status = {
        "regime": "bullish" if gap > 0 else "bearish",
        "last_close": last["Close"], "sma_fast": last["sma_fast"], "sma_slow": last["sma_slow"],
        "gap": gap, "as_of": full.index[-1].strftime("%Y-%m-%d"),
        "last_cross": crosses[-1] if crosses else None,
        "days_since_cross": int((cross[::-1] != 0).values.argmax()) if crosses else None,
    }

    result = {
        "params": {"ticker": ticker.upper(), "years": years, "fast": fast, "slow": slow,
                   "cost_bps": cost_bps, "execution": execution,
                   "start": full.index[0].strftime("%Y-%m-%d"), "end": full.index[-1].strftime("%Y-%m-%d")},
        "status": status,
        "strategy": s_stats, "buy_hold": b_stats,
        "comparison": comparison,
        "series": {"dates": dates(full.index), "close": full["Close"].values,
                   "sma_fast": full["sma_fast"].values, "sma_slow": full["sma_slow"].values,
                   "eq_strategy": eq_s.values, "eq_buy_hold": eq_b.values,
                   "dd_strategy": dd_s.values, "dd_buy_hold": dd_b.values, "position": held.values},
        "crosses": crosses,
        "yearly": [{"year": int(y), **row} for y, row in yearly.iterrows()],
    }
    return to_json_safe(result)


def latest_cross(ticker: str, fast: int = 50, slow: int = 200, lookback: int = 1) -> dict:
    """Used by the alert job: did a cross happen in the last `lookback` sessions?"""
    df = get_ohlc(ticker, period="3y", min_obs=slow + 5)
    f = df["Close"].rolling(fast).mean()
    s = df["Close"].rolling(slow).mean()
    sign = np.sign(f - s).dropna()
    recent = sign.diff().dropna().iloc[-lookback:]
    hit = recent[recent != 0]
    return {
        "ticker": ticker.upper(), "as_of": df.index[-1].strftime("%Y-%m-%d"),
        "close": float(df["Close"].iloc[-1]), "sma_fast": float(f.iloc[-1]), "sma_slow": float(s.iloc[-1]),
        "regime": "bullish" if sign.iloc[-1] > 0 else "bearish",
        "cross": None if hit.empty else {"date": hit.index[-1].strftime("%Y-%m-%d"),
                                         "type": "golden" if hit.iloc[-1] > 0 else "death"},
    }


if __name__ == "__main__":
    res = run("SPY")
    print(f"\n{res['params']['ticker']} SMA {res['params']['fast']}/{res['params']['slow']}  "
          f"{res['params']['start']} -> {res['params']['end']}, {res['params']['cost_bps']} bps, {res['params']['execution']}\n")
    print(pd.DataFrame(res["comparison"]).set_index("name")[["cagr", "volatility", "sharpe", "max_drawdown"]].round(4))
    st = res["status"]
    print(f"\nToday: {st['regime']} (gap {st['gap']:.2%}), last cross {st['last_cross']}")
