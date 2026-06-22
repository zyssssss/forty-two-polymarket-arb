from __future__ import annotations

from src.arbitrage_detector import detect_arbitrage
from src.models import FortyTwoNormalized, PolymarketNormalized, SuggestedAction


def _forty_two(win: float = 0.55, draw: float = 0.20, lost: float = 0.25) -> FortyTwoNormalized:
    return FortyTwoNormalized(
        platform="42",
        event_name="France vs Senegal",
        team_name="France",
        market_type="team_result",
        team_win_cost=win,
        team_draw_cost=draw,
        team_lost_cost=lost,
        rule_risk=False,
        rule_risk_reason="",
        timestamp="2026-06-17T03:00:00Z",
    )


def _poly(no: float = 0.33) -> PolymarketNormalized:
    return PolymarketNormalized(
        platform="polymarket",
        event_name="France vs Senegal",
        team_name="France",
        team_yes_cost=1 - no,
        team_no_cost=no,
        no_cost_is_estimated=False,
        rule_risk=False,
        rule_risk_reason="",
        timestamp="2026-06-17T03:00:00Z",
    )


def test_condition_a_passes_when_total_cost_below_threshold() -> None:
    signal = detect_arbitrage(_forty_two(win=0.55), _poly(no=0.33), 0.9)
    assert signal.condition_a_passed is True


def test_condition_a_fails_when_total_cost_at_or_above_threshold() -> None:
    signal = detect_arbitrage(_forty_two(win=0.58), _poly(no=0.33), 0.9)
    assert signal.condition_a_passed is False
    assert signal.suggested_action == SuggestedAction.NO_SIGNAL_CONDITION_A_FAILED


def test_condition_b_passes_when_draw_plus_lost_greater_than_poly_no() -> None:
    signal = detect_arbitrage(_forty_two(draw=0.20, lost=0.25), _poly(no=0.33), 0.9)
    assert signal.condition_b_passed is True


def test_condition_b_fails_when_draw_plus_lost_not_greater_than_poly_no() -> None:
    signal = detect_arbitrage(_forty_two(draw=0.10, lost=0.20), _poly(no=0.33), 0.9)
    assert signal.condition_b_passed is False
    assert signal.suggested_action == SuggestedAction.NO_SIGNAL_CONDITION_B_FAILED


def test_alert_only_when_condition_a_and_condition_b_both_pass() -> None:
    signal = detect_arbitrage(_forty_two(win=0.55, draw=0.20, lost=0.25), _poly(no=0.33), 0.9)
    assert signal.suggested_action == SuggestedAction.ALERT_ARBITRAGE_OPPORTUNITY
    assert round(signal.total_cost, 2) == 0.88
    assert round(signal.theoretical_margin, 2) == 0.12
    assert round(signal.polymarket_no_discount_vs_42, 2) == 0.12


def test_polymarket_rule_risk_blocks_alert() -> None:
    risky_poly = PolymarketNormalized(
        platform="polymarket",
        event_name="France vs Senegal",
        team_name="France",
        team_yes_cost=0.67,
        team_no_cost=0.33,
        no_cost_is_estimated=False,
        rule_risk=True,
        rule_risk_reason="Polymarket Team No rule is not confirmed as Draw + Team Lost",
        timestamp="2026-06-17T03:00:00Z",
    )
    signal = detect_arbitrage(_forty_two(), risky_poly, 0.9)
    assert signal.condition_a_passed is True
    assert signal.condition_b_passed is True
    assert signal.suggested_action == SuggestedAction.RULE_RISK_ONLY
