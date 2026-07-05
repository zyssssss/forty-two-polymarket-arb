"""Show normalized comparison using the best available snapshot."""
import json
from pathlib import Path

log = Path("C:/polymarket/forty-two-polymarket-arb/logs/prt_cdr_full_monitor")
snaps = sorted(log.glob("snapshot_*.json"))

# Find first snapshot with complete poly + 42 data
best_d = None
for s in reversed(snaps):
    d = json.loads(s.read_text(encoding="utf-8"))
    pg = d.get("polymarket_gamma") or {}
    ft = d.get("forty_two") or {}
    if pg.get("markets") and "error" not in ft:
        best_d = d
        break

if not best_d:
    # Fallback: use any snapshot
    best_d = json.loads(snaps[-1].read_text(encoding="utf-8"))

# Poly data
pg = best_d.get("polymarket_gamma") or {}
mkt = pg.get("markets", {})
home_p = 0.0; draw_p = 0.0; away_p = 0.0
if mkt:
    for q, m in mkt.items():
        o = m["outcomes"]
        yes = o.get("Yes", 0)
        ql = q.lower()
        if "portugal" in ql and "win" in ql: home_p = yes
        elif "draw" in ql: draw_p = yes
        elif "congo" in ql and "win" in ql: away_p = yes

# 42 data
ft = best_d.get("forty_two") or {}
outcomes = ft.get("outcomes", [])
total_p = sum(o["price"] for o in outcomes)

by_name = {}
for o in outcomes:
    n = o["name"].replace("\u2013", "-").replace("\u2265", ">=")
    for pfx in ["POR ", "COD "]:
        if n.startswith(pfx): n = n[len(pfx):]
    for sfx in [" COD", " POR"]:
        if n.endswith(sfx): n = n[:-len(sfx)]
    by_name[n] = float(o["price"])

POR = ["1-0","2-0","2-1","3-0","3-1","3-2",">=4-0",">=4-1",">=4-2",">=4-3"]
DRAW = ["0-0","1-1","2-2","3-3",">=4->=4"]

por_prob = sum(by_name.get(s, 0) for s in POR) / total_p if total_p else 0
draw_prob = sum(by_name.get(s, 0) for s in DRAW) / total_p if total_p else 0
drc_prob = 1 - por_prob - draw_prob

print("CORRECTED Cross-Platform Comparison")
print("====================================")
print(f"Snapshot: {snaps[-1].name} (most recent with complete data)")
print()
print(f"42.space (bonding curve, normalized)")
print(f"  Raw price sum: {total_p:.6f}")
print(f"  POR Win prob:  {por_prob:.4f}")
print(f"  Draw prob:     {draw_prob:.4f}")
print(f"  DRC Win prob:  {drc_prob:.4f}")
print(f"  Sum check:     {por_prob+draw_prob+drc_prob:.4f}")
print()
print(f"Polymarket (CLOB, direct probability)")
print(f"  POR Win:  {home_p:.4f}")
print(f"  Draw:     {draw_p:.4f}")
print(f"  DRC Win:  {away_p:.4f}")
print(f"  Sum:      {home_p+draw_p+away_p:.4f}")
print()
print(f"{'Outcome':<14} {'Poly(CLOB)':>12} {'42(norm)':>12} {'Diff':>10}")
print(f"{'-'*48}")
print(f"{'POR Win':<14} {home_p:>12.4f} {por_prob:>12.4f} {por_prob-home_p:>+10.4f}")
print(f"{'Draw':<14} {draw_p:>12.4f} {draw_prob:>12.4f} {draw_prob-draw_p:>+10.4f}")
print(f"{'DRC Win':<14} {away_p:>12.4f} {drc_prob:>12.4f} {drc_prob-away_p:>+10.4f}")

print(f"\nMETHOD: 42 implied prob = price_i / sum(all_prices)")
print(f"This converts marginal prices to probability scale (0-1).")
print(f"Real arbitrage still needs actual buy-cost quotes from both platforms.")
