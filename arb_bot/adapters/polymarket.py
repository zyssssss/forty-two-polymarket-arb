from __future__ import annotations

import requests

from arb_bot.adapters.base import PolymarketAdapter
from arb_bot.config import PolymarketConfig
from arb_bot.models import OrderBook, OrderBookLevel, PolymarketSnapshot


class HttpPolymarketAdapter(PolymarketAdapter):
    """Minimal CLOB HTTP adapter.

    Authenticated order placement is intentionally left behind a clear boundary
    because Polymarket signing setup varies by wallet/funder mode.
    """

    def __init__(self, config: PolymarketConfig, timeout: float = 10.0) -> None:
        self.config = config
        self.timeout = timeout

    def get_snapshot(self, market_id: str) -> PolymarketSnapshot:
        yes_price = self._get_price(market_id, "YES")
        no_price = self._get_price(market_id, "NO")
        yes_book = self._get_book(market_id, "YES")
        no_book = self._get_book(market_id, "NO")
        return PolymarketSnapshot(market_id=market_id, yes_price=yes_price, no_price=no_price, yes_book=yes_book, no_book=no_book)

    def average_fill_price(self, market_id: str, outcome: str, size: float) -> float:
        book = self._get_book(market_id, outcome)
        remaining = size
        notional = 0.0
        for level in book.asks:
            fill = min(remaining, level.size)
            notional += fill * level.price
            remaining -= fill
            if remaining <= 0:
                break
        if remaining > 0:
            raise ValueError("Insufficient Polymarket depth for requested size")
        return notional / size

    def place_limit_order(self, market_id: str, outcome: str, price: float, size: float) -> str:
        raise NotImplementedError("Live Polymarket order placement requires a signed CLOB client implementation")

    def _get_price(self, market_id: str, outcome: str) -> float:
        response = requests.get(
            f"{self.config.api_base}/price",
            params={"token_id": market_id, "side": "BUY"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        price = float(data.get("price", data.get(outcome.lower(), 0.0)))
        return price

    def _get_book(self, market_id: str, outcome: str) -> OrderBook:
        response = requests.get(f"{self.config.api_base}/book", params={"token_id": market_id}, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        asks = [OrderBookLevel(price=float(level["price"]), size=float(level["size"])) for level in data.get("asks", [])]
        bids = [OrderBookLevel(price=float(level["price"]), size=float(level["size"])) for level in data.get("bids", [])]
        return OrderBook(bids=bids, asks=asks)
