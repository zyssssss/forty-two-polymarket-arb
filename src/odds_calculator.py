from __future__ import annotations

import re

from src.models import FortyTwoMarket, FortyTwoNormalized, Outcome, PolymarketMarket, PolymarketNormalized, utc_now_iso


def decimal_odds_to_implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1:
        raise ValueError("decimal odds must be greater than 1")
    return 1.0 / decimal_odds


def polymarket_price_to_cost(price: float) -> float:
    cost = price / 100.0 if price > 1 else price
    if not 0 <= cost <= 1:
        raise ValueError("Polymarket price must be in [0, 1] or cents in [0, 100]")
    return cost


def normalize_polymarket_market(market: PolymarketMarket) -> PolymarketNormalized:
    yes_cost = polymarket_price_to_cost(market.yes_price)
    no_cost_is_estimated = market.no_price is None
    no_cost = 1.0 - yes_cost if no_cost_is_estimated else polymarket_price_to_cost(float(market.no_price))
    rule_text = market.rule_text.lower()
    rule_ok = any(text in rule_text for text in ("does not win", "not win", "draw", "lost", "lose", "doesn't win"))
    rule_risk = not rule_ok
    return PolymarketNormalized(
        platform="polymarket",
        event_name=market.event_name,
        team_name=market.team_name,
        team_yes_cost=yes_cost,
        team_no_cost=no_cost,
        no_cost_is_estimated=no_cost_is_estimated,
        rule_risk=rule_risk,
        rule_risk_reason="" if not rule_risk else "Polymarket Team No rule is not confirmed as Draw + Team Lost",
        timestamp=market.updated_at or utc_now_iso(),
    )


def normalize_forty_two_market(market: FortyTwoMarket, flag_excludes_4_4: bool = True) -> FortyTwoNormalized:
    market_type = normalize_market_type(market.market_type)
    if market_type in {"team_result", "moneyline"}:
        win, draw, lost = _normalize_direct_three_way(market.outcomes)
        groups = {"win": ["Team Win"], "draw": ["Draw"], "lost": ["Team Lost"]}
    elif market_type == "exact_score":
        win, draw, lost, groups = _normalize_exact_score(
            market.outcomes,
            target_side=str(market.raw.get("target_side", "home")),
        )
    else:
        raise ValueError(f"Unsupported 42 market type for World Cup monitor: {market.market_type}")

    for label, value in (("team_win_cost", win), ("team_draw_cost", draw), ("team_lost_cost", lost)):
        if not 0 <= value <= 1:
            raise ValueError(f"42 {label} out of range: {value}")

    rule_risk, reason = _detect_42_rule_risk(market.rule_text, market.outcomes, flag_excludes_4_4)
    return FortyTwoNormalized(
        platform="42",
        event_name=market.event_name,
        team_name=market.team_name,
        market_type=market_type,
        team_win_cost=win,
        team_draw_cost=draw,
        team_lost_cost=lost,
        rule_risk=rule_risk,
        rule_risk_reason=reason,
        timestamp=market.updated_at or utc_now_iso(),
        groups=groups,
    )


def normalize_market_type(market_type: str) -> str:
    value = (market_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if value in {"team_win_draw_lost", "win_draw_lost", "three_way", "team_result"}:
        return "team_result"
    if value in {"moneyline", "1x2"}:
        return "moneyline"
    if value in {"exact_score", "correct_score"}:
        return "exact_score"
    return "other"


def _normalize_direct_three_way(outcomes: list[Outcome]) -> tuple[float, float, float]:
    win = draw = lost = None
    for outcome in outcomes:
        name = outcome.name.lower()
        probability = _outcome_probability(outcome)
        if "draw" in name:
            draw = probability
        elif any(word in name for word in ("lost", "lose", "loss")):
            lost = probability
        elif "win" in name:
            win = probability
    if win is None or draw is None or lost is None:
        raise ValueError("42 direct market must contain Team Win, Draw, and Team Lost outcomes")
    return win, draw, lost


def _normalize_exact_score(
    outcomes: list[Outcome],
    target_side: str = "home",
) -> tuple[float, float, float, dict[str, list[str]]]:
    totals = {"win": 0.0, "draw": 0.0, "lost": 0.0}
    groups: dict[str, list[str]] = {"win": [], "draw": [], "lost": []}
    for outcome in outcomes:
        if _is_ambiguous_4_4(outcome.name):
            continue
        score = parse_score(outcome.name)
        if score is None:
            continue
        home, away = score
        probability = _outcome_probability(outcome)
        target, opponent = (away, home) if target_side == "away" else (home, away)
        if target > opponent:
            key = "win"
        elif target == opponent:
            key = "draw"
        else:
            key = "lost"
        totals[key] += probability
        groups[key].append(outcome.name)
    if not groups["win"] or not groups["draw"] or not groups["lost"]:
        raise ValueError("42 exact score market must include parseable win, draw, and lost outcomes")
    return totals["win"], totals["draw"], totals["lost"], groups


def parse_score(value: str) -> tuple[int, int] | None:
    text = value.strip().replace("≥", ">=").replace("–", "-").replace("—", "-")
    match = re.search(r"(?:>=)?(\d+)\s*-\s*(?:>=)?(\d+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _outcome_probability(outcome: Outcome) -> float:
    if outcome.decimal_odds is not None:
        return decimal_odds_to_implied_probability(outcome.decimal_odds)
    if outcome.price is not None:
        return polymarket_price_to_cost(outcome.price)
    raise ValueError(f"Outcome {outcome.name} has neither decimal odds nor price")


def _is_ambiguous_4_4(value: str) -> bool:
    normalized = value.replace(" ", "").replace("–", "-").replace("—", "-").replace(">=", "≥")
    return bool(re.search(r"≥4-≥4", normalized))


def _detect_42_rule_risk(
    rule_text: str,
    outcomes: list[Outcome],
    flag_excludes_4_4: bool,
) -> tuple[bool, str]:
    if not flag_excludes_4_4:
        return False, ""
    normalized = (rule_text or "").lower().replace(" ", "").replace("≥", ">=")
    has_ambiguous_bucket = any(_is_ambiguous_4_4(outcome.name) for outcome in outcomes)
    if ("excludes" in normalized and ">=4->=4" in normalized) or has_ambiguous_bucket:
        return True, "42 Team Win excludes ≥4-≥4, not fully equivalent to Polymarket Team Win"
    return False, ""
