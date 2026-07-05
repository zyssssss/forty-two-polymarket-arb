from __future__ import annotations

from src.models import FortyTwoTeamCosts, PolymarketTeamMarket
from src.team_normalizer import TeamNormalizer


class MarketMatcher:
    def __init__(self, normalizer: TeamNormalizer) -> None:
        self.normalizer = normalizer

    def match(
        self, forty_two: list[FortyTwoTeamCosts], polymarket: list[PolymarketTeamMarket]
    ) -> tuple[list[tuple[FortyTwoTeamCosts, PolymarketTeamMarket]], list[dict]]:
        matched: list[tuple[FortyTwoTeamCosts, PolymarketTeamMarket]] = []
        unmatched: list[dict] = []
        used_poly: set[int] = set()
        for ft in forty_two:
            found_index = None
            for index, poly in enumerate(polymarket):
                if index in used_poly:
                    continue
                if self._same_team_market(ft, poly):
                    found_index = index
                    break
            if found_index is None:
                unmatched.append({"source": "42", "event_name": ft.event_name, "team_name": ft.team_name})
            else:
                used_poly.add(found_index)
                matched.append((ft, polymarket[found_index]))
        for index, poly in enumerate(polymarket):
            if index not in used_poly:
                unmatched.append({"source": "polymarket", "event_name": poly.event_name, "team_name": poly.team_name})
        return matched, unmatched

    def _same_team_market(self, ft: FortyTwoTeamCosts, poly: PolymarketTeamMarket) -> bool:
        return (
            self.normalizer.equivalent(ft.team_name, poly.team_name)
            and self.normalizer.equivalent(ft.opponent_name, poly.opponent_name)
        ) or (
            self.normalizer.equivalent(ft.team_name, poly.team_name)
            and self.normalizer.equivalent(ft.event_name, poly.event_name)
        )
