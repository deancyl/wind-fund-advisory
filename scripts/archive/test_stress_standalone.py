# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path("d:/Google/Workspace/Wind")
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from strategy_bridge import StrategyBridge

def simulate_black_swan_stress_test(holdings, total_capital=100000.0, df_bt=None):
    if df_bt is None:
        # 归一化持仓
        if isinstance(holdings, dict):
            raw_w = {str(k): float(v) for k, v in holdings.items() if float(v) > 0}
        elif isinstance(holdings, list):
            raw_w = {}
            for item in holdings:
                if isinstance(item, dict):
                    c = item.get("fund_code") or item.get("code")
                    w = item.get("weight") or item.get("market_value", 0.0)
                    if c and float(w) > 0:
                        raw_w[str(c)] = float(w)
        else:
            raw_w = {}

        tot = sum(raw_w.values())
        if tot <= 0:
            norm_w = {"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10}
        else:
            norm_w = {k: v / tot for k, v in raw_w.items()}
        
        df_bt = StrategyBridge.build_custom_portfolio_backtest(fund_weights=norm_w)
    else:
        norm_w = holdings if isinstance(holdings, dict) else {}

    df_bt = df_bt.copy()
    df_bt["date_str"] = df_bt["date"].astype(str).str[:10]
    df_bt["dt"] = pd.to_datetime(df_bt["date_str"])

    slices_def = [
        {
            "id": "2018_trade_war",
            "name": "2018 贸易摩擦熊市",
            "start": "2018-01-29",
            "end": "2019-01-04",
            "desc": "中美贸易摩擦升级，金融去杠杆叠加估值盈利双杀",
            "severity": "极高风险",
        },
        {
            "id": "2022_valuation_kill",
            "name": "2022 核心资产杀估值",
            "start": "2021-12-13",
            "end": "2022-10-31",
            "desc": "美联储激进加息、地缘冲突与疫情冲击，全球资产杀估值",
            "severity": "高风险",
        },
        {
            "id": "2024_micro_liquidity",
            "name": "2024 微盘流动性危机",
            "start": "2024-01-02",
            "end": "2024-02-05",
            "desc": "雪球期权集中敲入与量化微盘踩踏，小微盘流动性抽水",
            "severity": "极端流动性冲击",
        },
    ]

    scenarios = []
    for sl in slices_def:
        sub = df_bt[(df_bt["date_str"] >= sl["start"]) & (df_bt["date_str"] <= sl["end"])].copy()
        if sub.empty:
            continue
        nav_s = sub["strategy_nav"].values
        cummax = np.maximum.accumulate(nav_s)
        dd = (nav_s - cummax) / np.maximum(cummax, 1e-8)
        max_dd_val = abs(float(np.min(dd)))
        max_dd_pct = max_dd_val * 100.0
        max_loss_amt = float(total_capital) * max_dd_val

        trough_idx = int(np.argmin(dd))
        peak_idx = int(np.argmax(nav_s[:trough_idx + 1]))
        peak_val = nav_s[peak_idx]
        peak_dt = sub["dt"].iloc[peak_idx]

        # 查找全周期回测中后续回本时间
        sub_post = df_bt[df_bt["dt"] >= peak_dt]
        rec_rows = sub_post[sub_post["strategy_nav"] >= peak_val]
        if len(rec_rows) > 1:
            rec_dt = rec_rows.iloc[1]["dt"]
            rec_tdays = len(df_bt[(df_bt["dt"] >= peak_dt) & (df_bt["dt"] <= rec_dt)])
            rec_days = (rec_dt - peak_dt).days
            rec_str = f"{rec_tdays} 交易日 (约 {round(rec_days / 30.4, 1)} 个月)"
        else:
            rec_str = "跨周期修复中"
            rec_tdays = -1

        # 沪深300同期最大回撤
        h300_s = sub["h300_nav"].values if "h300_nav" in sub.columns else sub["strategy_nav"].values
        h300_cummax = np.maximum.accumulate(h300_s)
        h300_dd = (h300_s - h300_cummax) / np.maximum(h300_cummax, 1e-8)
        h300_mdd_pct = abs(float(np.min(h300_dd))) * 100.0
        excess_defense = h300_mdd_pct - max_dd_pct

        scenarios.append({
            "id": sl["id"],
            "name": sl["name"],
            "period": f"{sl['start']} ~ {sl['end']}",
            "start_date": sl["start"],
            "end_date": sl["end"],
            "desc": sl["desc"],
            "severity": sl["severity"],
            "max_dd_pct": round(max_dd_pct, 2),
            "max_loss_amt": round(max_loss_amt, 2),
            "recovery_str": rec_str,
            "recovery_tdays": rec_tdays,
            "h300_mdd_pct": round(h300_mdd_pct, 2),
            "excess_defense_pct": round(excess_defense, 2),
        })

    return {
        "total_capital": total_capital,
        "portfolio_weights": norm_w,
        "scenarios": scenarios,
    }

if __name__ == "__main__":
    res = simulate_black_swan_stress_test({"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10})
    for sc in res["scenarios"]:
        print(sc["name"], "MaxDD:", sc["max_dd_pct"], "% Loss:", sc["max_loss_amt"], "Recovery:", sc["recovery_str"], "Excess:", sc["excess_defense_pct"], "%")
