# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path("d:/Google/Workspace/Wind")
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from strategy_bridge import StrategyBridge

df_bt = StrategyBridge.build_custom_portfolio_backtest(
    fund_weights={"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10},
    tier="C3",
    target_return_pct=15.0
)

slices = [
    {
        "name": "2018 贸易摩擦熊市",
        "start": "2018-01-29",
        "end": "2018-12-28",
        "desc": "中美贸易摩擦升级，去杠杆叠加估值盈利双杀",
        "h300_mdd": -31.8
    },
    {
        "name": "2022 杀估值熊市",
        "start": "2022-01-04",
        "end": "2022-10-31",
        "desc": "美联储激进加息、地缘冲突与疫情冲击，全球资产杀估值",
        "h300_mdd": -28.9
    },
    {
        "name": "2024 年初微盘流动性危机",
        "start": "2024-01-02",
        "end": "2024-02-08",
        "desc": "雪球集中敲入与量化微盘踩踏，小微盘遭遇流动性抽水",
        "h300_mdd": -7.3
    }
]

capital = 100000.0
results = []
df_bt['dt'] = pd.to_datetime(df_bt['date'])

for sl in slices:
    sub = df_bt[(df_bt['date'] >= sl['start']) & (df_bt['date'] <= sl['end'])].copy()
    if sub.empty:
        continue
    nav_s = sub['strategy_nav'].values
    cummax = np.maximum.accumulate(nav_s)
    dd = (nav_s - cummax) / np.maximum(cummax, 1e-8)
    max_dd_pct = abs(float(np.min(dd))) * 100.0
    max_loss_amt = capital * (max_dd_pct / 100.0)
    
    trough_idx = int(np.argmin(dd))
    peak_idx = int(np.argmax(nav_s[:trough_idx + 1]))
    peak_val = nav_s[peak_idx]
    peak_dt = sub['dt'].iloc[peak_idx]
    
    # 查找全周期回测中后续回本时间
    sub_post = df_bt[df_bt['dt'] >= peak_dt]
    rec_rows = sub_post[sub_post['strategy_nav'] >= peak_val]
    # 第一个大于等于 peak_val 的是 peak_dt 本身，找第二个
    if len(rec_rows) > 1:
        rec_dt = rec_rows.iloc[1]['dt']
        rec_days = (rec_dt - peak_dt).days
        rec_tdays = len(df_bt[(df_bt['dt'] >= peak_dt) & (df_bt['dt'] <= rec_dt)])
        rec_str = f"{rec_tdays} 交易日 (约 {round(rec_days / 30, 1)} 个月)"
    else:
        rec_str = "跨周期修复中"
        rec_days = -1
        rec_tdays = -1

    results.append({
        "name": sl['name'],
        "period": f"{sl['start']} ~ {sl['end']}",
        "max_dd_pct": round(max_dd_pct, 2),
        "max_loss_amt": round(max_loss_amt, 2),
        "recovery": rec_str,
        "h300_mdd": sl['h300_mdd'],
        "desc": sl['desc']
    })

for r in results:
    print(r)
