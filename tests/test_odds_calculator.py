from __future__ import annotations

from src.forty_two_adapter import MockFortyTwoAdapter
from src.models import FortyTwoMarket, Outcome, PolymarketMarket
from src.odds_calculator import (
    decimal_odds_to_implied_probability,
    normalize_forty_two_market,
    normalize_polymarket_market,
    polymarket_price_to_cost,
)


def test_decimal_odds_to_implied_probability() -> None:
    assert decimal_odds_to_implied_probability(2.0) == 0.5


def test_polymarket_yes_no_price_conversion() -> None:
    normalized = normalize_polymarket_market(
        PolymarketMarket(
            event_name="France vs Senegal",
            team_name="France",
            yes_price=67,
            no_price=None,
            rule_text="No means France does not win: Draw + France lost.",
        )
    )
    assert polymarket_price_to_cost(67) == 0.67
    assert normalized.team_yes_cost == 0.67
    assert round(normalized.team_no_cost, 2) == 0.33
    assert normalized.no_cost_is_estimated is True


def test_exact_score_team_win_cost_sum() -> None:
    market = MockFortyTwoAdapter().list_worldcup_markets()[0]
    normalized = normalize_forty_two_market(market)
    expected = sum(1 / odd for odd in [7.54, 7.00, 8.35, 17.23, 8.92, 13.59, 18.39, 28.19, 16.40, 32.00])
    assert abs(normalized.team_win_cost - expected) < 1e-12


def test_exact_score_team_draw_cost_sum() -> None:
    market = MockFortyTwoAdapter().list_worldcup_markets()[0]
    normalized = normalize_forty_two_market(market)
    expected = sum(1 / odd for odd in [11.00, 7.50, 15.00, 40.00])
    assert abs(normalized.team_draw_cost - expected) < 1e-12


def test_exact_score_team_lost_cost_sum() -> None:
    market = MockFortyTwoAdapter().list_worldcup_markets()[0]
    normalized = normalize_forty_two_market(market)
    expected = sum(1 / odd for odd in [12.00, 20.00, 14.00, 35.00, 28.00, 40.00])
    assert abs(normalized.team_lost_cost - expected) < 1e-12


def test_direct_team_result_market() -> None:
    market = FortyTwoMarket(
        event_name="France vs Senegal",
        team_name="France",
        market_type="team_result",
        outcomes=[
            Outcome("France Win", decimal_odds=2.0),
            Outcome("Draw", decimal_odds=4.0),
            Outcome("France Lost", decimal_odds=5.0),
        ],
    )
    normalized = normalize_forty_two_market(market)
    assert normalized.team_win_cost == 0.5
    assert normalized.team_draw_cost == 0.25
    assert normalized.team_lost_cost == 0.2


def test_excludes_4_4_sets_rule_risk() -> None:
    market = MockFortyTwoAdapter().list_worldcup_markets()[0]
    normalized = normalize_forty_two_market(market)
    assert normalized.rule_risk is True
    assert "≥4-≥4" in normalized.rule_risk_reason


def test_live_42_score_names_and_away_orientation() -> None:
    outcomes = [
        Outcome("TUR 1–0 USA", decimal_odds=2.0),
        Outcome("TUR 1–1 USA", decimal_odds=4.0),
        Outcome("TUR 0–≥4 USA", decimal_odds=5.0),
    ]
    home = normalize_forty_two_market(
        FortyTwoMarket("Türkiye vs USA", "Türkiye", "exact_score", outcomes, raw={"target_side": "home"})
    )
    away = normalize_forty_two_market(
        FortyTwoMarket("Türkiye vs USA", "USA", "exact_score", outcomes, raw={"target_side": "away"})
    )
    assert home.team_win_cost == 0.5
    assert home.team_draw_cost == 0.25
    assert home.team_lost_cost == 0.2
    assert away.team_win_cost == 0.2
    assert away.team_draw_cost == 0.25
    assert away.team_lost_cost == 0.5


def test_ambiguous_4_4_bucket_is_excluded_and_flagged() -> None:
    market = FortyTwoMarket(
        "France vs Senegal",
        "France",
        "exact_score",
        [
            Outcome("FRA 1–0 SEN", decimal_odds=2.0),
            Outcome("FRA 1–1 SEN", decimal_odds=4.0),
            Outcome("FRA 0–1 SEN", decimal_odds=5.0),
            Outcome("FRA ≥4–≥4 SEN", decimal_odds=10.0),
        ],
        raw={"target_side": "home"},
    )
    normalized = normalize_forty_two_market(market)
    assert normalized.team_draw_cost == 0.25
    assert normalized.rule_risk is True
