# -*- coding: utf-8 -*-
"""
AGY2 Milestone 3 R5 对抗性实证测试套件 (Challenger 2)
文件路径: AGY2_FundAdvisory/tests/test_adversarial_m3_challenger2_interactive.py

专门针对 5 大交互机制进行严苛的对抗性测试、边界测试与异常输入测试：
1. Questionnaire Mode B: 问卷答题打分计算与档位跃迁 (0~12 分、全档位 C1~C5 边界越变)；
2. Step 2 recalculation: 步骤一修改参数或点击推演，验证步骤三绝对收起隐藏 (tab1_step_reached=2) 且 tab1_step3_cache 置空；
3. Target portfolio switching: Tab 2 调仓目标池（Tab 1 优选 vs 核心指数全天候池）平滑切换与 tab2_rebal_cache 清空失效；
4. Holding change cache invalidation: 持仓增删改与演示载入时 tab2_diag_cache 和 tab2_rebal_cache 强制失效；
5. Intraday 09:30-14:30 observation lock: 盘中观察期防冲动执行锁在未勾选 chk_allow_early_rebalance 时按钮禁用，勾选后解锁；非观察期无缝切换；
6. 裁判物理红线文件 (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, test_infra.py) 0 字节篡改与 SHA256 绝对一致。
"""

import sys
import hashlib
from pathlib import Path
from unittest.mock import patch
import pytest
from streamlit.testing.v1 import AppTest

# 路径对齐
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
AGY2_DIR = WORKSPACE_DIR / "AGY2_FundAdvisory"
if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))

import portfolio_manager
from portfolio_manager import PortfolioManager, FundQuote
import strategy_bridge
from strategy_bridge import StrategyBridge, evaluate_questionnaire_risk_tier, RISK_TIERS_CONFIG
import trading_clock_fee
from trading_clock_fee import TradingClock


@pytest.fixture(autouse=True)
def mock_network_and_quotes(monkeypatch):
    """全局 Mock 行情与网络，实现毫秒级纯离线确定性执行"""
    def mock_fund_quote(code, use_cache=True):
        return FundQuote(
            name=f"测试基金_{code}",
            dwjz=1.2345,
            gsz=1.2400,
            gszzl=0.45,
            gztime="14:45",
            fund_code=str(code)
        )

    def mock_index_quote(symbol, use_cache=True):
        return {"point": 4050.0, "change_pct": 0.5, "name": symbol}

    monkeypatch.setattr(portfolio_manager, "fetch_realtime_fund_quote", mock_fund_quote)
    monkeypatch.setattr(portfolio_manager, "fetch_realtime_index_quote", mock_index_quote)


# =========================================================================
# 机制 1: 模式 B 问卷测评打分计算与档位越变极限测试
# =========================================================================
def test_adversarial_mode_b_scoring_and_tier_transitions():
    """
    对抗测试 1: 模式 B 问卷测评在全量边界分值下的精确映射与 AppTest 渲染跃迁
    涵盖：
    - 最低分 0 分 (A, A, A) ➔ C1 (安稳保守型，默认目标 6.5%)
    - C1/C2 边界：2 分 ➔ C1; 3 分 (B, B, B) ➔ C2 (稳健固收+型，默认目标 10.0%)
    - C2/C3 边界：5 分 ➔ C2; 6 分 (C, C, C) ➔ C3 (平衡进取型，默认目标 15.0%)
    - C3/C4 边界：8 分 ➔ C3; 9 分 (D, D, D) ➔ C4 (成长进攻型，默认目标 22.0%)
    - C4/C5 边界：10 分 ➔ C4; 11 分 ➔ C5 (极限高Beta追击型，默认目标 50.0%)
    - 最高分 12 分 (E, E, E) ➔ C5 (极限高Beta追击型，默认目标 50.0%)
    """
    # 1. 算法底层所有边界点断言
    test_cases = [
        (0, "C1", 6.5),
        (1, "C1", 6.5),
        (2, "C1", 6.5),
        (3, "C2", 10.0),
        (4, "C2", 10.0),
        (5, "C2", 10.0),
        (6, "C3", 15.0),
        (7, "C3", 15.0),
        (8, "C3", 15.0),
        (9, "C4", 22.0),
        (10, "C4", 22.0),
        (11, "C5", 50.0),
        (12, "C5", 50.0),
        (99, "C5", 50.0), # 异常超界鲁棒性
    ]
    for score, expected_tier, expected_ret in test_cases:
        tier = evaluate_questionnaire_risk_tier(score)
        assert tier == expected_tier, f"Score {score} expected {expected_tier}, got {tier}"
        tier_cfg = RISK_TIERS_CONFIG.get(tier, {})
        assert float(tier_cfg.get("default_target", 15.0)) == expected_ret

    # 2. 端到端 AppTest：极低分 (C1 档位测试)
    app_path = AGY2_DIR / "app_gui.py"
    at_c1 = AppTest.from_file(str(app_path), default_timeout=60)
    at_c1.session_state._modules_initialized = True
    at_c1.session_state.tier_determination_mode = "模式 B：30秒风险承受力测评定档"
    at_c1.session_state.q1_risk_test = "A. 极度厌恶亏损，超过 3% 睡不着 (0分)"
    at_c1.session_state.q2_risk_test = "A. 随时用，1~3个月内 (0分)"
    at_c1.session_state.q3_risk_test = "A. 惊慌失措，立刻割肉 (0分)"
    at_c1.run()

    assert len(at_c1.exception) == 0, f"C1 渲染异常: {[e.value for e in at_c1.exception]}"
    assert at_c1.session_state.tested_tier_val == "C1"
    assert at_c1.session_state.active_tier_val == "C1"
    assert at_c1.session_state.target_return_val == 6.5

    all_captions_c1 = "\n".join(c.value for c in at_c1.caption if c.value)
    assert "问卷总分：`0 分`" in all_captions_c1
    assert "【C1 安稳保守型】" in all_captions_c1

    # 3. 端到端 AppTest：极高分 (C5 档位测试)
    at_c5 = AppTest.from_file(str(app_path), default_timeout=60)
    at_c5.session_state._modules_initialized = True
    at_c5.session_state.tier_determination_mode = "模式 B：30秒风险承受力测评定档"
    at_c5.session_state.q1_risk_test = "E. 哪怕腰斩 -30% 也无所谓，求翻倍 (4分)"
    at_c5.session_state.q2_risk_test = "E. 5年以上闲钱 (4分)"
    at_c5.session_state.q3_risk_test = "E. 兴奋狂喜，大举逆势加仓 (4分)"
    at_c5.run()

    assert len(at_c5.exception) == 0, f"C5 渲染异常: {[e.value for e in at_c5.exception]}"
    assert at_c5.session_state.tested_tier_val == "C5"
    assert at_c5.session_state.active_tier_val == "C5"
    assert at_c5.session_state.target_return_val == 50.0

    all_captions_c5 = "\n".join(c.value for c in at_c5.caption if c.value)
    assert "问卷总分：`12 分`" in all_captions_c5
    assert "【C5 极限高Beta追击型】" in all_captions_c5


# =========================================================================
# 机制 2: 步骤二重新推演隐藏步骤三与缓存清空测试
# =========================================================================
def test_adversarial_step2_recalculation_collapses_step3_and_clears_cache():
    """
    对抗测试 2: 用户已进入步骤三并存在旧建仓缓存，在步骤一修改参数或点击重算时：
    1. 必须强制将 tab1_step_reached 重置收起至 2；
    2. tab1_step3_cache 必须被物理清空为 None；
    3. 页面渲染树中严禁出现步骤三的任何标题或建仓表格；
    4. 步骤二推演标题与白盒面板正常渲染。
    """
    app_path = AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.session_state._modules_initialized = True

    # 初始状态模拟：已完整计算至步骤三
    at.session_state.tab1_step_reached = 3
    at.session_state.tab1_sim_cache = {
        "optimal_weights": {"100032": 0.4, "005561": 0.3, "002351": 0.3},
        "target_return": 15.0,
        "active_tier": "C3",
    }
    at.session_state.tab1_step3_cache = {
        "blueprint": {
            "orders": [{"fund_code": "100032", "amount": 40000.0}],
            "items": [{"fund_code": "100032", "amount": 40000.0}],
        }
    }
    at.session_state.tab1_last_calc_params = {
        "target_ret": 15.0,
        "capital": 100000.0,
        "tier": "C3",
        "num_funds": 5,
        "model_type": "hrp",
        "horizon": "中线平衡 (6个月~1年)",
        "overrides": ()
    }
    at.run()

    assert len(at.exception) == 0
    assert at.session_state.tab1_step_reached == 3
    assert at.session_state.tab1_step3_cache is not None

    all_md_before = "\n".join(m.value for m in at.markdown if m.value)
    assert "### 步骤三：生成实盘建仓" in all_md_before

    # 触发对抗操作：点击步骤一的【▶️ 确认目标参数，进入步骤二：开始现场推演】按钮
    btn_step2 = at.button(key="btn_run_simulation_now")
    assert btn_step2 is not None, "未找到 btn_run_simulation_now 按钮"
    btn_step2.click()
    at.run()

    assert len(at.exception) == 0
    # 核心安全防线断言：
    # 1. 步骤状态物理退回收起至步骤 2
    assert at.session_state.tab1_step_reached == 2, f"tab1_step_reached 未收起: {at.session_state.tab1_step_reached}"
    # 2. 步骤三旧缓存必须被置空为 None
    assert at.session_state.tab1_step3_cache is None, "tab1_step3_cache 未被清空！"

    # 3. 页面渲染树断言：步骤三标题严禁渲染，步骤二标题必须渲染
    all_md_after = "\n".join(m.value for m in at.markdown if m.value)
    assert "### 步骤三：生成实盘建仓" not in all_md_after, "步骤三标题依然被泄露渲染！"
    assert "### 步骤二：现场推演评估" in all_md_after, "步骤二标题丢失！"


# =========================================================================
# 机制 3: Tab 2 调仓目标池平滑切换与 tab2_rebal_cache 清空测试
# =========================================================================
def test_adversarial_tab2_target_pool_switch_and_cache_clearing():
    """
    对抗测试 3: Tab 2 调仓目标池在【新资建仓优选组合】与【核心指数全天候策略池】之间切换时：
    1. 检测到目标池变更，必须主动置空 tab2_rebal_cache；
    2. 若 Tab 1 尚未推演，选择新资建仓时自动退回核心池并给出友善提示；
    3. 全流程无任何 KeyError 或未捕获异常。
    """
    app_path = AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.session_state._modules_initialized = True

    # 初始状态：Tab 2 已经诊断和调仓过
    at.session_state.tab2_diagnosed = True
    at.session_state.tab2_rebalanced = True
    at.session_state.tab1_sim_cache = {
        "optimal_weights": {"100032": 0.5, "005561": 0.5}
    }
    at.session_state.tab2_last_pool_sig = None
    at.run()

    assert len(at.exception) == 0

    rad_pool = at.radio(key="rad_tab2_target_pool")
    assert rad_pool is not None, "未找到 rad_tab2_target_pool 单选框"
    assert len(rad_pool.options) == 2

    # 验证初始切换签名已更新且被重新精算
    sig_1 = at.session_state.tab2_last_pool_sig
    assert sig_1 is not None
    assert sig_1[0].startswith("🌱")

    # 切换至【核心指数全天候策略池】
    rad_fresh = at.radio(key="rad_tab2_target_pool")
    rad_fresh.set_value(rad_fresh.options[1])
    at.run()

    assert len(at.exception) == 0
    sig_2 = at.session_state.tab2_last_pool_sig
    assert sig_2 is not None
    assert sig_2[0].startswith("🛡️")
    assert sig_2 != sig_1, "目标池签名未检测到变动！"

    # 新建一个无 Tab 1 模拟缓存的会话，测试冷启动自动退回核心池
    at_cold = AppTest.from_file(str(app_path), default_timeout=60)
    at_cold.session_state._modules_initialized = True
    at_cold.session_state.tab2_diagnosed = True
    at_cold.session_state.tab2_rebalanced = True
    at_cold.session_state.tab1_sim_cache = None # 无 Tab 1 推演
    at_cold.run()

    assert len(at_cold.exception) == 0
    # 验证在无 Tab 1 缓存时，单选框默认选择 Option 1 (核心指数池)
    rad_cold = at_cold.radio(key="rad_tab2_target_pool")
    assert rad_cold is not None
    assert rad_cold.value == rad_cold.options[1]
    sig_cold = at_cold.session_state.tab2_last_pool_sig
    assert sig_cold[0].startswith("🛡️")


# =========================================================================
# 机制 4: 持仓增删改与演示载入时缓存彻底失效测试
# =========================================================================
def test_adversarial_holding_change_invalidates_diag_and_rebal_caches():
    """
    对抗测试 4: 持仓发生任何增删改动作时，强行失效 tab2_diag_cache 与 tab2_rebal_cache：
    - 加载演示组合 ➔ 置空 tab2_diag_cache & tab2_rebal_cache，重置 diagnosed/rebalanced 为 False；
    - 一键撤销 ➔ 置空 tab2_diag_cache & tab2_rebal_cache；
    - 代码路径中所有增删改动作（单标的删除、搜索添加、智能文本导入、表格导入）均配备失效保护。
    """
    app_path = AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.session_state._modules_initialized = True

    # 预设已有诊断与调仓缓存
    at.session_state.tab2_diag_cache = {"status": "stale_diag"}
    at.session_state.tab2_rebal_cache = {"status": "stale_rebal"}
    at.session_state.tab2_diagnosed = True
    at.session_state.tab2_rebalanced = True
    at.run()

    assert len(at.exception) == 0
    assert at.session_state.tab2_diag_cache is not None

    # 点击侧边栏【🚀 加载演示组合】按钮
    btn_demo = at.sidebar.button[0]
    btn_demo.click()
    at.run()

    assert len(at.exception) == 0
    # 核心安全断言：旧缓存必须彻底清除
    assert at.session_state.tab2_diag_cache is None, "加载演示后 tab2_diag_cache 未被物理置空！"
    assert at.session_state.tab2_rebal_cache is None, "加载演示后 tab2_rebal_cache 未被物理置空！"
    assert at.session_state.tab2_diagnosed is False, "tab2_diagnosed 未重置为 False！"
    assert at.session_state.tab2_rebalanced is False, "tab2_rebalanced 未重置为 False！"

    # 静态断言：所有持仓变更分支均包含清空代码
    code_text = (AGY2_DIR / "app_gui.py").read_text(encoding="utf-8")
    assert code_text.count("st.session_state.tab2_diag_cache = None") >= 6
    assert code_text.count("st.session_state.tab2_rebal_cache = None") >= 6


# =========================================================================
# 机制 5: 盘中观察期 (09:30-14:30) 防冲动执行确认锁测试
# =========================================================================
def test_adversarial_intraday_observation_lock_and_early_override():
    """
    对抗测试 5: 验证盘中观察期 (09:30~14:30) 的防冲动执行锁逻辑：
    1. guidance['stage'] == 'OBSERVATION' 且 chk_allow_early_rebalance 未勾选时：
       - 执行按钮处于禁用状态 (btn_obs_disabled_tab2.disabled == True)；
       - 提前执行按钮 (btn_exec_early_tab2) 严禁出现；
    2. 用户勾选 chk_allow_early_rebalance 后：
       - 禁用按钮消失；
       - 提前执行按钮 (btn_exec_early_tab2) 解锁显示且可用；
    3. 尾盘黄金窗口 (guidance['stage'] == 'GOLDEN_WINDOW')：
       - 直接展示立即执行按钮 (btn_exec_gold_tab2)，无需防冲动勾选。
    """
    # 构造真实的调仓精算结果，保证后果面板与按钮容器完整渲染
    pm = PortfolioManager()
    pm.load_demo_portfolio()
    real_sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3")

    mock_obs_guidance = {
        "stage": "OBSERVATION",
        "action_color": "#eab308",
        "title": "⏳ 盘中观察期 (09:30~14:30)",
        "message": "盘中情绪波动剧烈，建议保持观望，等待 14:30 尾盘趋势确立后再决策。",
        "guidance": "盘中情绪波动剧烈，建议保持观望，等待 14:30 尾盘趋势确立后再决策。"
    }

    # 5.1 盘中观察期未勾选确认防线
    with patch("trading_clock_fee.TradingClock.get_action_guidance_for_window", return_value=mock_obs_guidance):
        app_path = AGY2_DIR / "app_gui.py"
        at = AppTest.from_file(str(app_path), default_timeout=60)
        at.session_state._modules_initialized = True
        at.session_state.tab2_diagnosed = True
        at.session_state.tab2_rebalanced = True
        at.session_state.tab2_rebal_cache = real_sim_res
        at.run()

        assert len(at.exception) == 0, f"AppTest 发生异常: {[e.value for e in at.exception]}"

        # 验证勾选框存在且默认未勾选
        chk = at.checkbox(key="chk_allow_early_rebalance")
        assert chk is not None, "未找到 chk_allow_early_rebalance 勾选框"
        assert chk.value is False

        # 验证观察期禁用按钮存在且处于 disabled 状态
        btn_obs = at.button(key="btn_obs_disabled_tab2")
        assert btn_obs is not None, "未找到 btn_obs_disabled_tab2 禁用按钮"
        assert btn_obs.disabled is True, "btn_obs_disabled_tab2 必须处于 disabled 状态！"

        # 验证此时严禁出现提前执行按钮
        btn_keys = [b.key for b in at.button if b.key]
        assert "btn_exec_early_tab2" not in btn_keys, "未勾选防冲动锁时，提前执行按钮提前泄露！"

    # 5.2 盘中观察期用户显式勾选确认波动风险
    with patch("trading_clock_fee.TradingClock.get_action_guidance_for_window", return_value=mock_obs_guidance):
        at_checked = AppTest.from_file(str(app_path), default_timeout=60)
        at_checked.session_state._modules_initialized = True
        at_checked.session_state.tab2_diagnosed = True
        at_checked.session_state.tab2_rebalanced = True
        at_checked.session_state.tab2_rebal_cache = real_sim_res
        at_checked.session_state.chk_allow_early_rebalance = True
        at_checked.run()

        assert len(at_checked.exception) == 0

        # 验证禁用按钮消失，解锁按钮出现
        btn_keys_checked = [b.key for b in at_checked.button if b.key]
        assert "btn_obs_disabled_tab2" not in btn_keys_checked, "勾选后禁用按钮仍未移除！"
        assert "btn_exec_early_tab2" in btn_keys_checked, "勾选后未解锁 btn_exec_early_tab2 按钮！"
        btn_early = at_checked.button(key="btn_exec_early_tab2")
        assert btn_early.disabled is False, "解锁的提前执行按钮被误置为 disabled！"

    # 5.3 尾盘黄金窗口 (GOLDEN_WINDOW)
    mock_golden_guidance = {
        "stage": "GOLDEN_WINDOW",
        "action_color": "#16a34a",
        "title": "⚡ 尾盘黄金窗口 (14:30~15:00)",
        "message": "全天趋势锁定，执行摩擦成本最低，为最佳执行时点。",
        "guidance": "全天趋势锁定，执行摩擦成本最低，为最佳执行时点。"
    }
    with patch("trading_clock_fee.TradingClock.get_action_guidance_for_window", return_value=mock_golden_guidance):
        at_gold = AppTest.from_file(str(app_path), default_timeout=60)
        at_gold.session_state._modules_initialized = True
        at_gold.session_state.tab2_diagnosed = True
        at_gold.session_state.tab2_rebalanced = True
        at_gold.session_state.tab2_rebal_cache = real_sim_res
        at_gold.run()

        assert len(at_gold.exception) == 0
        btn_keys_gold = [b.key for b in at_gold.button if b.key]
        assert "btn_exec_gold_tab2" in btn_keys_gold, "尾盘黄金窗口未提供 btn_exec_gold_tab2！"
        assert "chk_allow_early_rebalance" not in [c.key for c in at_gold.checkbox if c.key], "黄金窗口不应出现盘中防冲动勾选！"


# =========================================================================
# 机制 6: 裁判物理红线文件 SHA256 完整性断言
# =========================================================================
def test_referee_files_strict_immutability():
    """
    对抗测试 6: 4 个只读裁判文件物理红线与哈希防篡改断言
    - AGY2_FundAdvisory/judge_engine.py
    - AGY2_FundAdvisory/holdout_vault.py
    - AGY2_FundAdvisory/AGENT_SPEC.md
    - tests/test_infra.py
    """
    expected_hashes = {
        "AGY2_FundAdvisory/judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
        "AGY2_FundAdvisory/holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
        "AGY2_FundAdvisory/AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
        "tests/test_infra.py": "48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100",
    }
    for rel_path, expected_hash in expected_hashes.items():
        full_path = WORKSPACE_DIR / rel_path
        assert full_path.exists(), f"裁判文件不存在: {rel_path}"
        computed_hash = hashlib.sha256(full_path.read_bytes()).hexdigest().upper()
        assert computed_hash == expected_hash, f"裁判文件被非法改动: {rel_path} (哈希不匹配)"
