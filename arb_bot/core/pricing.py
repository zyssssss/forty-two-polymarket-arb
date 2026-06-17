from __future__ import annotations

from arb_bot.models import OutcomeQuote


def decimal_odds_to_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1:
        raise ValueError("decimal_odds must be greater than 1")
    return 1.0 / decimal_odds


def polymarket_price_to_probability(price_cents: float) -> float:
    price = price_cents / 100.0 if price_cents > 1 else price_cents
    if not 0 <= price <= 1:
        raise ValueError("Polymarket price must be a probability or cents in [0, 100]")
    return price


def exact_score_market_to_equivalent_probability(
    outcomes: list[OutcomeQuote],
    target_score_list: list[str],
) -> float:
    wanted = set(target_score_list)
    by_name = {outcome.name: outcome for outcome in outcomes}
    missing = sorted(wanted - set(by_name))
    if missing:
        raise ValueError(f"Missing exact score outcomes: {', '.join(missing)}")
    total = 0.0
    for score in target_score_list:
        outcome = by_name[score]
        if outcome.decimal_odds is None:
            raise ValueError(f"Outcome {score} has no decimal odds")
        total += decimal_odds_to_probability(outcome.decimal_odds)
    return total


def calculate_forty_two_basket_cost(
    target_scores: list[str],
    outcomes: list[OutcomeQuote],
    target_payout: float = 1.0,
) -> tuple[float, list[dict[str, float | str]]]:
    if target_payout <= 0:
        raise ValueError("target_payout must be positive")
    by_name = {outcome.name: outcome for outcome in outcomes}
    orders: list[dict[str, float | str]] = []
    total_cost = 0.0
    for score in target_scores:
        outcome = by_name[score]
        if outcome.decimal_odds is None:
            raise ValueError(f"Outcome {score} has no decimal odds")
        stake = target_payout / outcome.decimal_odds
        total_cost += stake
        orders.append(
            {
                "outcome_id": outcome.outcome_id,
                "outcome": outcome.name,
                "decimal_odds": outcome.decimal_odds,
                "stake": stake,
                "expected_payout": target_payout,
            }
        )
    return total_cost, orders


def calculate_polymarket_hedge_cost(opposite_price: float, target_payout: float = 1.0) -> float:
    if target_payout <= 0:
        raise ValueError("target_payout must be positive")
    return polymarket_price_to_probability(opposite_price) * target_payout


def calculate_total_expected_cost_after_fees_and_slippage(
    forty_two_cost: float,
    polymarket_cost: float,
    forty_two_fee: float = 0.0,
    polymarket_fee: float = 0.0,
    forty_two_redeem_tax: float = 0.0,
    slippage: float = 0.0,
) -> float:
    extras = forty_two_fee + polymarket_fee + forty_two_redeem_tax + slippage
    if extras < 0:
        raise ValueError("fees, tax, and slippage cannot be negative in expected cost")
    return forty_two_cost + polymarket_cost + extras
