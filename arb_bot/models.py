from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class HedgeStatus(str, Enum):
    HEDGEABLE = "HEDGEABLE"
    NOT_HEDGEABLE = "NOT_HEDGEABLE"
    NOT_FULLY_HEDGEABLE = "NOT_FULLY_HEDGEABLE"


class Action(str, Enum):
    ALERT_ONLY = "ALERT_ONLY"
    NO_ACTION = "NO_ACTION"
    ARBITRAGE = "ARBITRAGE_BUY_42_AND_BUY_POLYMARKET_OPPOSITE"


@dataclass(frozen=True)
class OutcomeQuote:
    outcome_id: str
    name: str
    decimal_odds: float | None = None
    buy_depth: float = 0.0
    sell_depth: float = 0.0
    buy_quote: float | None = None
    sell_quote: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class OrderBook:
    bids: list[OrderBookLevel] = field(default_factory=list)
    asks: list[OrderBookLevel] = field(default_factory=list)

    def ask_liquidity(self, max_price: float | None = None) -> float:
        levels = self.asks if max_price is None else [level for level in self.asks if level.price <= max_price]
        return sum(level.size for level in levels)


@dataclass(frozen=True)
class PolymarketSnapshot:
    market_id: str
    yes_price: float
    no_price: float
    yes_book: OrderBook
    no_book: OrderBook
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class FortyTwoSnapshot:
    market_id: str
    market_type: str
    outcomes: list[OutcomeQuote]
    redeem_tax: float | None
    quick_select_text: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RuleCheckResult:
    status: HedgeStatus
    action: Action
    reasons: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == HedgeStatus.HEDGEABLE and self.action != Action.ALERT_ONLY


@dataclass(frozen=True)
class ArbitrageSignal:
    event_name: str
    target_outcome: str
    action: Action
    status: HedgeStatus
    forty_two_equivalent_probability: float
    polymarket_reference_probability: float
    polymarket_opposite_price: float
    total_cost: float
    locked_profit_estimate: float
    expected_roi: float
    suggested_42_orders: list[dict[str, Any]]
    suggested_polymarket_order: dict[str, Any]
    risk_flags: list[str]
    rule_reasons: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ExecutionReport:
    signal: ArbitrageSignal
    paper_trading: bool
    auto_trade: bool
    executed: bool
    order_ids: list[str]
    reason: str
