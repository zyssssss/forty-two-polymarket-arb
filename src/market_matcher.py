from __future__ import annotations

from src.models import FortyTwoMarket, MatchedMarket, PolymarketMarket
from src.team_normalizer import TeamNormalizer


class MarketMatcher:
    def __init__(self, normalizer: TeamNormalizer) -> None:
        self.normalizer = normalizer

    def match(
        self,
        forty_two_markets: list[FortyTwoMarket],
        polymarket_markets: list[PolymarketMarket],
    ) -> tuple[list[MatchedMarket], list[dict[str, str]]]:
        poly_index: dict[tuple[str, str], PolymarketMarket] = {}
        unmatched: list[dict[str, str]] = []
        for market in polymarket_markets:
            event = self.normalizer.canonical_event_name(market.event_name)
            team = self.normalizer.normalize_team(market.team_name)
            if event:
                poly_index[(event, team)] = market

        matches: list[MatchedMarket] = []
        for market in forty_two_markets:
            event = self.normalizer.canonical_event_name(market.event_name)
            team = self.normalizer.normalize_team(market.team_name)
            if not event:
                unmatched.append({"platform": "42", "event_name": market.event_name, "reason": "could not parse event name"})
                continue
            polymarket = poly_index.get((event, team))
            if polymarket is None:
                unmatched.append({"platform": "42", "event_name": market.event_name, "team_name": market.team_name, "reason": "no matching Polymarket market"})
                continue
            matches.append(MatchedMarket(market, polymarket, event, team))
        return matches, unmatched
