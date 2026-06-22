from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


DEFAULT_ALIASES = {
    "France": "FRA",
    "Senegal": "SEN",
    "Brazil": "BRA",
    "Germany": "GER",
    "England": "ENG",
    "Argentina": "ARG",
    "Spain": "ESP",
    "Portugal": "POR",
    "United States": "USA",
    "Netherlands": "NED",
    "Japan": "JPN",
    "Sweden": "SWE",
    "Tunisia": "TUN",
    "Norway": "NOR",
    "Iraq": "IRQ",
    "Scotland": "SCO",
    "Morocco": "MAR",
    "Haiti": "HTI",
    "Australia": "AUS",
    "Turkey": "TUR",
    "Paraguay": "PAR",
    "Canada": "CAN",
    "Switzerland": "SUI",
    "Qatar": "QAT",
    "Bosnia and Herzegovina": "BIH",
}


@dataclass(frozen=True)
class NotificationConfig:
    console: bool = True
    webhook_url: str = ""


@dataclass(frozen=True)
class MarketsConfig:
    sport: str = "soccer"
    competition: str = "World Cup"


@dataclass(frozen=True)
class RiskFlagConfig:
    allow_partial_coverage_alert: bool = True
    flag_42_excludes_4_4: bool = True


@dataclass(frozen=True)
class ApiConfig:
    api_base_url: str = ""
    clob_base_url: str = ""


@dataclass(frozen=True)
class AppConfig:
    scan_interval_seconds: int = 60
    target_total_cost_threshold: float = 0.9
    markets: MarketsConfig = field(default_factory=MarketsConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    risk_flags: RiskFlagConfig = field(default_factory=RiskFlagConfig)
    data_dir: str = "data"
    use_mock_data: bool = False
    polymarket: ApiConfig = field(default_factory=ApiConfig)
    forty_two: ApiConfig = field(default_factory=ApiConfig)
    team_aliases: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ALIASES))


def load_config(config_path: str = "config.example.json", env_path: str = ".env") -> AppConfig:
    load_dotenv(env_path)
    raw: dict[str, Any] = {}
    path = Path(config_path)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))

    notifications = raw.get("notifications", {})
    markets = raw.get("markets", {})
    risk_flags = raw.get("risk_flags", {})
    aliases = dict(DEFAULT_ALIASES)
    aliases.update(raw.get("team_aliases", {}))

    return AppConfig(
        scan_interval_seconds=int(raw.get("scan_interval_seconds", 60)),
        target_total_cost_threshold=float(raw.get("target_total_cost_threshold", 0.9)),
        markets=MarketsConfig(
            sport=str(markets.get("sport", "soccer")),
            competition=str(markets.get("competition", "World Cup")),
        ),
        notifications=NotificationConfig(
            console=bool(notifications.get("console", True)),
            webhook_url=os.getenv("WEBHOOK_URL", notifications.get("webhook_url", "")),
        ),
        risk_flags=RiskFlagConfig(
            allow_partial_coverage_alert=bool(risk_flags.get("allow_partial_coverage_alert", True)),
            flag_42_excludes_4_4=bool(risk_flags.get("flag_42_excludes_4_4", True)),
        ),
        data_dir=str(raw.get("data_dir", "data")),
        use_mock_data=bool(raw.get("use_mock_data", False)),
        polymarket=ApiConfig(
            api_base_url=os.getenv(
                "POLYMARKET_API_BASE_URL",
                raw.get("polymarket", {}).get("api_base_url", "https://gamma-api.polymarket.com"),
            ),
            clob_base_url=os.getenv(
                "POLYMARKET_CLOB_BASE_URL",
                raw.get("polymarket", {}).get("clob_base_url", "https://clob.polymarket.com"),
            ),
        ),
        forty_two=ApiConfig(
            api_base_url=os.getenv(
                "FORTY_TWO_API_BASE_URL",
                raw.get("forty_two", {}).get("api_base_url", "https://rest.ft.42.space"),
            )
        ),
        team_aliases=aliases,
    )
