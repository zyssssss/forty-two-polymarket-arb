from __future__ import annotations

import json
import math
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import PolymarketMarket


class PolymarketAdapter(ABC):
    @abstractmethod
    def list_worldcup_markets(self) -> list[PolymarketMarket]:
        raise NotImplementedError


class HttpPolymarketAdapter(PolymarketAdapter):
    def __init__(
        self,
        api_base_url: str = "https://gamma-api.polymarket.com",
        clob_base_url: str = "https://clob.polymarket.com",
        timeout: float = 15.0,
        search_pages: int = 30,
    ) -> None:
        self.api_base_url = (api_base_url or "https://gamma-api.polymarket.com").rstrip("/")
        self.clob_base_url = clob_base_url.rstrip("/")
        self.timeout = timeout
        self.search_pages = search_pages
        self.session = _session()
        self.last_diagnostics: dict[str, Any] = {}

    def list_worldcup_markets(self) -> list[PolymarketMarket]:
        candidates = self._fetch_candidates()
        markets: list[PolymarketMarket] = []
        clob_errors = 0
        for item in candidates:
            parsed = self._parse_match_market(item)
            if parsed is None:
                continue
            event_name, team_name, yes_index, no_index = parsed
            prices = _json_list(item.get("outcomePrices"))
            token_ids = _json_list(item.get("clobTokenIds"))
            yes_price = _float_at(prices, yes_index)
            no_price = _float_at(prices, no_index)
            price_source = "gamma"
            if len(token_ids) > max(yes_index, no_index):
                try:
                    yes_price = self._clob_buy_price(str(token_ids[yes_index]))
                    no_price = self._clob_buy_price(str(token_ids[no_index]))
                    price_source = "clob_buy"
                except (requests.RequestException, ValueError, KeyError):
                    clob_errors += 1
            if yes_price is None:
                continue
            raw = dict(item)
            raw["price_source"] = price_source
            markets.append(
                PolymarketMarket(
                    event_name=event_name,
                    team_name=team_name,
                    yes_price=yes_price,
                    no_price=no_price,
                    rule_text=str(item.get("description", "")),
                    updated_at=item.get("updatedAt"),
                    raw=raw,
                )
            )
        self.last_diagnostics = {
            "source": self.api_base_url,
            "candidate_count": len(candidates),
            "compatible_match_market_count": len(markets),
            "clob_fallback_count": clob_errors,
            "latest_gamma_update": max(
                (str(item.get("updatedAt", "")) for item in candidates),
                default="",
            ),
            "clob_probe_price": self._probe_clob(candidates),
        }
        return markets

    def _fetch_candidates(self) -> list[dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        first = self._fetch_search_page(1)
        page_size = max(1, len(first.get("events", [])))
        total = int(first.get("pagination", {}).get("totalResults", page_size))
        page_count = min(self.search_pages, max(1, math.ceil(total / page_size)))
        pages = [(1, first)]
        with ThreadPoolExecutor(max_workers=min(8, self.search_pages)) as executor:
            futures = {
                executor.submit(self._fetch_search_page, page): page
                for page in range(2, page_count + 1)
            }
            for future in as_completed(futures):
                pages.append((futures[future], future.result()))
        for _, payload in sorted(pages):
            for event in payload.get("events", []):
                for item in event.get("markets", []):
                    if item.get("active") and not item.get("closed") and _is_worldcup_item({**item, "events": [event]}):
                        enriched = dict(item)
                        enriched["events"] = [event]
                        found[str(item.get("id", item.get("slug", len(found))))] = enriched
        return list(found.values())

    def _fetch_search_page(self, page: int) -> dict[str, Any]:
        response = self.session.get(
            f"{self.api_base_url}/public-search",
            params={"q": "World Cup", "limit_per_type": 100, "page": page},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise ValueError("Polymarket /public-search returned an invalid payload")
        return payload

    def _parse_match_market(self, item: dict[str, Any]) -> tuple[str, str, int, int] | None:
        outcomes = [str(value).strip().lower() for value in _json_list(item.get("outcomes"))]
        if "yes" not in outcomes or "no" not in outcomes:
            return None
        question = str(item.get("question", "")).strip()
        event_title = next(
            (
                str(event.get("title", "")).strip()
                for event in item.get("events", [])
                if _parse_event_teams(str(event.get("title", "")))
            ),
            "",
        )
        teams = _parse_event_teams(event_title)
        if not teams:
            return None
        win_match = re.search(r"will\s+(.+?)\s+win(?:\s+(?:the|this|their))?\s+(?:match|game)|^(.+?)\s+to\s+win$", question, re.I)
        if not win_match:
            return None
        team_name = next((group.strip() for group in win_match.groups() if group), "")
        normalized = {_clean_team(team): team for team in teams}
        team_name = normalized.get(_clean_team(team_name), "")
        if not team_name:
            return None
        return f"{teams[0]} vs {teams[1]}", team_name, outcomes.index("yes"), outcomes.index("no")

    def _clob_buy_price(self, token_id: str) -> float:
        response = self.session.get(
            f"{self.clob_base_url}/price",
            params={"token_id": token_id, "side": "BUY"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        price = float(response.json()["price"])
        if not 0 <= price <= 1:
            raise ValueError(f"Invalid CLOB price: {price}")
        return price

    def _probe_clob(self, candidates: list[dict[str, Any]]) -> float | None:
        for item in candidates:
            token_ids = _json_list(item.get("clobTokenIds"))
            if token_ids:
                try:
                    price = self._clob_buy_price(str(token_ids[0]))
                    if 0 < price < 1:
                        return price
                except (requests.RequestException, ValueError, KeyError):
                    continue
        return None


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=0.4, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    return []


def _float_at(values: list[Any], index: int) -> float | None:
    try:
        return float(values[index])
    except (IndexError, TypeError, ValueError):
        return None


def _is_worldcup_item(item: dict[str, Any]) -> bool:
    text = " ".join(
        [str(item.get("question", "")), str(item.get("description", ""))]
        + [str(event.get("title", "")) for event in item.get("events", [])]
    )
    return bool(re.search(r"\b(?:fifa\s+)?world\s+cup\b", text, re.I))


def _parse_event_teams(value: str) -> tuple[str, str] | None:
    parts = re.split(r"\s+(?:vs\.?|v|versus)\s+", value.strip(), maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    right = re.split(r"\s+-\s+|:\s*", parts[1], maxsplit=1)[0].strip()
    left = re.split(r":\s*", parts[0])[-1].strip()
    return (left, right) if left and right else None


def _clean_team(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


class MockPolymarketAdapter(PolymarketAdapter):
    def list_worldcup_markets(self) -> list[PolymarketMarket]:
        return [
            PolymarketMarket(
                event_name="France vs Senegal",
                team_name="France",
                yes_price=0.67,
                no_price=0.33,
                rule_text="France No means France does not win: Draw + France lost.",
                raw={"source": "mock"},
            )
        ]
