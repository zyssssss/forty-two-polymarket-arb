"""
Portugal vs DR Congo - Full Cross-Platform Arbitrage Monitor
Uses live APIs:
  - Polymarket: Gamma API + CLOB API
  - 42.space: REST API (rest.ft.42.space)

Runs continuously, records snapshots, detects arbitrage opportunities.
No trades executed. All data logged to files.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
LOG_DIR = BASE / "logs" / "prt_cdr_full_monitor"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# === Configuration ===
POLY_GAMMA_URL = "https://gamma-api.polymarket.com"
POLY_CLOB_URL = "https://clob.polymarket.com"
FORTY_TWO_API = "https://rest.ft.42.space"
FORTY_TWO_CONTRACT = "0xBcD1Bc19b678b3677536431c0433F18C3E4e4723"
MATCH = "Portugal vs DR Congo"
MATCH_END = "2026-06-17T17:00:00Z"

# Polymarket YES token IDs
POLY_TOKENS = {
    "portugal_win_yes": "76071109489406808599878692125264766321676001700733380917373465772841855210643",
    "draw_yes": "2328333301741750345417630454121106244367883081134709887163965516147303610120",
    "congo_win_yes": "59454896622130760276442490722222126894150925046963444585060045915889624278803",
}

# 42 exact scores mapping: which scores = Portugal Win
POR_WIN_SCORES = [
    "1-0", "2-0", "2-1", "3-0", "3-1", "3-2",
    ">=4-0", ">=4-1", ">=4-2", ">=4-3",
]
DRAW_SCORES = ["0-0", "1-1", "2-2", "3-3", ">=4->=4"]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "PolymarketArbBot/1.0",
    "Accept": "application/json",
})


def fetch_polymarket_gamma():
    """Fetch event overview via Gamma API."""
    r = SESSION.get(f"{POLY_GAMMA_URL}/events", params={"slug": "fifwc-prt-cdr-2026-06-17"}, timeout=15)
    r.raise_for_status()
    events = r.json()
    if not events:
        return None
    ev = events[0]
    markets = {}
    for m in ev.get("markets", []):
        prices = json.loads(m.get("outcomePrices", "[]"))
        outcomes = json.loads(m.get("outcomes", "[]"))
        markets[m["question"]] = {
            "condition_id": m.get("conditionId"),
            "outcomes": {outcomes[i]: float(prices[i]) for i in range(len(outcomes))},
            "volume": float(m.get("volume", 0)),
            "liquidity": float(m.get("liquidity", 0)),
        }
    return {
        "event": ev.get("title", MATCH),
        "active": ev.get("active"),
        "closed": ev.get("closed"),
        "volume_total": float(ev.get("volume", 0)),
        "liquidity_total": float(ev.get("liquidity", 0)),
        "volume_24hr": float(ev.get("volume24hr", 0)),
        "competitive": float(ev.get("competitive", 0)),
        "markets": markets,
    }


def fetch_polymarket_clob(token_id: str) -> dict:
    """Fetch CLOB order book for a specific token."""
    r = SESSION.get(f"{POLY_CLOB_URL}/book", params={"token_id": token_id}, timeout=10)
    r.raise_for_status()
    data = r.json()
    best_bid = float(data["bids"][0]["price"]) if data.get("bids") else 0
    best_ask = float(data["asks"][0]["price"]) if data.get("asks") else 0
    bid_size = float(data["bids"][0]["size"]) if data.get("bids") else 0
    ask_size = float(data["asks"][0]["size"]) if data.get("asks") else 0
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": round((best_bid + best_ask) / 2, 4) if best_bid and best_ask else 0,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "spread": round(best_ask - best_bid, 4) if best_bid and best_ask else 0,
    }


def fetch_42_market():
    """Fetch 42.space market data."""
    for attempt in range(3):
        try:
            r = SESSION.get(
                f"{FORTY_TWO_API}/api/v1/markets/{FORTY_TWO_CONTRACT}",
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()

            outcomes = []
            for item in data.get("outcomes", []):
                raw_name = item.get("name", "")
                # Normalize: "POR X–Y COD" -> "X-Y"
                name = raw_name
                for prefix in ["POR ", "COD "]:
                    if name.startswith(prefix):
                        name = name[len(prefix):]
                for suffix in [" COD", " POR"]:
                    if name.endswith(suffix):
                        name = name[:-len(suffix)]
                name = name.replace("\u2013", "-").replace("\u2265", ">=")

                outcomes.append({
                    "name": name,
                    "raw_name": raw_name,
                    "price": float(item.get("price", 0)),
                    "volume": float(item.get("volume", 0)),
                    "market_cap": float(item.get("marketCap", 0)),
                    "minted": float(item.get("mintedQuantity", 0)),
                    "payout": float(item.get("payout", 0)),
                })

            return {
                "market": data.get("question", MATCH),
                "status": data.get("status"),
                "volume_total": data.get("volume"),
                "market_cap_total": data.get("totalMarketCap"),
                "traders": data.get("traders"),
                "elapsed_pct": data.get("elapsedPct"),
                "end_date": data.get("endDate"),
                "outcomes": outcomes,
            }
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return {"error": str(e)}
    return {"error": "max retries exceeded"}


def calculate_arbitrage(poly_data: dict, ft_data: dict | None) -> list[dict]:
    """Compare Polymarket and 42 data for arbitrage."""
    signals = []

    if not poly_data:
        return signals

    poly_markets = poly_data.get("markets", {})

    # 1. Internal Polymarket Moneyline arbitrage
    home_q = next((q for q in poly_markets if "portugal" in q.lower() and "win" in q.lower()), None)
    draw_q = next((q for q in poly_markets if "draw" in q.lower()), None)
    away_q = next((q for q in poly_markets if "congo" in q.lower() and "win" in q.lower()), None)

    home_p = poly_markets[home_q]["outcomes"].get("Yes", 0) if home_q else 0
    draw_p = poly_markets[draw_q]["outcomes"].get("Yes", 0) if draw_q else 0
    away_p = poly_markets[away_q]["outcomes"].get("Yes", 0) if away_q else 0
    total_yes = home_p + draw_p + away_p
    profit = round((1.0 - total_yes) * 100, 4)

    signals.append({
        "type": "poly_moneyline_arb",
        "home": round(home_p, 4),
        "draw": round(draw_p, 4),
        "away": round(away_p, 4),
        "total_sum": round(total_yes, 4),
        "profit_pct": profit,
        "is_arbitrage": total_yes < 1.0,
    })

    # 2. Cross-platform: Polymarket vs 42 basket — compare IMPLIED PROBABILITIES, not raw prices
    if ft_data and "error" not in ft_data and ft_data.get("outcomes"):
        ft_outcomes = ft_data["outcomes"]
        ft_by_name = {o["name"]: o for o in ft_outcomes}

        # 42 uses bonding curve: marginal price != probability.
        # To convert 42 marginal price to implied probability:
        #   implied_prob_i = price_i / sum(all_prices)
        # This normalizes the 25 outcomes so they sum to 1.0, making them
        # comparable to Polymarket's direct probabilities.
        all_prices = [o["price"] for o in ft_outcomes]
        total_price = sum(all_prices) if all_prices else 1.0

        # Portugal Win implied prob from 42
        por_scores_found = [s for s in POR_WIN_SCORES if s in ft_by_name]
        por_missing = [s for s in POR_WIN_SCORES if s not in ft_by_name]
        if por_scores_found:
            por_42_raw = sum(ft_by_name[s]["price"] for s in por_scores_found)
            por_42_prob = por_42_raw / total_price  # normalize to probability scale
            poly_no_price = 1.0 - home_p if home_p else 0  # Poly NO = P(not POR win)

            # True arbitrage: if 42 says P(POR win) > Poly says P(POR win),
            # then buying 42 POR win + Poly POR NO could be profitable.
            # But we also need execution quotes to confirm.
            divergence = por_42_prob - home_p

            signals.append({
                "type": "cross_platform_prob_compare",
                "strategy": "Compare POR Win implied probability across platforms",
                "42_scores_used": por_scores_found,
                "42_scores_missing": por_missing,
                "42_raw_price_sum": round(por_42_raw, 6),
                "42_total_prices": round(total_price, 6),
                "42_implied_prob": round(por_42_prob, 6),
                "poly_implied_prob": round(home_p, 4),
                "divergence": round(divergence, 4),
                "divergence_pct": round(divergence * 100, 2),
                "note": "42 prob from normalized marginal prices. REAL arbitrage requires quoting actual buy/sell costs on both platforms.",
                "needs_quote_validation": True,
            })

        # Draw
        draw_scores_found = [s for s in DRAW_SCORES if s in ft_by_name]
        draw_missing = [s for s in DRAW_SCORES if s not in ft_by_name]
        if draw_scores_found:
            draw_42_raw = sum(ft_by_name[s]["price"] for s in draw_scores_found)
            draw_42_prob = draw_42_raw / total_price
            divergence_draw = draw_42_prob - draw_p

            signals.append({
                "type": "cross_platform_prob_compare_draw",
                "strategy": "Compare Draw implied probability across platforms",
                "42_scores_used": draw_scores_found,
                "42_scores_missing": draw_missing,
                "42_raw_price_sum": round(draw_42_raw, 6),
                "42_total_prices": round(total_price, 6),
                "42_implied_prob": round(draw_42_prob, 6),
                "poly_implied_prob": round(draw_p, 4),
                "divergence": round(divergence_draw, 4),
                "divergence_pct": round(divergence_draw * 100, 2),
                "note": "42 prob from normalized marginal prices. REAL arbitrage requires quoting actual buy/sell costs on both platforms.",
                "needs_quote_validation": True,
            })

    return signals


def log_snapshot(poly_gamma: dict, poly_clob: dict, ft_data: dict, signals: list, iteration: int) -> Path:
    """Save complete snapshot."""
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
    snapshot = {
        "iteration": iteration,
        "timestamp": ts,
        "polymarket_gamma": poly_gamma,
        "polymarket_clob": poly_clob,
        "forty_two": ft_data,
        "signals": signals,
    }
    path = LOG_DIR / f"snapshot_{iteration:06d}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    return path


def print_report(poly_gamma: dict, poly_clob: dict, ft_data: dict, signals: list, iteration: int):
    """Console report."""
    ts = datetime.now().strftime("%H:%M:%S")
    markets = poly_gamma.get("markets", {}) if poly_gamma else {}

    print(f"\n{'='*70}")
    print(f" [{ts}] #{iteration} | {MATCH}")
    if poly_gamma:
        print(f"  Poly Vol: ${poly_gamma['volume_total']:,.0f} | 24h: ${poly_gamma['volume_24hr']:,.0f} | Active: {poly_gamma['active']}")
    if ft_data and "error" not in ft_data:
        print(f"  42 Vol: ${ft_data['volume_total']:,.0f} | MCap: ${ft_data['market_cap_total']:,.0f} | Status: {ft_data['status']} | Elapsed: {ft_data['elapsed_pct']:.1%}")
    elif ft_data:
        print(f"  42: ERROR - {ft_data.get('error', 'unknown')[:80]}")
    print(f"{'='*70}")

    # Moneyline
    home_q = next((q for q in markets if "portugal" in q.lower() and "win" in q.lower()), None)
    draw_q = next((q for q in markets if "draw" in q.lower()), None)
    away_q = next((q for q in markets if "congo" in q.lower() and "win" in q.lower()), None)
    if home_q:
        print(f"\n  Polymarket Moneyline:")
        for q, m in markets.items():
            o = m.get("outcomes", {})
            print(f"    {q[:55]:<55} Yes={o.get('Yes', 0):.4f}  No={o.get('No', 0):.4f}")

    # CLOB data
    if poly_clob:
        print(f"\n  CLOB Order Books (mid prices):")
        for name, token_id in POLY_TOKENS.items():
            clob = poly_clob.get(token_id, {})
            if clob:
                b_bid = clob.get('best_bid', 0)
                b_ask = clob.get('best_ask', 0)
                b_mid = clob.get('mid', 0)
                b_spr = clob.get('spread', 0)
                print(f"    {name:<25} bid={b_bid:.4f} ask={b_ask:.4f} mid={b_mid:.4f} spread={b_spr:.4f}")

    # 42 data summary
    if ft_data and "error" not in ft_data and ft_data.get("outcomes"):
        outcomes = ft_data["outcomes"]
        por_scores = [o for o in outcomes if o["name"] in POR_WIN_SCORES]
        draw_scores = [o for o in outcomes if o["name"] in DRAW_SCORES]
        all_prices = [o["price"] for o in outcomes]
        total_p = sum(all_prices)
        print(f"\n  42 Raw Data:")
        print(f"    POR Win ({len(por_scores)}/{len(POR_WIN_SCORES)} scores): raw sum={sum(o['price'] for o in por_scores):.6f}")
        print(f"    Draw ({len(draw_scores)}/{len(DRAW_SCORES)} scores): raw sum={sum(o['price'] for o in draw_scores):.6f}")
        print(f"    Total 25 prices: {total_p:.6f}")
        por_prob = sum(o['price'] for o in por_scores) / total_p if total_p else 0
        draw_prob = sum(o['price'] for o in draw_scores) / total_p if total_p else 0
        print(f"    POR Win implied prob (normalized): {por_prob:.4f}")
        print(f"    Draw implied prob (normalized):    {draw_prob:.4f}")

    # Signals
    for sig in signals:
        if sig["type"] == "poly_moneyline_arb":
            arb = ">>> ARBITRAGE!" if sig.get("is_arbitrage") else "(no arb)"
            print(f"\n  *** Poly Moneyline: sum={sig['total_sum']:.4f} profit={sig['profit_pct']:+.3f}% {arb}")
            print(f"      (P1+P2+P3 < 1.0 = risk-free across 3 Poly markets)")
        elif "cross_platform_prob_compare" in sig["type"]:
            div = sig.get("divergence", 0)
            div_pct = sig.get("divergence_pct", 0)
            flag = ">> DIVERGENCE" if abs(div) > 0.03 else "(aligned)"
            label = "POR Win" if "draw" not in sig["type"] else "Draw"
            print(f"\n  *** Cross-platform {label}: 42 prob={sig['42_implied_prob']:.4f} vs Poly prob={sig['poly_implied_prob']:.4f}")
            print(f"      Divergence: {div:+.4f} ({div_pct:+.2f}%) {flag} -- NEEDS REAL QUOTE VALIDATION")
            if sig.get("needs_quote_validation"):
                print(f"      WARNING: 42 prob derived from normalized marginal prices,")
                print(f"      not actual buy-cost quotes. Real arb requires trade simulation.")

    print()


def main():
    interval = float(os.environ.get("INTERVAL", "15"))
    max_iter = int(os.environ.get("MAX_ITER", "0"))

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Full cross-platform arbitrage monitor")
    print(f"  Sources: Polymarket Gamma + CLOB, 42.space REST API")
    print(f"  Interval: {interval}s | Logs: {LOG_DIR}")
    print(f"  Press Ctrl+C to stop\n")

    iteration = 0
    try:
        while True:
            iteration += 1
            if max_iter > 0 and iteration > max_iter:
                break

            error_count = 0

            poly_gamma = None
            try:
                poly_gamma = fetch_polymarket_gamma()
            except Exception as e:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Poly Gamma error: {e}")
                error_count += 1

            poly_clob = {}
            for name, token_id in POLY_TOKENS.items():
                try:
                    poly_clob[token_id] = fetch_polymarket_clob(token_id)
                except Exception:
                    pass

            ft_data = None
            try:
                ft_data = fetch_42_market()
            except Exception as e:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] 42 error: {e}")
                error_count += 1

            signals = calculate_arbitrage(poly_gamma, ft_data)
            log_snapshot(poly_gamma, poly_clob, ft_data, signals, iteration)
            print_report(poly_gamma, poly_clob, ft_data, signals, iteration)

            if error_count >= 3:
                print("  Too many errors. Pausing 30s...")
                time.sleep(30)
            time.sleep(interval)

    except KeyboardInterrupt:
        pass

    # Build summary CSV
    summary_path = LOG_DIR / "summary.csv"
    snaps = sorted(LOG_DIR.glob("snapshot_*.json"))
    if snaps:
        with open(summary_path, "w") as f:
            f.write("iteration,timestamp,home_yes,draw_yes,away_yes,total_sum,profit_pct,"
                    "42_por_prob,42_draw_prob,42_por_divergence,42_draw_divergence,42_status,42_vol,42_mcap,poly_vol\n")
            for sp in snaps:
                try:
                    d = json.loads(sp.read_text(encoding="utf-8"))
                    sigs = {s["type"]: s for s in d.get("signals", [])}
                    ml = sigs.get("poly_moneyline_arb", {})
                    cp = sigs.get("cross_platform_prob_compare", {})
                    cp2 = sigs.get("cross_platform_prob_compare_draw", {})
                    pg = d.get("polymarket_gamma") or {}
                    ft = d.get("forty_two") or {}
                    f.write(f"{d['iteration']},{d['timestamp']},"
                            f"{ml.get('home','')},{ml.get('draw','')},{ml.get('away','')},"
                            f"{ml.get('total_sum','')},{ml.get('profit_pct','')},"
                            f"{cp.get('42_implied_prob','')},{cp2.get('42_implied_prob','')},"
                            f"{cp.get('divergence','')},{cp2.get('divergence','')},"
                            f"{ft.get('status','error')},{ft.get('volume_total','')},"
                            f"{ft.get('market_cap_total','')},{pg.get('volume_total','')}\n")
                except Exception:
                    pass
    print(f"\nSummary: {summary_path}")
    print(f"Logs: {LOG_DIR}")


if __name__ == "__main__":
    main()
