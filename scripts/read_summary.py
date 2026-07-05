import json
from pathlib import Path

log = Path("C:/polymarket/forty-two-polymarket-arb/logs/prt_cdr_full_monitor")
snaps = sorted(log.glob("snapshot_*.json"))
print(f"Total snapshots: {len(snaps)}")

if snaps:
    d = json.loads(snaps[-1].read_text(encoding="utf-8"))
    print(f"\nLatest snapshot: {snaps[-1].name}")
    
    ft = d.get("forty_two", {})
    if "error" not in ft:
        print(f"\n42 Market Status: {ft.get('status')} | Elapsed: {ft.get('elapsed_pct', 0):.1%}")
        print(f"42 Volume: ${ft.get('volume_total', 0):,.0f} | MCap: ${ft.get('market_cap_total', 0):,.0f}")
        
        outcomes = ft.get("outcomes", [])
        por_scores = ["1-0","2-0","2-1","3-0","3-1","3-2",">=4-0",">=4-1",">=4-2",">=4-3"]
        draw_scores = ["0-0","1-1","2-2","3-3",">=4->=4"]
        
        por_items = [o for o in outcomes if o["name"] in por_scores]
        draw_items = [o for o in outcomes if o["name"] in draw_scores]
        
        print(f"\n42 POR Win Basket ({len(por_items)}/{len(por_scores)} scores):")
        for o in sorted(por_items, key=lambda x: -x["price"]):
            print(f"  {o['name']:<8} price={o['price']:.6f}  mcap=${o['market_cap']:,.0f}")
        print(f"  TOTAL: {sum(o['price'] for o in por_items):.6f}")
        
        print(f"\n42 Draw Basket ({len(draw_items)}/{len(draw_scores)} scores):")
        for o in sorted(draw_items, key=lambda x: -x["price"]):
            print(f"  {o['name']:<8} price={o['price']:.6f}  mcap=${o['market_cap']:,.0f}")
        print(f"  TOTAL: {sum(o['price'] for o in draw_items):.6f}")

    pg = d.get("polymarket_gamma", {})
    markets = pg.get("markets", {})
    print(f"\nPolymarket:")
    print(f"  Volume: ${pg.get('volume_total', 0):,.0f} | Active: {pg.get('active')}")
    for q, m in markets.items():
        o = m.get("outcomes", {})
        print(f"  {q}: Yes={o.get('Yes', 0):.4f} No={o.get('No', 0):.4f}")

    sigs = d.get("signals", [])
    print(f"\nArbitrage Signals:")
    for s in sigs:
        t = s["type"]
        if t == "poly_moneyline_arb":
            arb = "ARBITRAGE" if s.get("is_arbitrage") else "no"
            print(f"  Poly Moneyline: sum={s['total_sum']:.4f} profit={s['profit_pct']:+.3f}% [{arb}]")
        elif "cross_platform_prob_compare" in t:
            label = "POR Win" if "draw" not in t else "Draw"
            print(f"  Cross-platform {label}: 42 prob={s['42_implied_prob']:.4f} vs Poly={s['poly_implied_prob']:.4f}")
            print(f"    Divergence: {s['divergence']:+.4f} ({s['divergence_pct']:+.2f}%) -- NEEDS QUOTE VALIDATION")
            print(f"    Raw: 42 sum={s['42_raw_price_sum']:.6f} / total={s['42_total_prices']:.6f} = {s['42_implied_prob']:.4f}")
    
    print(f"\nLogs: {log}")
