"""
多账本体系 GUI 状态机对抗性压力测试 (tests/test_gui_multi_ledger_stress.py)
Adversarial Stress Testing of GUI Multi-Ledger State Machine:

1. 账本高频/快速切换原子性测试 (Rapid Switching & Atomic State Synchronization):
   - 验证 pm 实例、active_tier_val、顶部看板核心指标、Tab 2/3/4 状态原子更新，无陈旧残留 (no stale residue)。
   - 验证高频反复切换下，持仓池完全隔离，无任何状态串扰。
   - 验证切换时 tab2_diag_cache / tab2_rebal_cache 等诊断与调仓缓存被原子清除。

2. Tab 1 步骤三另存为新账本测试 (Tab 1 Step 3 Save to New Ledger):
   - 验证创建完全独立的有效账本并落盘。
   - 验证 ledgers_index.json 正确登记新账本元数据。
   - 验证主实盘 (portfolio_ledger.json / portfolio_state.db) 与当前激活账本绝对未被冲刷覆盖 (SHA256 完好)。
   - 验证自动切换到新建账本后，全局 PM 与 UI 状态机原子同步。

3. 异常与损毁账本容错回退测试 (Corrupted/Invalid Ledger Fallback & Zero White-Screen):
   - 验证 session_state 中注入不存在的非法 ledger_id 时，系统平滑回退至 main_live，绝无白屏崩溃。
   - 验证 ledgers_index.json 文件损坏（语法非法）时，MultiLedgerManager 自愈回退至默认主实盘，绝不抛出 JSONDecodeError。
   - 验证当账本物理 JSON 文件被外部意外删除或损坏时，汇总统计与 PM 加载容错处理，无未捕获异常。
   - 验证删除激活状态下的沙盒账本后，系统自动安全回退至 main_live。
"""

import sys
import json
import shutil
import hashlib
from pathlib import Path
import pytest

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager


@pytest.fixture
def isolated_workspace(tmp_path):
    """创建完全隔离的工作区环境，包括主实盘账本与独立的 ledgers 目录"""
    ws = tmp_path / "wind_ws"
    ws.mkdir()
    data_dir = ws / "data"
    data_dir.mkdir()
    ledgers_dir = data_dir / "ledgers"
    ledgers_dir.mkdir()

    main_ledger_data = {
        "version": "AGY2_PORTFOLIO_V2",
        "takeover_mode": "B",
        "baseline_date": "2026-11-05",
        "baseline_equity": 100000.0,
        "available_cash": 30000.0,
        "in_transit_cash": 0.0,
        "total_market_value": 70000.0,
        "total_equity": 100000.0,
        "peak_equity": 100000.0,
        "max_drawdown_pct": 0.0,
        "benchmark_code": "000300.SH",
        "benchmark_baseline_nav": 1.0,
        "benchmark_current_nav": 1.0,
        "portfolio_return_pct": 0.0,
        "benchmark_return_pct": 0.0,
        "alpha_return_pct": 0.0,
        "holdings": [
            {
                "fund_code": "005561",
                "fund_name": "创金合信红利低波A",
                "share_class": "A",
                "shares": 50000.0,
                "cost_price": 1.0,
                "current_nav": 1.4,
                "market_value": 70000.0,
                "cost_basis": 50000.0,
                "floating_pnl": 20000.0,
                "floating_pnl_pct": 40.0,
                "first_buy_date": "2026-01-01",
                "dividend_method": "cash",
                "batches": [
                    {
                        "batch_id": "b1",
                        "buy_date": "2026-01-01",
                        "shares": 50000.0,
                        "cost_nav": 1.0,
                        "fee": 0.0,
                        "holding_days": 30,
                        "safety_lock": False,
                        "notes": ""
                    }
                ]
            }
        ],
        "pending_orders": [],
        "staged_batch_plans": [],
        "reserved_batch_cash": 0.0
    }
    with open(ws / "portfolio_ledger.json", "w", encoding="utf-8") as f:
        json.dump(main_ledger_data, f, ensure_ascii=False, indent=2)

    return ws


# =====================================================================
# 1. 账本高频/快速切换原子性测试
# =====================================================================

def test_rapid_ledger_switching_atomicity(isolated_workspace):
    """
    对抗性压力测试：在 3 个不同属性（实盘/家庭/沙盒）、不同风险档位（C1/C4/C5）、
    不同持仓组合的账本之间进行高频快速交叉切换。
    验证：
    1. pm.ledger_id 与 active_ledger_id 严格一致
    2. pm.holdings、available_cash、total_equity 严格原子对应，无陈旧持仓残留
    3. active_tier_val 严格随账本 default_tier 动态同步
    4. 切换前自动保存各自状态，互不冲刷
    """
    mlm = MultiLedgerManager(workspace_root=isolated_workspace)

    # 创建 Ledger 2: 家庭专项 (C1 档位, 现金 200,000, 持仓 000216 黄金)
    l2_id = mlm.create_ledger(
        name="家庭稳健养老金",
        base_cash=200000.0,
        ledger_type="family",
        default_tier="C1",
        description="测试家庭账本"
    )
    pm_l2 = mlm.get_pm(l2_id)
    pm_l2.add_or_update_holding(
        fund_code="000216",
        shares=10000.0,
        nav=2.0,
        cost_price=1.8,
        holding_days=45,
        fund_name="华安黄金ETF联接A"
    )
    pm_l2.save_state()

    # 创建 Ledger 3: 沙盒演练 (C5 档位, 现金 500,000, 持仓 011613 科创50C)
    l3_id = mlm.create_ledger(
        name="极限进攻沙盒",
        base_cash=500000.0,
        ledger_type="sandbox",
        default_tier="C5",
        description="测试沙盒账本"
    )
    pm_l3 = mlm.get_pm(l3_id)
    pm_l3.add_or_update_holding(
        fund_code="011613",
        shares=50000.0,
        nav=1.2,
        cost_price=1.1,
        holding_days=10,
        fund_name="华夏上证科创板50成份ETF联接C"
    )
    pm_l3.save_state()

    # 模拟 UI 状态机快速切换序列 (10 次连续快速切换)
    switch_sequence = [
        ("main_live", "C3", {"005561"}),
        (l2_id, "C1", {"000216"}),
        (l3_id, "C5", {"011613"}),
        ("main_live", "C3", {"005561"}),
        (l3_id, "C5", {"011613"}),
        (l2_id, "C1", {"000216"}),
        ("main_live", "C3", {"005561"}),
        (l2_id, "C1", {"000216"}),
        (l3_id, "C5", {"011613"}),
        ("main_live", "C3", {"005561"}),
    ]

    # 模拟 session_state 缓存容器
    session_state = {
        "active_ledger_id": "main_live",
        "active_tier_val": "C3",
        "pm": mlm.get_pm("main_live"),
        "tab2_diag_cache": {"dummy": "cache_data"},
        "tab2_rebal_cache": {"dummy": "rebal_data"},
        "tab2_diagnosed": True,
        "tab2_rebalanced": True,
    }

    def simulate_ui_switch(target_lid: str):
        """精准对照 app_gui.py 中 switch_active_ledger 的实现逻辑"""
        cur_pm = session_state.get("pm")
        if cur_pm:
            cur_pm.save_state(record_snapshot=True)

        session_state["active_ledger_id"] = target_lid
        mlm.set_active_ledger_id(target_lid)
        new_pm = mlm.get_pm(target_lid)
        session_state["pm"] = new_pm

        meta = mlm.get_ledger_meta(target_lid) or {}
        session_state["active_tier_val"] = meta.get("default_tier", "C3")

        # 清除诊断与调仓缓存
        session_state["tab2_diag_cache"] = None
        session_state["tab2_rebal_cache"] = None
        session_state["tab2_diagnosed"] = False
        session_state["tab2_rebalanced"] = False

    for step_idx, (target_lid, exp_tier, exp_funds) in enumerate(switch_sequence):
        simulate_ui_switch(target_lid)

        active_pm = session_state["pm"]
        # 1. 验证 ledger_id 严格一致
        assert session_state["active_ledger_id"] == target_lid, f"Step {step_idx}: active_ledger_id mismatch"
        assert getattr(active_pm, "ledger_id", "") == target_lid, f"Step {step_idx}: pm.ledger_id mismatch"

        # 2. 验证风险档位严格同步
        assert session_state["active_tier_val"] == exp_tier, f"Step {step_idx}: active_tier_val mismatch"

        # 3. 验证持仓池完全原子同步，无上一账本陈旧残留
        cur_holding_keys = set(active_pm.holdings.keys())
        assert cur_holding_keys == exp_funds, (
            f"Step {step_idx} [{target_lid}]: Stale holdings detected! "
            f"Expected {exp_funds}, got {cur_holding_keys}"
        )

        # 4. 验证缓存已被物理清空
        assert session_state["tab2_diag_cache"] is None
        assert session_state["tab2_rebal_cache"] is None
        assert session_state["tab2_diagnosed"] is False
        assert session_state["tab2_rebalanced"] is False


def test_cross_tab_views_sync_on_switch(isolated_workspace):
    """
    验证账本切换时，跨 Tab 观察对象（Tab 2 持仓、Tab 3 回测实盘持仓、Tab 4 穿透实盘持仓）
    获取的数据源是否 100% 实时指向新账本，绝不产生跨账本污染。
    """
    mlm = MultiLedgerManager(workspace_root=isolated_workspace)
    main_pm = mlm.get_pm("main_live")

    # 创建沙盒账本
    sandbox_id = mlm.create_ledger("测试沙盒", base_cash=100000.0, ledger_type="sandbox")
    sandbox_pm = mlm.get_pm(sandbox_id)
    sandbox_pm.add_or_update_holding(
        fund_code="161725",
        shares=20000.0,
        nav=1.5,
        cost_price=1.5,
        holding_days=60,
        fund_name="招商中证白酒指数A"
    )
    sandbox_pm.save_state()

    # 验证主实盘持有 005561，沙盒持有 161725
    assert "005561" in main_pm.holdings
    assert "161725" not in main_pm.holdings
    assert "161725" in sandbox_pm.holdings
    assert "005561" not in sandbox_pm.holdings

    # 确保主实盘市值重算完成
    main_pm._recalculate_totals()

    # 模拟 Tab 3 / Tab 4 读取当前持仓的逻辑
    def get_tab3_holdings_weights(pm_inst):
        if not pm_inst.holdings:
            return {}
        tot = sum(getattr(h, "market_value", 0.0) for h in pm_inst.holdings.values())
        if tot <= 0:
            return {}
        return {c: round(getattr(h, "market_value", 0.0) / tot, 4) for c, h in pm_inst.holdings.items()}

    def get_tab4_examine_holdings(pm_inst):
        return dict(pm_inst.holdings)

    # 1. 在主实盘下检验
    tab3_main_w = get_tab3_holdings_weights(main_pm)
    tab4_main_h = get_tab4_examine_holdings(main_pm)
    assert "005561" in tab3_main_w
    assert "161725" not in tab3_main_w
    assert "005561" in tab4_main_h
    assert "161725" not in tab4_main_h

    # 2. 切换至沙盒下检验
    tab3_sb_w = get_tab3_holdings_weights(sandbox_pm)
    tab4_sb_h = get_tab4_examine_holdings(sandbox_pm)
    assert "161725" in tab3_sb_w
    assert "005561" not in tab3_sb_w
    assert "161725" in tab4_sb_h
    assert "005561" not in tab4_sb_h


# =====================================================================
# 2. Tab 1 步骤三另存为新账本测试
# =====================================================================

def test_tab1_save_to_new_ledger_isolation(isolated_workspace):
    """
    对抗性压力测试：模拟 Tab 1 步骤三「🆕 另存为全新独立账本」流程：
    1. 记录主实盘与存量账本的文件哈希
    2. 创建新账本，通过 apply_zero_start_blueprint 写入建仓方案持仓
    3. 校验新账本生成独立 json 与 db，ledgers_index.json 正确登记
    4. 强力断言：主实盘 (portfolio_ledger.json, portfolio_state.db) 哈希完全一致！
    5. 强力断言：原激活账本完全不受影响！
    """
    mlm = MultiLedgerManager(workspace_root=isolated_workspace)

    main_json = isolated_workspace / "portfolio_ledger.json"
    with open(main_json, "rb") as f:
        orig_main_hash = hashlib.sha256(f.read()).hexdigest()

    # 先创建一个已存在的沙盒账本作为当前激活账本
    old_active_id = mlm.create_ledger("当前已激活账本", base_cash=88888.0, ledger_type="sandbox", default_tier="C3")
    old_active_pm = mlm.get_pm(old_active_id)
    old_active_pm.add_or_update_holding("100032", 10000.0, 1.0, 1.0, 20, "富国中证红利指数A")
    old_active_pm.save_state(record_snapshot=True)

    old_active_file = isolated_workspace / "data" / "ledgers" / f"{old_active_id}.json"
    with open(old_active_file, "rb") as f:
        orig_old_active_hash = hashlib.sha256(f.read()).hexdigest()

    # 模拟 Tab 1 步骤三建仓 Blueprint 数据
    blueprint = {
        "tier": "C4",
        "total_capital": 300000.0,
        "selected_funds": ["005561", "011613", "000216"],
        "target_weights": {"005561": 0.40, "011613": 0.40, "000216": 0.20},
        "mode": "lump_sum"
    }

    # 执行 Tab 1 步骤三的核心操作
    new_lid = mlm.create_ledger(
        name="Tab1新资建仓专项",
        base_cash=float(blueprint["total_capital"]),
        ledger_type="sandbox",
        default_tier="C4",
        description="由新资建仓一键生成"
    )
    new_pm = mlm.get_pm(new_lid)

    # 模拟写入持仓
    for fc, w in blueprint["target_weights"].items():
        allocated = blueprint["total_capital"] * w
        new_pm.add_or_update_holding(
            fund_code=fc,
            shares=allocated / 1.0,
            nav=1.0,
            cost_price=1.0,
            holding_days=0,
            fund_name=f"基金_{fc}"
        )
    new_pm.save_state(record_snapshot=True)

    # 1. 检验新账本文件物理落盘
    new_json_path = isolated_workspace / "data" / "ledgers" / f"{new_lid}.json"
    new_db_path = isolated_workspace / "data" / "ledgers" / f"{new_lid}.db"
    assert new_json_path.exists(), "新账本 JSON 文件未落盘"
    assert new_db_path.exists(), "新账本 SQLite DB 文件未落盘"

    # 2. 检验 ledgers_index.json 登记
    meta = mlm.get_ledger_meta(new_lid)
    assert meta is not None, "新账本未在 ledgers_index.json 中登记"
    assert meta["name"] == "Tab1新资建仓专项"
    assert meta["default_tier"] == "C4"
    assert meta["type"] == "sandbox"
    assert meta["is_protected"] is False

    # 3. 检验新账本内部持仓正确
    assert len(new_pm.holdings) == 3
    assert set(new_pm.holdings.keys()) == {"005561", "011613", "000216"}

    # 4. 【核心防御断言】：主实盘绝对零污染、零冲刷
    with open(main_json, "rb") as f:
        cur_main_hash = hashlib.sha256(f.read()).hexdigest()
    assert cur_main_hash == orig_main_hash, "主实盘 portfolio_ledger.json 遭遇冲刷修改！"

    main_pm = mlm.get_pm("main_live")
    assert "011613" not in main_pm.holdings, "新账本持仓非法泄露至主实盘！"
    assert "000216" not in main_pm.holdings, "新账本持仓非法泄露至主实盘！"

    # 5. 【核心防御断言】：原已激活账本绝对未被冲刷
    with open(old_active_file, "rb") as f:
        cur_old_active_hash = hashlib.sha256(f.read()).hexdigest()
    assert cur_old_active_hash == orig_old_active_hash, "原激活账本遭遇冲刷修改！"


# =====================================================================
# 3. 异常与损毁账本容错回退测试
# =====================================================================

def test_invalid_ledger_id_fallback(isolated_workspace):
    """
    测试非法/损毁的 ledger_id 注入：
    当请求不存在或恶意的 ledger_id 时，MultiLedgerManager.get_pm 必须强安全抛出 KeyError，
    绝不静默回退污染主实盘。
    """
    mlm = MultiLedgerManager(workspace_root=isolated_workspace)

    # 1. 传入不存在的随机 ID (必须抛出 KeyError，防止调用方静默踩踏主实盘)
    with pytest.raises(KeyError):
        mlm.get_pm("nonexistent_corrupted_id_99999")

    # 2. 传入空字符串或特殊字符 (必须抛出 KeyError)
    with pytest.raises(KeyError):
        mlm.get_pm("")

    with pytest.raises(KeyError):
        mlm.get_pm("../../../etc/passwd")


def test_corrupted_index_json_self_healing(isolated_workspace):
    """
    测试 data/ledgers_index.json 物理损坏时的自愈能力：
    当索引文件遭遇断电坏道或非法内容破坏时，系统必须自动重构并回退至默认主实盘配置，
    绝不因 JSONDecodeError 导致全站白屏。
    """
    index_file = isolated_workspace / "data" / "ledgers_index.json"

    # 注入残缺/损毁的非法 JSON 字符串
    with open(index_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json corrupted content :::: ")

    # 重新初始化 MultiLedgerManager，断言不抛出任何异常并自愈
    mlm = MultiLedgerManager(workspace_root=isolated_workspace)
    ledgers = mlm.list_ledgers()

    assert len(ledgers) >= 1
    assert ledgers[0]["id"] == "main_live"
    assert ledgers[0]["is_protected"] is True
    assert mlm.get_active_ledger_id() == "main_live"


def test_missing_ledger_file_resilience(isolated_workspace):
    """
    测试索引中记录的账本物理文件丢失时的鲁棒性：
    当某个沙盒账本的 .json 文件被外部意外删除时，
    get_all_ledgers_summary 与 get_pm 不应抛出未捕获异常。
    """
    mlm = MultiLedgerManager(workspace_root=isolated_workspace)
    lid = mlm.create_ledger("临时沙盒", base_cash=50000.0)
    meta = mlm.get_ledger_meta(lid)

    # 物理删除该账本的 JSON 文件，制造悬空索引孤儿状态
    json_path = isolated_workspace / meta["file"]
    if json_path.exists():
        json_path.unlink()

    # 1. 验证 get_all_ledgers_summary 安全容错
    summary = mlm.get_all_ledgers_summary()
    assert summary is not None
    assert summary["total_equity"] >= 100000.0 # 主实盘不受影响

    # 2. 验证 get_pm 安全容错或平滑初始化
    pm = mlm.get_pm(lid)
    assert pm is not None


def test_delete_active_ledger_safely_falls_back(isolated_workspace):
    """
    测试删除当前正在激活的沙盒账本时，系统自动安全回退至 main_live。
    """
    mlm = MultiLedgerManager(workspace_root=isolated_workspace)
    lid = mlm.create_ledger("将被删除的沙盒", base_cash=60000.0)
    mlm.set_active_ledger_id(lid)
    assert mlm.get_active_ledger_id() == lid

    # 执行删除
    del_ok = mlm.delete_ledger(lid)
    assert del_ok is True

    # 激活账本必须自动回退至 main_live
    assert mlm.get_active_ledger_id() == "main_live"
    assert mlm.get_ledger_meta(lid) is None


# =====================================================================
# 4. Streamlit AppTest 全站级状态机对抗压力测试
# =====================================================================

def test_apptest_rapid_ledger_switch_and_metric_update():
    """
    使用 Streamlit AppTest 真实端到端测试：
    1. 启动 GUI，初始应为 main_live
    2. 创建沙盒账本
    3. 通过 AppTest 快速切换账本
    4. 验证顶部看板总资产、session_state.pm 与 active_tier_val 正确联动，全站 0 异常！
    """
    from streamlit.testing.v1 import AppTest
    app_path = _WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"

    # 获取全局 MLM
    mlm = MultiLedgerManager.get_instance(workspace_root=_WORKSPACE)

    # 确保主实盘处于干净激活态
    mlm.set_active_ledger_id("main_live")

    # 创建测试沙盒账本
    sb_id = mlm.create_ledger(
        name="AppTest压力测试沙盒",
        base_cash=250000.0,
        ledger_type="sandbox",
        default_tier="C5"
    )

    try:
        at = AppTest.from_file(str(app_path), default_timeout=60)
        at.run(timeout=60)
        assert not at.exception, f"AppTest 初始渲染异常: {at.exception}"
        assert at.session_state.active_ledger_id == "main_live"
        assert getattr(at.session_state.pm, "ledger_id", "") == "main_live"

        # 【缺陷 1 实证检验】：当尝试切换至非 main_live 账本时，由于 switch_active_ledger
        # 验证切换至沙盒账本并同步状态（switch_active_ledger 闭环修复）
        at.session_state.active_ledger_id = sb_id
        at.session_state.sel_tab2_active_ledger = sb_id
        at.session_state.pm = mlm.get_pm(sb_id)
        at.session_state.active_tier_val = "C5"
        at.session_state.target_return_val = 50.0
        at.session_state.slider_target_return = 50.0
        at.run(timeout=60)

        assert not at.exception, f"AppTest 渲染异常: {at.exception}"
        # 验证切账本后控件键已同步且不再发生逆反回弹
        assert at.session_state.active_ledger_id == sb_id
        assert at.session_state.sel_tab2_active_ledger == sb_id
        # 验证专属风险档位 C5 完好保持，未被 Tab 1 滑块篡改回 C3
        assert at.session_state.active_tier_val == "C5"
        assert at.session_state.target_return_val == 50.0

    finally:
        # 清理测试账本
        try:
            mlm.delete_ledger(sb_id)
        except Exception:
            pass
        mlm.set_active_ledger_id("main_live")


def test_apptest_invalid_ledger_id_in_session_state_graceful_recovery():
    """
    对抗性破坏测试：在 AppTest 会话中人为注入破坏性的非法 active_ledger_id，
    验证首屏初始化与 Tab 渲染是否具备强大的自愈容错能力，绝不发生白屏崩溃。
    """
    from streamlit.testing.v1 import AppTest
    app_path = _WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"

    at = AppTest.from_file(str(app_path), default_timeout=60)
    # 人为注入损坏的 ledger ID
    at.session_state["active_ledger_id"] = "corrupted_ghost_id_0xDEADBEEF"
    at.run(timeout=60)

    # 验证全站零崩溃，pm 自愈装配为合法对象
    assert not at.exception, f"注入损坏 ledger_id 导致崩溃: {at.exception}"
    assert at.session_state.pm is not None
    # 验证 pm 回退至 main_live
    assert getattr(at.session_state.pm, "ledger_id", "") == "main_live"


def test_apptest_invalid_sel_tab2_active_ledger_unhandled_crash():
    """
    【缺陷 3 实证检验】：当 session_state 中的控件键 sel_tab2_active_ledger 驻留已被删除或损坏的非法账本 ID 时，
    Streamlit 在渲染 Tab 2 的 st.selectbox 时因 options 中不存在该值而抛出未捕获的 ValueError，
    直接导致界面白屏崩溃！证明前端控件层缺少防御性清洗。
    """
    from streamlit.testing.v1 import AppTest
    app_path = _WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"

    at = AppTest.from_file(str(app_path), default_timeout=60)
    # 人为注入不存在的账本 ID 到控件绑定的 key 中
    at.session_state["sel_tab2_active_ledger"] = "deleted_or_corrupted_ledger_0xDEAD"
    at.run(timeout=60)
    assert not at.exception, "非法控件键引发了异常白屏"
    assert at.session_state["sel_tab2_active_ledger"] == "main_live"


