from __future__ import annotations

import time
from typing import Any

import requests

from src.models import FortyTwoTeamCosts
from src.odds_calculator import ScoreOutcome, exact_score_costs, normalize_score_name
from src.polymarket_adapter import split_event_teams
from src.team_normalizer import TeamNormalizer


class FortyTwoAdapter:
    def __init__(self, base_url: str, normalizer: TeamNormalizer, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.normalizer = normalizer
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "worldcup-arb-monitor/1.0", "Accept": "application/json"})

    def get_worldcup_markets(self, addresses: list[str] | None = None) -> list[dict[str, Any]]:
        if addresses:
            return [self.get_market(address) for address in addresses]
        response = self.session.get(
            f"{self.base_url}/api/v1/markets",
            params={"limit": 500, "status": "live", "contract_version": 2},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        markets = data.get("data", data if isinstance(data, list) else [])
        return [m for m in markets if self._is_worldcup_market(m)]

    def get_market(self, address: str) -> dict[str, Any]:
        for attempt in range(3):
            try:
                response = self.session.get(f"{self.base_url}/api/v1/markets/{address}", timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("unreachable")

    def get_team_costs(self, addresses: list[str] | None = None) -> list[FortyTwoTeamCosts]:
        rows: list[FortyTwoTeamCosts] = []
        for market in self.get_worldcup_markets(addresses):
            teams = split_event_teams(str(market.get("question", "")))
            if not teams:
                continue
            home, away = [self.normalizer.normalize(team) for team in teams]
            outcomes = self._score_outcomes(market)
            if not outcomes:
                continue
            for team, opponent, side in [(home, away, "home"), (away, home, "away")]:
                win, draw, lost, risk, reason, groups = exact_score_costs(outcomes, side)
                extra_risk, extra_reason = self._market_rule_risk(market)
                rule_risk = risk or extra_risk
                rule_reason = "; ".join(x for x in [reason, extra_reason] if x)
                rows.append(
                    FortyTwoTeamCosts(
                        platform="42",
                        event_name=f"{home} vs {away}",
                        team_name=team,
                        opponent_name=opponent,
                        market_type="exact_score",
                        team_win_cost=win,
                        team_draw_cost=draw,
                        team_lost_cost=lost,
                        rule_risk=rule_risk,
                        rule_risk_reason=rule_reason,
                        raw={"market": market, "groups": groups},
                    )
                )
        return rows

    def _score_outcomes(self, market: dict[str, Any]) -> list[ScoreOutcome]:
        raw_outcomes = market.get("outcomes", [])
        prices = [float(o.get("price", 0.0)) for o in raw_outcomes]
        total_price = sum(prices)
        normalized_prices = [p / total_price for p in prices] if total_price > 0 and not 0.95 <= total_price <= 1.05 else prices
        result: list[ScoreOutcome] = []
        for index, item in enumerate(raw_outcomes):
            raw_name = str(item.get("name", ""))
            name = normalize_score_name(raw_name)
            decimal_odds = item.get("decimal_odds") or item.get("decimalOdds")
            result.append(
                ScoreOutcome(
                    name=name,
                    decimal_odds=float(decimal_odds) if decimal_odds else None,
                    cost=normalized_prices[index] if index < len(normalized_prices) else None,
                    raw=item,
                )
            )
        return result

    @staticmethod
    def _is_worldcup_market(market: dict[str, Any]) -> bool:
        text = " ".join(str(market.get(key, "")) for key in ["question", "categories", "subcategories", "topics", "tags"])
        return "world cup" in text.lower() or "fifa" in text.lower()

    @staticmethod
    def _market_rule_risk(market: dict[str, Any]) -> tuple[bool, str]:
        text = " ".join(str(market.get(key, "")) for key in ["description", "ancillaryData"])
        normalized = text.lower().replace(" ", "")
        if "excludes≥4-≥4" in normalized or "excludes>=4->=4" in normalized:
            return True, "42 Team Win excludes >=4->=4, not fully equivalent to Polymarket Team Win"
        return False, ""
