import json
from pathlib import Path

p = Path(r"d:\Google\Workspace\Wind\data\ledgers\combat_29_funds.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

holdings = data["holdings"]
print(f"Total count: {len(holdings)}")
total_mv = sum(h["market_value"] for h in holdings)
total_cost = sum(h["cost_basis"] for h in holdings)
total_pnl = sum(h["floating_pnl"] for h in holdings)

print(f"Total MV: {total_mv:.2f}")
print(f"Total Cost: {total_cost:.2f}")
print(f"Total PnL: {total_pnl:.2f}")
print(f"Diff MV - Cost: {total_mv - total_cost:.2f}")
print(f"data total_market_value: {data.get('total_market_value')}")
print(f"data available_cash: {data.get('available_cash')}")
print(f"data total_equity: {data.get('total_equity')}")

# Check 7 core, 3 waist, 19 tail
core = [h for h in holdings if h["market_value"] >= 1000.0]
waist = [h for h in holdings if 100.0 <= h["market_value"] < 1000.0]
tail = [h for h in holdings if h["market_value"] < 100.0]
print(f"Core count: {len(core)}, sum MV: {sum(h['market_value'] for h in core):.2f}, sum Cost: {sum(h['cost_basis'] for h in core):.2f}")
print(f"Waist count: {len(waist)}, sum MV: {sum(h['market_value'] for h in waist):.2f}, sum Cost: {sum(h['cost_basis'] for h in waist):.2f}")
print(f"Tail count: {len(tail)}, sum MV: {sum(h['market_value'] for h in tail):.2f}, sum Cost: {sum(h['cost_basis'] for h in tail):.2f}")

deep_loss = [h for h in holdings if h["floating_pnl_pct"] <= -10.0]
print(f"\nDeep loss funds (<= -10%): {len(deep_loss)}")
for h in deep_loss:
    print(f"  {h['fund_code']} {h['fund_name']}: MV={h['market_value']}, PnL={h['floating_pnl']}, PnL%={h['floating_pnl_pct']}%")
