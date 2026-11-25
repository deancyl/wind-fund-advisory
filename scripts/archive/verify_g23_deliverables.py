import sys
from pathlib import Path
sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))

def verify_r1():
    print("--- 正在验证 R1: 核心指数走廊多模检索与实时候选 ---")
    from data_loader import validate_and_fetch_code, search_index_and_fund_candidates
    for q in ["hldb", "红利低波", "H30269"]:
        res = validate_and_fetch_code(q)
        assert res is not None, f"Query '{q}' returned None from validate_and_fetch_code!"
        assert res["code"] == "H30269", f"Query '{q}' did not resolve to H30269, got: {res}"
        print(f"  [OK] validate_and_fetch_code('{q}') -> code: {res['code']}, name: {res['name']}")

    cands = search_index_and_fund_candidates("hldb")
    assert len(cands) > 0, "search_index_and_fund_candidates('hldb') returned empty!"
    assert any(c["code"] == "H30269" for c in cands), f"H30269 not in candidates: {cands}"
    print(f"  [OK] search_index_and_fund_candidates('hldb') returned {len(cands)} candidates, including: {cands[0]}")

    cands_cn = search_index_and_fund_candidates("红利低波")
    assert any(c["code"] == "H30269" for c in cands_cn), "H30269 not in candidates for '红利低波'"
    print(f"  [OK] search_index_and_fund_candidates('红利低波') resolved correctly.")

    invalid_res = validate_and_fetch_code("invalid_garbage_code")
    assert invalid_res is None, "Invalid query should return None"
    print("  [OK] Invalid queries safely return None.")
    print("R1 全部断言通过!\n")

def verify_r2():
    print("--- 正在验证 R2: 四级穿透盘中实时估值与 0.95 倍系数 ---")
    from portfolio_manager import PortfolioManager
    pm = PortfolioManager()
    
    # Check 110020 -> 000300
    q_110020 = pm.fetch_realtime_fund_quote("110020")
    q_300 = pm.fetch_realtime_index_quote("000300")
    print(f"  110020 gszzl: {q_110020['gszzl']}, 000300 chg: {q_300['change_pct']}")
    if not q_110020.get("is_official_nav", False) and not q_110020.get("real_tiantian_live", False):
        assert abs(q_110020["gszzl"] - round(q_300["change_pct"] * 0.95, 2)) < 1e-4

    # Check 011613 -> 000688
    q_011613 = pm.fetch_realtime_fund_quote("011613")
    q_688 = pm.fetch_realtime_index_quote("000688")
    print(f"  011613 gszzl: {q_011613['gszzl']}, 000688 chg: {q_688['change_pct']}")
    if not q_011613.get("is_official_nav", False) and not q_011613.get("real_tiantian_live", False):
        assert abs(q_011613["gszzl"] - round(q_688["change_pct"] * 0.95, 2)) < 1e-4

    # Check 000216 -> sh518880
    q_000216 = pm.fetch_realtime_fund_quote("000216")
    q_gold = pm.fetch_realtime_index_quote("sh518880")
    print(f"  000216 gszzl: {q_000216['gszzl']}, sh518880 chg: {q_gold['change_pct']}")
    if not q_000216.get("is_official_nav", False) and not q_000216.get("real_tiantian_live", False):
        assert abs(q_000216["gszzl"] - round(q_gold["change_pct"] * 0.95, 2)) < 1e-4

    # Check bond bounding [-0.5, +0.5]
    q_bond = pm.fetch_realtime_fund_quote("000086")
    print(f"  000086 (纯债) gszzl: {q_bond['gszzl']} (严格在 [-0.5%, +0.5%] 区间)")
    assert -0.5 <= q_bond["gszzl"] <= 0.5

    # Check tail fund name
    from multi_ledger_manager import MultiLedgerManager
    mlm = MultiLedgerManager()
    pm29 = mlm.get_pm("combat_29_funds")
    h_tail = pm29.holdings.get("000058") or pm29.holdings.get("000086")
    assert h_tail is not None, "000058/000086 not found in combat_29_funds"
    assert "华夏中小板" in h_tail.fund_name or "工银瑞信" in h_tail.fund_name, f"Tail fund name wrong: {h_tail.fund_name}"
    print(f"  [OK] 尾仓基金名称正确校验为: '{h_tail.fund_name}' ({h_tail.fund_code})")
    print("R2 全部断言通过!\n")

def verify_rebalance_tail():
    print("--- 正在验证 R2: 存量 29 组合碎片尾仓防逆向加仓 ---")
    from multi_ledger_manager import MultiLedgerManager
    from strategy_bridge import StrategyBridge
    mlm = MultiLedgerManager()
    pm29 = mlm.get_pm("combat_29_funds")
    orders = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=pm29.holdings,
        available_cash=pm29.available_cash,
        target_weights_funds={},
        pm=pm29
    )
    items = orders["items"]
    tail_items = [it for it in items if float(it.get("market_value", 0.0)) < 200.0]
    print(f"  共检测到 {len(tail_items)} 只市值 < 200 元的尾仓标的:")
    for it in tail_items:
        fc = it["fund_code"]
        mv = it["market_value"]
        act = it["action"]
        t_w = it["target_weight_pct"]
        diff = it["diff_amount"]
        act_txt = it.get("action_text", "")
        assert t_w == 0.0, f"Tail fund {fc} has non-zero target weight: {t_w}"
        assert act == "SELL", f"Tail fund {fc} action is not SELL: {act}"
        assert diff <= 0.0, f"Tail fund {fc} has positive diff amount: {diff}"
        print(f"    - {fc} ({it.get('fund_name')}): 市值 ¥{mv:.2f}, 目标占比 {t_w:.2f}%, 指令 {act} ({act_txt}), 金额 ¥{diff:.2f}")

    # Check specifically tail fund 000058 / 000086
    it_tail = next((it for it in items if it["fund_code"] in ("000058", "000086")), None)
    assert it_tail is not None, "Tail fund 000058/000086 not found in items"
    assert it_tail["target_weight_pct"] == 0.0
    assert it_tail["action"] == "SELL"
    assert "清仓" in it_tail.get("action_text", "")
    print(f"  [OK] {it_tail['fund_code']} 碎片尾仓锁定清仓归拢，绝无逆向加仓!")
    print("调仓尾仓防加仓断言通过!\n")

def verify_r4():
    print("--- 正在验证 R4: 宏观汇率、美债利率校准与首屏预警哨 ---")
    from advisory_engine import compute_ten_dimension_votes, ActiveRiskSentry
    from multi_ledger_manager import MultiLedgerManager
    votes = compute_ten_dimension_votes()
    dims = votes["dimensions"]

    # Dim 4: US 10Y and spread (④ 国际联动)
    d4 = next(d for d in dims if d.get("dimension_id") == 4 or "国际联动" in d["name"])
    print(f"  第 4 维 (美债利差): {d4['reason']}")
    assert "4.42%" in d4["reason"], f"US 10Y rate is not 4.42%: {d4['reason']}"
    assert "bp" in d4["reason"], f"Spread not in reason: {d4['reason']}"
    assert "5.12%" not in d4["reason"], f"Obsolete 5.12% found: {d4['reason']}"

    # Dim 5: FX (⑤ 外汇锁汇)
    d5 = next(d for d in dims if d.get("dimension_id") == 5 or "外汇锁汇" in d["name"])
    print(f"  第 5 维 (离岸汇率): {d5['reason']}")
    assert "-2.00%" not in d5["reason"] and "-2.07%" not in d5["reason"], f"Error multiplied by 100 found: {d5['reason']}"
    assert "7.2385" in d5["reason"]

    # ActiveRiskSentry 001071 check on combat_29_funds
    mlm = MultiLedgerManager()
    pm29 = mlm.get_pm("combat_29_funds")
    sentry = ActiveRiskSentry()
    report = sentry.inspect_portfolio(pm29.holdings)
    red_001071_alerts = [a for a in report.get("alerts", []) if a.get("fund_code") == "001071" and str(a.get("level")).lower() in ("red", "critical")]
    print(f"  001071 红色报警数量: {len(red_001071_alerts)}")
    assert len(red_001071_alerts) == 0, f"001071 has false red alerts: {red_001071_alerts}"
    print("R4 全部断言通过!\n")

if __name__ == "__main__":
    verify_r1()
    verify_r2()
    verify_rebalance_tail()
    verify_r4()
    print("========================================")
    print("G23 世代 R1-R4 全部交付物核验 100% 成功!")
    print("========================================")
