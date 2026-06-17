# 42 + Polymarket Cross-Platform Hedge Arbitrage Bot

Python implementation for monitoring the same sports/event exposure on 42 and Polymarket. It converts all odds into implied probability / buy cost, treats Polymarket as the liquid reference market, and looks for cases where a 42 target basket plus the Polymarket opposite side costs less than `1 - min_profit_margin`.

Default mode is safe:

- `paper_trading=true`
- `auto_trade=false`
- live order methods are adapter boundaries, not silently wired
- if settlement rules differ, or 42 redeem tax is unavailable, the bot emits `ALERT_ONLY`

## Directory Structure

```text
forty_two_polymarket_arb/
  arb_bot/
    adapters/
      base.py              # exchange adapter interfaces
      forty_two.py         # HTTP / Playwright 42 adapter boundary
      mock.py              # deterministic demo adapters
      polymarket.py        # minimal CLOB HTTP market-data adapter
    core/
      arbitrage.py         # signal generation
      pricing.py           # odds/probability/cost math
      rules.py             # settlement and hedgeability checks
    storage/logger.py      # SQLite + JSONL logs
    config.py              # .env + config.json loader
    execution.py           # paper/live gate, requote, unwind hook
    main.py                # CLI runner
    models.py
    notifications.py
  examples/france_senegal_demo.py
  tests/test_pricing_and_rules.py
  .env.example
  config.example.json
  requirements.txt
```

## Install

```bash
cd /Users/zyssssss/Documents/Playground/forty_two_polymarket_arb
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Copy the examples:

```bash
cp .env.example .env
cp config.example.json config.json
```

Important config fields:

- `min_profit_margin`: default `0.03`
- `safety_margin`: default `0.05`
- `max_position_per_market`
- `max_total_exposure`
- `max_slippage`
- `min_liquidity`
- `event_mappings[].forty_two_market_type`: `exact_score`, `yes_no`, or `other`
- `event_mappings[].exact_score_mapping.target_scores`: all exact-score cells that belong to the target result
- `event_mappings[].exact_score_mapping.is_complete_target_coverage`: must be true for live eligibility

## Exact Score Rule

Do not compare one exact score to a win/loss market.

For a 42 exact-score market, the target result cost is:

```text
sum(1 / decimal_odds for every exact score belonging to the target result)
```

If 42 Quick Select says `FRA wins the match excludes ≥4 - ≥4`, the market is marked `NOT_FULLY_HEDGEABLE` because results such as `5-4`, `6-4`, and `6-5` are France wins but sit inside the excluded high-score bucket.

## Run Demo

```bash
PYTHONPATH=. python examples/france_senegal_demo.py
```

Demo assumptions:

- Polymarket France YES = `0.67`
- Polymarket France NO = `0.33`
- 42 France Win exact-score basket = `0.55`
- total cost = `0.55 + 0.33 = 0.88`
- theoretical locked profit = `0.12`

Expected action:

```text
ARBITRAGE_BUY_42_AND_BUY_POLYMARKET_OPPOSITE
```

## Run Once

```bash
PYTHONPATH=. python -m arb_bot.main --config config.example.json --once
```

The runner logs:

- `raw_market_snapshot`
- `signal_log`
- `order_log`
- `position_log`
- `error_log`
- `pnl_log`

to both SQLite and JSONL.

## Live Trading Notes

Live trading is intentionally gated. It is only possible when:

1. `paper_trading=false`
2. `auto_trade=true`
3. both adapters implement audited limit-order placement
4. both sides are requoted immediately before execution
5. profit remains above `min_profit_margin`
6. liquidity, slippage, position, fee, and redeem-tax checks pass
7. the venue supports a credible simultaneous-fill workflow

If one side fills and the other does not, `ExecutionEngine` calls `emergency_unwind()` on the 42 adapter. Production use should implement exchange-specific cancel, sell, redeem, and alert escalation there.
