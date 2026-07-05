import requests, json

match_token = '0xBcD1Bc19b678b3677536431c0433F18C3E4e4723'

# Try various 42 API patterns
urls = [
    ('https://www.42.space/api/markets', {'event': match_token}),
    ('https://www.42.space/api/events/markets', {'token': match_token}),
    ('https://www.42.space/api/sports/fifa/markets', {'token': match_token}),
]

for url, params in urls:
    try:
        r = requests.get(url, params=params, timeout=15)
        print(f"GET {url}?{params} -> status={r.status_code} length={len(r.text)}")
        if r.status_code == 200:
            ct = r.headers.get('content-type', '')
            if 'json' in ct:
                data = r.json()
                print(json.dumps(data, indent=2)[:3000])
            else:
                print(r.text[:500])
            print()
    except Exception as e:
        print(f"GET {url} -> {e}")
        print()

# Also try the event endpoint directly  
url_patterns = [
    f'https://www.42.space/api/events/{match_token}',
    f'https://www.42.space/api/event/{match_token}',
    f'https://www.42.space/api/match/{match_token}/markets',
]
for url in url_patterns:
    try:
        r = requests.get(url, timeout=15, headers={'Accept': 'application/json'})
        print(f"GET {url} -> status={r.status_code} length={len(r.text)}")
        if r.status_code == 200:
            ct = r.headers.get('content-type', '')
            if 'json' in ct:
                data = r.json()
                print(json.dumps(data, indent=2)[:3000])
            else:
                print(r.text[:500])
            print()
    except Exception as e:
        print(f"GET {url} -> {e}")
        print()
