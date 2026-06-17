from __future__ import annotations

from typing import Any

import requests

from arb_bot.adapters.base import FortyTwoAdapter
from arb_bot.config import FortyTwoConfig
from arb_bot.models import FortyTwoSnapshot, OutcomeQuote


class HttpFortyTwoAdapter(FortyTwoAdapter):
    def __init__(self, config: FortyTwoConfig, timeout: float = 10.0) -> None:
        self.config = config
        self.timeout = timeout
        self.session = requests.Session()
        if config.cookie:
            self.session.headers.update({"Cookie": config.cookie})

    def get_snapshot(self, market_id: str, market_type: str) -> FortyTwoSnapshot:
        if not self.config.api_base:
            raise NotImplementedError("42 API base is not configured; use PlaywrightFortyTwoAdapter or MockFortyTwoAdapter")
        response = self.session.get(f"{self.config.api_base}/markets/{market_id}", timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        outcomes = [
            OutcomeQuote(
                outcome_id=str(item["id"]),
                name=str(item["name"]),
                decimal_odds=float(item["decimal_odds"]),
                buy_depth=float(item.get("buy_depth", 0.0)),
                sell_depth=float(item.get("sell_depth", 0.0)),
                buy_quote=item.get("buy_quote"),
                sell_quote=item.get("sell_quote"),
                metadata=item,
            )
            for item in data.get("outcomes", [])
        ]
        redeem_tax = data.get("redeem_tax")
        return FortyTwoSnapshot(
            market_id=market_id,
            market_type=market_type,
            outcomes=outcomes,
            redeem_tax=None if redeem_tax is None else float(redeem_tax),
            quick_select_text=data.get("quick_select_text"),
        )

    def get_buy_quote(self, market_id: str, outcome_id: str, stake: float) -> dict[str, Any]:
        response = self.session.post(
            f"{self.config.api_base}/markets/{market_id}/quote/buy",
            json={"outcome_id": outcome_id, "stake": stake},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_sell_or_redeem_quote(self, market_id: str, outcome_id: str, size: float) -> dict[str, Any]:
        response = self.session.post(
            f"{self.config.api_base}/markets/{market_id}/quote/sell",
            json={"outcome_id": outcome_id, "size": size},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def place_limit_order(self, market_id: str, outcome_id: str, stake: float, limit_odds: float) -> str:
        raise NotImplementedError("Live 42 order placement must be wired to the official API or audited browser flow")

    def emergency_unwind(self, market_id: str, order_ids: list[str]) -> None:
        raise NotImplementedError("Emergency unwind must be implemented for the selected 42 execution venue")


class PlaywrightFortyTwoAdapter(HttpFortyTwoAdapter):
    """Placeholder adapter for sites without stable APIs.

    Keep browser automation behind this adapter so the execution layer does not
    depend on DOM selectors. Add audited selectors here once 42 market pages are
    available.
    """

    def get_snapshot(self, market_id: str, market_type: str) -> FortyTwoSnapshot:
        raise NotImplementedError("Playwright scraping selectors must be configured for the specific 42 market UI")
