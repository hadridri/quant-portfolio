"""Golden / death cross e-mail alerts.

Runs on GitHub Actions every 15 minutes on market days. Each run scans every ticker of
quant/universe.py (plus the WATCHLIST variable) using the latest price as today's
provisional close, and sends an e-mail when SMA 50 has crossed SMA 200.

state.json remembers which side each ticker was on, so a cross is reported once.
One e-mail per ticker per day at most, even if the averages touch several times.

Configuration (environment variables or GitHub Actions secrets):
    SMTP_HOST, SMTP_PORT    smtp.gmail.com, 465
    SMTP_USER               sender address
    SMTP_PASSWORD           Gmail App Password (never your real password)
    ALERT_TO                recipient (defaults to SMTP_USER)
    WATCHLIST               extra tickers, comma separated
    DAILY_DIGEST            "0" disables the end-of-day summary e-mail

Usage
    python -m quant.alert          # one check, writes state.json and scan.json
    python -m quant.alert --test   # send a sample alert now
"""
from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

from .data import get_closes
from .sma import scan
from .universe import NAMES, UNIVERSE

DIGEST_HOUR_UTC = 21.25     # first run after the US close
HISTORY_SIZE = 200
FOOTER = "Based on the latest price, confirmed at the close. Educational project, not investment advice."


def watchlist() -> list[str]:
    extra = [t.strip().upper() for t in os.getenv("WATCHLIST", "").split(",") if t.strip()]
    return list(dict.fromkeys(UNIVERSE + extra))


def send_email(subject: str, text: str, html: str) -> bool:
    host, user = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER")
    pwd = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "")  # Gmail shows app passwords in groups of 4
    if not (host and user and pwd):
        print("  e-mail skipped: SMTP_HOST / SMTP_USER / SMTP_PASSWORD not set")
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, os.getenv("ALERT_TO") or user
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    port = int(os.getenv("SMTP_PORT", "465"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)
    print("  e-mail sent")
    return True


def _describe(r: dict) -> str:
    return (f"{r['ticker']} ({NAMES.get(r['ticker'], r['ticker'])}): price {r['price']:.2f}, "
            f"SMA 50 {r['sma_fast']:.2f}, SMA 200 {r['sma_slow']:.2f}")


def _email_body(title: str, sections: list[tuple[str, list[dict]]]) -> tuple[str, str]:
    text, html = [title, ""], [f"<div style='font-family:Arial,sans-serif'><h3>{title}</h3>"]
    for heading, rows in sections:
        if rows:
            text += [heading] + [f"  {_describe(r)}" for r in rows] + [""]
            html.append(f"<p><b>{heading}</b></p><ul>" + "".join(f"<li>{_describe(r)}</li>" for r in rows) + "</ul>")
    text.append(FOOTER)
    html.append(f"<p style='color:#666;font-size:12px'>{FOOTER}</p></div>")
    return "\n".join(text), "".join(html)


def send_cross_alert(golden: list[dict], death: list[dict], prefix: str = "") -> bool:
    names = ", ".join(r["ticker"] for r in golden + death)
    kind = "Golden cross" if golden and not death else "Death cross" if death and not golden else "SMA cross"
    title = f"{prefix}{kind}: {names}"
    return send_email(title, *_email_body(title, [
        ("Golden cross (SMA 50 moved above SMA 200):", golden),
        ("Death cross (SMA 50 moved below SMA 200):", death),
    ]))


def check(state: dict, rows: list[dict], now: datetime) -> tuple[list[dict], list[dict]]:
    """Update `state` and return the (golden, death) crosses to report."""
    today = now.strftime("%Y-%m-%d")
    tickers = state.setdefault("tickers", {})
    golden, death = [], []
    for r in rows:
        prev = tickers.get(r["ticker"])
        if prev is None:                        # first time seen: nothing to compare with
            tickers[r["ticker"]] = {"sign": r["sign"], "last_alert": None}
            continue
        if r["sign"] == prev["sign"]:
            continue
        prev["sign"] = r["sign"]
        if prev.get("last_alert") == today:     # the averages are touching: no repeat today
            continue
        prev["last_alert"] = today
        (golden if r["sign"] > 0 else death).append(r)
        state.setdefault("history", []).insert(0, {
            "time": now.strftime("%Y-%m-%d %H:%M"), "ticker": r["ticker"],
            "type": "golden" if r["sign"] > 0 else "death", "price": r["price"]})
    state["history"] = state.get("history", [])[:HISTORY_SIZE]
    return golden, death


def send_digest(state: dict, rows: list[dict], now: datetime) -> None:
    """One summary per session, on the first run after the US close (GitHub can start
    that run hours late, hence the window running past midnight UTC)."""
    hour = now.hour + now.minute / 60
    session = (now - timedelta(hours=7)).strftime("%Y-%m-%d")
    if not (hour >= DIGEST_HOUR_UTC or hour < 7) or state.get("digest_date") == session or os.getenv("DAILY_DIGEST") == "0":
        return
    crossed = {h["ticker"] for h in state.get("history", []) if h["time"] >= f"{session} 07:00"}
    today_rows = [r for r in rows if r["ticker"] in crossed]
    near = sorted((r for r in rows if abs(r["gap"]) < 0.01 and r["ticker"] not in crossed), key=lambda r: abs(r["gap"]))
    title = f"SMA 50/200 daily summary: {len(today_rows)} cross(es) today"
    body = _email_body(f"{title} ({len(rows)} tickers checked)", [
        ("Crossed today:", today_rows), ("Close to crossing (gap under 1%):", near[:15])])
    if send_email(title, *body):
        state["digest_date"] = session


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--test", action="store_true", help="send a sample alert")
    p.add_argument("--state", default="state.json")
    p.add_argument("--scan", default="scan.json")
    args = p.parse_args(argv)

    if args.test:
        rows = scan(get_closes(["SPY", "AAPL"]))
        return 0 if send_cross_alert(rows[:1], rows[1:], prefix="TEST - ") else 1

    path = Path(args.state)
    state = json.loads(path.read_text()) if path.exists() and path.stat().st_size else {}
    tickers = watchlist()
    closes = get_closes(tickers)
    rows = scan(closes)
    if len(rows) < len(tickers) / 2:
        print(f"Only {len(rows)}/{len(tickers)} tickers loaded: Yahoo problem, skipping this run.")
        return 1

    now = datetime.now(timezone.utc)
    golden, death = check(state, rows, now)
    if golden or death:
        send_cross_alert(golden, death)     # raises on failure: state is not saved, next run retries
    send_digest(state, rows, now)

    path.write_text(json.dumps(state, separators=(",", ":")))
    Path(args.scan).write_text(json.dumps({
        "checked_at": now.strftime("%Y-%m-%d %H:%M"), "rows": rows, "history": state.get("history", [])[:30],
    }, separators=(",", ":")))
    print(f"{now:%H:%M} UTC: {len(rows)}/{len(tickers)} tickers checked, "
          f"{len(golden)} golden, {len(death)} death.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
