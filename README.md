# World Cup 42 + Polymarket Arbitrage Monitor

只做世界杯预测市场套利监控和提醒，不做真实交易，不连接钱包，不保存私钥或 Cookie。

## Core Logic

针对同一场世界杯比赛和同一目标队伍：

```text
Condition A: 42_team_win_cost + polymarket_team_no_cost < 0.9
Condition B: 42_team_draw_cost + 42_team_lost_cost > polymarket_team_no_cost
```

只有 A 和 B 同时成立才输出 `ALERT_ARBITRAGE_OPPORTUNITY`。

## APIs

- Polymarket: `https://gamma-api.polymarket.com/events`
- 42.space: `https://rest.ft.42.space/api/v1/markets/{address}`

42 的 REST `price` 如果是 bonding-curve marginal price 且所有 outcome 价格总和不接近 1，会先归一化为 `price / sum(all_prices)`，再拆成 Win / Draw / Lost 成本，避免把 marginal price 直接当作 Polymarket 概率比较。

## Structure

```text
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
  test_worldcup_monitor.py
```

Legacy `arb_bot/` 代码仍保留，但新版监控入口是根目录 `main.py`。

## Install

```powershell
cd C:\polymarket\forty-two-polymarket-arb
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
copy .env.example .env
```

## Configure

编辑 `config.example.json` 或复制为自己的配置：

```powershell
copy config.example.json config.local.json
```

关键字段：

- `scan_interval_seconds`: 扫描间隔
- `target_total_cost_threshold`: 默认 `0.9`
- `polymarket_event_slugs`: 指定 Polymarket World Cup event slug
- `forty_two_market_addresses`: 指定 42 market address
- `notifications.webhook_url`: 可选 webhook

## Run Once

```powershell
$env:PYTHONPATH = "C:\polymarket\forty-two-polymarket-arb"
.venv\Scripts\python.exe main.py --config config.example.json --once
```

## Run 24/7

```powershell
$env:PYTHONPATH = "C:\polymarket\forty-two-polymarket-arb"
.venv\Scripts\python.exe main.py --config config.example.json
```

## Logs

- `data/market_snapshots.jsonl`: 每次扫描原始标准化盘口
- `data/signals.jsonl`: 套利提醒
- `data/unmatched_markets.jsonl`: 无法匹配的市场
- `data/errors.jsonl`: API 错误、解析错误、超时

## Tests

```powershell
$env:PYTHONPATH = "C:\polymarket\forty-two-polymarket-arb"
.venv\Scripts\python.exe -m pytest tests -v
```
