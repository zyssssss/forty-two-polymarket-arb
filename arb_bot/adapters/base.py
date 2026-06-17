from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from arb_bot.models import FortyTwoSnapshot, PolymarketSnapshot


class PolymarketAdapter(ABC):
    @abstractmethod
    def get_snapshot(self, market_id: str) -> PolymarketSnapshot:
        raise NotImplementedError

    @abstractmethod
    def average_fill_price(self, market_id: str, outcome: str, size: float) -> float:
        raise NotImplementedError

    @abstractmethod
    def place_limit_order(self, market_id: str, outcome: str, price: float, size: float) -> str:
        raise NotImplementedError


class FortyTwoAdapter(ABC):
    @abstractmethod
    def get_snapshot(self, market_id: str, market_type: str) -> FortyTwoSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_buy_quote(self, market_id: str, outcome_id: str, stake: float) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_sell_or_redeem_quote(self, market_id: str, outcome_id: str, size: float) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def place_limit_order(self, market_id: str, outcome_id: str, stake: float, limit_odds: float) -> str:
        raise NotImplementedError

    @abstractmethod
    def emergency_unwind(self, market_id: str, order_ids: list[str]) -> None:
        raise NotImplementedError
