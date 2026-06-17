from __future__ import annotations

from typing import Any

from arb_bot.config import BotConfig
from arb_bot.core.pricing import (
    calculate_forty_two_basket_cost,
    calculate_polymarket_hedge_cost,
    calculate_total_expected_cost_after_fees_and_slippage,
    exact_score_market_to_equivalent_probability,
    polymarket_price_to_probability,
)
from arb_bot.core.rules import check_rule_consistency
from arb_bot.models import Action, ArbitrageSignal, FortyTwoSnapshot, HedgeStatus, PolymarketSnapshot


class ArbitrageEngine:
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def evaluate(
        self,
        mapping: dict[str, Any],
        polymarket: PolymarketSnapshot,
        forty_two: FortyTwoSnapshot,
        target_payout: float = 1.0,
    ) -> ArbitrageSignal:
        rule_check = check_rule_consistency(mapping)
        target_scores = list(mapping.get("exact_score_mapping", {}).get("target_scores", []))
        risk_flags = list(rule_check.reasons)

        if forty_two.redeem_tax is None:
            risk_flags.append("42 redeem tax unavailable; live trading prohibited")

        if mapping.get("forty_two_market_type") == "exact_score":
            forty_two_probability = exact_score_market_to_equivalent_probability(forty_two.outcomes, target_scores)
            forty_two_cost, suggested_42_orders = calculate_forty_two_basket_cost(
                target_scores,
                forty_two.outcomes,
                target_payout=target_payout,
            )
        else:
            outcome = _find_outcome(forty_two, mapping["target_outcome"])
            if outcome.decimal_odds is None:
                raise ValueError(f"42 outcome {mapping['target_outcome']} has no decimal odds")
            forty_two_probability = 1.0 / outcome.decimal_odds
            forty_two_cost = forty_two_probability * target_payout
            suggested_42_orders = [
                {
                    "outcome_id": outcome.outcome_id,
                    "outcome": outcome.name,
                    "decimal_odds": outcome.decimal_odds,
                    "stake": forty_two_cost,
                    "expected_payout": target_payout,
                }
            ]

        polymarket_reference_probability = polymarket_price_to_probability(polymarket.yes_price)
        polymarket_opposite_price = polymarket_price_to_probability(polymarket.no_price)
        polymarket_cost = calculate_polymarket_hedge_cost(polymarket_opposite_price, target_payout=target_payout)
        slippage = self.config.safety_margin * 0.01
        redeem_tax = forty_two.redeem_tax if forty_two.redeem_tax is not None else 1.0
        total_cost = calculate_total_expected_cost_after_fees_and_slippage(
            forty_two_cost=forty_two_cost,
            polymarket_cost=polymarket_cost,
            forty_two_redeem_tax=redeem_tax,
            slippage=slippage,
        )
        locked_profit = target_payout - total_cost
        expected_roi = locked_profit / total_cost if total_cost > 0 else 0.0

        liquidity = polymarket.no_book.ask_liquidity()
        if liquidity < self.config.min_liquidity:
            risk_flags.append(f"Polymarket NO liquidity {liquidity:.4f} below min_liquidity {self.config.min_liquidity:.4f}")
        if forty_two_cost > self.config.max_position_per_market:
            risk_flags.append("42 suggested position exceeds max_position_per_market")
        if polymarket_cost > self.config.max_position_per_market:
            risk_flags.append("Polymarket suggested position exceeds max_position_per_market")

        profitable = total_cost < 1.0 - self.config.min_profit_margin
        executable = (
            rule_check.status == HedgeStatus.HEDGEABLE
            and forty_two.redeem_tax is not None
            and profitable
            and not risk_flags
        )
        action = Action.ARBITRAGE if executable else Action.ALERT_ONLY if risk_flags or not rule_check.ok else Action.NO_ACTION
        status = rule_check.status if rule_check.status != HedgeStatus.HEDGEABLE else HedgeStatus.HEDGEABLE

        return ArbitrageSignal(
            event_name=mapping["event_name"],
            target_outcome=mapping["target_outcome"],
            action=action,
            status=status,
            forty_two_equivalent_probability=forty_two_probability,
            polymarket_reference_probability=polymarket_reference_probability,
            polymarket_opposite_price=polymarket_opposite_price,
            total_cost=total_cost,
            locked_profit_estimate=locked_profit,
            expected_roi=expected_roi,
            suggested_42_orders=suggested_42_orders,
            suggested_polymarket_order={
                "market_id": polymarket.market_id,
                "side": "BUY",
                "outcome": mapping.get("polymarket_outcome_no", "NO"),
                "price": polymarket_opposite_price,
                "size": target_payout,
                "type": "LIMIT",
            },
            risk_flags=risk_flags,
            rule_reasons=rule_check.reasons,
        )


def _find_outcome(snapshot: FortyTwoSnapshot, name: str):
    for outcome in snapshot.outcomes:
        if outcome.name == name or outcome.outcome_id == name:
            return outcome
    raise ValueError(f"Outcome {name} not found in 42 snapshot")
