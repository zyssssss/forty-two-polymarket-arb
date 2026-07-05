from __future__ import annotations

import pytest

from src.arbitrage_detector import detect_arbitrage
from src.models import FortyTwoTeamCosts, PolymarketTeamMarket
from src.odds_calculator import ScoreOutcome, decimal_odds_to_implied_probability, exact_score_costs, polymarket_yes_no_cost
from src.team_normalizer import TeamNormalizer


def test_decimal_odds_to_implied_probability() -> None:
    assert round(decimal_odds_to_implied_probability(7.54), 6) == round(1 / 7.54, 6)
    with pytest.raises(ValueError):
        decimal_odds_to_implied_probability(1.0)


def test_polymarket_yes_no_price_conversion() -> None:
    yes, no, estimated = polymarket_yes_no_cost(0.67, 0.33)
    assert yes == 0.67
    assert no == 0.33
    assert estimated is False
    yes, no, estimated = polymarket_yes_no_cost(67, None)
    assert yes == 0.67
    assert round(no, 2) == 0.33
    assert estimated is True


def france_senegal_outcomes() -> list[ScoreOutcome]:
    data = {
        "1-0": 7.54, "2-0": 7.00, "3-0": 8.35, "4-0": 17.23, "2-1": 8.92,
        "3-1": 13.59, "4-1": 18.39, "3-2": 28.19, "4-2": 16.40, "4-3": 32.00,
        "0-0": 11.00, "1-1": 7.50, "2-2": 15.00, "3-3": 40.00,
        "0-1": 12.00, "0-2": 20.00, "1-2": 14.00, "0-3": 35.00, "1-3": 28.00, "2-3": 40.00,
    }
    return [ScoreOutcome(name=name, decimal_odds=odds) for name, odds in data.items()]


def test_exact_score_team_win_cost() -> None:
    win, _draw, _lost, _risk, _reason, groups = exact_score_costs(france_senegal_outcomes(), "home")
    expected = sum(1 / x for x in [7.54, 7.00, 8.35, 17.23, 8.92, 13.59, 18.39, 28.19, 16.40, 32.00])
    assert round(win, 6) == round(expected, 6)
    assert len(groups["win"]) == 10


def test_exact_score_team_draw_cost() -> None:
    _win, draw, _lost, _risk, _reason, groups = exact_score_costs(france_senegal_outcomes(), "home")
    expected = sum(1 / x for x in [11.00, 7.50, 15.00, 40.00])
    assert round(draw, 6) == round(expected, 6)
    assert len(groups["draw"]) == 4


def test_exact_score_team_lost_cost() -> None:
    _win, _draw, lost, _risk, _reason, groups = exact_score_costs(france_senegal_outcomes(), "home")
    expected = sum(1 / x for x in [12.00, 20.00, 14.00, 35.00, 28.00, 40.00])
    assert round(lost, 6) == round(expected, 6)
    assert len(groups["lost"]) == 6


def make_signal(win: float, draw: float, lost: float, no: float):
    ft = FortyTwoTeamCosts("42", "France vs Senegal", "France", "Senegal", "exact_score", win, draw, lost, False, "")
    poly = PolymarketTeamMarket("France vs Senegal", "France", "Senegal", 1 - no, no, False)
    return detect_arbitrage(ft, poly, 0.9)


def test_condition_a_passed() -> None:
    signal = make_signal(0.55, 0.20, 0.25, 0.33)
    assert signal.condition_a_passed is True


def test_condition_a_failed() -> None:
    signal = make_signal(0.60, 0.20, 0.25, 0.33)
    assert signal.condition_a_passed is False


def test_condition_b_passed() -> None:
    signal = make_signal(0.55, 0.20, 0.25, 0.33)
    assert signal.condition_b_passed is True


def test_condition_b_failed() -> None:
    signal = make_signal(0.55, 0.10, 0.10, 0.33)
    assert signal.condition_b_passed is False


def test_only_both_conditions_trigger_alert() -> None:
    assert make_signal(0.55, 0.20, 0.25, 0.33).suggested_action == "ALERT_ARBITRAGE_OPPORTUNITY"
    assert make_signal(0.60, 0.20, 0.25, 0.33).suggested_action == "NO_SIGNAL_CONDITION_A_FAILED"
    assert make_signal(0.55, 0.10, 0.10, 0.33).suggested_action == "NO_SIGNAL_CONDITION_B_FAILED"


def test_france_fra_match() -> None:
    normalizer = TeamNormalizer()
    assert normalizer.equivalent("France", "FRA")


def test_excludes_4_4_rule_risk() -> None:
    outcomes = france_senegal_outcomes() + [ScoreOutcome(name=">=4->=4", decimal_odds=50.0)]
    _win, _draw, _lost, risk, reason, groups = exact_score_costs(outcomes, "home")
    assert risk is True
    assert ">=4->=4" in groups["ambiguous"]
    assert "ambiguous" in reason
