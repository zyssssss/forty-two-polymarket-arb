from __future__ import annotations

import json
import time

import requests


POLY_URL = "https://gamma-api.polymarket.com/events"
POLY_PARAMS = {"slug": "fifwc-prt-cdr-2026-06-17"}
FT_URL = "https://rest.ft.42.space/api/v1/markets/0xBcD1Bc19b678b3677536431c0433F18C3E4e4723"


def check(name: str, url: str, params: dict | None = None) -> bool:
    print(f"\n{name}")
    print(f"  URL: {url}")
    started = time.time()
    try:
        response = requests.get(url, params=params, timeout=20, headers={"User-Agent": "worldcup-arb-monitor/1.0"})
        elapsed = time.time() - started
        print(f"  HTTP: {response.status_code}  time={elapsed:.2f}s")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            print(f"  OK: list length={len(data)}")
        elif isinstance(data, dict):
            print(f"  OK: keys={list(data)[:8]}")
        else:
            print(f"  OK: type={type(data).__name__}")
        return True
    except Exception as exc:
        elapsed = time.time() - started
        print(f"  FAIL after {elapsed:.2f}s: {exc!r}")
        return False


def main() -> None:
    poly_ok = check("Polymarket Gamma", POLY_URL, POLY_PARAMS)
    ft_ok = check("42 REST", FT_URL)
    print("\nSUMMARY")
    print(json.dumps({"polymarket_gamma": poly_ok, "forty_two_rest": ft_ok}, indent=2))


if __name__ == "__main__":
    main()
