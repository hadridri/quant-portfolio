"""Market data layer: yfinance download with a small on-disk cache.

Yahoo throttles aggressive callers, so every download is cached for 15 minutes
in ./cache. clear_cache() forces a refresh. During market hours the last row is
today's session so far, so the last "close" is the latest available price.
"""
from __future__ import annotations

import hashlib
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_TTL = 15 * 60  # seconds


class DataError(ValueError):
    """Raised when a ticker cannot be downloaded or has too little history."""


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / (hashlib.md5(key.encode()).hexdigest() + ".pkl")


def _download(tickers: list[str], period: str) -> pd.DataFrame:
    key = f"{','.join(sorted(tickers))}|{period}"
    path = _cache_path(key)
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL:
        return pickle.loads(path.read_bytes())

    # Sequential download with retries: yfinance's threaded mode can drop a
    # ticker at random ("database is locked"), which would look like a bad symbol.
    raw = None
    for attempt in range(3):
        raw = yf.download(tickers, period=period, auto_adjust=True,
                          progress=False, group_by="column", threads=False)
        if raw is not None and not raw.empty and not _missing(raw, tickers):
            path.write_bytes(pickle.dumps(raw))
            return raw
        time.sleep(1 + attempt)
    if raw is None or raw.empty:
        raise DataError(f"No data returned by Yahoo Finance for {', '.join(tickers)}.")
    return raw  # partial result, not cached; get_prices reports the missing ticker


def _missing(raw: pd.DataFrame, tickers: list[str]) -> list[str]:
    close = raw["Close"]
    if isinstance(close, pd.Series):
        return [] if close.notna().any() else tickers
    return [t for t in tickers if t not in close.columns or close[t].isna().all()]


def clear_cache() -> None:
    for f in CACHE_DIR.glob("*.pkl"):
        f.unlink(missing_ok=True)


def get_closes(tickers, period: str = "3y") -> pd.DataFrame:
    """Close prices for a long ticker list. Unlike get_prices, bad tickers are
    skipped and each column keeps its own calendar (rows may contain gaps)."""
    tickers = clean_tickers(tickers)
    close = yf.download(tickers, period=period, auto_adjust=True, progress=False,
                        group_by="column", threads=True)["Close"]
    close = close.reindex(columns=tickers)
    missing = [t for t in tickers if close[t].isna().all()]
    if missing:  # threaded mode drops tickers at random, retry those one at a time
        retry = yf.download(missing, period=period, auto_adjust=True, progress=False,
                            group_by="column", threads=False)["Close"]
        if not retry.empty:
            close = close.combine_first(retry.reindex(columns=missing))
    return close.dropna(axis=1, how="all").reindex(columns=[t for t in tickers if t in close.columns])


def clean_tickers(tickers) -> list[str]:
    if isinstance(tickers, str):
        tickers = tickers.replace(";", ",").split(",")
    out = []
    for t in tickers:
        t = t.strip().upper()
        if t and t not in out:
            if len(t) > 15 or not all(c.isalnum() or c in ".-^=" for c in t):
                raise DataError(f"'{t}' is not a valid ticker symbol.")
            out.append(t)
    if not out:
        raise DataError("Please provide at least one ticker.")
    return out


def get_prices(tickers, period: str = "5y", min_obs: int = 250) -> pd.DataFrame:
    """Adjusted close prices, one column per ticker, rows with gaps dropped."""
    tickers = clean_tickers(tickers)
    raw = _download(tickers, period)
    close = raw["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    close = close.reindex(columns=tickers)

    missing = [t for t in tickers if close[t].dropna().empty]
    if missing:
        raise DataError(f"Unknown or delisted ticker(s): {', '.join(missing)}.")
    close = close.dropna()
    if len(close) < min_obs:
        raise DataError(f"Only {len(close)} common trading days found; need at least {min_obs}.")
    return close


def get_ohlc(ticker: str, period: str = "max", min_obs: int = 260) -> pd.DataFrame:
    """Open / Close for a single ticker (needed for next-open execution)."""
    ticker = clean_tickers(ticker)[0]
    raw = _download([ticker], period)
    df = pd.DataFrame({
        "Open": raw["Open"][ticker] if isinstance(raw["Open"], pd.DataFrame) else raw["Open"],
        "Close": raw["Close"][ticker] if isinstance(raw["Close"], pd.DataFrame) else raw["Close"],
    }).dropna()
    df = df[(df["Open"] > 0) & (df["Close"] > 0)]
    if len(df) < min_obs:
        raise DataError(f"{ticker}: only {len(df)} trading days available; need at least {min_obs}.")
    return df


def to_json_safe(obj):
    """Recursively convert numpy / pandas objects into JSON-serialisable Python."""
    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return to_json_safe(obj.tolist())
    if isinstance(obj, (pd.Timestamp,)):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, (np.floating, float)):
        return None if not np.isfinite(obj) else round(float(obj), 6)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def dates(index) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.DatetimeIndex(index)]


def perf_stats(returns: pd.Series, periods: int = 252, rf: float = 0.0) -> dict:
    """Standard performance block shared by the backtests."""
    r = returns.fillna(0.0)
    equity = (1 + r).cumprod()
    years = len(r) / periods
    total = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else np.nan
    vol = r.std() * np.sqrt(periods)
    sharpe = (r.mean() * periods - rf) / vol if r.std() > 0 else np.nan
    downside = r[r < 0].std() * np.sqrt(periods)
    sortino = r.mean() * periods / downside if downside > 0 else np.nan
    dd = equity / equity.cummax() - 1
    calmar = cagr / abs(dd.min()) if dd.min() < 0 else np.nan
    return {
        "total_return": total, "cagr": cagr, "volatility": vol, "sharpe": sharpe,
        "sortino": sortino, "max_drawdown": dd.min(), "calmar": calmar,
    }
