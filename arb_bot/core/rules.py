from __future__ import annotations

from typing import Any

from arb_bot.models import Action, HedgeStatus, RuleCheckResult


def check_rule_consistency(mapping: dict[str, Any]) -> RuleCheckResult:
    reasons: list[str] = []
    event_name = mapping.get("event_name")
    if not event_name:
        reasons.append("missing event_name; cannot confirm both markets reference the same event")

    poly_time = mapping.get("polymarket_settlement_time") or mapping.get("settlement_time")
    forty_two_time = mapping.get("forty_two_settlement_time") or mapping.get("settlement_time")
    if not poly_time or not forty_two_time or poly_time != forty_two_time:
        reasons.append("settlement time differs or is missing")

    poly_def = _normalize_rule(mapping.get("polymarket_settlement_definition") or mapping.get("settlement_definition"))
    forty_two_def = _normalize_rule(mapping.get("forty_two_settlement_definition") or mapping.get("settlement_definition"))
    if not poly_def or not forty_two_def or poly_def != forty_two_def:
        reasons.append("settlement definition differs or is missing, including 90 minutes / extra time / penalties")

    market_type = mapping.get("forty_two_market_type")
    if market_type == "exact_score":
        exact = mapping.get("exact_score_mapping", {})
        quick_select = str(exact.get("quick_select_text", ""))
        excluded_buckets = [str(bucket) for bucket in exact.get("excluded_buckets", [])]
        complete = bool(exact.get("is_complete_target_coverage", False))
        if not complete:
            reasons.append("42 exact score target scores do not fully cover target result")
        if "excludes" in quick_select.lower() and "≥4" in quick_select:
            reasons.append("42 Quick Select excludes ≥4-≥4; high-score target wins are not covered")
        if any("≥4" in bucket for bucket in excluded_buckets):
            reasons.append("42 exact score mapping excludes ≥4 bucket; target result is not fully hedgeable")
        if not exact.get("target_scores"):
            reasons.append("missing exact_score_mapping.target_scores")

    if reasons:
        status = HedgeStatus.NOT_FULLY_HEDGEABLE if any("≥4" in reason or "fully cover" in reason for reason in reasons) else HedgeStatus.NOT_HEDGEABLE
        return RuleCheckResult(status=status, action=Action.ALERT_ONLY, reasons=reasons)
    return RuleCheckResult(status=HedgeStatus.HEDGEABLE, action=Action.NO_ACTION, reasons=[])


def _normalize_rule(value: Any) -> str:
    return " ".join(str(value or "").lower().strip().split())
