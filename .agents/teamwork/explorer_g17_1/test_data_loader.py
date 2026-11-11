import sys
from pathlib import Path

sys.path.insert(0, str(Path("d:/Google/Workspace/Wind/AGY2_FundAdvisory")))

from data_loader import DataLoader

fx = DataLoader.fetch_realtime_usdcnh_fx(use_cache=False)
print("fetch_realtime_usdcnh_fx result:", fx)

macro = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
print("\nfetch_macro_cross_market_indicators result:", macro)
