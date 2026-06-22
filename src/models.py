from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SuggestedAction(str, Enum):
    ALERT_ARBITRAGE_OPPORTUNITY = "ALERT_ARBITRAGE_OPPORTUNITY"
    NO_SIGNAL_CONDITION_A_FAILED = "NO_SIGNAL_CONDITION_A_FAILED"
    NO_SIGNAL_CONDITION_B_FAILED = "NO_SIGNAL_CONDITION_B_FAILED"
    NO_SIGNAL_BOTH_CONDITIONS_FAILED = "NO_SIGNAL_BOTH_CONDITIONS_FAILED"
    RULE_RISK_ONLY = "RULE_RISK_ONLY"


@dataclass(frozen=True)
class Outcome:
    name: str
    decimal_odds: float | None = None
    price: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FortyTwoMarket:
    event_name: str
    team_name: str
    market_type: str
    outcomes: list[Outcome]
    rule_text: str = ""
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolymarketMarket:
    event_name: str
    team_name: str
    yes_price: float
    no_price: float | None
    rule_text: str = ""
    updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FortyTwoNormalized:
    platform: str
    event_name: str
    team_name: str
    market_type: str
    team_win_cost: float
    team_draw_cost: float
    team_lost_cost: float
    rule_risk: bool
    rule_risk_reason: str
    timestamp: str
    data_source: str = "42"
    groups: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class PolymarketNormalized:
    platform: str
    event_name: str
    team_name: str
    team_yes_cost: float
    team_no_cost: float
    no_cost_is_estimated: bool
    rule_risk: bool
    rule_risk_reason: str
    timestamp: str
    data_source: str = "polymarket"


@dataclass(frozen=True)
class MatchedMarket:
    forty_two: FortyTwoMarket
    polymarket: PolymarketMarket
    canonical_event_name: str
    canonical_team_name: str


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
    suggested_action: SuggestedAction


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
