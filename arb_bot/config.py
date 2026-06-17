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
class PolymarketConfig:
    api_base: str = "https://clob.polymarket.com"
    chain_id: int = 137
    private_key: str = ""
    funder_address: str = ""
    signature_type: int = 0


@dataclass(frozen=True)
class FortyTwoConfig:
    api_base: str = ""
    username: str = ""
    password: str = ""
    cookie: str = ""
    headless: bool = True
    browser_profile: str = ""


@dataclass(frozen=True)
class NotificationsConfig:
    console: bool = True
    webhook_url: str = ""


@dataclass(frozen=True)
class BotConfig:
    paper_trading: bool = True
    auto_trade: bool = False
    min_profit_margin: float = 0.03
    safety_margin: float = 0.05
    max_position_per_market: float = 100.0
    max_total_exposure: float = 500.0
    max_slippage: float = 0.02
    min_liquidity: float = 10.0
    check_interval_seconds: int = 10
    database_path: str = "arb_bot.sqlite3"
    jsonl_dir: str = "logs"
    polymarket: PolymarketConfig = field(default_factory=PolymarketConfig)
    forty_two: FortyTwoConfig = field(default_factory=FortyTwoConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    event_mappings: list[dict[str, Any]] = field(default_factory=list)


def _bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config(config_path: str | Path = "config.json", env_path: str | Path = ".env") -> BotConfig:
    load_dotenv(env_path)
    raw: dict[str, Any] = {}
    path = Path(config_path)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))

    poly_raw = raw.get("polymarket", {})
    forty_two_raw = raw.get("forty_two", {})
    notifications_raw = raw.get("notifications", {})

    polymarket = PolymarketConfig(
        api_base=os.getenv("POLYMARKET_API_BASE", poly_raw.get("api_base", "https://clob.polymarket.com")),
        chain_id=int(os.getenv("POLYMARKET_CHAIN_ID", poly_raw.get("chain_id", 137))),
        private_key=os.getenv("POLYMARKET_PRIVATE_KEY", poly_raw.get("private_key", "")),
        funder_address=os.getenv("POLYMARKET_FUNDER_ADDRESS", poly_raw.get("funder_address", "")),
        signature_type=int(os.getenv("POLYMARKET_SIGNATURE_TYPE", poly_raw.get("signature_type", 0))),
    )
    forty_two = FortyTwoConfig(
        api_base=os.getenv("FORTY_TWO_API_BASE", forty_two_raw.get("api_base", "")),
        username=os.getenv("FORTY_TWO_USERNAME", forty_two_raw.get("username", "")),
        password=os.getenv("FORTY_TWO_PASSWORD", forty_two_raw.get("password", "")),
        cookie=os.getenv("FORTY_TWO_COOKIE", forty_two_raw.get("cookie", "")),
        headless=_bool(os.getenv("FORTY_TWO_HEADLESS", forty_two_raw.get("headless", True)), True),
        browser_profile=os.getenv("FORTY_TWO_BROWSER_PROFILE", forty_two_raw.get("browser_profile", "")),
    )
    notifications = NotificationsConfig(
        console=_bool(notifications_raw.get("console", True), True),
        webhook_url=os.getenv("WEBHOOK_URL", notifications_raw.get("webhook_url", "")),
    )
    return BotConfig(
        paper_trading=_bool(os.getenv("PAPER_TRADING", raw.get("paper_trading", True)), True),
        auto_trade=_bool(os.getenv("AUTO_TRADE", raw.get("auto_trade", False)), False),
        min_profit_margin=float(raw.get("min_profit_margin", 0.03)),
        safety_margin=float(raw.get("safety_margin", 0.05)),
        max_position_per_market=float(raw.get("max_position_per_market", 100.0)),
        max_total_exposure=float(raw.get("max_total_exposure", 500.0)),
        max_slippage=float(raw.get("max_slippage", 0.02)),
        min_liquidity=float(raw.get("min_liquidity", 10.0)),
        check_interval_seconds=int(raw.get("check_interval_seconds", 10)),
        database_path=str(raw.get("database_path", "arb_bot.sqlite3")),
        jsonl_dir=str(raw.get("jsonl_dir", "logs")),
        polymarket=polymarket,
        forty_two=forty_two,
        notifications=notifications,
        event_mappings=list(raw.get("event_mappings", [])),
    )
