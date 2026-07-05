import requests, json
r = requests.get("https://gamma-api.polymarket.com/events", params={"slug": "fifwc-prt-cdr-2026-06-17"})
e = r.json()[0]
print(f"active={e['active']} closed={e['closed']} endDate={e['endDate']}")
for m in e['markets']:
    print(f"  {m['question']}: {m['outcomePrices']}")
