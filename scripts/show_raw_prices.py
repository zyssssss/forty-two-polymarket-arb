"""Show raw 42 API prices for all 25 outcomes."""
import requests, json

r = requests.get("https://rest.ft.42.space/api/v1/markets/0xBcD1Bc19b678b3677536431c0433F18C3E4e4723", timeout=15)
d = r.json()
outcomes = d["outcomes"]

print(f"Total outcomes: {len(outcomes)}")
total_price = sum(float(o["price"]) for o in outcomes)
print(f"Sum of ALL 25 prices: {total_price:.6f}")
print(f"Total market cap: ${float(d['totalMarketCap']):,.0f}")
print(f"Total volume: ${float(d['volume']):,.0f}")
print()

print(f"{'Outcome':<20} {'Price':>10} {'MarketCap':>12} {'Volume':>12}")
print("-" * 56)
for o in sorted(outcomes, key=lambda x: -float(x["price"])):
    name = o["name"]
    price = float(o["price"])
    mcap = float(o["marketCap"])
    vol = float(o["volume"])
    print(f"{name:<20} {price:>10.6f} ${mcap:>11,.0f} ${vol:>11,.0f}")

# Show which belong to POR win
por_scores = ["1-0","2-0","2-1","3-0","3-1","3-2",">=4-0",">=4-1",">=4-2",">=4-3"]
draw_scores = ["0-0","1-1","2-2","3-3",">=4->=4"]

by_name = {}
for o in outcomes:
    name = o["name"]
    norm = name.replace("\u2013", "-").replace("\u2265", ">=")
    for pfx in ["POR ", "COD "]:
        if norm.startswith(pfx): norm = norm[len(pfx):]
    for sfx in [" COD", " POR"]:
        if norm.endswith(sfx): norm = norm[:-len(sfx)]
    by_name[norm] = float(o["price"])

por_sum = sum(by_name.get(s, 0) for s in por_scores)
draw_sum = sum(by_name.get(s, 0) for s in draw_scores)
other_sum = total_price - por_sum - draw_sum

print(f"\n=== Basket breakdown ===")
print(f"POR Win basket ({len(por_scores)} scores): {por_sum:.6f}")
print(f"Draw basket     ({len(draw_scores)} scores):  {draw_sum:.6f}")
print(f"Other (DRC win, etc.):              {other_sum:.6f}")
print(f"Total check:                        {por_sum + draw_sum + other_sum:.6f}")
