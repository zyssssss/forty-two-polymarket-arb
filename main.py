from __future__ import annotations

import argparse
import time
import traceback
from dataclasses import asdict

from src.arbitrage_detector import detect_arbitrage
from src.config import load_config
from src.forty_two_adapter import FortyTwoAdapter
from src.logger import JsonlLogger
from src.market_matcher import MarketMatcher
from src.models import utc_now_iso
from src.notifier import Notifier
from src.polymarket_adapter import PolymarketAdapter
from src.team_normalizer import TeamNormalizer


def scan_once(config_path: str) -> dict:
    config = load_config(config_path)
    normalizer = TeamNormalizer(config.team_aliases)
    logger = JsonlLogger(config.data_dir)
    notifier = Notifier(config.notifications.console, config.notifications.webhook_url)

    polymarket = PolymarketAdapter(config.polymarket_api_base_url, normalizer)
    forty_two = FortyTwoAdapter(config.forty_two_api_base_url, normalizer)
    matcher = MarketMatcher(normalizer)

    poly_markets = []
    ft_costs = []

    try:
        poly_markets = polymarket.get_team_markets(config.polymarket_event_slugs)
    except Exception as exc:
        logger.error({
            "timestamp": utc_now_iso(),
            "source": "polymarket",
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        })

    try:
        ft_costs = forty_two.get_team_costs(config.forty_two_market_addresses)
    except Exception as exc:
        logger.error({
            "timestamp": utc_now_iso(),
            "source": "42",
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        })

    logger.market_snapshot(
        {
            "timestamp": utc_now_iso(),
            "polymarket_count": len(poly_markets),
            "forty_two_count": len(ft_costs),
            "polymarket": [asdict(x) for x in poly_markets],
            "forty_two": [asdict(x) for x in ft_costs],
        }
    )

    matches, unmatched = matcher.match(ft_costs, poly_markets)
    for item in unmatched:
        logger.unmatched({"timestamp": utc_now_iso(), **item})

    signals = []
    for ft, poly in matches:
        signal = detect_arbitrage(ft, poly, config.target_total_cost_threshold)
        signals.append(signal)
        if signal.suggested_action == "ALERT_ARBITRAGE_OPPORTUNITY":
            logger.signal(signal)
            notifier.send(signal)

    return {"matches": len(matches), "signals": len(signals), "alerts": sum(s.suggested_action == "ALERT_ARBITRAGE_OPPORTUNITY" for s in signals)}


def main() -> None:
    parser = argparse.ArgumentParser(description="World Cup 42.space + Polymarket arbitrage monitor")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.once:
        result = scan_once(args.config)
        print(f"scan_once result: {result}")
        return

    while True:
        try:
            result = scan_once(args.config)
            print(f"[{utc_now_iso()}] scan result: {result}")
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"[{utc_now_iso()}] scan error: {exc}")
        time.sleep(config.scan_interval_seconds)


if __name__ == "__main__":
    main()
