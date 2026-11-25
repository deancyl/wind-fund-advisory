import hashlib
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

def check_sha256(rel_path: str, expected_sha: str):
    f_path = WORKSPACE_ROOT / rel_path
    assert f_path.exists(), f"文件不存在: {rel_path}"
    actual_sha = hashlib.sha256(f_path.read_bytes()).hexdigest()
    assert actual_sha == expected_sha, f"SHA256 篡改红线违背! {rel_path} 实际: {actual_sha}, 期望: {expected_sha}"
    print(f"🔒 SHA256 严格一致: {rel_path}")

def check_string_in_file(rel_path: str, search_str: str):
    f_path = WORKSPACE_ROOT / rel_path
    text = f_path.read_text(encoding="utf-8")
    assert search_str in text, f"文件 {rel_path} 缺少关键契约字符串: {search_str}"
    print(f"✅ 关键契约存在: {search_str[:40]}...")

def main():
    print("=== G7 核心安全底线与接口契约校验 ===")
    
    # 1. 物理安全红线校验 (四大只读裁判文件)
    check_sha256("AGY2_FundAdvisory/judge_engine.py", "76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be")
    check_sha256("AGY2_FundAdvisory/holdout_vault.py", "88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a")
    check_sha256("AGY2_FundAdvisory/AGENT_SPEC.md", "a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957")
    check_sha256("tests/test_infra.py", "48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100")

    # 2. app_gui.py 关键字符串与测试契约
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", "<b>{len(pm.holdings)} 只</b>")
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", 'if "edited_table" in locals() and edited_table is not None:')
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", "btn_sentry_act_")
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", "btn_sentry_evid_")
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", "rad_tab2_view_mode")
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", "tab4_highlight_module")
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", "dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6")
    check_string_in_file("AGY2_FundAdvisory/app_gui.py", "sub_tab1, sub_tab2, sub_tab3")

    # 3. advisory_engine.py 算子契约
    check_string_in_file("AGY2_FundAdvisory/advisory_engine.py", "class OnlineHeuristicFactorEvolver:")
    check_string_in_file("AGY2_FundAdvisory/advisory_engine.py", "get_60d_rolling_nav_and_trajectory")
    check_string_in_file("AGY2_FundAdvisory/advisory_engine.py", "find_same_company_conversions")
    check_string_in_file("AGY2_FundAdvisory/advisory_engine.py", "evaluate_macro_dividend_policy")

    # 4. strategy_bridge.py 下沉方法导出契约
    check_string_in_file("AGY2_FundAdvisory/strategy_bridge.py", "find_same_company_conversions = StrategyBridge.find_same_company_conversions")
    check_string_in_file("AGY2_FundAdvisory/strategy_bridge.py", "evaluate_macro_dividend_policy = StrategyBridge.evaluate_macro_dividend_policy")

    print("🎉 ALL INVARIANTS PASS! 四大裁判文件 100% 原始未改，所有静态与动态契约严格达标！")

if __name__ == "__main__":
    main()
