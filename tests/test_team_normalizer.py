from __future__ import annotations

from src.config import DEFAULT_ALIASES
from src.market_matcher import MarketMatcher
from src.models import FortyTwoMarket, PolymarketMarket
from src.team_normalizer import TeamNormalizer


def test_france_and_fra_match() -> None:
    normalizer = TeamNormalizer(DEFAULT_ALIASES)
    assert normalizer.normalize_team("France") == "FRA"
    assert normalizer.normalize_team("FRA") == "FRA"
    assert normalizer.canonical_event_name("France vs Senegal") == "FRA vs SEN"
    assert normalizer.canonical_event_name("FRA vs SEN") == "FRA vs SEN"


def test_market_matcher_matches_aliases() -> None:
    normalizer = TeamNormalizer(DEFAULT_ALIASES)
    matcher = MarketMatcher(normalizer)
    matches, unmatched = matcher.match(
        [FortyTwoMarket("FRA vs SEN", "FRA", "exact_score", [])],
        [PolymarketMarket("France vs Senegal", "France", yes_price=0.67, no_price=0.33)],
    )
    assert len(matches) == 1
    assert unmatched == []
