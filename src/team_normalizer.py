from __future__ import annotations

import re
import unicodedata


class TeamNormalizer:
    def __init__(self, aliases: dict[str, str]) -> None:
        self.aliases = aliases
        self.lookup: dict[str, str] = {}
        for name, code in aliases.items():
            canonical = _clean(name)
            normalized_code = _clean(code)
            self.lookup[canonical] = code.upper()
            self.lookup[normalized_code] = code.upper()
        for code in aliases.values():
            self.lookup[_clean(code)] = code.upper()

    def normalize_team(self, value: str) -> str:
        cleaned = _clean(value)
        return self.lookup.get(cleaned, cleaned.upper())

    def normalize_event(self, event_name: str) -> tuple[str, str] | None:
        parts = re.split(r"\s+(?:vs|v|versus)\s+|\s*-\s*", event_name, flags=re.IGNORECASE)
        parts = [part.strip() for part in parts if part.strip()]
        if len(parts) != 2:
            return None
        return self.normalize_team(parts[0]), self.normalize_team(parts[1])

    def canonical_event_name(self, event_name: str) -> str | None:
        teams = self.normalize_event(event_name)
        if not teams:
            return None
        return f"{teams[0]} vs {teams[1]}"


def _clean(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).strip().lower()
    return re.sub(r"\s+", " ", normalized)
