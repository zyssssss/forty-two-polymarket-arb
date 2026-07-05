from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class PolymarketTeamMarket:
    event_name: str
    team_name: str
    opponent_name: str
    yes_cost: float
    no_cost: float
    no_cost_is_estimated: bool
    rule_risk: bool = False
    rule_risk_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class FortyTwoTeamCosts:
    platform: str
    event_name: str
    team_name: str
    opponent_name: str
    market_type: str
    team_win_cost: float
    team_draw_cost: float
    team_lost_cost: float
    rule_risk: bool
    rule_risk_reason: str
    raw: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class ArbitrageSignal:
    event_name: str
    team_name: str
    forty_two_team_win_cost: float
    forty_two_team_draw_cost: float
    forty_two_team_lost_cost: float
    forty_two_draw_plus_lost_cost: float
    polymarket_team_yes_cost: float
    polymarket_team_no_cost: float
    no_cost_is_estimated: bool
    total_cost: float
    theoretical_margin: float
    polymarket_no_discount_vs_42: float
    condition_a_passed: bool
    condition_b_passed: bool
    rule_risk: bool
    rule_risk_reason: str
    data_source: str
    timestamp: str
    suggested_action: str
