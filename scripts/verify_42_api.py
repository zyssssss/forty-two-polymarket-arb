import requests, json

resp = requests.get("https://rest.ft.42.space/api/v1/markets/0xBcD1Bc19b678b3677536431c0433F18C3E4e4723")
d = resp.json()

print("=== 42 Market Summary ===")
for k in ['title', 'category', 'status', 'collateralToken', 'volume', 'totalMarketCap', 'liquidity']:
    print(f"  {k}: {d.get(k)}")

print(f"  outcomeCount: {len(d.get('outcomes', []))}")
print(f"\n  Top 20 outcomes by price:")
for o in sorted(d.get('outcomes', []), key=lambda x: -float(x.get('price', 0)))[:20]:
    print(f"    {o['name']:<20} price={float(o['price']):.6f}  vol={o.get('volume', '0')}")
