from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import requests


POLY = "https://gamma-api.polymarket.com"
FT = "https://rest.ft.42.space"
POLY_WC_PAGE = "https://polymarket.com/sports/world-cup/games"


def get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(url, params=params, timeout=30, headers={"User-Agent": "worldcup-arb-monitor/1.0"})
    response.raise_for_status()
    return response.json()


def parse_time(value: Any) -> datetime:
    if not value:
        return datetime.max.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.max.replace(tzinfo=timezone.utc)


def is_worldcup_text(text: str) -> bool:
    lower = text.lower()
    return "world cup" in lower or "fifa" in lower or "fifwc" in lower


def clean_match_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_polymarket() -> list[dict[str, Any]]:
    # Gamma endpoint can be intermittent, but when reachable this returns enough to filter fifwc markets.
    events = get_json(f"{POLY}/events", {"limit": 500, "active": "true"})
    rows = []
    for event in events if isinstance(events, list) else []:
        text = " ".join(str(event.get(k, "")) for k in ["title", "slug", "ticker", "description"])
        if not is_worldcup_text(text):
            continue
        markets = event.get("markets", [])
        if not markets:
            continue
        rows.append(
            {
                "platform": "polymarket",
                "title": clean_match_title(str(event.get("title", ""))),
                "slug": event.get("slug"),
                "endDate": event.get("endDate"),
                "gameStartTime": markets[0].get("gameStartTime") if markets else None,
                "active": event.get("active"),
                "closed": event.get("closed"),
                "volume": float(event.get("volume", 0) or 0),
                "liquidity": float(event.get("liquidity", 0) or 0),
                "market_count": len(markets),
            }
        )
    if len(rows) < 5:
        rows.extend(fetch_polymarket_from_worldcup_page())
    deduped = {str(row.get("slug")): row for row in rows if row.get("slug")}
    return sorted(deduped.values(), key=lambda x: parse_time(x.get("gameStartTime") or x.get("endDate")))


def fetch_polymarket_from_worldcup_page() -> list[dict[str, Any]]:
    html = requests.get(POLY_WC_PAGE, timeout=30, headers={"User-Agent": "worldcup-arb-monitor/1.0"}).text
    slugs = []
    for match in re.finditer(r"/sports/world-cup/(fifwc-[a-z0-9-]+-\d{4}-\d{2}-\d{2})", html):
        slug = match.group(1)
        if slug not in slugs:
            slugs.append(slug)
    rows = []
    for slug in slugs[:24]:
        try:
            events = get_json(f"{POLY}/events", {"slug": slug})
        except Exception:
            continue
        for event in events if isinstance(events, list) else []:
            markets = event.get("markets", [])
            rows.append(
                {
                    "platform": "polymarket",
                    "title": clean_match_title(str(event.get("title", ""))),
                    "slug": event.get("slug"),
                    "endDate": event.get("endDate"),
                    "gameStartTime": markets[0].get("gameStartTime") if markets else None,
                    "active": event.get("active"),
                    "closed": event.get("closed"),
                    "volume": float(event.get("volume", 0) or 0),
                    "liquidity": float(event.get("liquidity", 0) or 0),
                    "market_count": len(markets),
                }
            )
    return rows


def fetch_42() -> list[dict[str, Any]]:
    data = get_json(f"{FT}/api/v1/markets", {"limit": 500, "offset": 0, "status": "all", "contract_version": 2})
    markets = data.get("data", data if isinstance(data, list) else [])
    rows = []
    for market in markets:
        text = " ".join(str(market.get(k, "")) for k in ["question", "categories", "subcategories", "topics", "tags"])
        if not is_worldcup_text(text):
            continue
        rows.append(
            {
                "platform": "42",
                "title": clean_match_title(str(market.get("question", ""))),
                "address": market.get("address"),
                "slug": market.get("slug"),
                "startDate": market.get("startDate"),
                "endDate": market.get("endDate"),
                "status": market.get("status"),
                "volume": float(market.get("volume", 0) or 0),
                "market_cap": float(market.get("totalMarketCap", 0) or 0),
            }
        )
    return sorted(rows, key=lambda x: parse_time(x.get("startDate") or x.get("endDate")))


def print_rows(name: str, rows: list[dict[str, Any]], limit: int = 12) -> None:
    print(f"\n{name} ({len(rows)} found)")
    print("-" * 100)
    for row in rows[:limit]:
        date = row.get("gameStartTime") or row.get("startDate") or row.get("endDate")
        ident = row.get("slug") or row.get("address")
        status = row.get("status") or f"active={row.get('active')} closed={row.get('closed')}"
        print(f"{date} | {status:<24} | vol=${row.get('volume', 0):,.0f} | {row.get('title')} | {ident}")


def upcoming(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    future = [row for row in rows if parse_time(row.get("gameStartTime") or row.get("startDate") or row.get("endDate")) >= now]
    return future[:limit] if future else rows[-limit:]


def main() -> None:
    result: dict[str, Any] = {"polymarket": [], "forty_two": []}
    try:
        result["polymarket"] = fetch_polymarket()
    except Exception as exc:
        print(f"Polymarket fetch failed: {exc!r}")
    try:
        result["forty_two"] = fetch_42()
    except Exception as exc:
        print(f"42 fetch failed: {exc!r}")

    print_rows("Polymarket recent/upcoming World Cup events", upcoming(result["polymarket"]))
    print_rows("42 recent/upcoming World Cup markets", upcoming(result["forty_two"]))
    with open("data/recent_worldcup_markets.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\nSaved: data/recent_worldcup_markets.json")


if __name__ == "__main__":
    main()
