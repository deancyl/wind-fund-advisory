"""
多账本管理引擎 (MultiLedgerManager) 核心自动化单元测试
测试范围：
1. 主实盘账本初始化与物理防删除保护 (main_live 保护)
2. 新建独立账本与独立文件落盘
3. 账本深拷贝克隆与元数据维护
4. 账本重命名与删除（文件清理与状态回退）
5. 独立 SQLite 数据库物理隔离防冲刷（修改沙盒持仓不影响主实盘）
6. 全账本家庭资产汇总统计 (get_all_ledgers_summary)
7. portfolio_manager 模块 re-export 兼容性
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
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, MultiLedgerManager as ReExportedMLM


@pytest.fixture
def temp_workspace(tmp_path):
    """创建隔离的测试临时工作区，并复制必要的主实盘初始文件"""
    ws = tmp_path / "test_workspace"
    ws.mkdir()
    
    # 初始化主实盘 portfolio_ledger.json
    main_ledger_data = {
        "version": "AGY2_PORTFOLIO_V2",
        "takeover_mode": "B",
        "baseline_date": "2026-11-05",
        "baseline_equity": 100000.0,
        "available_cash": 40000.0,
        "in_transit_cash": 0.0,
        "total_market_value": 60000.0,
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
                "current_nav": 1.2,
                "market_value": 60000.0,
                "cost_basis": 50000.0,
                "floating_pnl": 10000.0,
                "floating_pnl_pct": 20.0,
                "first_buy_date": "2026-01-01",
                "dividend_method": "cash",
                "batches": []
            }
        ],
        "pending_orders": [],
        "staged_batch_plans": [],
        "reserved_batch_cash": 0.0
    }
    with open(ws / "portfolio_ledger.json", "w", encoding="utf-8") as f:
        json.dump(main_ledger_data, f, ensure_ascii=False, indent=2)

    return ws


def test_re_export():
    """验证 MultiLedgerManager 在 portfolio_manager 中成功 re-export"""
    assert ReExportedMLM is not None
    assert ReExportedMLM.__name__ == "MultiLedgerManager"
    assert issubclass(ReExportedMLM, MultiLedgerManager) or ReExportedMLM is MultiLedgerManager


def test_init_and_main_protection(temp_workspace):
    """测试 MultiLedgerManager 初始化及主实盘防删除物理保护"""
    mlm = MultiLedgerManager(workspace_root=temp_workspace)
    ledgers = mlm.list_ledgers()
    assert len(ledgers) >= 1
    assert ledgers[0]["id"] == "main_live"
    assert ledgers[0]["is_protected"] is True

    # 验证物理删除保护
    with pytest.raises(PermissionError) as exc_info:
        mlm.delete_ledger("main_live")
    assert "主实盘账本受物理保护" in str(exc_info.value)


def test_create_and_manage_ledger(temp_workspace):
    """测试创建、重命名、查询独立账本"""
    mlm = MultiLedgerManager(workspace_root=temp_workspace)

    lid = mlm.create_ledger(
        name="测试子女教育金",
        base_cash=200000.0,
        ledger_type="family",
        default_tier="C2",
        description="用于教育规划"
    )
    assert lid.startswith("family_")

    meta = mlm.get_ledger_meta(lid)
    assert meta is not None
    assert meta["name"] == "测试子女教育金"
    assert meta["type"] == "family"
    assert meta["default_tier"] == "C2"

    # 验证独立 json 文件生成
    json_path = temp_workspace / meta["file"]
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        jdata = json.load(f)
    assert jdata["available_cash"] == 200000.0
    assert jdata["total_equity"] == 200000.0

    # 重命名测试
    renamed = mlm.rename_ledger(lid, "重命名教育金")
    assert renamed is True
    meta2 = mlm.get_ledger_meta(lid)
    assert meta2["name"] == "重命名教育金"


def test_clone_ledger(temp_workspace):
    """测试账本克隆功能"""
    mlm = MultiLedgerManager(workspace_root=temp_workspace)
    clone_id = mlm.clone_ledger("main_live", "主实盘演练副本")

    assert clone_id.startswith("sandbox_clone_")
    meta = mlm.get_ledger_meta(clone_id)
    assert meta is not None
    assert meta["name"] == "主实盘演练副本"
    assert meta["type"] == "sandbox"

    # 验证克隆出来的持仓完整保留
    clone_json = temp_workspace / meta["file"]
    assert clone_json.exists()
    with open(clone_json, "r", encoding="utf-8") as f:
        cdata = json.load(f)
    assert len(cdata["holdings"]) == 1
    assert cdata["holdings"][0]["fund_code"] == "005561"


def test_storage_isolation_and_no_contamination(temp_workspace):
    """关键测试：修改沙盒持仓与保存状态，绝不污染或清空主实盘数据"""
    mlm = MultiLedgerManager(workspace_root=temp_workspace)

    # 记录主实盘原始文件哈希
    main_file = temp_workspace / "portfolio_ledger.json"
    with open(main_file, "rb") as f:
        orig_main_hash = hashlib.sha256(f.read()).hexdigest()

    # 创建沙盒
    sandbox_id = mlm.create_ledger("极端高风险沙盒", base_cash=50000.0, ledger_type="sandbox")
    sandbox_pm = mlm.get_pm(sandbox_id)

    # 验证沙盒独立 DB 与 JSON 绑定
    assert str(sandbox_pm.ledger_json_path).endswith(f"{sandbox_id}.json")
    assert str(sandbox_pm.db_path).endswith(f"{sandbox_id}.db")

    # 对沙盒增加持仓并保存
    sandbox_pm.add_or_update_holding(
        fund_code="008888",
        shares=10000.0,
        nav=1.6,
        cost_price=1.5,
        holding_days=30,
        fund_name="华夏国证半导体芯片ETF联接A"
    )
    sandbox_pm.save_state(record_snapshot=True)

    # 断言沙盒内部持仓正确
    assert "008888" in sandbox_pm.holdings
    assert len(sandbox_pm.holdings) == 1

    # 断言主实盘文件内容与哈希完全无变化
    with open(main_file, "rb") as f:
        current_main_hash = hashlib.sha256(f.read()).hexdigest()
    assert current_main_hash == orig_main_hash

    # 加载主实盘 PM，断言主实盘持仓仍然只有原始的 005561，绝无 008888
    main_pm = mlm.get_pm("main_live")
    assert "005561" in main_pm.holdings
    assert "008888" not in main_pm.holdings


def test_delete_ledger_and_cleanup(temp_workspace):
    """测试删除账本与物理清理文件"""
    mlm = MultiLedgerManager(workspace_root=temp_workspace)
    lid = mlm.create_ledger("待删除账本", base_cash=10000.0)
    meta = mlm.get_ledger_meta(lid)
    json_path = temp_workspace / meta["file"]
    db_path = temp_workspace / meta["db_file"]

    # 产生 db 文件
    pm = mlm.get_pm(lid)
    pm.save_state()
    assert json_path.exists()
    assert db_path.exists()

    # 设为当前激活账本
    mlm.set_active_ledger_id(lid)
    assert mlm.get_active_ledger_id() == lid

    # 执行删除
    deleted = mlm.delete_ledger(lid)
    assert deleted is True
    assert mlm.get_ledger_meta(lid) is None
    assert not json_path.exists()
    assert not db_path.exists()
    # 激活账本回退至 main_live
    assert mlm.get_active_ledger_id() == "main_live"


def test_get_all_ledgers_summary(temp_workspace):
    """测试全账本家庭资产汇总计算"""
    mlm = MultiLedgerManager(workspace_root=temp_workspace)
    # 主实盘已有 100,000 总资产，10,000 浮盈，1 只持仓
    # 创建额外账本
    mlm.create_ledger("稳健养老金", base_cash=300000.0, ledger_type="family")

    summary = mlm.get_all_ledgers_summary()
    assert summary["total_equity"] == pytest.approx(400000.0)
    assert summary["total_floating_pnl"] == pytest.approx(10000.0)
    assert summary["total_funds"] == 1
    assert len(summary["ledgers"]) == 2
    assert summary["df"] is not None
    assert len(summary["df"]) == 2


def test_apptest_multi_ledger_session_state():
    """通过 Streamlit AppTest 验证多账本状态机与 UI 装配零报错"""
    from streamlit.testing.v1 import AppTest
    app_path = _WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=30)
    at.run()
    assert not at.exception, f"AppTest raised exception: {at.exception}"
    assert at.session_state.active_ledger_id == "main_live"
    assert at.session_state.mlm is not None
    assert at.session_state.pm is not None
    assert getattr(at.session_state.pm, "ledger_id", "") == "main_live"

