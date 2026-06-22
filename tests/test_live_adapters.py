from __future__ import annotations

from unittest.mock import Mock

from src.forty_two_adapter import HttpFortyTwoAdapter
from src.polymarket_adapter import HttpPolymarketAdapter


def _response(payload: object) -> Mock:
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_forty_two_uses_payout_over_price_as_decimal_odds() -> None:
    adapter = HttpFortyTwoAdapter()
    adapter.session.get = Mock(
        return_value=_response(
            {
                "data": [
                    {
                        "question": "France vs Senegal",
                        "description": "90 minutes plus stoppage.",
                        "updatedAt": "2026-06-21T03:00:00Z",
                        "outcomes": [
                            {"name": "FRA 1–0 SEN", "price": 0.01, "payout": 0.02},
                            {"name": "FRA 1–1 SEN", "price": 0.01, "payout": 0.04},
                            {"name": "FRA 0–1 SEN", "price": 0.01, "payout": 0.05},
                        ],
                    }
                ],
                "pagination": {"hasMore": False},
            }
        )
    )
    markets = adapter.list_worldcup_markets()
    assert len(markets) == 2
    assert markets[0].outcomes[0].decimal_odds == 2.0
    assert markets[0].outcomes[0].metadata["implied_probability"] == 0.5


def test_polymarket_uses_clob_buy_prices_for_match_market() -> None:
    adapter = HttpPolymarketAdapter(search_pages=1)
    market = {
        "id": "1",
        "question": "Will France win the match?",
        "description": "No resolves if France does not win the match.",
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.67", "0.33"]',
        "clobTokenIds": '["yes-token", "no-token"]',
        "updatedAt": "2026-06-21T03:00:00Z",
        "events": [{"title": "France vs Senegal - World Cup"}],
    }
    adapter._fetch_candidates = Mock(return_value=[market])
    adapter._clob_buy_price = Mock(side_effect=[0.68, 0.34, 0.68])
    result = adapter.list_worldcup_markets()
    assert len(result) == 1
    assert result[0].yes_price == 0.68
    assert result[0].no_price == 0.34
    assert result[0].raw["price_source"] == "clob_buy"
