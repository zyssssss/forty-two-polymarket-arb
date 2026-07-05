import requests, json

token = '0xBcD1Bc19b678b3677536431c0433F18C3E4e4723'

urls = [
    f'https://www.42.space/api/sport/fifa/{token}/markets',
    f'https://www.42.space/api/markets/{token}',
    f'https://www.42.space/sport/fifa/{token}',
]

for url in urls:
    try:
        r = requests.get(url, timeout=15, headers={'Accept': 'application/json'})
        print(f"{url}: status={r.status_code}")
        if r.status_code == 200:
            ct = r.headers.get('content-type', '')
            if 'json' in ct:
                print(json.dumps(r.json(), indent=2)[:3000])
            else:
                # maybe HTML, extract market data
                text = r.text
                for marker in ['window.__INITIAL_STATE__', 'window.__NUXT__', 'marketData', 'window.__DATA__']:
                    idx = text.find(marker)
                    if idx >= 0:
                        print(f"  Found {marker} at position {idx}")
                        snippet = text[idx:idx+500]
                        print(f"  Snippet: {snippet[:200]}...")
                        break
    except Exception as e:
        print(f"{url}: {e}")
