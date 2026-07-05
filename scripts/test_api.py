"""Quick test of Polymarket API for Portugal vs DR Congo"""
import requests, json, time

print("Testing Polymarket API...")

# Test 1: CLUB book endpoint
token = "76071109489406808599878692125264766321676001700733380917373465772841855210643"
try:
    r = requests.get("https://clob.polymarket.com/book", params={"token_id": token}, timeout=10)
    print(f"CLOB book: status={r.status_code}")
    if r.status_code == 200:
        book = r.json()
        bid = float(book["bids"][0]["price"]) if book.get("bids") else 0
        ask = float(book["asks"][0]["price"]) if book.get("asks") else 0
        print(f"  Portugal YES: bid={bid}, ask={ask}")
    else:
        print(f"  Error: {r.text[:200]}")
except Exception as e:
    print(f"  Exception: {e}")

# Test 2: Gamma API 
try:
    r = requests.get("https://gamma-api.polymarket.com/events", params={"slug": "fifwc-prt-cdr-2026-06-17"}, timeout=10)
    print(f"Gamma events: status={r.status_code}")
    if r.status_code == 200:
        events = r.json()
        if events:
            ev = events[0]
            print(f"  Event: {ev['title']}")
            for m in ev.get('markets', []):
                prices = json.loads(m.get('outcomePrices', '[]'))
                print(f"  {m['question']}: {prices}")
except Exception as e:
    print(f"  Exception: {e}")

print("\nDone.")
