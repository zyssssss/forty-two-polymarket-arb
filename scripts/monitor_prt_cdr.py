"""
Portugal vs DR Congo - Cross-platform Arbitrage Monitor
Monitors Polymarket (Gamma API) every N seconds.
Records all price snapshots to JSON log files until match ends.
No real trades. No wallet needed.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "prt_cdr_monitor"
LOG_DIR.mkdir(parents=True, exist_ok=True)

EVENT_SLUG = "fifwc-prt-cdr-2026-06-17"
GAMMA_BASE = "https://gamma-api.polymarket.com"
EVENT_NAME = "Portugal vs DR Congo"
MATCH_UTC = "2026-06-17T17:00:00Z"


def fetch_event_data():
    """Fetch all market data for the event from Gamma API."""
    try:
        r = requests.get(
            f"{GAMMA_BASE}/events",
            params={"slug": EVENT_SLUG},
            timeout=10,
        )
        r.raise_for_status()
        events = r.json()
        if not events:
            return None
        return events[0]
    except Exception as e:
        print(f"  [ERR] Gamma API: {e}")
        return None


def parse_prices(event: dict) -> dict:
    """Extract structured price data from Gamma event response."""
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_name": event.get("title", EVENT_NAME),
        "volume": float(event.get("volume", 0)),
        "liquidity": float(event.get("liquidity", 0)),
        "volume_24hr": float(event.get("volume24hr", 0)),
        "competitive": float(event.get("competitive", 0)),
        "markets": {},
        "arbitrage_checks": {},
    }

    for m in event.get("markets", []):
        question = m.get("question", "")
        outcomes_raw = json.loads(m.get("outcomes", "[]"))
        prices_raw = json.loads(m.get("outcomePrices", "[]"))

        market = {
            "id": m.get("id"),
            "question": question,
            "condition_id": m.get("conditionId"),
            "volume": float(m.get("volume", 0)),
            "liquidity": float(m.get("liquidity", 0)),
            "outcomes": [],
            "clob_token_ids": json.loads(m.get("clobTokenIds", "[]")),
        }

        for i, outcome in enumerate(outcomes_raw):
            price = float(prices_raw[i]) if i < len(prices_raw) else 0
            market["outcomes"].append({
                "name": outcome,
                "price": price,
            })

        result["markets"][question] = market

    # Check for internal Polymarket arbitrage (Moneyline bias)
    # In a fair market, P(home) + P(draw) + P(away) should = 1.0
    moneyline_markets = {}
    for q, m in result["markets"].items():
        for o in m["outcomes"]:
            moneyline_markets[o["name"]] = o["price"]

    if "Yes" in moneyline_markets:
        yes_home = result["markets"].get("Will Portugal win on 2026-06-17?", {}).get("outcomes", [])
        yes_draw = result["markets"].get("Will Portugal vs. DR Congo end in a draw?", {}).get("outcomes", [])
        yes_away = result["markets"].get("Will DR Congo win on 2026-06-17?", {}).get("outcomes", [])

        home_p = yes_home[0]["price"] if yes_home else 0
        draw_p = yes_draw[0]["price"] if yes_draw else 0
        away_p = yes_away[0]["price"] if yes_away else 0

        total_yes = home_p + draw_p + away_p
        implied_margin = round((1.0 - total_yes) * 100, 4)

        result["arbitrage_checks"] = {
            "type": "moneyline_sum",
            "home_p": home_p,
            "draw_p": draw_p,
            "away_p": away_p,
            "total_yes_sum": round(total_yes, 4),
            "implied_profit_pct": implied_margin,
            "is_arbitrage": total_yes < 1.0,
        }

    return result


def log_snapshot(data: dict) -> Path:
    """Save snapshot to timestamped JSON file."""
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
    safe_ts = ts.replace(":", "-")
    filename = LOG_DIR / f"snapshot_{safe_ts}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filename


def print_summary(data: dict, iteration: int):
    """Console output."""
    ts = datetime.now().strftime("%H:%M:%S")
    arb = data.get("arbitrage_checks", {})

    print(f"\n{'='*60}")
    print(f" [{ts}] #{iteration} | {data.get('event_name', EVENT_NAME)}")
    print(f" Vol: ${data['volume']:,.0f} | Liq: ${data['liquidity']:,.0f} | Vol24h: ${data['volume_24hr']:,.0f}")
    print(f" Competitive: {data.get('competitive', 0):.4f}")
    print(f"{'='*60}")

    print(f"\n  {'Market':<45} {'Yes':>8} {'No':>8}")
    print(f"  {'-'*61}")
    for q, m in data.get("markets", {}).items():
        outcomes = m.get("outcomes", [])
        yes_p = outcomes[0]["price"] if len(outcomes) > 0 else 0
        no_p = outcomes[1]["price"] if len(outcomes) > 1 else 0
        print(f"  {q:<45} {yes_p:>8.4f} {no_p:>8.4f}")

    if arb:
        home = arb.get("home_p", 0)
        draw = arb.get("draw_p", 0)
        away = arb.get("away_p", 0)
        total = arb.get("total_yes_sum", 0)
        profit = arb.get("implied_profit_pct", 0)
        is_arb = arb.get("is_arbitrage", False)

        arb_flag = "<<< ARBITRAGE DETECTED!" if is_arb else "(no arb)"
        print(f"\n  Moneyline sum: {home:.4f}+{draw:.4f}+{away:.4f} = {total:.4f}")
        print(f"  Implied profit: {profit:+.4f}% {arb_flag}")

    print(f"\n  Log: {LOG_DIR}")


def main():
    interval = float(os.environ.get("INTERVAL", "10"))
    max_iter = int(os.environ.get("MAX_ITER", "0"))

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting monitor for: {EVENT_NAME}")
    print(f"  Polymarket event slug: {EVENT_SLUG}")
    print(f"  Interval: {interval}s | Log dir: {LOG_DIR}")
    print(f"  Press Ctrl+C to stop\n")

    iteration = 0
    try:
        while True:
            iteration += 1
            if max_iter > 0 and iteration > max_iter:
                print(f"\nReached max iterations ({max_iter}). Stopping.")
                break

            event = fetch_event_data()
            if event is None:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Failed to fetch. Retrying in {interval}s...")
                time.sleep(interval)
                continue

            data = parse_prices(event)
            log_snapshot(data)
            print_summary(data, iteration)

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Monitoring stopped. {iteration} snapshots saved.")
        print(f"  Logs: {LOG_DIR}")

    # Write a summary CSV for easy analysis
    csv_path = LOG_DIR / "summary.csv"
    snapshot_files = sorted(LOG_DIR.glob("snapshot_*.json"))
    if snapshot_files:
        with open(csv_path, "w") as f:
            f.write("timestamp,home_yes,draw_yes,away_yes,total_sum,implied_profit_pct,volume,liquidity\n")
            for sf in snapshot_files:
                try:
                    d = json.loads(sf.read_text(encoding="utf-8"))
                    arb = d.get("arbitrage_checks", {})
                    f.write(f"{d['timestamp']},{arb.get('home_p','')},{arb.get('draw_p','')},"
                            f"{arb.get('away_p','')},{arb.get('total_yes_sum','')},"
                            f"{arb.get('implied_profit_pct','')},{d['volume']},{d['liquidity']}\n")
                except Exception:
                    pass
        print(f"  Summary CSV: {csv_path}")


if __name__ == "__main__":
    main()
