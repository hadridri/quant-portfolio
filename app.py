"""Flask server: serves the website and runs the Python models live on yfinance.

    pip install -r requirements.txt
    python app.py            ->  http://127.0.0.1:8050

In Spyder: open this file and press F5, then open the URL in a browser.
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from quant import montecarlo, pairs, sma
from quant.data import DataError

SITE = Path(__file__).resolve().parent / "site"
app = Flask(__name__, static_folder=None)


def _float(name, default, lo=None, hi=None):
    try:
        v = float(request.args.get(name, default))
    except ValueError:
        raise DataError(f"'{name}' must be a number.")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise DataError(f"'{name}' must be between {lo} and {hi}.")
    return v


def _period(default):
    p = request.args.get("period", default)
    if p not in {"1y", "2y", "3y", "5y", "10y"}:
        raise DataError("period must be one of 1y, 2y, 3y, 5y, 10y.")
    return p


@app.errorhandler(DataError)
def data_error(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(Exception)
def unexpected(e):
    app.logger.exception(e)
    return jsonify(error=f"Server error: {e}"), 500


@app.get("/api/health")
def health():
    return jsonify(ok=True)


@app.get("/api/montecarlo")
def api_montecarlo():
    tickers = request.args.get("tickers", ",".join(montecarlo.DEFAULT_TICKERS))
    weights = request.args.get("weights")
    weights = [float(x) for x in weights.split(",")] if weights else None
    return jsonify(montecarlo.run(
        tickers=tickers.split(","), weights=weights, period=_period("3y"),
        horizon=int(_float("horizon", 21, 1, 252)), n_sims=int(_float("sims", 10000, 1000, 50000)),
        alpha=_float("alpha", 0.95, 0.8, 0.999), notional=_float("notional", 1_000_000, 1)))


@app.get("/api/pairs")
def api_pairs():
    return jsonify(pairs.run(
        ticker_a=request.args.get("a", "V"), ticker_b=request.args.get("b", "MA"), period=_period("5y"),
        window=int(_float("window", 30, 5, 250)), hedge_window=int(_float("hedge_window", 120, 30, 500)),
        entry=_float("entry", 2.0, 0.1, 10), exit_=_float("exit", 0.5, 0, 10), stop=_float("stop", 3.5, 0.2, 20),
        cost_bps=_float("cost", 5, 0, 200), rolling=request.args.get("rolling", "1") != "0"))


@app.get("/api/sma")
def api_sma():
    execution = request.args.get("execution", "next_open")
    if execution not in {"next_open", "next_close"}:
        raise DataError("execution must be next_open or next_close.")
    return jsonify(sma.run(
        ticker=request.args.get("ticker", "SPY"), years=int(_float("years", 20, 2, 40)),
        fast=int(_float("fast", 50, 2, 399)), slow=int(_float("slow", 200, 3, 400)),
        cost_bps=_float("cost", 10, 0, 200), execution=execution))


@app.get("/")
def index():
    return send_from_directory(SITE, "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(SITE, path)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 8050)), debug=False)
