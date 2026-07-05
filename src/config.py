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


@dataclass(frozen=True)
class NotificationsConfig:
    console: bool = True
    webhook_url: str = ""


@dataclass(frozen=True)
class RiskFlagsConfig:
    allow_partial_coverage_alert: bool = True
    flag_42_excludes_4_4: bool = True


@dataclass(frozen=True)
class AppConfig:
    scan_interval_seconds: int = 60
    target_total_cost_threshold: float = 0.9
    polymarket_api_base_url: str = "https://gamma-api.polymarket.com"
    forty_two_api_base_url: str = "https://rest.ft.42.space"
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    risk_flags: RiskFlagsConfig = field(default_factory=RiskFlagsConfig)
    team_aliases: dict[str, list[str]] = field(default_factory=dict)
    forty_two_market_addresses: list[str] = field(default_factory=list)
    polymarket_event_slugs: list[str] = field(default_factory=list)
    data_dir: str = "data"


def load_config(config_path: str | Path = "config.example.json", env_path: str | Path = ".env") -> AppConfig:
    load_dotenv(env_path)
    path = Path(config_path)
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    notifications_raw = raw.get("notifications", {})
    risk_raw = raw.get("risk_flags", {})

    return AppConfig(
        scan_interval_seconds=int(raw.get("scan_interval_seconds", 60)),
        target_total_cost_threshold=float(raw.get("target_total_cost_threshold", 0.9)),
        polymarket_api_base_url=os.getenv(
            "POLYMARKET_API_BASE_URL", raw.get("polymarket_api_base_url", "https://gamma-api.polymarket.com")
        ).rstrip("/"),
        forty_two_api_base_url=os.getenv(
            "FORTY_TWO_API_BASE_URL", raw.get("forty_two_api_base_url", "https://rest.ft.42.space")
        ).rstrip("/"),
        notifications=NotificationsConfig(
            console=bool(notifications_raw.get("console", True)),
            webhook_url=os.getenv("WEBHOOK_URL", notifications_raw.get("webhook_url", "")),
        ),
        risk_flags=RiskFlagsConfig(
            allow_partial_coverage_alert=bool(risk_raw.get("allow_partial_coverage_alert", True)),
            flag_42_excludes_4_4=bool(risk_raw.get("flag_42_excludes_4_4", True)),
        ),
        team_aliases=dict(raw.get("team_aliases", {})),
        forty_two_market_addresses=list(raw.get("forty_two_market_addresses", [])),
        polymarket_event_slugs=list(raw.get("polymarket_event_slugs", [])),
        data_dir=str(raw.get("data_dir", "data")),
    )
