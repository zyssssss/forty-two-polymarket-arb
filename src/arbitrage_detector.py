from __future__ import annotations

from src.models import ArbitrageSignal, FortyTwoNormalized, PolymarketNormalized, SuggestedAction, utc_now_iso


def detect_arbitrage(
    forty_two: FortyTwoNormalized,
    polymarket: PolymarketNormalized,
    target_total_cost_threshold: float = 0.9,
    allow_partial_coverage_alert: bool = True,
) -> ArbitrageSignal:
    draw_plus_lost = forty_two.team_draw_cost + forty_two.team_lost_cost
    total_cost = forty_two.team_win_cost + polymarket.team_no_cost
    theoretical_margin = 1.0 - total_cost
    discount = draw_plus_lost - polymarket.team_no_cost
    condition_a = total_cost < target_total_cost_threshold
    condition_b = draw_plus_lost > polymarket.team_no_cost
    rule_risk = forty_two.rule_risk or polymarket.rule_risk
    rule_reason = "; ".join(reason for reason in (forty_two.rule_risk_reason, polymarket.rule_risk_reason) if reason)

    if polymarket.rule_risk:
        action = SuggestedAction.RULE_RISK_ONLY
    elif condition_a and condition_b and (allow_partial_coverage_alert or not forty_two.rule_risk):
        action = SuggestedAction.ALERT_ARBITRAGE_OPPORTUNITY
    elif condition_a and not condition_b:
        action = SuggestedAction.NO_SIGNAL_CONDITION_B_FAILED
    elif condition_b and not condition_a:
        action = SuggestedAction.NO_SIGNAL_CONDITION_A_FAILED
    elif rule_risk:
        action = SuggestedAction.RULE_RISK_ONLY
    else:
        action = SuggestedAction.NO_SIGNAL_BOTH_CONDITIONS_FAILED

    return ArbitrageSignal(
        event_name=forty_two.event_name,
        team_name=forty_two.team_name,
        forty_two_team_win_cost=forty_two.team_win_cost,
        forty_two_team_draw_cost=forty_two.team_draw_cost,
        forty_two_team_lost_cost=forty_two.team_lost_cost,
        forty_two_draw_plus_lost_cost=draw_plus_lost,
        polymarket_team_yes_cost=polymarket.team_yes_cost,
        polymarket_team_no_cost=polymarket.team_no_cost,
        no_cost_is_estimated=polymarket.no_cost_is_estimated,
        total_cost=total_cost,
        theoretical_margin=theoretical_margin,
        polymarket_no_discount_vs_42=discount,
        condition_a_passed=condition_a,
        condition_b_passed=condition_b,
        rule_risk=rule_risk,
        rule_risk_reason=rule_reason,
        data_source="42+polymarket",
        timestamp=utc_now_iso(),
        suggested_action=action,
    )
