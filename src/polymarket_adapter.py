from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

from src.models import PolymarketTeamMarket
from src.odds_calculator import polymarket_yes_no_cost
from src.team_normalizer import TeamNormalizer


class PolymarketAdapter:
    def __init__(self, base_url: str, normalizer: TeamNormalizer, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.normalizer = normalizer
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "worldcup-arb-monitor/1.0"})

    def get_worldcup_events(self, slugs: list[str] | None = None) -> list[dict[str, Any]]:
        if slugs:
            events: list[dict[str, Any]] = []
            for slug in slugs:
                events.extend(self._get_events({"slug": slug}))
            return events
        raw = self._get_events({"active": "true", "limit": 200})
        return [e for e in raw if self._is_worldcup_event(e)]

    def get_team_markets(self, slugs: list[str] | None = None) -> list[PolymarketTeamMarket]:
        team_markets: list[PolymarketTeamMarket] = []
        for event in self.get_worldcup_events(slugs):
            title = str(event.get("title") or event.get("ticker") or "")
            teams = split_event_teams(title)
            if not teams:
                continue
            home, away = [self.normalizer.normalize(team) for team in teams]
            for market in event.get("markets", []):
                parsed_team = extract_win_team(str(market.get("question", "")))
                if not parsed_team:
                    continue
                team = self.normalizer.normalize(parsed_team)
                if team not in {home, away}:
                    continue
                opponent = away if team == home else home
                outcomes = safe_json_list(market.get("outcomes"))
                prices = [float(x) for x in safe_json_list(market.get("outcomePrices"))]
                price_by_outcome = {str(outcomes[i]): prices[i] for i in range(min(len(outcomes), len(prices)))}
                yes_cost, no_cost, estimated = polymarket_yes_no_cost(
                    price_by_outcome.get("Yes", 0.0), price_by_outcome.get("No")
                )
                description = str(market.get("description", ""))
                rule_risk, reason = self._rule_risk(description)
                team_markets.append(
                    PolymarketTeamMarket(
                        event_name=f"{home} vs {away}",
                        team_name=team,
                        opponent_name=opponent,
                        yes_cost=yes_cost,
                        no_cost=no_cost,
                        no_cost_is_estimated=estimated,
                        rule_risk=rule_risk,
                        rule_risk_reason=reason,
                        raw={"event": event, "market": market},
                    )
                )
        return team_markets

    def _get_events(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        for attempt in range(3):
            try:
                response = self.session.get(f"{self.base_url}/events", params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, list) else []
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        return []

    @staticmethod
    def _is_worldcup_event(event: dict[str, Any]) -> bool:
        text = " ".join(str(event.get(key, "")) for key in ["title", "slug", "description", "ticker"])
        return "world cup" in text.lower() or str(event.get("slug", "")).startswith("fifwc-")

    @staticmethod
    def _rule_risk(description: str) -> tuple[bool, str]:
        normalized = description.lower()
        if "first 90 minutes" not in normalized and "90 minutes" not in normalized:
            return True, "Polymarket rule text does not clearly state 90 minutes only"
        return False, ""


def safe_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def split_event_teams(title: str) -> tuple[str, str] | None:
    match = re.split(r"\s+(?:vs\.?|v\.?|–|-)\s+", title, maxsplit=1, flags=re.IGNORECASE)
    if len(match) != 2:
        return None
    return match[0].strip(), match[1].strip()


def extract_win_team(question: str) -> str | None:
    match = re.match(r"Will\s+(.+?)\s+win\s+on\s+", question, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None
