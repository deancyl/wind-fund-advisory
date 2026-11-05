# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

WORKSPACE_ROOT = Path("d:/Google/Workspace/Wind")
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from strategy_bridge import StrategyBridge
from portfolio_optimizer import WinRateOptimizer, QUANT_MODELS_CATALOG

print("Testing loading matrix and candidates...")
dl_mat = StrategyBridge.load_matrix()
print(f"Matrix loaded, rows: {len(dl_mat)}, cols: {len(dl_mat.columns)}")

# Test existing 4 models
for m in ["hrp_cvar", "cond_winrate", "min_cvar", "kelly_momentum"]:
    res = StrategyBridge.compute_n_funds_model_portfolio(
        tier="C3",
        target_return_pct=15.0,
        num_funds=6,
        model_type=m,
        capital=100000.0
    )
    w = res["optimal_weights"]
    print(f"Model {m}: sum={sum(w.values()):.4f}, distinct={len(set(w.values()))}, weights={w}")
