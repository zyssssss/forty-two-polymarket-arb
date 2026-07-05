"""
Compare Polymarket (CLOB) vs 42.space (bonding curve) pricing models.
Shows the CORRECT way to normalize 42 marginal prices for comparison.
"""
import requests, json

TIMEOUT = 20

print("=" * 68)
print("Polymarket vs 42.space: Correct Cross-Platform Comparison")
print("=" * 68)

# --- Fetch data ---
print("\nFetching live data...")
poly = None
ft = None
try:
    r = requests.get("https://gamma-api.polymarket.com/events",
                      params={"slug": "fifwc-prt-cdr-2026-06-17"}, timeout=TIMEOUT)
    poly = r.json()[0]
    print("  Polymarket: OK")
except Exception as e:
    print(f"  Polymarket: FAILED ({e})")

try:
    r = requests.get("https://rest.ft.42.space/api/v1/markets/0xBcD1Bc19b678b3677536431c0433F18C3E4e4723", timeout=TIMEOUT)
    ft = r.json()
    print("  42.space: OK")
except Exception as e:
    print(f"  42.space: FAILED ({e})")

if not poly or not ft:
    print("\nCannot compare — one or both data sources unavailable.")
    exit(1)

# --- Extract Polymarket prices ---
markets = {}
for m in poly["markets"]:
    outcomes = json.loads(m["outcomes"])
    prices = json.loads(m["outcomePrices"])
    for i, o in enumerate(outcomes):
        markets[o] = float(prices[i])

home_p = markets.get("Yes", None)  # Portugal Win
draw_p = markets.get("Yes", None)  # Draw  — need to get from the right market
away_p = markets.get("Yes", None)  # DR Congo Win

# Actually need to parse market questions properly
for m in poly["markets"]:
    q = m["question"]
    outcomes = json.loads(m["outcomes"])
    prices = json.loads(m["outcomePrices"])
    for i, o in enumerate(outcomes):
        if o == "Yes":
            if "portugal" in q.lower() and "win" in q.lower():
                home_p = float(prices[i])
            elif "draw" in q.lower():
                draw_p = float(prices[i])
            elif "congo" in q.lower() and "win" in q.lower():
                away_p = float(prices[i])

print(f"\n--- Polymarket (CLOB) ---")
print(f"  Portugal Win:     {home_p:.4f}   (<- direct probability)")
print(f"  Draw:             {draw_p:.4f}   (<- direct probability)")
print(f"  DR Congo Win:     {away_p:.4f}   (<- direct probability)")
print(f"  Sum of 3 YES:     {home_p + draw_p + away_p:.4f}   (<- should be ~1.0)")
print(f"  Volume: ${float(poly['volume']):,.0f}")

# --- Extract 42 prices ---
outcomes = ft["outcomes"]
all_prices = [float(o["price"]) for o in outcomes]
total_price = sum(all_prices)

# Normalize: name matching
def normalize(name):
    n = name.replace("\u2013", "-").replace("\u2265", ">=")
    for pfx in ["POR ", "COD "]:
        if n.startswith(pfx): n = n[len(pfx):]
    for sfx in [" COD", " POR"]:
        if n.endswith(sfx): n = n[:-len(sfx)]
    return n

by_name = {normalize(o["name"]): float(o["price"]) for o in outcomes}

POR_WIN = ["1-0","2-0","2-1","3-0","3-1","3-2",">=4-0",">=4-1",">=4-2",">=4-3"]
DRAW = ["0-0","1-1","2-2","3-3",">=4->=4"]

por_raw = sum(by_name.get(s, 0) for s in POR_WIN)
draw_raw = sum(by_name.get(s, 0) for s in DRAW)

por_prob = por_raw / total_price if total_price else 0
draw_prob = draw_raw / total_price if total_price else 0

print(f"\n--- 42.space (Bonding Curve) ---")
print(f"  Total 25 outcomes")
print(f"  Sum of all 25 marginal prices: {total_price:.6f}   (<- NOT 1.0!)")
print(f"  Volume: ${float(ft['volume']):,.0f}")
print(f"  Market Cap: ${float(ft['totalMarketCap']):,.0f}")
print(f"")
print(f"  POR Win raw marginal sum: {por_raw:.6f}")
print(f"  Draw raw marginal sum:    {draw_raw:.6f}")
print(f"")
print(f"  AFTER NORMALIZATION (price / total):")
print(f"  POR Win implied prob:    {por_prob:.4f}")
print(f"  Draw implied prob:       {draw_prob:.4f}")
print(f"  DRC Win implied prob:    {1 - por_prob - draw_prob:.4f}")
print(f"  Sum (check):             {por_prob + draw_prob + (1 - por_prob - draw_prob):.4f}")

# --- Comparison ---
print(f"\n{'='*68}")
print(f"  CROSS-PLATFORM COMPARISON (same-scale probabilities)")
print(f"{'='*68}")
print(f"")
print(f"  {'Outcome':<16} {'Poly (CLOB)':>14} {'42 (normalized)':>18} {'Divergence':>12}")
print(f"  {'-'*60}")
print(f"  {'Portugal Win':<16} {home_p:>14.4f} {por_prob:>18.4f} {por_prob - home_p:>+12.4f}")
print(f"  {'Draw':<16} {draw_p:>14.4f} {draw_prob:>18.4f} {draw_prob - draw_p:>+12.4f}")

por_div = por_prob - home_p
draw_div = draw_prob - draw_p

print(f"")
if abs(por_div) > 0.05:
    print(f"  >> Portugal Win: {por_div*100:+.1f}% divergence — warrants further investigation")
else:
    print(f"  >> Portugal Win: aligned (within 5%)")
if abs(draw_div) > 0.05:
    print(f"  >> Draw: {draw_div*100:+.1f}% divergence — warrants further investigation")
else:
    print(f"  >> Draw: aligned (within 5%)")

print(f"\n  NOTE: 42 prob is NORMALIZED from marginal prices (price_i / sum(all_prices)).")
print(f"  This is an APPROXIMATION. Real arbitrage requires:")
print(f"    1. Simulating actual buy cost on 42's bonding curve")
print(f"    2. Getting live fill quotes from Polymarket CLOB")
print(f"    3. Accounting for gas, fees, and slippage on both sides")
