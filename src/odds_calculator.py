from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreOutcome:
    name: str
    decimal_odds: float | None = None
    cost: float | None = None
    raw: dict | None = None


def decimal_odds_to_implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1:
        raise ValueError("decimal_odds must be > 1")
    return 1.0 / decimal_odds


def polymarket_yes_no_cost(yes_price: float, no_price: float | None = None) -> tuple[float, float, bool]:
    yes_cost = _normalize_price(yes_price)
    if no_price is None:
        return yes_cost, 1.0 - yes_cost, True
    return yes_cost, _normalize_price(no_price), False


def _normalize_price(value: float) -> float:
    price = value / 100.0 if value > 1 else value
    if not 0 <= price <= 1:
        raise ValueError("price must be in [0, 1] or cents [0, 100]")
    return price


def normalize_score_name(raw_name: str) -> str:
    value = raw_name.replace("\u2013", "-").replace("\u2014", "-").replace("–", "-").replace("≥", ">=")
    parts = value.split()
    if len(parts) >= 3 and "-" in parts[1]:
        return parts[1]
    match = re.search(r"(>=?\d+|\d+)\s*-\s*(>=?\d+|\d+)", value)
    return f"{match.group(1)}-{match.group(2)}" if match else value.strip()


def classify_score(score: str) -> str:
    home, away = score.split("-", 1)
    if home == ">=4" and away == ">=4":
        return "ambiguous"
    home_min = 4 if home == ">=4" else int(home)
    away_min = 4 if away == ">=4" else int(away)
    if home_min > away_min:
        return "home_win"
    if home_min < away_min:
        return "away_win"
    return "draw"


def outcome_cost(outcome: ScoreOutcome) -> float:
    if outcome.decimal_odds is not None:
        return decimal_odds_to_implied_probability(outcome.decimal_odds)
    if outcome.cost is not None:
        return outcome.cost
    raise ValueError(f"outcome {outcome.name} has neither decimal_odds nor cost")


def exact_score_costs(outcomes: list[ScoreOutcome], target_side: str) -> tuple[float, float, float, bool, str, dict]:
    groups: dict[str, list[str]] = {"win": [], "draw": [], "lost": [], "ambiguous": []}
    costs = {"win": 0.0, "draw": 0.0, "lost": 0.0}
    for outcome in outcomes:
        score = normalize_score_name(outcome.name)
        relation = classify_score(score)
        if relation == "ambiguous":
            groups["ambiguous"].append(score)
            continue
        if relation == "draw":
            bucket = "draw"
        elif (target_side == "home" and relation == "home_win") or (target_side == "away" and relation == "away_win"):
            bucket = "win"
        else:
            bucket = "lost"
        costs[bucket] += outcome_cost(outcome)
        groups[bucket].append(score)

    rule_risk = bool(groups["ambiguous"])
    reason = "42 exact score includes ambiguous >=4->=4 bucket" if rule_risk else ""
    return costs["win"], costs["draw"], costs["lost"], rule_risk, reason, groups
