"""Test real API adapters with live data."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arb_bot.adapters.polymarket import HttpPolymarketAdapter
from arb_bot.adapters.forty_two_rest import FortyTwoRestAdapter, normalize_score_name
from arb_bot.config import PolymarketConfig

# Test 1: Polymarket adapter
print("=" * 60)
print("1. Testing Polymarket CLOB Adapter")
print("=" * 60)
poly = HttpPolymarketAdapter(PolymarketConfig())
token_id = "76071109489406808599878692125264766321676001700733380917373465772841855210643"
try:
    snap = poly.get_snapshot(token_id)
    print(f"  Market: {token_id[:16]}...")
    print(f"  YES price: {snap.yes_price:.4f}")
    print(f"  NO price: {snap.no_price:.4f}")
    print(f"  YES book asks: {len(snap.yes_book.asks)} levels")
    print(f"  NO book asks: {len(snap.no_book.asks)} levels")
    if snap.yes_book.asks:
        print(f"  YES best ask: {snap.yes_book.asks[0].price:.4f} x {snap.yes_book.asks[0].size:.2f}")
    if snap.no_book.asks:
        print(f"  NO best ask: {snap.no_book.asks[0].price:.4f} x {snap.no_book.asks[0].size:.2f}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: 42 REST adapter
print("\n" + "=" * 60)
print("2. Testing 42 REST Adapter")
print("=" * 60)
ft = FortyTwoRestAdapter()
contract = "0xBcD1Bc19b678b3677536431c0433F18C3E4e4723"
try:
    snap = ft.get_snapshot(contract, "exact_score")
    print(f"  Market: {contract}")
    print(f"  Total outcomes: {len(snap.outcomes)}")
    print(f"  Quick select: {snap.quick_select_text}")
    print(f"\n  All outcomes (normalized):")
    for o in sorted(snap.outcomes, key=lambda x: -float(x.decimal_odds or 0)):
        raw = o.metadata.get("raw_name", o.name)
        print(f"    {o.name:<10} (raw: {raw:<22})  dec_odds={o.decimal_odds or 0:>8.1f}  price={o.buy_quote:.6f}  mcap={o.buy_depth:.0f}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: name normalization
print("\n" + "=" * 60)
print("3. Name Normalization Test")
print("=" * 60)
test_cases = [
    "POR 1–0 COD",
    "POR 2–1 COD",
    "POR >=4–0 COD",
    "POR 0–>=4 COD",
    "POR 0–0 COD",
    "POR >=4–>=4 COD",
    "COD 1–0 POR",
]
for tc in test_cases:
    result = normalize_score_name(tc)
    print(f"  '{tc}' -> '{result}'")
