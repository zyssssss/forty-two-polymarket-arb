from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import FortyTwoMarket, Outcome


class FortyTwoAdapter(ABC):
    @abstractmethod
    def list_worldcup_markets(self) -> list[FortyTwoMarket]:
        raise NotImplementedError


class HttpFortyTwoAdapter(FortyTwoAdapter):
    def __init__(self, api_base_url: str = "https://rest.ft.42.space", timeout: float = 15.0) -> None:
        self.api_base_url = (api_base_url or "https://rest.ft.42.space").rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(total=3, connect=3, read=3, backoff_factor=0.4, status_forcelist=(429, 500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.last_diagnostics: dict[str, Any] = {}

    def list_worldcup_markets(self) -> list[FortyTwoMarket]:
        response = self.session.get(
            f"{self.api_base_url}/api/v1/markets",
            params={
                "tag": "soccer_match",
                "status": "live",
                "category": "Sports",
                "subcategory": "Football",
                "topic": "FIFA World Cup",
                "start_date_min": "2026-01-01T00:00:00.000Z",
                "start_date_max": "2027-01-02T00:00:00.000Z",
                "limit": 500,
                "offset": 0,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", [])
        markets: list[FortyTwoMarket] = []
        rejected = 0
        for item in items:
            teams = _market_teams(item)
            if teams is None:
                rejected += 1
                continue
            outcomes = []
            invalid_outcome = False
            for value in item.get("outcomes", []):
                price = _positive_float(value.get("price"))
                payout = _positive_float(value.get("payout"))
                if price is None or payout is None:
                    invalid_outcome = True
                    break
                decimal_odds = payout / price
                if decimal_odds <= 1:
                    invalid_outcome = True
                    break
                outcomes.append(
                    Outcome(
                        name=str(value.get("name", "")),
                        decimal_odds=decimal_odds,
                        metadata={**value, "implied_probability": price / payout},
                    )
                )
            if invalid_outcome or not outcomes:
                rejected += 1
                continue
            rule_text = str(item.get("description", ""))
            for target_side, team_name in (("home", teams[0]), ("away", teams[1])):
                markets.append(
                    FortyTwoMarket(
                        event_name=f"{teams[0]} vs {teams[1]}",
                        team_name=team_name,
                        market_type="exact_score",
                        outcomes=outcomes,
                        rule_text=rule_text,
                        updated_at=item.get("updatedAt"),
                        raw={**item, "target_side": target_side, "price_model": "decimal_odds=payout/price"},
                    )
                )
        self.last_diagnostics = {
            "source": self.api_base_url,
            "raw_market_count": len(items),
            "normalized_team_market_count": len(markets),
            "rejected_market_count": rejected,
            "has_more": bool(payload.get("pagination", {}).get("hasMore")),
        }
        return markets


def _market_teams(item: dict[str, Any]) -> tuple[str, str] | None:
    question = str(item.get("question", ""))
    if " vs " not in question.lower():
        return None
    left, right = question.split(" vs ", 1)
    left = left.strip()
    right = right.split(" - ", 1)[0].strip()
    return (left, right) if left and right else None


def _positive_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


class MockFortyTwoAdapter(FortyTwoAdapter):
    def list_worldcup_markets(self) -> list[FortyTwoMarket]:
        win_scores = {
            "1-0": 7.54, "2-0": 7.00, "3-0": 8.35, "4-0": 17.23, "2-1": 8.92,
            "3-1": 13.59, "4-1": 18.39, "3-2": 28.19, "4-2": 16.40, "4-3": 32.00,
        }
        draw_scores = {"0-0": 11.00, "1-1": 7.50, "2-2": 15.00, "3-3": 40.00}
        lost_scores = {"0-1": 12.00, "0-2": 20.00, "1-2": 14.00, "0-3": 35.00, "1-3": 28.00, "2-3": 40.00}
        outcomes = [Outcome(name=score, decimal_odds=odds) for score, odds in {**win_scores, **draw_scores, **lost_scores}.items()]
        exact_score_market = FortyTwoMarket(
            event_name="FRA vs SEN",
            team_name="FRA",
            market_type="exact_score",
            outcomes=outcomes,
            rule_text="Quick Select: FRA wins the match excludes ≥4 - ≥4",
            raw={"source": "mock", "target_side": "home"},
        )
        direct_alert_market = FortyTwoMarket(
            event_name="France vs Senegal",
            team_name="France",
            market_type="team_result",
            outcomes=[
                Outcome("France Win", decimal_odds=1 / 0.55),
                Outcome("Draw", decimal_odds=1 / 0.20),
                Outcome("France Lost", decimal_odds=1 / 0.25),
            ],
            rule_text="France Win / Draw / France Lost three-way World Cup market.",
            raw={"source": "mock-alert"},
        )
        return [exact_score_market, direct_alert_market]
