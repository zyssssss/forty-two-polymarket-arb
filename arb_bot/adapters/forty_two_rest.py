"""
42.space REST API adapter using the official API at rest.ft.42.space.
Replaces the placeholder HttpFortyTwoAdapter with a working implementation.
"""
from __future__ import annotations

from typing import Any

import requests

import re

from arb_bot.adapters.base import FortyTwoAdapter
from arb_bot.config import FortyTwoConfig
from arb_bot.models import FortyTwoSnapshot, OutcomeQuote


def normalize_score_name(raw_name: str) -> str:
    """Convert 42 API outcome names like 'POR 2–0 COD' to simplified '2-0' format.
    
    42 API uses U+2013 (EN DASH) for score separator and U+2265 (>=) for 4+ goals.
    
    Examples:
      - 'POR 2–0 COD' -> '2-0'
      - 'POR ≥4–0 COD' -> '>=4-0'
      - 'POR 0–≥4 COD' -> '0->=4'
      - 'POR 0–0 COD' -> '0-0'
    """
    result = raw_name
    # Remove team prefixes/suffixes: "POR " prefix and " COD" suffix
    for prefix in ["POR ", "COD "]:
        if result.startswith(prefix):
            result = result[len(prefix):]
    for suffix in [" COD", " POR"]:
        if result.endswith(suffix):
            result = result[: -len(suffix)]
    
    # Replace the en-dash (U+2013) with a regular hyphen
    result = result.replace("\u2013", "-")
    # Replace ≥ (U+2265) with >=
    result = result.replace("\u2265", ">=")
    
    return result.strip()


class FortyTwoRestAdapter(FortyTwoAdapter):
    """Adapter for the 42.space REST API (rest.ft.42.space).

    Endpoints:
      GET /api/v1/markets/{address}          -> full market data + outcomes
      GET /api/v1/market-data/prices?outcome_index=N&market={address} -> current price
      GET /api/v1/market-data/stats?market={address} -> per-outcome stats

    No authentication required for reading market data.
    """

    BASE_URL = "https://rest.ft.42.space"

    def __init__(self, config: FortyTwoConfig | None = None, timeout: float = 10.0) -> None:
        self.config = config or FortyTwoConfig()
        self.timeout = timeout
        self.session = requests.Session()

    def get_snapshot(self, market_id: str, market_type: str) -> FortyTwoSnapshot:
        """Fetch market data from the 42 REST API.

        Args:
            market_id: The contract address (0x...) of the market.
            market_type: One of 'exact_score', 'yes_no', or 'other'.
        """
        url = f"{self.BASE_URL}/api/v1/markets/{market_id}"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        outcomes = []
        for item in data.get("outcomes", []):
            raw_price = float(item.get("price", 0))
            decimal_odds = (1.0 / raw_price) if raw_price > 0 else None
            raw_name = str(item.get("name", ""))
            normalized_name = normalize_score_name(raw_name)

            outcomes.append(
                OutcomeQuote(
                    outcome_id=str(item.get("index", item.get("tokenId", ""))),
                    name=normalized_name,
                    decimal_odds=decimal_odds,
                    buy_depth=float(item.get("marketCap", 0)),
                    sell_depth=float(item.get("volume", 0)),
                    buy_quote=raw_price,
                    sell_quote=None,
                    metadata={
                        "token_id": item.get("tokenId"),
                        "raw_name": raw_name,
                        "market_cap": item.get("marketCap"),
                        "minted_quantity": item.get("mintedQuantity"),
                        "payout": item.get("payout"),
                        "symbol": item.get("symbol"),
                    },
                )
            )

        # 42 doesn't have explicit redeem tax; use 0 as default (bonding curve pricing is in the spread)
        redeem_tax = 0.0

        return FortyTwoSnapshot(
            market_id=market_id,
            market_type=market_type,
            outcomes=outcomes,
            redeem_tax=redeem_tax,
            quick_select_text=data.get("question"),
            metadata={
                "title": data.get("title"),
                "status": data.get("status"),
                "volume": data.get("volume"),
                "total_market_cap": data.get("totalMarketCap"),
                "collateral_symbol": data.get("collateralSymbol"),
                "end_date": data.get("endDate"),
                "categories": data.get("categories"),
                "tags": data.get("tags"),
            },
        )

    def get_buy_quote(self, market_id: str, outcome_id: str, stake: float) -> dict[str, Any]:
        """Estimate buy quote based on current price and outcome market cap.

        Note: 42 uses bonding curve pricing, so the actual buy price depends on
        the size of the purchase relative to the pool. This is an approximation.
        """
        url = f"{self.BASE_URL}/api/v1/markets/{market_id}"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Find the specified outcome
        target_outcome = None
        for item in data.get("outcomes", []):
            if str(item.get("index")) == outcome_id or str(item.get("tokenId")) == outcome_id:
                target_outcome = item
                break

        if target_outcome is None:
            raise ValueError(f"Outcome {outcome_id} not found in market {market_id}")

        price = float(target_outcome.get("price", 0))
        estimated_return = stake / price if price > 0 else 0

        return {
            "outcome_id": outcome_id,
            "stake": stake,
            "estimated_price": price,
            "estimated_return": estimated_return,
            "estimated_fee": 0.0,
            "raw": target_outcome,
        }

    def get_sell_or_redeem_quote(self, market_id: str, outcome_id: str, size: float) -> dict[str, Any]:
        """Estimate sell/redeem quote.

        Note: 42's bonding curve means selling tokens returns the current pool share.
        This is an approximation based on current price.
        """
        url = f"{self.BASE_URL}/api/v1/markets/{market_id}"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        target_outcome = None
        for item in data.get("outcomes", []):
            if str(item.get("index")) == outcome_id or str(item.get("tokenId")) == outcome_id:
                target_outcome = item
                break

        if target_outcome is None:
            raise ValueError(f"Outcome {outcome_id} not found in market {market_id}")

        price = float(target_outcome.get("price", 0))
        estimated_value = size * price

        return {
            "outcome_id": outcome_id,
            "size": size,
            "estimated_price": price,
            "estimated_value": estimated_value,
            "estimated_fee": 0.0,
            "raw": target_outcome,
        }

    def place_limit_order(self, market_id: str, outcome_id: str, stake: float, limit_odds: float) -> str:
        raise NotImplementedError(
            "Live 42 order placement requires wallet connection and blockchain transaction. "
            "Use the 42.space web interface for trading."
        )

    def emergency_unwind(self, market_id: str, order_ids: list[str]) -> None:
        raise NotImplementedError(
            "Emergency unwind must be implemented for the selected 42 execution venue. "
            "Use the 42.space web interface to sell positions."
        )
