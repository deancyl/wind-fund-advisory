import sys
from pathlib import Path

workspace_root = Path(r"D:\Google\Workspace\Wind")
sys.path.insert(0, str(workspace_root / "AGY2_FundAdvisory"))

from multi_ledger_manager import MultiLedgerManager
from advisory_engine import ActiveRiskSentry

mlm = MultiLedgerManager.get_instance(workspace_root)
pm_combat = mlm.get_pm("combat_29_funds")

sentry = ActiveRiskSentry()
rep = sentry.inspect_portfolio(
    holdings=pm_combat.holdings,
    investor_risk_tier="C3"
)

print(f"Total alerts: {len(rep['alerts'])}")
for idx, a in enumerate(rep['alerts'], 1):
    print(f"[{idx}] Level: {a['level']} | Dim: {a['dimension']} | Title: {a['title']}")
