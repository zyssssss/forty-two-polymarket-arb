import requests, json

r = requests.get('https://clob.polymarket.com/markets', params={'slug': 'fifwc-prt-cdr-2026-06-17'})
data = r.json()
print(f"Total markets found: {len(data)}")
for m in data[:20]:
    token = m.get('condition_id', 'N/A')
    token0 = m.get('tokens', [{}])[0].get('token_id', '') if m.get('tokens') else ''
    token1 = m.get('tokens', [{}])[1].get('token_id', '') if len(m.get('tokens', [])) > 1 else ''
    question = m.get('question', 'N/A')
    outcomes = json.dumps(m.get('outcomes', ''))
    print(f"token={token} | t0={token0} | t1={token1} | {question[:80]}")
