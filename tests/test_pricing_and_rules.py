from __future__ import annotations

from arb_bot.adapters.mock import MockFortyTwoAdapter, MockPolymarketAdapter
from arb_bot.config import BotConfig
from arb_bot.core.arbitrage import ArbitrageEngine
from arb_bot.core.pricing import decimal_odds_to_probability, polymarket_price_to_probability
from arb_bot.core.rules import check_rule_consistency
from arb_bot.models import Action, HedgeStatus


def _mapping() -> dict:
    return {
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


def test_basic_probability_conversions() -> None:
    assert decimal_odds_to_probability(2.0) == 0.5
    assert polymarket_price_to_probability(67) == 0.67
    assert polymarket_price_to_probability(0.67) == 0.67


def test_arbitrage_signal_for_demo_numbers() -> None:
    mapping = _mapping()
    signal = ArbitrageEngine(BotConfig(min_profit_margin=0.03, safety_margin=0.0)).evaluate(
        mapping,
        MockPolymarketAdapter().get_snapshot(mapping["polymarket_market_id"]),
        MockFortyTwoAdapter().get_snapshot(mapping["forty_two_market_id"], mapping["forty_two_market_type"]),
    )
    assert signal.action == Action.ARBITRAGE
    assert round(signal.forty_two_equivalent_probability, 2) == 0.55
    assert round(signal.polymarket_opposite_price, 2) == 0.33
    assert round(signal.total_cost, 2) == 0.88
    assert round(signal.locked_profit_estimate, 2) == 0.12


def test_quick_select_excluding_high_score_bucket_is_not_fully_hedgeable() -> None:
    mapping = _mapping()
    mapping["exact_score_mapping"]["quick_select_text"] = "FRA wins the match excludes ≥4 - ≥4"
    mapping["exact_score_mapping"]["excluded_buckets"] = ["≥4-≥4"]
    result = check_rule_consistency(mapping)
    assert result.status == HedgeStatus.NOT_FULLY_HEDGEABLE
    assert result.action == Action.ALERT_ONLY
