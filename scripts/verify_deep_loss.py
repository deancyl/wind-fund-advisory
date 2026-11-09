import sys
sys.path.insert(0, ".")
import json
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager

with open("data/ledgers/combat_29_funds.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print("=== IN JSON FILE ===")
json_targets = {h["fund_code"]: h for h in d["holdings"] if h["fund_code"] in ["100032", "011613", "161725"]}
sum_json_pnl = 0.0
for code in ["100032", "011613", "161725"]:
    item = json_targets[code]
    print(f"Code {code}: MV={item['market_value']}, Cost={item['cost_basis']}, PnL={item['floating_pnl']}, Days={item['batches'][0]['holding_days']}")
    sum_json_pnl += item['floating_pnl']
print(f"Total Deep Loss in JSON: {sum_json_pnl:.2f}")

print("\n=== IN PM RUNTIME OBJECT ===")
mlm = MultiLedgerManager.get_instance()
pm = mlm.get_pm("combat_29_funds")
sum_pm_pnl = 0.0
for code in ["100032", "011613", "161725"]:
    h = pm.holdings[code]
    print(f"Code {code}: MV={h.market_value}, Cost={h.cost_basis}, PnL={h.floating_pnl}, Days={h.batches[0].holding_days}")
    sum_pm_pnl += h.floating_pnl
print(f"Total Deep Loss in PM: {sum_pm_pnl:.2f}")

print("\n=== ALL 29 BATCHES IN JSON ===")
all_json_days = [b["holding_days"] for h in d["holdings"] for b in h["batches"]]
print(f"Min days in JSON: {min(all_json_days)}, Max days in JSON: {max(all_json_days)}")
all_pm_days = [b.holding_days for h in pm.holdings.values() for b in h.batches]
print(f"Min days in PM: {min(all_pm_days)}, Max days in PM: {max(all_pm_days)}")
