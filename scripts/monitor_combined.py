"""
Portugal vs DR Congo Complete Arbitrage Monitor
- Polymarket: Gamma API (reliable)
- 42.space: Playwright scraping (attempted) + manual fallback

Runs continuously, logs all data to files.
"""
from __future__ import annotations

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = Path(__file__).resolve().parent.parent
LOG_DIR = BASE / "logs" / "prt_cdr_combined"
LOG_DIR.mkdir(parents=True, exist_ok=True)

EVENT_SLUG = "fifwc-prt-cdr-2026-06-17"
GAMMA_URL = "https://gamma-api.polymarket.com"
FORTY_TWO_URL = "https://www.42.space/sport/fifa/0xBcD1Bc19b678b3677536431c0433F18C3E4e4723"
MATCH = "Portugal vs DR Congo"


def fetch_polymarket():
    """Fetch Polymarket data via Gamma API."""
    r = requests.get(f"{GAMMA_URL}/events", params={"slug": EVENT_SLUG}, timeout=15)
    r.raise_for_status()
    events = r.json()
    if not events:
        return None
    ev = events[0]
    markets = {}
    for m in ev.get("markets", []):
        outcomes = json.loads(m.get("outcomes", "[]"))
        prices = json.loads(m.get("outcomePrices", "[]"))
        markets[m["question"]] = {
            "condition_id": m.get("conditionId"),
            "outcomes": {outcomes[i]: float(prices[i]) for i in range(min(len(outcomes), len(prices)))},
            "volume": float(m.get("volume", 0)),
        }
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "polymarket_gamma_api",
        "event": ev.get("title", MATCH),
        "volume": float(ev.get("volume", 0)),
        "liquidity": float(ev.get("liquidity", 0)),
        "volume_24hr": float(ev.get("volume24hr", 0)),
        "competitive": float(ev.get("competitive", 0)),
        "active": ev.get("active"),
        "closed": ev.get("closed"),
        "markets": markets,
    }


def fetch_42_playwright():
    """Try to scrape 42.space with Playwright."""
    try:
        script = BASE / "scripts" / "_42_scraper.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=45,
            cwd=str(BASE),
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "42_playwright",
                "data": data,
            }
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "42_playwright",
                "error": result.stderr[:500] if result.stderr else "no output",
            }
    except subprocess.TimeoutExpired:
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "source": "42_playwright", "error": "timeout"}
    except Exception as e:
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "source": "42_playwright", "error": str(e)}


def compute_signal(poly_data, forty_two_data):
    """Compare Polymarket and 42 data for arbitrage opportunities."""
    signals = []

    if not poly_data:
        return signals

    markets = poly_data.get("markets", {})

    # 1. Internal Polymarket arbitrage check
    home_q = None; draw_q = None; away_q = None
    for q in markets:
        ql = q.lower()
        if "portugal win" in ql:
            home_q = q
        elif "draw" in ql:
            draw_q = q
        elif "congo win" in ql or "dr congo" in ql:
            away_q = q

    if home_q and draw_q and away_q:
        home_p = markets[home_q]["outcomes"].get("Yes", 0)
        draw_p = markets[draw_q]["outcomes"].get("Yes", 0)
        away_p = markets[away_q]["outcomes"].get("Yes", 0)
        total = home_p + draw_p + away_p
        profit = round((1.0 - total) * 100, 4)

        signals.append({
            "type": "polymarket_internal_arb",
            "home": round(home_p, 4),
            "draw": round(draw_p, 4),
            "away": round(away_p, 4),
            "total_yes_sum": round(total, 4),
            "profit_pct": profit,
            "is_arbitrage": total < 1.0,
        })

    # 2. Cross-platform comparison (if 42 data available)
    if forty_two_data and "error" not in forty_two_data:
        ft = forty_two_data.get("data", {})
        ft_markets = ft.get("markets", {})

        for pm_q, pm_mkt in markets.items():
            for ft_q, ft_data in ft_markets.items():
                # Simple fuzzy match
                pm_words = set(pm_q.lower().split())
                ft_words = set(ft_q.lower().split())
                overlap = pm_words & ft_words
                if len(overlap) > 2:
                    # Found matching market - compare prices
                    pm_yes = pm_mkt["outcomes"].get("Yes", 0)
                    ft_yes = ft_data.get("yes_price", 0)
                    if pm_yes and ft_yes:
                        diff = abs(pm_yes - ft_yes)
                        if diff > 0.03:  # >3% divergence = potential arb
                            signals.append({
                                "type": "cross_platform_arb",
                                "market": pm_q,
                                "polymarket_price": round(pm_yes, 4),
                                "42_price": round(ft_yes, 4),
                                "divergence_pct": round(diff * 100, 2),
                            })

    return signals


def log_full_snapshot(poly_data, ft_data, signals, iteration):
    """Save complete snapshot to JSON."""
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
    snapshot = {
        "iteration": iteration,
        "timestamp": ts,
        "polymarket": poly_data,
        "forty_two": ft_data,
        "signals": signals,
    }
    filepath = LOG_DIR / f"snapshot_{iteration:06d}_{ts}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    return filepath


def print_status(poly_data, ft_data, signals, iteration, filepath):
    """Console output."""
    ts = datetime.now().strftime("%H:%M:%S")
    mkt = poly_data.get("markets", {}) if poly_data else {}
    
    print(f"\n{'='*65}")
    print(f" [{ts}] #{iteration} | {MATCH}")
    print(f" Vol: ${poly_data['volume']:,.0f} | Liq: ${poly_data['liquidity']:,.0f}" if poly_data else "  [NO POLY DATA]")
    print(f"{'='*65}")
    
    print(f"\n  {'Polymarket Markets':<50} {'Yes':>8} {'No':>8}")
    print(f"  {'-'*66}")
    for q, m in sorted(mkt.items()):
        o = m.get("outcomes", {})
        yes_p = o.get("Yes", 0)
        no_p = o.get("No", 0)
        print(f"  {q[:48]:<50} {yes_p:>8.4f} {no_p:>8.4f}")
    
    print(f"\n  42.space: ", end="")
    if ft_data and "error" not in ft_data:
        ft_data_points = ft_data.get("data", {}).get("markets", {})
        print(f"{len(ft_data_points)} markets found")
        for name, info in ft_data_points.items():
            print(f"    {name[:50]}: {info}")
    elif ft_data and "error" in ft_data:
        print(f"ERROR: {ft_data['error'][:80]}")
    else:
        print("not fetched")
    
    for sig in signals:
        if sig["type"] == "polymarket_internal_arb":
            arb_flag = ">>> ARBITRAGE!" if sig["is_arbitrage"] else "(no arb)"
            print(f"\n  *** {sig['type']}: sum={sig['total_yes_sum']:.4f} profit={sig['profit_pct']:+.3f}% {arb_flag}")
        elif sig["type"] == "cross_platform_arb":
            print(f"\n  *** CROSS-PLATFORM: {sig['market'][:40]} PM={sig['polymarket_price']:.4f} 42={sig['42_price']:.4f} diff={sig['divergence_pct']:.2f}%")
    
    print(f"\n  -> {filepath}")


def main():
    interval = float(os.environ.get("INTERVAL", "15"))
    max_iter = int(os.environ.get("MAX_ITER", "0"))
    scrape_42 = os.environ.get("SCRAPE_42", "1") == "1"

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting combined monitor")
    print(f"  Polymarket: Gamma API (auto)")
    print(f"  42.space: {'Playwright (auto)' if scrape_42 else 'DISABLED'}")
    print(f"  Interval: {interval}s | Logs: {LOG_DIR}")
    print(f"  Press Ctrl+C to stop\n")

    iteration = 0
    successes = 0
    
    try:
        while True:
            iteration += 1
            if max_iter > 0 and iteration > max_iter:
                break

            poly_data = None
            ft_data = None
            signals = []

            # Fetch Polymarket
            try:
                poly_data = fetch_polymarket()
                successes += 1
            except Exception as e:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Polymarket error: {e}")

            # Fetch 42
            if scrape_42:
                ft_data = fetch_42_playwright()

            # Compute signals
            signals = compute_signal(poly_data, ft_data)

            # Log
            filepath = log_full_snapshot(poly_data, ft_data, signals, iteration)

            # Print
            print_status(poly_data, ft_data, signals, iteration, filepath)

            time.sleep(interval)

    except KeyboardInterrupt:
        pass

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Done. {successes}/{iteration} Polymarket fetches succeeded.")
    print(f"  Logs: {LOG_DIR}")

    # Build summary CSV
    csv_path = LOG_DIR / "summary.csv"
    snapshots = sorted(LOG_DIR.glob("snapshot_*.json"))
    if snapshots:
        with open(csv_path, "w") as f:
            f.write("iteration,timestamp,home_yes,draw_yes,away_yes,total_sum,profit_pct,"
                    "poly_volume,poly_liquidity,42_status\n")
            for sp in snapshots:
                try:
                    d = json.loads(sp.read_text(encoding="utf-8"))
                    poly = d.get("polymarket") or {}
                    mkt = poly.get("markets", {})
                    home_p = 0; draw_p = 0; away_p = 0
                    for q, mm in mkt.items():
                        ql = q.lower()
                        yes_p = mm["outcomes"].get("Yes", 0)
                        if "portugal win" in ql: home_p = yes_p
                        elif "draw" in ql: draw_p = yes_p
                        elif "congo" in ql: away_p = yes_p
                    total = home_p + draw_p + away_p
                    profit = (1.0 - total) * 100 if total else 0
                    ft_status = "error" if (d.get("forty_two") and "error" in d["forty_two"]) else "ok" if d.get("forty_two") else "none"
                    f.write(f"{d.get('iteration','')},{d.get('timestamp','')},"
                            f"{home_p},{draw_p},{away_p},{total},{profit:.4f},"
                            f"{poly.get('volume','')},{poly.get('liquidity','')},{ft_status}\n")
                except Exception:
                    pass
        print(f"  CSV: {csv_path}")


if __name__ == "__main__":
    main()
