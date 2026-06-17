from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from enum import Enum
from typing import Any

from arb_bot.config import NotificationsConfig
from arb_bot.models import ArbitrageSignal


def format_signal(signal: ArbitrageSignal, auto_trade_allowed: bool) -> str:
    return (
        "【套利信号】\n"
        f"事件：{signal.event_name}\n"
        f"42 买入对象：{signal.target_outcome}\n"
        f"Polymarket 对冲对象：{signal.suggested_polymarket_order.get('outcome')}\n"
        f"42 等效成本：{signal.forty_two_equivalent_probability:.4f}\n"
        f"Polymarket 反向成本：{signal.polymarket_opposite_price:.4f}\n"
        f"总成本：{signal.total_cost:.4f}\n"
        f"理论利润：{signal.locked_profit_estimate:.4f}\n"
        f"是否规则一致：{signal.status.value}\n"
        f"是否允许自动交易：{auto_trade_allowed}\n"
        f"风险提示：{'; '.join(signal.risk_flags or ['无'])}"
    )


class Notifier:
    def __init__(self, config: NotificationsConfig) -> None:
        self.config = config

    def send_signal(self, signal: ArbitrageSignal, auto_trade_allowed: bool) -> None:
        message = format_signal(signal, auto_trade_allowed)
        if self.config.console:
            print(message)
        if self.config.webhook_url:
            import requests

            requests.post(self.config.webhook_url, json={"text": message, "signal": _jsonable(asdict(signal))}, timeout=10).raise_for_status()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value
