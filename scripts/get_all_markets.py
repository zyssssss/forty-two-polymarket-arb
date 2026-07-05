import requests, json

r = requests.get('https://gamma-api.polymarket.com/events', params={'slug': 'fifwc-prt-cdr-2026-06-17'})
events = r.json()
event = events[0]

print(f"Event: {event['title']}")
print(f"Total markets: {len(event.get('markets', []))}")
print(f"Neg risk market ID: {event.get('negRiskMarketID')}")
print()

for m in event.get('markets', []):
    print(f"--- {m.get('id')} ---")
    print(f"  question: {m.get('question')}")
    print(f"  conditionId: {m.get('conditionId')}")
    print(f"  outcomes: {m.get('outcomes')}")
    print(f"  outcomePrices: {m.get('outcomePrices')}")
    print(f"  clobTokenIds: {m.get('clobTokenIds')}")
    valid_until = m.get('endDate')
    print(f"  endDate: {valid_until}")
    print()
