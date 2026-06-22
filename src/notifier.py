from __future__ import annotations

from src.logger import _jsonable
from src.models import ArbitrageSignal


def format_signal(signal: ArbitrageSignal) -> str:
    return (
        "【世界杯套利机会】\n\n"
        f"比赛：{signal.event_name}\n"
        f"队伍：{signal.team_name}\n"
        f"42 Win 成本：{signal.forty_two_team_win_cost:.4f}\n"
        f"42 Draw 成本：{signal.forty_two_team_draw_cost:.4f}\n"
        f"42 Lost 成本：{signal.forty_two_team_lost_cost:.4f}\n"
        f"42 Draw + Lost 成本：{signal.forty_two_draw_plus_lost_cost:.4f}\n"
        f"Polymarket Yes 成本：{signal.polymarket_team_yes_cost:.4f}\n"
        f"Polymarket No 成本：{signal.polymarket_team_no_cost:.4f}\n"
        f"No 是否估算：{'是' if signal.no_cost_is_estimated else '否'}\n"
        f"总成本 42 Win + Polymarket No：{signal.total_cost:.4f}\n"
        f"理论空间：{signal.theoretical_margin:.2%}\n"
        f"Polymarket No 相对 42 Draw+Lost 折价：{signal.polymarket_no_discount_vs_42:.2%}\n"
        f"Condition A 是否成立：{'是' if signal.condition_a_passed else '否'}\n"
        f"Condition B 是否成立：{'是' if signal.condition_b_passed else '否'}\n"
        f"是否存在规则风险：{'是' if signal.rule_risk else '否'}\n"
        f"规则风险原因：{signal.rule_risk_reason or '无'}\n"
        f"时间：{signal.timestamp}\n"
        f"建议动作：{signal.suggested_action.value}"
    )


class Notifier:
    def __init__(self, console: bool = True, webhook_url: str = "") -> None:
        self.console = console
        self.webhook_url = webhook_url

    def send(self, signal: ArbitrageSignal) -> None:
        message = format_signal(signal)
        if self.console:
            print(message)
        if self.webhook_url:
            import requests

            requests.post(self.webhook_url, json={"text": message, "signal": _jsonable(signal)}, timeout=10).raise_for_status()
