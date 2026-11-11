import sys
from pathlib import Path

workspace_root = Path(r"D:\Google\Workspace\Wind")
sys.path.insert(0, str(workspace_root / "AGY2_FundAdvisory"))

from advisory_engine import generate_chief_advisor_memo

# Tab 1 opt_weights dictionary
opt_weights = {
    "005561": 0.35,
    "002351": 0.20,
    "110020": 0.15,
    "011613": 0.15,
    "017436": 0.10,
    "000216": 0.05
}

# In Tab 1, it calls:
# memo_t1 = generate_chief_advisor_memo(snapshot=snapshot, holdings=opt_weights, ...)
memo = generate_chief_advisor_memo(holdings=opt_weights)
pathology = memo["portfolio_pathology"]

print("=== Tab 1 opt_weights Call Output ===")
print("deep_loss_count:", pathology["deep_loss_count"])
print("frag_count:", pathology["frag_count"])
print("frag_amt:", pathology["frag_amt"])
print("content:", pathology["content"])
