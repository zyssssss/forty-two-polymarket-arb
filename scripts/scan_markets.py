import requests, json

# Search for Portugal vs DR Congo markets
keywords = ['PRT', 'CDR', 'Portugal', 'DR Congo', 'Congo', 'Portugal vs DR Congo', 'Portugal – DR Congo']

# Try different approaches
# 1. Gamma API for sports events
try:
    r = requests.get('https://gamma-api.polymarket.com/events', params={
        'slug': 'fifwc-prt-cdr-2026-06-17'
    })
    if r.status_code == 200:
        data = r.json()
        print("=== Gamma Events ===")
        print(json.dumps(data, indent=2)[:5000])
except Exception as e:
    print(f"Gamma events error: {e}")

# 2. CLOB markets with tag filter
try:
    r = requests.get('https://clob.polymarket.com/markets', params={
        'tag': 'sports'
    }, timeout=15)
    data = r.json()
    print(f"\n=== CLOB markets with sports tag: {len(data)} results ===")
    
    # Filter by slug containing prt or cdr
    matching = [m for m in data if 'prt' in m.get('market_slug', '').lower() and 'cdr' in m.get('market_slug', '').lower()]
    if not matching:
        # Try searching by question keywords
        matching = [m for m in data if any(kw.lower() in m.get('question', '').lower() for kw in ['portugal', 'congo', 'prt', 'cdr'])]
    
    for m in matching:
        tokens = m.get('tokens', [])
        print(f"\n  condition_id: {m.get('condition_id')}")
        print(f"  question: {m.get('question')}")
        for t in tokens:
            print(f"  token: {t.get('token_id')} outcome: {t.get('outcome')} price: {t.get('price')}")
except Exception as e:
    print(f"CLOB error: {e}")
