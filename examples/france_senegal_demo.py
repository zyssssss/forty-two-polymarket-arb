from __future__ import annotations

from arb_bot.adapters.mock import MockFortyTwoAdapter, MockPolymarketAdapter
from arb_bot.config import BotConfig
from arb_bot.core.arbitrage import ArbitrageEngine
from arb_bot.notifications import format_signal


def main() -> None:
    config = BotConfig(min_profit_margin=0.03, safety_margin=0.0, min_liquidity=10.0)
    mapping = {
        "event_name": "France vs Senegal",
        "polymarket_market_id": "poly-france-senegal",
        "polymarket_outcome_yes": "France YES",
        "polymarket_outcome_no": "France NO",
        "forty_two_market_id": "42-france-senegal-exact-score",
        "forty_two_market_type": "exact_score",
        "target_outcome": "France Win",
        "settlement_definition": "90 minutes only",
        "polymarket_settlement_definition": "90 minutes only",
        "forty_two_settlement_definition": "90 minutes only",
        "settlement_time": "2026-06-20T20:00:00Z",
        "polymarket_settlement_time": "2026-06-20T20:00:00Z",
        "forty_two_settlement_time": "2026-06-20T20:00:00Z",
        "exact_score_mapping": {
            "target_scores": ["1-0", "2-0", "2-1", "3-0", "3-1", "3-2"],
            "excluded_buckets": [],
            "is_complete_target_coverage": True,
            "quick_select_text": "FRA wins the match",
        },
    }
    poly = MockPolymarketAdapter().get_snapshot(mapping["polymarket_market_id"])
    forty_two = MockFortyTwoAdapter().get_snapshot(mapping["forty_two_market_id"], mapping["forty_two_market_type"])
    signal = ArbitrageEngine(config).evaluate(mapping, poly, forty_two)
    print(format_signal(signal, auto_trade_allowed=False))
    print(f"action={signal.action.value}")


if __name__ == "__main__":
    main()
