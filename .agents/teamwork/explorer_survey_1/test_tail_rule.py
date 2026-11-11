import sys
from pathlib import Path

workspace_root = Path(r"D:\Google\Workspace\Wind")
sys.path.insert(0, str(workspace_root / "AGY2_FundAdvisory"))

from multi_ledger_manager import MultiLedgerManager

mlm = MultiLedgerManager.get_instance(workspace_root)
pm_combat = mlm.get_pm("combat_29_funds")

tail_funds = []
for code, h in pm_combat.holdings.items():
    mv = float(getattr(h, "market_value", 0.0))
    s_cls = str(getattr(h, "share_class", "A")).upper()
    fname = str(getattr(h, "fund_name", ""))
    
    # ActiveRiskSentry standard
    is_tail = (
        mv < 100.0
        or (mv < 200.0 and (s_cls == "C" or any(k in fname for k in ["联接", "ETF", "指数", "红包", "体验", "尾仓"])))
    )
    if is_tail:
        tail_funds.append((code, fname, mv, s_cls))

print(f"Tail funds count: {len(tail_funds)}")
print(f"Total tail amount: {sum(x[2] for x in tail_funds):.2f}")
for code, fn, mv, s in tail_funds:
    print(f"  {code}: {fn} ({s}类, {mv:.2f}元)")
