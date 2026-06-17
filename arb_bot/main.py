from __future__ import annotations

import argparse
import time

from arb_bot.adapters.mock import MockFortyTwoAdapter, MockPolymarketAdapter
from arb_bot.config import load_config
from arb_bot.core.arbitrage import ArbitrageEngine
from arb_bot.execution import ExecutionEngine
from arb_bot.notifications import Notifier
from arb_bot.storage.logger import EventLogger


def run_once(config_path: str) -> None:
    config = load_config(config_path)
    polymarket = MockPolymarketAdapter()
    forty_two = MockFortyTwoAdapter()
    engine = ArbitrageEngine(config)
    executor = ExecutionEngine(config, engine, forty_two, polymarket)
    notifier = Notifier(config.notifications)
    logger = EventLogger(config.database_path, config.jsonl_dir)

    for mapping in config.event_mappings:
        poly_snapshot = polymarket.get_snapshot(mapping["polymarket_market_id"])
        forty_two_snapshot = forty_two.get_snapshot(mapping["forty_two_market_id"], mapping["forty_two_market_type"])
        logger.log("raw_market_snapshot", {"polymarket": poly_snapshot, "forty_two": forty_two_snapshot})
        signal = engine.evaluate(mapping, poly_snapshot, forty_two_snapshot)
        logger.log("signal_log", signal)
        notifier.send_signal(signal, auto_trade_allowed=(not config.paper_trading and config.auto_trade))
        report = executor.execute(signal, mapping)
        logger.log("order_log", report)


def main() -> None:
    parser = argparse.ArgumentParser(description="42 + Polymarket hedge arbitrage bot")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        run_once(args.config)
        return
    config = load_config(args.config)
    try:
        while True:
            run_once(args.config)
            time.sleep(config.check_interval_seconds)
    except KeyboardInterrupt:
        print("Shutdown requested. Exiting cleanly.")


if __name__ == "__main__":
    main()
