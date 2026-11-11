import sys
from pathlib import Path

workspace_root = Path(r"D:\Google\Workspace\Wind")
sys.path.insert(0, str(workspace_root / "AGY2_FundAdvisory"))

from multi_ledger_manager import MultiLedgerManager

mlm = MultiLedgerManager.get_instance(workspace_root)
pm_combat = mlm.get_pm("combat_29_funds")

deep_loss_list = []
tail_fragments = []
tot_val = 0.0

for code, h in pm_combat.holdings.items():
    mv = float(getattr(h, "market_value", 0.0) or (h.get("market_value", 0.0) if isinstance(h, dict) else 0.0))
    tot_val += mv
    
    # 兼容优先级读取
    cost_v = 0.0
    shares = float(getattr(h, "shares", 0.0) or (h.get("shares", 0.0) if isinstance(h, dict) else 0.0))
    cost_p = float(getattr(h, "cost_price", None) or getattr(h, "cost_nav", 0.0) or (h.get("cost_price", h.get("cost_nav", 0.0)) if isinstance(h, dict) else 0.0) or 0.0)
    
    cost_b = float(getattr(h, "cost_basis", None) or getattr(h, "cost_value", 0.0) or (h.get("cost_basis", h.get("cost_value", 0.0)) if isinstance(h, dict) else 0.0) or 0.0)
    
    if cost_b > 0:
        cost_v = cost_b
    elif shares > 0 and cost_p > 0:
        cost_v = shares * cost_p

    pl_ratio = 0.0
    if cost_v > 0:
        pl_ratio = (mv / cost_v - 1.0)
    else:
        raw_pnl_pct = getattr(h, "floating_pnl_pct", None) or getattr(h, "pnl_pct", None) or (h.get("floating_pnl_pct") or h.get("pnl_pct") if isinstance(h, dict) else None)
        if raw_pnl_pct is not None:
            pl_ratio = float(raw_pnl_pct) / 100.0
            cost_v = mv / (1.0 + pl_ratio) if (1.0 + pl_ratio) > 0 else mv

    pnl_amt = getattr(h, "floating_pnl", None) or (h.get("floating_pnl") if isinstance(h, dict) else None)
    if pnl_amt is None:
        pnl_amt = mv - cost_v

    fname = getattr(h, "fund_name", "") or (h.get("fund_name", "") if isinstance(h, dict) else "")
    fcode = getattr(h, "fund_code", "") or (h.get("fund_code", "") if isinstance(h, dict) else code)

    if pl_ratio < -0.10:
        deep_loss_list.append((fname or fcode, pl_ratio, float(pnl_amt)))
    if 0 < mv < 200.0:
        tail_fragments.append((fname or fcode, mv))

print(f"Total Portfolio Value: {tot_val:.2f}")
print(f"Deep Loss Count: {len(deep_loss_list)}")
for item in deep_loss_list:
    print(f"  - {item[0]}: 盈亏率={item[1]*100:.2f}%, 盈亏额={item[2]:.2f}")

print(f"\nTail Fragments Count: {len(tail_fragments)}")
print(f"Tail Fragments Total Amount: {sum(x[1] for x in tail_fragments):.2f}")
