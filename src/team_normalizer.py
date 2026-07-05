from __future__ import annotations

import re


DEFAULT_ALIASES: dict[str, list[str]] = {
    "France": ["FRA"], "Senegal": ["SEN"], "Brazil": ["BRA"], "Germany": ["GER"],
    "England": ["ENG"], "Argentina": ["ARG"], "Spain": ["ESP"], "Portugal": ["POR"],
    "United States": ["USA", "US", "United States of America"], "Netherlands": ["NED", "Holland"],
    "Japan": ["JPN"], "Sweden": ["SWE"], "Tunisia": ["TUN"], "Norway": ["NOR"],
    "Iraq": ["IRQ"], "Scotland": ["SCO"], "Morocco": ["MAR"], "Haiti": ["HTI"],
    "Australia": ["AUS"], "Turkey": ["TUR", "Turkiye"], "Paraguay": ["PAR"],
    "Canada": ["CAN"], "Switzerland": ["SUI"], "Qatar": ["QAT"],
    "Bosnia and Herzegovina": ["BIH"], "DR Congo": ["CDR", "COD", "Congo DR", "Congo Democratic Republic", "Democratic Republic of Congo"],
}


def canonical_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


class TeamNormalizer:
    def __init__(self, aliases: dict[str, list[str]] | None = None) -> None:
        merged = dict(DEFAULT_ALIASES)
        for name, values in (aliases or {}).items():
            merged.setdefault(name, [])
            merged[name].extend(values)
        self.lookup: dict[str, str] = {}
        for canonical, values in merged.items():
            self.lookup[canonical_key(canonical)] = canonical
            for value in values:
                self.lookup[canonical_key(value)] = canonical

    def normalize(self, value: str) -> str:
        stripped = " ".join(value.strip().split())
        return self.lookup.get(canonical_key(stripped), stripped)

    def equivalent(self, left: str, right: str) -> bool:
        return self.normalize(left) == self.normalize(right)
