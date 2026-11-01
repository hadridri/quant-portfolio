# Quant Research Portfolio — Hadrien

Three risk-first quant projects built end to end in Python, served as an interactive website.
The models run **live on Yahoo Finance data** through a Flask API. A static snapshot of each
project is published to GitHub Pages, so recruiters can browse the site without a server.

| # | Project | What it shows |
|---|---------|---------------|
| 01 | **Monte Carlo VaR & Expected Shortfall** | 10,000 Cholesky-correlated scenarios; MC vs parametric vs historical VaR; correlation sensitivity and crisis stress test |
| 02 | **Pairs trading lab** | Any two tickers: Engle-Granger cointegration, rolling hedge ratio (no look-ahead), z-score signals with stop-loss, OU half-life, costs, rolling cointegration stability |
| 03 | **SMA 50/200 crossover** | Next-open execution, transaction costs, buy & hold benchmark, look-ahead bias measurement, trending vs choppy years, **e-mail / push alert on every golden or death cross** |

## Run locally

```bash
pip install -r requirements.txt
python app.py          # http://127.0.0.1:8050
```

In **Spyder**, open `app.py` and press F5, then open http://127.0.0.1:8050.
Each model also runs on its own and prints a report:

```bash
python -m quant.montecarlo
python -m quant.pairs
python -m quant.sma
```

## Structure

```
app.py                 Flask server (API + website)
build_static.py        pre-computes JSON snapshots into site/data for GitHub Pages
quant/
  data.py              yfinance download, 6-hour disk cache, performance stats
  montecarlo.py        Project 1
  pairs.py             Project 2
  sma.py               Project 3
  alert.py             golden / death cross notifier (SMTP e-mail + ntfy push)
site/                  index.html + one page per project, assets/, data/
.github/workflows/
  sma-alert.yml        daily cross check after the US close
  pages.yml            rebuilds snapshots and deploys site/ to GitHub Pages
```

## SMA cross alerts

The alert runs on GitHub Actions every weekday at 21:30 UTC, so it works with the laptop closed.

1. Create a Gmail **App Password** (Google Account → Security → 2-Step Verification → App passwords).
2. In the repo: Settings → Secrets and variables → Actions:
   - Secrets: `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`, optionally `NTFY_TOPIC`
   - Variable: `WATCHLIST` (e.g. `SPY,QQQ,AAPL,MSFT`)
3. Actions → *SMA crossover alert* → Run workflow → mode `test`.

Local equivalent: `export SMTP_HOST=smtp.gmail.com SMTP_USER=... SMTP_PASSWORD=...` then `python -m quant.alert --test`.

## Deploy the website

Push to GitHub, then Settings → Pages → Source: **GitHub Actions**. The `pages.yml` workflow refreshes the
data every weekday. On Pages the site shows the snapshot presets; custom tickers need the Flask API
(locally, or on a free host such as Render with `python app.py`).

## Methodology notes

- Signals are always executed **after** they are known: next close for pairs, next open for SMA.
- The pairs hedge ratio is a rolling OLS lagged by one day; the full-sample β is reported only for diagnosis.
- Costs are charged on every position change (both legs for pairs).
- Annualisation uses 252 trading days. For crypto (365-day markets), treat ratios as approximate.

*Educational project, not investment advice.*
