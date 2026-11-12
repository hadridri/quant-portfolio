# Portfolio risk simulator

Personal project in Python: a portfolio simulator to measure and manage risk,
with market data from Yahoo Finance. Built with Streamlit.

| Tab | What it does |
|-----|--------------|
| **Portfolio & VaR** | Build a portfolio with your own tickers and weights, backtest it, Monte Carlo VaR and Expected Shortfall, correlation matrix, then find the allocation with the best Sharpe ratio, tested walk-forward without future data |
| **Pairs trading** | Engle-Granger cointegration, rolling hedge ratio, z-score signals, with plain instructions on what to buy and sell today |
| **Golden cross** | SMA 50/200 scanner on about 300 tickers (137 PEA-eligible), 5-year backtest against buy & hold, e-mail alert on each new cross |

## Run locally

In **Spyder**: open `run_local.py` and press **F5**. Or from a terminal:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Each model also runs on its own in Spyder: `quant/montecarlo.py`, `quant/portfolio.py`, `quant/pairs.py`, `quant/sma.py`.

## Structure

```
streamlit_app.py       entry point
views/                 one file per page, common.py for shared helpers
quant/
  universe.py          tickers offered in the app and scanned for alerts
  data.py              yfinance download, 15-minute cache
  montecarlo.py        VaR and Expected Shortfall (Cholesky-correlated simulation)
  portfolio.py         backtest, max Sharpe optimiser, walk-forward test
  pairs.py             cointegration, z-score, half-life, trade instructions
  sma.py               SMA 50/200 backtest and scanner
  alert.py             golden / death cross e-mails
.github/workflows/
  sma-alert.yml        runs alert.py every 5 minutes on market days
```

## E-mail alerts

GitHub Actions runs `quant/alert.py` every 5 minutes on market days (one run loops through the session), using the latest price as today's
provisional close, plus one summary after the US close. Secrets: `SMTP_USER`, `SMTP_PASSWORD`
(Gmail App Password), `ALERT_TO`. Optional variables: `WATCHLIST` (extra tickers), `DAILY_DIGEST` (`0` to disable).

*Educational project, not investment advice.*
