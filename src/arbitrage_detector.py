from __future__ import annotations

from src.models import ArbitrageSignal, FortyTwoTeamCosts, PolymarketTeamMarket, utc_now_iso


def detect_arbitrage(
    ft: FortyTwoTeamCosts,
    poly: PolymarketTeamMarket,
    target_total_cost_threshold: float = 0.9,
) -> ArbitrageSignal:
    draw_plus_lost = ft.team_draw_cost + ft.team_lost_cost
    total_cost = ft.team_win_cost + poly.no_cost
    theoretical_margin = 1.0 - total_cost
    discount = draw_plus_lost - poly.no_cost
    condition_a = total_cost < target_total_cost_threshold
    condition_b = draw_plus_lost > poly.no_cost

    if condition_a and condition_b:
        action = "ALERT_ARBITRAGE_OPPORTUNITY"
    elif condition_a:
        action = "NO_SIGNAL_CONDITION_B_FAILED"
    elif condition_b:
        action = "NO_SIGNAL_CONDITION_A_FAILED"
    else:
        action = "NO_SIGNAL_BOTH_CONDITIONS_FAILED"

    rule_risk = ft.rule_risk or poly.rule_risk
    rule_reason = "; ".join(reason for reason in [ft.rule_risk_reason, poly.rule_risk_reason] if reason)
    return ArbitrageSignal(
        event_name=ft.event_name,
        team_name=ft.team_name,
        forty_two_team_win_cost=ft.team_win_cost,
        forty_two_team_draw_cost=ft.team_draw_cost,
        forty_two_team_lost_cost=ft.team_lost_cost,
        forty_two_draw_plus_lost_cost=draw_plus_lost,
        polymarket_team_yes_cost=poly.yes_cost,
        polymarket_team_no_cost=poly.no_cost,
        no_cost_is_estimated=poly.no_cost_is_estimated,
        total_cost=total_cost,
        theoretical_margin=theoretical_margin,
        polymarket_no_discount_vs_42=discount,
        condition_a_passed=condition_a,
        condition_b_passed=condition_b,
        rule_risk=rule_risk,
        rule_risk_reason=rule_reason,
        data_source="42.space REST + Polymarket Gamma",
        timestamp=utc_now_iso(),
        suggested_action=action,
    )
