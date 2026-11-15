import sys
import os
WORKSPACE_DIR = r"D:\Google\Workspace\Wind"
sys.path.insert(0, WORKSPACE_DIR)
sys.path.insert(0, os.path.join(WORKSPACE_DIR, "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.data_loader import DataLoader

try:
    mb = DataLoader.fetch_market_turnover_and_sentiment()
    print("Market breadth keys:", list(mb.keys()))
    print("total_turnover:", mb.get("total_turnover"))
    print("turnover_str:", mb.get("turnover_str"))
    print("up_pct:", mb.get("up_pct"))
    print("up_count:", mb.get("up_count"))
    print("down_count:", mb.get("down_count"))
except Exception as e:
    print("Error:", e)
