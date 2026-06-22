from __future__ import annotations

import argparse
import time

from src.arbitrage_detector import detect_arbitrage
from src.config import load_config
from src.forty_two_adapter import HttpFortyTwoAdapter, MockFortyTwoAdapter
from src.logger import JsonlLogger
from src.market_matcher import MarketMatcher
from src.models import SuggestedAction
from src.notifier import Notifier
from src.odds_calculator import normalize_forty_two_market, normalize_polymarket_market
from src.polymarket_adapter import HttpPolymarketAdapter, MockPolymarketAdapter
from src.team_normalizer import TeamNormalizer


def scan_once(config_path: str) -> dict[str, int]:
    config = load_config(config_path)
    logger = JsonlLogger(config.data_dir)
    notifier = Notifier(config.notifications.console, config.notifications.webhook_url)
    normalizer = TeamNormalizer(config.team_aliases)
    matcher = MarketMatcher(normalizer)

    if config.use_mock_data:
        forty_two_adapter = MockFortyTwoAdapter()
        polymarket_adapter = MockPolymarketAdapter()
    else:
        forty_two_adapter = HttpFortyTwoAdapter(config.forty_two.api_base_url)
        polymarket_adapter = HttpPolymarketAdapter(
            config.polymarket.api_base_url,
            config.polymarket.clob_base_url or "https://clob.polymarket.com",
        )

    try:
        forty_two_markets = forty_two_adapter.list_worldcup_markets()
        polymarket_markets = polymarket_adapter.list_worldcup_markets()
        logger.market_snapshot({"forty_two": forty_two_markets, "polymarket": polymarket_markets})

        matches, unmatched = matcher.match(forty_two_markets, polymarket_markets)
        for item in unmatched:
            logger.unmatched_market(item)

        alert_count = 0
        for match in matches:
            forty_two = normalize_forty_two_market(match.forty_two, config.risk_flags.flag_42_excludes_4_4)
            polymarket = normalize_polymarket_market(match.polymarket)
            signal = detect_arbitrage(
                forty_two,
                polymarket,
                target_total_cost_threshold=config.target_total_cost_threshold,
                allow_partial_coverage_alert=config.risk_flags.allow_partial_coverage_alert,
            )
            logger.signal(signal)
            if signal.suggested_action == SuggestedAction.ALERT_ARBITRAGE_OPPORTUNITY:
                alert_count += 1
                notifier.send(signal)
        return {
            "forty_two": len(forty_two_markets),
            "polymarket": len(polymarket_markets),
            "matched": len(matches),
            "alerts": alert_count,
        }
    except Exception as exc:
        logger.error({"error": str(exc), "type": type(exc).__name__})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="World Cup 42.space + Polymarket arbitrage monitor")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--check-live", action="store_true")
    args = parser.parse_args()

    if args.check_live:
        config = load_config(args.config)
        forty_two = HttpFortyTwoAdapter(config.forty_two.api_base_url)
        polymarket = HttpPolymarketAdapter(
            config.polymarket.api_base_url,
            config.polymarket.clob_base_url or "https://clob.polymarket.com",
        )
        forty_two_markets = forty_two.list_worldcup_markets()
        polymarket_markets = polymarket.list_worldcup_markets()
        print("42:", forty_two.last_diagnostics)
        print("Polymarket:", polymarket.last_diagnostics)
        print(f"Comparable markets: 42={len(forty_two_markets)}, Polymarket={len(polymarket_markets)}")
        if not forty_two_markets:
            raise SystemExit("42 live API returned no usable exact-score markets")
        if not polymarket.last_diagnostics.get("candidate_count"):
            raise SystemExit("Polymarket Gamma returned no World Cup candidates")
        if polymarket.last_diagnostics.get("clob_probe_price") is None:
            raise SystemExit("Polymarket CLOB price probe failed")
        return
    if args.once:
        print("Scan:", scan_once(args.config))
        return

    config = load_config(args.config)
    try:
        while True:
            try:
                print("Scan:", scan_once(args.config))
            except Exception as exc:
                print(f"Scan failed; retrying after {config.scan_interval_seconds}s: {exc}")
            time.sleep(config.scan_interval_seconds)
    except KeyboardInterrupt:
        print("Shutdown requested. Exiting cleanly.")


if __name__ == "__main__":
    main()
