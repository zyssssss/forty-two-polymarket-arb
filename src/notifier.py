from __future__ import annotations

import requests

from src.models import ArbitrageSignal


class Notifier:
    def __init__(self, console: bool = True, webhook_url: str = "", timeout: float = 10.0) -> None:
        self.console = console
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, signal: ArbitrageSignal) -> None:
        if signal.suggested_action != "ALERT_ARBITRAGE_OPPORTUNITY":
            return
        message = format_signal(signal)
        if self.console:
            print(message)
        if self.webhook_url:
            requests.post(self.webhook_url, json={"text": message, "signal": signal.__dict__}, timeout=self.timeout)


def yes_no(value: bool) -> str:
    return "是" if value else "否"


def format_signal(signal: ArbitrageSignal) -> str:
    return f"""【世界杯套利机会】

比赛：{signal.event_name}
队伍：{signal.team_name}
42 Win 成本：{signal.forty_two_team_win_cost:.4f}
42 Draw 成本：{signal.forty_two_team_draw_cost:.4f}
42 Lost 成本：{signal.forty_two_team_lost_cost:.4f}
42 Draw + Lost 成本：{signal.forty_two_draw_plus_lost_cost:.4f}
Polymarket Yes 成本：{signal.polymarket_team_yes_cost:.4f}
Polymarket No 成本：{signal.polymarket_team_no_cost:.4f}
No 是否估算：{yes_no(signal.no_cost_is_estimated)}
总成本 42 Win + Polymarket No：{signal.total_cost:.4f}
理论空间：{signal.theoretical_margin:.2%}
Polymarket No 相对 42 Draw+Lost 折价：{signal.polymarket_no_discount_vs_42:.2%}
Condition A 是否成立：{yes_no(signal.condition_a_passed)}
Condition B 是否成立：{yes_no(signal.condition_b_passed)}
是否存在规则风险：{yes_no(signal.rule_risk)}
规则风险原因：{signal.rule_risk_reason}
时间：{signal.timestamp}
建议动作：{signal.suggested_action}
"""
