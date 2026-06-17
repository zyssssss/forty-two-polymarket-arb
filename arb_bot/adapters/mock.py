from __future__ import annotations

from arb_bot.adapters.base import FortyTwoAdapter, PolymarketAdapter
from arb_bot.models import FortyTwoSnapshot, OrderBook, OrderBookLevel, OutcomeQuote, PolymarketSnapshot


class MockPolymarketAdapter(PolymarketAdapter):
    def get_snapshot(self, market_id: str) -> PolymarketSnapshot:
        return PolymarketSnapshot(
            market_id=market_id,
            yes_price=0.67,
            no_price=0.33,
            yes_book=OrderBook(asks=[OrderBookLevel(price=0.67, size=100.0)]),
            no_book=OrderBook(asks=[OrderBookLevel(price=0.33, size=100.0)]),
        )

    def average_fill_price(self, market_id: str, outcome: str, size: float) -> float:
        return 0.33 if outcome.upper().endswith("NO") or outcome.upper() == "NO" else 0.67

    def place_limit_order(self, market_id: str, outcome: str, price: float, size: float) -> str:
        return f"paper-poly-{market_id}-{outcome}-{price}-{size}"


class MockFortyTwoAdapter(FortyTwoAdapter):
    def get_snapshot(self, market_id: str, market_type: str) -> FortyTwoSnapshot:
        outcomes = [
            OutcomeQuote("score-1-0", "1-0", decimal_odds=10.0, buy_depth=100),
            OutcomeQuote("score-2-0", "2-0", decimal_odds=10.0, buy_depth=100),
            OutcomeQuote("score-2-1", "2-1", decimal_odds=10.0, buy_depth=100),
            OutcomeQuote("score-3-0", "3-0", decimal_odds=10.0, buy_depth=100),
            OutcomeQuote("score-3-1", "3-1", decimal_odds=10.0, buy_depth=100),
            OutcomeQuote("score-3-2", "3-2", decimal_odds=20.0, buy_depth=100),
        ]
        return FortyTwoSnapshot(
            market_id=market_id,
            market_type=market_type,
            outcomes=outcomes,
            redeem_tax=0.0,
            quick_select_text="FRA wins the match",
        )

    def get_buy_quote(self, market_id: str, outcome_id: str, stake: float) -> dict:
        return {"market_id": market_id, "outcome_id": outcome_id, "stake": stake, "fee": 0.0}

    def get_sell_or_redeem_quote(self, market_id: str, outcome_id: str, size: float) -> dict:
        return {"market_id": market_id, "outcome_id": outcome_id, "size": size, "redeem_tax": 0.0}

    def place_limit_order(self, market_id: str, outcome_id: str, stake: float, limit_odds: float) -> str:
        return f"paper-42-{market_id}-{outcome_id}-{stake}-{limit_odds}"

    def emergency_unwind(self, market_id: str, order_ids: list[str]) -> None:
        return None
