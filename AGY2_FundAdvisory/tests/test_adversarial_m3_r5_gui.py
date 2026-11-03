# -*- coding: utf-8 -*-
"""
R5 GUI 交互、信噪比/动量加速度呈现与五大交互防线全覆盖对抗测试套件
(test_adversarial_m3_r5_gui.py)
"""

import sys
import hashlib
from pathlib import Path
from unittest.mock import patch
import pytest
from streamlit.testing.v1 import AppTest

_WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
_AGY2_DIR = _WORKSPACE_DIR / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))

import portfolio_manager
from portfolio_manager import PortfolioManager, FundQuote
import strategy_bridge
from strategy_bridge import StrategyBridge, evaluate_questionnaire_risk_tier


@pytest.fixture(autouse=True)
def mock_network_and_quotes(monkeypatch):
    """全局 Mock 行情与网络接口，实现毫秒级纯离线确定性测试"""
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


def test_r5_gui_normal_values_rendering():
    """
    对抗场景 1: 常规快照数值 (er_snr=0.75, mom_accel=+1.8%, effective_window=30, exhaustion=False)
    - 顶部看板卡片 2 准确渲染信噪比与动量加速度字符串及 Tooltip
    - 步骤二白盒面板卡片 2 准确渲染信噪比、自适应变速窗口与动量加速度
    - 衰竭预警徽章绝不渲染
    """
    real_snap = StrategyBridge.get_latest_market_snapshot()
    mock_snap = real_snap.copy()
    mock_snap["er_snr"] = 0.75
    mock_snap["mom_accel"] = 1.8
    mock_snap["effective_momentum_window"] = 30
    mock_snap["momentum_exhaustion_warning"] = False
    mock_snap["momentum_exhaustion_text"] = ""

    with patch("strategy_bridge.StrategyBridge.get_latest_market_snapshot", return_value=mock_snap):
        app_path = _AGY2_DIR / "app_gui.py"
        at = AppTest.from_file(str(app_path), default_timeout=60)
        at.session_state._modules_initialized = True
        at.session_state.tab1_step_reached = 2
        at.session_state.tab1_sim_cache = {
            "optimal_weights": {"100032": 0.4, "005561": 0.3, "002351": 0.3},
            "target_return": 15.0,
            "active_tier": "C3",
        }
        at.run()

        assert len(at.exception) == 0, f"AppTest 发生异常: {[e.value for e in at.exception]}"

        all_md = "\n".join(m.value for m in at.markdown if m.value)

        # 1. 顶部看板卡片 2 呈现校验
        assert "🧭 市场定调与攻防线" in all_md, "top_c2 核心标题丢失"
        assert "📡信噪比 ER: 0.75 ｜ ⚡动量加速度: +1.8%" in all_md, "top_c2 信噪比与动量加速度格式不符"
        assert "考夫曼信噪比(ER): 0.75 (自适应窗口 30日)\n动量加速度: +1.80%" in all_md, "top_c2 Tooltip 丢失"
        assert "📈破" in all_md and "🛡️跌" in all_md, "top_c2 攻防点位丢失"

        # 2. 步骤二白盒面板卡片 2 呈现校验
        assert "② 均线动量状态 (MA20)" in all_md, "c_sig2 均线动量状态标题丢失"
        assert "考夫曼信噪比 (ER / SNR): <b>0.75</b> (自适应变速窗口: 30日)" in all_md, "c_sig2 信噪比或变速窗口丢失"
        assert "动量加速度 (Mom Accel): <b>+1.80%</b>" in all_md, "c_sig2 动量加速度格式不符"

        # 3. 衰竭预警徽章必须未渲染
        warn_text = "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"
        assert warn_text not in all_md, "正常行情下不应渲染衰竭预警文案"


def test_r5_gui_exhaustion_warning_active_with_minus_3_2():
    """
    对抗场景 2: 动量衰竭预警激活 (momentum_exhaustion_warning=True, mom_accel=-3.2%, er_snr=0.85, effective_window=26)
    - 顶部看板卡片 2 渲染预警徽章 「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」
    - 步骤二白盒面板卡片 2 渲染预警文案块与负动量加速度
    - 准确显示 -3.2% 负加速度与信噪比
    """
    real_snap = StrategyBridge.get_latest_market_snapshot()
    mock_snap = real_snap.copy()
    mock_snap["momentum_exhaustion_warning"] = True
    mock_snap["mom_accel"] = -3.2
    mock_snap["er_snr"] = 0.85
    mock_snap["effective_momentum_window"] = 26
    mock_snap["momentum_exhaustion_text"] = "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"

    with patch("strategy_bridge.StrategyBridge.get_latest_market_snapshot", return_value=mock_snap):
        app_path = _AGY2_DIR / "app_gui.py"
        at = AppTest.from_file(str(app_path), default_timeout=60)
        at.session_state._modules_initialized = True
        at.session_state.tab1_step_reached = 2
        at.session_state.tab1_sim_cache = {
            "optimal_weights": {"100032": 0.4, "005561": 0.3, "002351": 0.3},
            "target_return": 15.0,
            "active_tier": "C3",
        }
        at.run()

        assert len(at.exception) == 0, f"AppTest 发生异常: {[e.value for e in at.exception]}"

        all_md = "\n".join(m.value for m in at.markdown if m.value)

        warn_text = "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"
        # 断言预警文案必须在页面中被渲染呈现
        assert warn_text in all_md, "衰竭预警被激活时，未能找到警示文案"
        # 顶部卡片应显示数值
        assert "📡信噪比 ER: 0.85 ｜ ⚡动量加速度: -3.2%" in all_md, "top_c2 负加速度与信噪比未正确渲染"
        # 白盒卡片应显示数值
        assert "考夫曼信噪比 (ER / SNR): <b>0.85</b> (自适应变速窗口: 26日)" in all_md, "c_sig2 白盒卡片信噪比未正确呈现"
        assert "动量加速度 (Mom Accel): <b>-3.20%</b>" in all_md, "c_sig2 动量加速度 -3.20% 未呈现"


def test_r5_gui_cold_start_missing_keys_fallback():
    """
    对抗场景 3: 缺少 R1/R2 指标键的冷启动 / 最小化快照 (缺少 er_snr, mom_accel, effective_momentum_window 等)
    - 验证鲁棒安全兜底：默认 SNR=0.65, 动量加速度=0.0%, 自适应窗口=60日
    - 绝不触发 KeyError / TypeError / NoneType 异常
    - 页面正常渲染且衰竭预警不呈现
    """
    real_snap = StrategyBridge.get_latest_market_snapshot()
    mock_snap = real_snap.copy()
    # 彻底剥离所有 R1/R2 新增指标字段，模拟冷启动或遗留数据源
    for key in [
        "er_snr",
        "mom_accel",
        "mom_accel_star",
        "effective_momentum_window",
        "effective_window",
        "momentum_exhaustion_warning",
        "momentum_exhaustion_text"
    ]:
        mock_snap.pop(key, None)

    with patch("strategy_bridge.StrategyBridge.get_latest_market_snapshot", return_value=mock_snap):
        app_path = _AGY2_DIR / "app_gui.py"
        at = AppTest.from_file(str(app_path), default_timeout=60)
        at.session_state._modules_initialized = True
        at.session_state.tab1_step_reached = 2
        at.session_state.tab1_sim_cache = {
            "optimal_weights": {"100032": 0.4, "005561": 0.3, "002351": 0.3},
            "target_return": 15.0,
            "active_tier": "C3",
        }
        at.run()

        # 核心断言: 0 异常
        assert len(at.exception) == 0, f"冷启动缺少指标键时 AppTest 抛出异常: {[e.value for e in at.exception]}"

        all_md = "\n".join(m.value for m in at.markdown if m.value)

        # 验证兜底默认值呈现: ER=0.65, 加速度=+0.0%, 窗口=60日
        assert "📡信噪比 ER: 0.65 ｜ ⚡动量加速度: +0.0%" in all_md, "top_c2 冷启动默认值兜底失败"
        assert "考夫曼信噪比(ER): 0.65 (自适应窗口 60日)\n动量加速度: +0.00%" in all_md, "top_c2 Tooltip 兜底失败"
        assert "考夫曼信噪比 (ER / SNR): <b>0.65</b> (自适应变速窗口: 60日)" in all_md, "c_sig2 冷启动信噪比/窗口兜底失败"
        assert "动量加速度 (Mom Accel): <b>+0.00%</b>" in all_md, "c_sig2 冷启动动量加速度兜底失败"

        # 衰竭预警绝不触发
        warn_text = "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"
        assert warn_text not in all_md, "冷启动状态下不应错误触发衰竭预警"


def test_r5_gui_exhaustion_warning_missing_text_fallback():
    """
    对抗场景 4: 预警标志激活 (momentum_exhaustion_warning=True) 但文案为空或未提供
    - 验证文本兜底机制: 自动退化为默认文案「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」
    - 页面不崩溃且警报徽章完整渲染
    """
    real_snap = StrategyBridge.get_latest_market_snapshot()
    mock_snap = real_snap.copy()
    mock_snap["momentum_exhaustion_warning"] = True
    mock_snap["momentum_exhaustion_text"] = None  # 缺失或为空
    mock_snap["er_snr"] = 0.88
    mock_snap["mom_accel"] = -2.8
    mock_snap["effective_momentum_window"] = 25

    with patch("strategy_bridge.StrategyBridge.get_latest_market_snapshot", return_value=mock_snap):
        app_path = _AGY2_DIR / "app_gui.py"
        at = AppTest.from_file(str(app_path), default_timeout=60)
        at.session_state._modules_initialized = True
        at.session_state.tab1_step_reached = 2
        at.session_state.tab1_sim_cache = {
            "optimal_weights": {"100032": 0.4, "005561": 0.3, "002351": 0.3},
            "target_return": 15.0,
            "active_tier": "C3",
        }
        at.run()

        assert len(at.exception) == 0, f"AppTest 发生异常: {[e.value for e in at.exception]}"

        all_md = "\n".join(m.value for m in at.markdown if m.value)

        default_warn = "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"
        assert default_warn in all_md, "当 momentum_exhaustion_text 为 None 时未能安全退化为默认预警文案"
        assert "📡信噪比 ER: 0.88 ｜ ⚡动量加速度: -2.8%" in all_md
        assert "考夫曼信噪比 (ER / SNR): <b>0.88</b> (自适应变速窗口: 25日)" in all_md


def test_r5_gui_five_interaction_mechanisms_and_referee_integrity():
    """
    对抗场景 5: 验证 5 大交互防线机制与 4 个裁判文件物理红线完整性
    """
    # 机制 1: 问卷定档算法 3 题计算覆盖 (0~12 分)
    assert evaluate_questionnaire_risk_tier(1) == "C1"
    assert evaluate_questionnaire_risk_tier(4) == "C2"
    assert evaluate_questionnaire_risk_tier(7) == "C3"
    assert evaluate_questionnaire_risk_tier(9) == "C4"
    assert evaluate_questionnaire_risk_tier(12) == "C5"

    # 机制 2: 步骤一重算折叠步骤三与备选切换刷新代码路径静态断言
    gui_code = (_AGY2_DIR / "app_gui.py").read_text(encoding="utf-8")
    assert "st.session_state.tab1_step_reached = 2" in gui_code
    assert "st.session_state.tab1_step3_cache = None" in gui_code
    assert "st.session_state.tab1_trigger_sim = True" in gui_code

    # 机制 3: Tab 2 目标池切换与持仓变动缓存失效静态断言
    assert "st.session_state.tab2_rebal_cache = None" in gui_code
    assert "rad_tab2_target_pool" in gui_code
    assert "tab2_diag_cache = None" in gui_code

    # 机制 4: 盘中观察期防冲动执行确认勾选锁静态断言
    assert "chk_allow_early_rebalance" in gui_code
    assert "btn_obs_disabled_tab2" in gui_code
    assert "btn_exec_early_tab2" in gui_code

    # 机制 5: 4 个只读裁判文件物理红线与哈希防篡改断言
    expected_hashes = {
        "AGY2_FundAdvisory/judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
        "AGY2_FundAdvisory/holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
        "AGY2_FundAdvisory/AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
        "tests/test_infra.py": "48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100",
    }
    for rel_path, expected_hash in expected_hashes.items():
        full_path = _WORKSPACE_DIR / rel_path
        assert full_path.exists(), f"裁判文件不存在: {rel_path}"
        computed_hash = hashlib.sha256(full_path.read_bytes()).hexdigest().upper()
        assert computed_hash == expected_hash, f"裁判文件被非法改动: {rel_path} (哈希不匹配)"
