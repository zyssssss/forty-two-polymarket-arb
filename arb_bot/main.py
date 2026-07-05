"""
42 + Polymarket Cross-Platform Hedge Arbitrage Bot
Supports both mock (demo) and real API adapters.
"""
from __future__ import annotations

import argparse
import time

from arb_bot.adapters.mock import MockFortyTwoAdapter, MockPolymarketAdapter
from arb_bot.adapters.polymarket import HttpPolymarketAdapter
from arb_bot.adapters.forty_two_rest import FortyTwoRestAdapter
from arb_bot.config import load_config
from arb_bot.core.arbitrage import ArbitrageEngine
from arb_bot.execution import ExecutionEngine
from arb_bot.notifications import Notifier
from arb_bot.storage.logger import EventLogger


def run_once(config_path: str, use_mock: bool = False) -> None:
    config = load_config(config_path)

    if use_mock:
        polymarket_adapter = MockPolymarketAdapter()
        forty_two_adapter = MockFortyTwoAdapter()
    else:
        polymarket_adapter = HttpPolymarketAdapter(config.polymarket)
        forty_two_adapter = FortyTwoRestAdapter(config.forty_two)

    engine = ArbitrageEngine(config)
    executor = ExecutionEngine(config, engine, forty_two_adapter, polymarket_adapter)
    notifier = Notifier(config.notifications)
    logger = EventLogger(config.database_path, config.jsonl_dir)

    for mapping in config.event_mappings:
        poly_snapshot = polymarket_adapter.get_snapshot(mapping["polymarket_market_id"])
        forty_two_snapshot = forty_two_adapter.get_snapshot(
            mapping["forty_two_market_id"], mapping.get("forty_two_market_type", "exact_score")
        )
        logger.log("raw_market_snapshot", {
            "polymarket": poly_snapshot.__dict__ if hasattr(poly_snapshot, '__dict__') else str(poly_snapshot),
            "forty_two": forty_two_snapshot.__dict__ if hasattr(forty_two_snapshot, '__dict__') else str(forty_two_snapshot),
        })
        signal = engine.evaluate(mapping, poly_snapshot, forty_two_snapshot)
        logger.log("signal_log", signal.__dict__ if hasattr(signal, '__dict__') else str(signal))
        notifier.send_signal(signal, auto_trade_allowed=(not config.paper_trading and config.auto_trade))
        report = executor.execute(signal, mapping)
        logger.log("order_log", report.__dict__ if hasattr(report, '__dict__') else str(report))


def main() -> None:
    parser = argparse.ArgumentParser(description="42 + Polymarket hedge arbitrage bot")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--mock", action="store_true", help="Use mock adapters for demo/testing")
    args = parser.parse_args()

    if args.once:
        run_once(args.config, use_mock=args.mock)
        return

    config = load_config(args.config)
    try:
        while True:
            run_once(args.config, use_mock=args.mock)
            time.sleep(config.check_interval_seconds)
    except KeyboardInterrupt:
        print("Shutdown requested. Exiting cleanly.")


if __name__ == "__main__":
    main()
