# World Cup Arbitrage Monitor

Python monitor for World Cup prediction markets on 42.space and Polymarket.
Version 1 is alert-only: it does not trade, does not connect wallets, and does not store private keys or cookies.

## Logic

42 is normalized into three costs:

- `42_team_win_cost`
- `42_team_draw_cost`
- `42_team_lost_cost`

Polymarket is normalized into:

- `polymarket_team_yes_cost`
- `polymarket_team_no_cost`

The monitor emits an alert only when both conditions pass:

```text
Condition A: 42_team_win_cost + polymarket_team_no_cost < target_total_cost_threshold
Condition B: 42_team_draw_cost + 42_team_lost_cost > polymarket_team_no_cost
```

The default threshold is `0.9`.

If 42 exact score rules say `excludes ≥4 - ≥4`, the monitor can still alert, but it marks:

```text
rule_risk = true
rule_risk_reason = "42 Team Win excludes ≥4-≥4, not fully equivalent to Polymarket Team Win"
```

That means the signal is not strict risk-free arbitrage; it is a partial-coverage price-dislocation alert.

## Structure

```text
worldcup-arb-monitor/
  README.md
  requirements.txt
  .env.example
  config.example.json
  main.py
  src/
    config.py
    models.py
    polymarket_adapter.py
    forty_two_adapter.py
    team_normalizer.py
    market_matcher.py
    odds_calculator.py
    arbitrage_detector.py
    notifier.py
    logger.py
  data/
    market_snapshots.jsonl
    signals.jsonl
    unmatched_markets.jsonl
    errors.jsonl
  tests/
    test_odds_calculator.py
    test_arbitrage_detector.py
    test_team_normalizer.py
```

The local folder is still named `forty_two_polymarket_arb`, but the code follows the PRD structure.

## Install

```bash
cd /Users/zyssssss/Documents/Playground/forty_two_polymarket_arb
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

```bash
cp .env.example .env
cp config.example.json config.json
```

`.env`:

```text
POLYMARKET_API_BASE_URL=https://gamma-api.polymarket.com
POLYMARKET_CLOB_BASE_URL=https://clob.polymarket.com
FORTY_TWO_API_BASE_URL=https://rest.ft.42.space
WEBHOOK_URL=
```

`config.json`:

```json
{
  "scan_interval_seconds": 60,
  "target_total_cost_threshold": 0.9,
  "markets": {
    "sport": "soccer",
    "competition": "World Cup"
  },
  "notifications": {
    "console": true,
    "webhook_url": ""
  },
  "risk_flags": {
    "allow_partial_coverage_alert": true,
    "flag_42_excludes_4_4": true
  }
}
```

The example config defaults to live, read-only endpoints:

- Polymarket Gamma: `https://gamma-api.polymarket.com`
- Polymarket CLOB: `https://clob.polymarket.com`
- 42 market REST API: `https://rest.ft.42.space`

42 exact-score API values are normalized as:

```text
decimal_odds = payout / price
implied_probability = price / payout
```

The raw 42 `price` field must never be summed directly.
The ambiguous `≥4–≥4` cell is excluded from Win/Draw/Lost totals and marks the
market as partial coverage because it contains winning, drawing, and losing
scorelines.

## Run

One scan:

```bash
PYTHONPATH=. python main.py --config config.example.json --once
```

Verify live connectivity and report usable market counts:

```bash
PYTHONPATH=. python main.py --config config.example.json --check-live
```

The check distinguishes API connectivity from market compatibility. It is valid
for Polymarket to return zero compatible single-match Team Yes/No markets when
only tournament-winner or group-winner markets are listed; those markets are
intentionally rejected.

24-hour loop:

```bash
PYTHONPATH=. python main.py --config config.json
```

Stop with `Ctrl-C`.

## Alert Format

```text
【世界杯套利机会】

比赛：France vs Senegal
队伍：France
42 Win 成本：0.55
42 Draw 成本：0.20
42 Lost 成本：0.25
42 Draw + Lost 成本：0.45
Polymarket Yes 成本：0.67
Polymarket No 成本：0.33
No 是否估算：否
总成本 42 Win + Polymarket No：0.88
理论空间：12%
Polymarket No 相对 42 Draw+Lost 折价：12%
Condition A 是否成立：是
Condition B 是否成立：是
是否存在规则风险：是
规则风险原因：42 Team Win excludes ≥4-≥4, not fully equivalent to Polymarket Team Win
时间：2026-06-17T03:00:00Z
建议动作：ALERT_ARBITRAGE_OPPORTUNITY
```

## Logs

All scans write JSONL files:

- `data/market_snapshots.jsonl`
- `data/signals.jsonl`
- `data/unmatched_markets.jsonl`
- `data/errors.jsonl`

## Tests

```bash
PYTHONPATH=. pytest tests
```

The tests cover decimal odds conversion, Polymarket yes/no conversion, exact-score grouping, Condition A/B, alias matching, and `excludes ≥4-≥4` rule-risk tagging.
