from __future__ import annotations

from arb_bot.adapters.base import FortyTwoAdapter, PolymarketAdapter
from arb_bot.config import BotConfig
from arb_bot.core.arbitrage import ArbitrageEngine
from arb_bot.models import Action, ArbitrageSignal, ExecutionReport


class ExecutionEngine:
    def __init__(
        self,
        config: BotConfig,
        engine: ArbitrageEngine,
        forty_two_adapter: FortyTwoAdapter,
        polymarket_adapter: PolymarketAdapter,
    ) -> None:
        self.config = config
        self.engine = engine
        self.forty_two_adapter = forty_two_adapter
        self.polymarket_adapter = polymarket_adapter

    def execute(self, signal: ArbitrageSignal, mapping: dict) -> ExecutionReport:
        if signal.action != Action.ARBITRAGE:
            return ExecutionReport(signal, self.config.paper_trading, self.config.auto_trade, False, [], "signal is not executable arbitrage")
        if self.config.paper_trading or not self.config.auto_trade:
            return ExecutionReport(signal, self.config.paper_trading, self.config.auto_trade, False, ["paper-only"], "paper trading or auto_trade disabled")

        refreshed_42 = self.forty_two_adapter.get_snapshot(mapping["forty_two_market_id"], mapping["forty_two_market_type"])
        refreshed_poly = self.polymarket_adapter.get_snapshot(mapping["polymarket_market_id"])
        refreshed = self.engine.evaluate(mapping, refreshed_poly, refreshed_42)
        if refreshed.action != Action.ARBITRAGE:
            return ExecutionReport(refreshed, self.config.paper_trading, self.config.auto_trade, False, [], "profit or safety checks failed after requote")

        order_ids: list[str] = []
        try:
            for order in refreshed.suggested_42_orders:
                order_ids.append(
                    self.forty_two_adapter.place_limit_order(
                        mapping["forty_two_market_id"],
                        str(order["outcome_id"]),
                        float(order["stake"]),
                        float(order["decimal_odds"]),
                    )
                )
            poly = refreshed.suggested_polymarket_order
            order_ids.append(
                self.polymarket_adapter.place_limit_order(
                    str(poly["market_id"]),
                    str(poly["outcome"]),
                    float(poly["price"]),
                    float(poly["size"]),
                )
            )
        except Exception as exc:
            self.forty_two_adapter.emergency_unwind(mapping["forty_two_market_id"], order_ids)
            return ExecutionReport(refreshed, self.config.paper_trading, self.config.auto_trade, False, order_ids, f"execution failed; emergency unwind attempted: {exc}")

        return ExecutionReport(refreshed, self.config.paper_trading, self.config.auto_trade, True, order_ids, "executed")
