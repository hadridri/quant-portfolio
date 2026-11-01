"""SMA 50/200 golden / death cross notifier.

Checks every ticker of the watchlist after the US close and, when the 50-day
SMA crossed the 200-day SMA on the latest session, sends:
    - an e-mail (any SMTP server, e.g. Gmail with an App Password), and/or
    - a push notification to your phone via ntfy.sh (free, no account).

Configuration (environment variables or GitHub Actions secrets):
    WATCHLIST       "SPY,QQQ,AAPL"         tickers to monitor
    SMTP_HOST       smtp.gmail.com
    SMTP_PORT       465
    SMTP_USER       you@gmail.com
    SMTP_PASSWORD   16-character Gmail App Password (never your real password)
    ALERT_TO        where to send the e-mail (defaults to SMTP_USER)
    NTFY_TOPIC      a hard-to-guess topic name, subscribe to it in the ntfy app

Usage
    python -m quant.alert              # daily check, notifies only on a new cross
    python -m quant.alert --test       # send a test notification now
    python -m quant.alert --digest     # always send the current status table
    python -m quant.alert --lookback 5 # treat crosses of the last 5 sessions as new
"""
from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
import urllib.request
from email.message import EmailMessage

from .sma import latest_cross

DEFAULT_WATCHLIST = "SPY,QQQ,AAPL,MSFT,NVDA,GLD"


def watchlist() -> list[str]:
    return [t.strip().upper() for t in os.getenv("WATCHLIST", DEFAULT_WATCHLIST).split(",") if t.strip()]


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
    print(f"  e-mail sent to {msg['To']}")
    return True


def send_push(title: str, text: str, tags: str = "chart_with_upwards_trend") -> bool:
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        print("  push skipped: NTFY_TOPIC not set")
        return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=text.encode(),
                                 headers={"Title": title, "Tags": tags, "Priority": "high"})
    urllib.request.urlopen(req, timeout=20).read()
    print(f"  push sent to ntfy topic '{topic}'")
    return True


def format_report(rows: list[dict], title: str) -> tuple[str, str]:
    lines = [title, ""]
    trs = []
    for r in rows:
        c = r.get("cross")
        tag = f"{c['type'].upper()} CROSS on {c['date']}" if c else r["regime"]
        gap = r["sma_fast"] / r["sma_slow"] - 1
        lines.append(f"{r['ticker']:<6} close {r['close']:>10.2f}  SMA50 {r['sma_fast']:>10.2f}  "
                     f"SMA200 {r['sma_slow']:>10.2f}  gap {gap:+.2%}  {tag}")
        colour = "#16a34a" if r["regime"] == "bullish" else "#dc2626"
        trs.append(f"<tr><td><b>{r['ticker']}</b></td><td>{r['close']:.2f}</td><td>{r['sma_fast']:.2f}</td>"
                   f"<td>{r['sma_slow']:.2f}</td><td>{gap:+.2%}</td>"
                   f"<td style='color:{colour};font-weight:600'>{tag}</td></tr>")
    lines += ["", "Signal formed at the close; act no earlier than the next session.",
              "Not investment advice - educational project."]
    html = (f"<div style='font-family:Helvetica,Arial,sans-serif'><h2>{title}</h2>"
            "<table cellpadding='6' style='border-collapse:collapse'><tr style='background:#f1f1f1'>"
            "<th>Ticker</th><th>Close</th><th>SMA 50</th><th>SMA 200</th><th>Gap</th><th>Status</th></tr>"
            + "".join(trs) + "</table><p style='color:#666;font-size:12px'>Signal formed at the close; "
            "act no earlier than the next session. Educational project, not investment advice.</p></div>")
    return "\n".join(lines), html


def notify(rows: list[dict], title: str) -> None:
    text, html = format_report(rows, title)
    print(text)
    send_email(title, text, html)
    send_push(title, "\n".join(l for l in text.splitlines()[2:] if l.strip())[:3500])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--test", action="store_true", help="send a test notification")
    p.add_argument("--digest", action="store_true", help="send the status table even without a cross")
    p.add_argument("--lookback", type=int, default=1, help="sessions to look back for a cross")
    args = p.parse_args(argv)

    if args.test:
        notify([latest_cross("SPY")], "Test - SMA crossover alerts are working")
        return 0

    rows, errors = [], []
    for t in watchlist():
        try:
            rows.append(latest_cross(t, lookback=args.lookback))
        except Exception as e:  # one bad ticker must not kill the whole job
            errors.append(f"{t}: {e}")
    for e in errors:
        print("  warning:", e, file=sys.stderr)

    hits = [r for r in rows if r["cross"]]
    if hits:
        names = ", ".join(f"{r['ticker']} {r['cross']['type']}" for r in hits)
        notify(hits, f"SMA 50/200 cross: {names}")
    elif args.digest:
        notify(rows, "SMA 50/200 daily status")
    else:
        print(f"No new cross on {len(rows)} tickers ({', '.join(r['ticker'] for r in rows)}).")
    return 1 if errors and not rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
