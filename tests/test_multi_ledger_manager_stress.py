"""
Adversarial Stress Test Harness for MultiLedgerManager (tests/test_multi_ledger_manager_stress.py)
Authored by: teamwork_challenger (empirical_challenger)

Target Under Test: AGY2_FundAdvisory/multi_ledger_manager.py
Stress Dimensions:
1. Rapid lifecycle loop: high-frequency creation, clone, rename, deletion cycles, ID collision resilience.
2. Storage isolation: extreme batches, transactions, snapshots into sandbox; byte-for-byte SHA256 of main_live files.
3. Protection attacks: delete main_live via direct call, bypasses, case variants, path traversal aliases, protected flags.
4. Summary arithmetic integrity: exact arithmetic equality of aggregated assets, PnL, fund counts across diverse ledgers.
5. Fallback security: behavior on non-existent ledger IDs in get_pm.
"""

import sys
import json
import sqlite3
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
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, HoldingBatch, PendingOrder


def _calc_sha256(path: Path) -> str:
    """计算文件的 SHA256 哈希值"""
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture
def temp_stress_workspace(tmp_path):
    """构建完全隔离的压力测试工作区，包含真实初始化的 main_live JSON 与 SQLite DB"""
    ws = tmp_path / "stress_workspace"
    ws.mkdir(parents=True, exist_ok=True)

    main_json = ws / "portfolio_ledger.json"
    main_db = ws / "portfolio_state.db"

    main_data = {
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
                "batches": [
                    {
                        "batch_id": "BATCH_INIT_001",
                        "fund_code": "005561",
                        "shares": 50000.0,
                        "cost_price": 1.0,
                        "buy_date": "2026-01-01",
                        "holding_days": 180,
                        "share_class": "A"
                    }
                ]
            }
        ],
        "pending_orders": [],
        "staged_batch_plans": [],
        "reserved_batch_cash": 0.0
    }
    with open(main_json, "w", encoding="utf-8") as f:
        json.dump(main_data, f, ensure_ascii=False, indent=2)

    # 用 PortfolioManager 初始化 main_db 并存盘，确保包含完整的 SQLite 表结构与记录
    pm = PortfolioManager(
        db_path=str(main_db),
        ledger_json_path=str(main_json),
        ledger_id="main_live"
    )
    pm.save_state(record_snapshot=True)

    return ws


def test_stress_rapid_lifecycle_cycles(temp_stress_workspace):
    """
    压力维度 1: 高频高并发账本生命周期循环 (Rapid Multi-Ledger Creation, Clone, Rename, Deletion Cycles)
    - 验证高频创建 40 个账本时不发生 ID 碰撞
    - 验证克隆与重命名
    - 验证删除后文件被彻底清理且索引同步
    - 验证激活账本删除后自动平滑回退至 main_live
    - 验证索引文件的结构完整性与 main_live 置顶不变量
    """
    ws = temp_stress_workspace
    mlm = MultiLedgerManager(workspace_root=ws)

    created_ids = []
    # 快速创建 30 个各类型账本
    for i in range(30):
        l_type = ["sandbox", "family", "live"][i % 3]
        tier = ["C1", "C2", "C3", "C4", "C5"][i % 5]
        lid = mlm.create_ledger(
            name=f"高频账本_{i:03d}",
            base_cash=50000.0 + i * 1000.0,
            ledger_type=l_type,
            default_tier=tier
        )
        created_ids.append(lid)

    # 断言无任何重复 ID
    assert len(created_ids) == len(set(created_ids)), "高频生成账本出现 ID 碰撞！"

    # 克隆 10 个
    cloned_ids = []
    for i in range(10):
        src_id = created_ids[i]
        cid = mlm.clone_ledger(src_id=src_id, target_name=f"克隆副本_{i}")
        cloned_ids.append(cid)
    assert len(cloned_ids) == len(set(cloned_ids)), "高频克隆账本出现 ID 碰撞！"

    # 重命名 10 个
    for i in range(10):
        ok = mlm.rename_ledger(created_ids[i], f"重命名新名称_{i}")
        assert ok is True
        meta = mlm.get_ledger_meta(created_ids[i])
        assert meta["name"] == f"重命名新名称_{i}"

    # 设置激活账本为 created_ids[5]，然后删除它，断言激活账本回退至 main_live
    target_active = created_ids[5]
    mlm.set_active_ledger_id(target_active)
    assert mlm.get_active_ledger_id() == target_active

    del_ok = mlm.delete_ledger(target_active)
    assert del_ok is True
    assert mlm.get_active_ledger_id() == "main_live", "激活账本被删除后未自动回退至 main_live！"

    # 批量删除 15 个创建账本和 5 个克隆账本
    to_delete = created_ids[10:25] + cloned_ids[0:5]
    for lid in to_delete:
        meta = mlm.get_ledger_meta(lid)
        json_file = ws / meta["file"]
        db_file = ws / meta["db_file"]
        # 先保存一次产生 db
        pm = mlm.get_pm(lid)
        pm.save_state()
        assert json_file.exists()
        assert db_file.exists()

        # 删除
        ok = mlm.delete_ledger(lid)
        assert ok is True
        # 物理断言：文件必须被彻底清理
        assert not json_file.exists(), f"账本文件未被物理清理: {json_file}"
        assert not db_file.exists(), f"数据库文件未被物理清理: {db_file}"
        assert mlm.get_ledger_meta(lid) is None
        assert lid not in mlm._pm_cache

    # 校验最终索引文件完整性
    all_ledgers = mlm.list_ledgers()
    assert len(all_ledgers) >= 1
    assert all_ledgers[0]["id"] == "main_live", "main_live 必须始终置顶！"
    assert all_ledgers[0]["is_protected"] is True


def test_stress_isolation_extreme_batches_transactions_snapshots(temp_stress_workspace):
    """
    压力维度 2: 沙盒极端负载与物理隔离性验证 (Storage Isolation & Main-Live Invariant)
    - 在沙盒写入 40 只基金、100+ 批次、20 个在途挂单、25 次快照
    - 强行触发 SQLite DELETE FROM holdings 重写
    - 逐字节核验 portfolio_ledger.json 与 portfolio_state.db 的 SHA256 完全不变
    """
    ws = temp_stress_workspace
    main_json = ws / "portfolio_ledger.json"
    main_db = ws / "portfolio_state.db"

    # 记录沙盒操作前主实盘文件的绝对 SHA256
    orig_json_sha = _calc_sha256(main_json)
    orig_db_sha = _calc_sha256(main_db)
    assert len(orig_json_sha) == 64
    assert len(orig_db_sha) == 64

    # 记录主实盘 SQLite 内部各表行数
    with sqlite3.connect(main_db) as conn:
        c = conn.cursor()
        c.execute("SELECT count(*) FROM holdings")
        main_holdings_count = c.fetchone()[0]
        c.execute("SELECT count(*) FROM holding_batches")
        main_batches_count = c.fetchone()[0]
        c.execute("SELECT count(*) FROM portfolio_snapshots")
        main_snapshots_count = c.fetchone()[0]

    mlm = MultiLedgerManager(workspace_root=ws)
    sandbox_id = mlm.create_ledger("极端高频压力测试沙盒", base_cash=1000000.0, ledger_type="sandbox")
    sandbox_pm = mlm.get_pm(sandbox_id)

    # 验证沙盒绑定的存储路径是独立的
    assert str(sandbox_pm.ledger_json_path).endswith(f"{sandbox_id}.json")
    assert str(sandbox_pm.db_path).endswith(f"{sandbox_id}.db")

    # 注入 40 只基金持仓，每只生成 3 个不同批次 (共 120 个批次)
    for i in range(40):
        fcode = f"{i + 100000:06d}"
        fname = f"压力测试基金_{fcode}"
        sandbox_pm.add_or_update_holding(
            fund_code=fcode,
            shares=5000.0 + i * 100,
            nav=1.25,
            cost_price=1.10,
            holding_days=15 + i,
            fund_name=fname
        )
        # 为该基金追加额外批次
        h = sandbox_pm.holdings[fcode]
        h.batches.append(HoldingBatch(
            batch_id=f"B1_{fcode}",
            buy_date="2026-03-01",
            shares=2000.0,
            cost_nav=1.05,
            holding_days=60
        ))
        h.batches.append(HoldingBatch(
            batch_id=f"B2_{fcode}",
            buy_date="2026-04-01",
            shares=1000.0,
            cost_nav=1.15,
            holding_days=10
        ))

    # 添加 15 个在途挂单
    for i in range(15):
        sandbox_pm.pending_orders.append(PendingOrder(
            order_id=f"PO_{i:03d}",
            created_at="2026-11-05 10:00:00",
            effective_trade_date="2026-11-05",
            action="BUY" if i % 2 == 0 else "SELL",
            fund_code=f"{i + 100000:06d}",
            fund_name=f"挂单标的_{i}",
            amount=5000.0
        ))

    # 极端循环存盘 25 次，生成大量快照并反复触发 DELETE FROM holdings 表重写
    for s in range(25):
        sandbox_pm.save_state(record_snapshot=True)

    # 验证沙盒内部数据丰满
    assert len(sandbox_pm.holdings) == 40
    assert len(sandbox_pm.pending_orders) == 15
    sandbox_db = ws / "data" / "ledgers" / f"{sandbox_id}.db"
    assert sandbox_db.exists()
    with sqlite3.connect(sandbox_db) as s_conn:
        sc = s_conn.cursor()
        sc.execute("SELECT count(*) FROM holdings")
        assert sc.fetchone()[0] == 40
        sc.execute("SELECT count(*) FROM holding_batches")
        assert sc.fetchone()[0] >= 120
        sc.execute("SELECT count(*) FROM portfolio_snapshots")
        assert sc.fetchone()[0] >= 25

    # 核心红线核验：主实盘文件 byte-for-byte 绝对未被触碰！
    after_json_sha = _calc_sha256(main_json)
    after_db_sha = _calc_sha256(main_db)

    assert after_json_sha == orig_json_sha, (
        f"主实盘 JSON 文件哈希发生改变！被沙盒写入污染！\n"
        f"原始: {orig_json_sha}\n当前: {after_json_sha}"
    )
    assert after_db_sha == orig_db_sha, (
        f"主实盘 SQLite 数据库哈希发生改变！被沙盒写入踩踏！\n"
        f"原始: {orig_db_sha}\n当前: {after_db_sha}"
    )

    # 核验主实盘 SQLite 内部行数完好无损
    with sqlite3.connect(main_db) as conn:
        c = conn.cursor()
        c.execute("SELECT count(*) FROM holdings")
        assert c.fetchone()[0] == main_holdings_count
        c.execute("SELECT count(*) FROM holding_batches")
        assert c.fetchone()[0] == main_batches_count
        c.execute("SELECT count(*) FROM portfolio_snapshots")
        assert c.fetchone()[0] == main_snapshots_count


def test_protection_attack_direct_call(temp_stress_workspace):
    """
    攻击测试 3.1: 直接调用 delete_ledger('main_live') 必须被物理拦截
    """
    ws = temp_stress_workspace
    mlm = MultiLedgerManager(workspace_root=ws)
    main_json = ws / "portfolio_ledger.json"
    main_db = ws / "portfolio_state.db"

    with pytest.raises(PermissionError) as exc_info:
        mlm.delete_ledger("main_live")
    assert "主实盘账本受物理保护" in str(exc_info.value)
    assert main_json.exists()
    assert main_db.exists()


def test_protection_attack_case_and_whitespace_variants(temp_stress_workspace):
    """
    攻击测试 3.2: 针对 main_live 保护机制的大小写与空格变体绕过攻击
    【挑战者攻击目标】：
    尝试使用 'MAIN_LIVE', 'Main_Live', 'main_live ', '  MAIN_LIVE  ' 等大小写/空格变体调用 delete_ledger()。
    按照红线设计要求，任何针对主实盘的删除尝试都必须无条件抛出 PermissionError 坚决拒绝，
    绝不能因为大小写敏感而悄悄返回 False 或被视为普通不存在账本。
    """
    ws = temp_stress_workspace
    mlm = MultiLedgerManager(workspace_root=ws)
    main_json = ws / "portfolio_ledger.json"
    main_db = ws / "portfolio_state.db"

    attack_variants = [
        "MAIN_LIVE",
        "Main_Live",
        "main_live ",
        "  main_live  ",
        "  MAIN_LIVE  ",
        "MaIn_LiVe"
    ]

    for variant in attack_variants:
        # 断言对 main_live 的变体调用必须抛出 PermissionError
        with pytest.raises(PermissionError, match="主实盘账本受物理保护"):
            mlm.delete_ledger(variant)

    assert main_json.exists()
    assert main_db.exists()


def test_protection_attack_path_traversal_and_file_alias(temp_stress_workspace):
    """
    攻击测试 3.3: 路径遍历与主实盘文件别名攻击 (Path Traversal & Alias Bypass)
    【挑战者攻击场景】：
    恶意注入或损坏的索引元数据包含一个自定义 ID 的账本（如 'evil_sandbox'），
    但其文件路径通过未归一化的相对路径指向主实盘文件（如 'data/../portfolio_ledger.json'）。
    当删除该账本时，底层文件清理逻辑必须使用 .resolve() 物理识别并严禁 unlink 主实盘文件！
    """
    ws = temp_stress_workspace
    mlm = MultiLedgerManager(workspace_root=ws)
    main_json = ws / "portfolio_ledger.json"
    main_db = ws / "portfolio_state.db"

    orig_json_sha = _calc_sha256(main_json)
    orig_db_sha = _calc_sha256(main_db)

    # 恶意注入带有相对路径指向主实盘的索引条目
    index_data = mlm._read_index()
    index_data.setdefault("ledgers", []).append({
        "id": "evil_path_traversal",
        "name": "恶意路径遍历账本",
        "type": "sandbox",
        "file": "data/../portfolio_ledger.json",
        "db_file": "data/../portfolio_state.db",
        "is_protected": False,
        "created_at": "2026-11-05 00:00:00",
        "updated_at": "2026-11-05 00:00:00"
    })
    mlm._write_index(index_data)

    # 执行删除该账本
    mlm.delete_ledger("evil_path_traversal")

    # 物理断言：主实盘文件绝不能被误删除！
    assert main_json.exists(), "CRITICAL BUG: 主实盘 portfolio_ledger.json 被路径遍历漏洞误删！"
    assert main_db.exists(), "CRITICAL BUG: 主实盘 portfolio_state.db 被路径遍历漏洞误删！"
    assert _calc_sha256(main_json) == orig_json_sha
    assert _calc_sha256(main_db) == orig_db_sha


def test_protection_attack_protected_flag(temp_stress_workspace):
    """
    攻击测试 3.4: 对显式标记 is_protected=True 的自定义账本的删除攻击
    """
    ws = temp_stress_workspace
    mlm = MultiLedgerManager(workspace_root=ws)

    lid = mlm.create_ledger("家族信托基金", base_cash=5000000.0, ledger_type="family")
    # 显式锁定保护
    data = mlm._read_index()
    for l in data["ledgers"]:
        if l["id"] == lid:
            l["is_protected"] = True
    mlm._write_index(data)

    with pytest.raises(PermissionError) as exc_info:
        mlm.delete_ledger(lid)
    assert "受保护账本禁止删除" in str(exc_info.value)


def test_get_pm_nonexistent_ledger_safety(temp_stress_workspace):
    """
    攻击测试 3.5: get_pm 对不存在账本的静默回退安全性检验
    【挑战者安全审查】：
    当请求一个不存在或已删除的 ledger_id 时，如果 get_pm 静默返回 main_live 实例，
    可能导致调用方在毫不知情的情况下向主实盘生产账本写入脏数据。
    """
    ws = temp_stress_workspace
    mlm = MultiLedgerManager(workspace_root=ws)

    # 尝试获取一个明显不存在的账本
    fake_id = "non_existent_ledger_9999"
    with pytest.raises(KeyError, match="账本未找到"):
        mlm.get_pm(fake_id)


def test_stress_get_all_ledgers_summary_arithmetic_integrity(temp_stress_workspace):
    """
    压力维度 4: 全账本家庭资产汇总计算的算术恒等性检验 (Arithmetic Equality Integrity)
    - 构建由 8 个多样化账本构成的家庭星系：
      * main_live: 实盘持仓
      * 纯现金沙盒
      * 多持仓大幅浮盈家庭账本
      * 发生深度浮亏的沙盒
      * 存在在途交收现金的账本
      * 处于内存运行态未落盘的实时账本
      * 具有高精度微小金额的账本
    - 逐项断言算术恒等式：
      1. total_equity == sum(ledger.total_equity)
      2. total_floating_pnl == sum(ledger.floating_pnl)
      3. total_market_value == sum(ledger.market_value)
      4. total_funds == sum(ledger.holdings_count)
      5. total_equity == total_market_value + available_cash + in_transit_cash (各账本自洽)
      6. total_assets == total_equity && total_pnl == total_floating_pnl && total_holdings_count == total_funds
      7. DataFrame 渲染行数与数值严格对齐
    """
    ws = temp_stress_workspace
    mlm = MultiLedgerManager(workspace_root=ws)

    # 1. 创建纯现金沙盒
    mlm.create_ledger("纯现金理财沙盒", base_cash=250000.0, ledger_type="sandbox")

    # 2. 创建家庭子女教育账本 (大幅盈利)
    ed_id = mlm.create_ledger("子女高等教育基金", base_cash=100000.0, ledger_type="family", default_tier="C2")
    ed_pm = mlm.get_pm(ed_id)
    ed_pm.add_or_update_holding("008888", shares=20000.0, nav=2.50, cost_price=1.50, fund_name="芯片ETF", holding_days=90)
    ed_pm.add_or_update_holding("161725", shares=10000.0, nav=1.80, cost_price=1.20, fund_name="白酒分级", holding_days=120)
    ed_pm.save_state()

    # 3. 创建深度亏损投机沙盒
    loss_id = mlm.create_ledger("极端衍生品沙盒", base_cash=50000.0, ledger_type="sandbox", default_tier="C5")
    loss_pm = mlm.get_pm(loss_id)
    loss_pm.add_or_update_holding("161726", shares=30000.0, nav=0.70, cost_price=1.40, fund_name="医药分级", holding_days=45)
    loss_pm.save_state()

    # 4. 创建带有在途交收现金的账本
    transit_id = mlm.create_ledger("换仓在途过渡账本", base_cash=30000.0, ledger_type="family")
    transit_pm = mlm.get_pm(transit_id)
    transit_pm.in_transit_cash = 70000.0
    transit_pm.add_or_update_holding("000300", shares=10000.0, nav=1.0, cost_price=1.0, fund_name="沪深300", holding_days=30)
    transit_pm.save_state()

    # 5. 创建仅在内存中突变（未 save_state）的高频账本
    mem_id = mlm.create_ledger("实时未存盘沙盒", base_cash=80000.0, ledger_type="sandbox")
    mem_pm = mlm.get_pm(mem_id)
    mem_pm.add_or_update_holding("001071", shares=15000.0, nav=1.33, cost_price=1.00, fund_name="美股标普", holding_days=60)
    # 故意不调用 mem_pm.save_state()，检验 get_all_ledgers_summary 从内存 _pm_cache 抓取的能力

    # 6. 高精度金额微调账本
    prec_id = mlm.create_ledger("高精度零钱账本", base_cash=12345.67, ledger_type="sandbox")
    prec_pm = mlm.get_pm(prec_id)
    prec_pm.add_or_update_holding("005561", shares=123.45, nav=1.2345, cost_price=1.0001, fund_name="零钱红利", holding_days=5)
    prec_pm.save_state()

    # 执行全家庭汇总
    summary = mlm.get_all_ledgers_summary()

    ledgers = summary["ledgers"]
    assert len(ledgers) == 7 # 1 main + 6 created

    # 逐项算术求和核验
    sum_equity = sum(l["total_equity"] for l in ledgers)
    sum_pnl = sum(l["floating_pnl"] for l in ledgers)
    sum_mv = sum(l["market_value"] for l in ledgers)
    sum_funds = sum(l["holdings_count"] for l in ledgers)

    # 1. 总资产算术恒等
    assert summary["total_equity"] == pytest.approx(sum_equity, abs=0.05), (
        f"总资产汇总算术不相等: summary={summary['total_equity']}, sum={sum_equity}"
    )
    assert summary["total_assets"] == summary["total_equity"]

    # 2. 总浮盈算术恒等 (允许正负抵消)
    assert summary["total_floating_pnl"] == pytest.approx(sum_pnl, abs=0.05), (
        f"总浮盈汇总算术不相等: summary={summary['total_floating_pnl']}, sum={sum_pnl}"
    )
    assert summary["total_pnl"] == summary["total_floating_pnl"]

    # 3. 总持仓市值算术恒等
    assert summary["total_market_value"] == pytest.approx(sum_mv, abs=0.05), (
        f"总市值汇总算术不相等: summary={summary['total_market_value']}, sum={sum_mv}"
    )

    # 4. 总基金只数算术恒等 (严格整数相等)
    assert summary["total_funds"] == sum_funds, (
        f"总基金只数不相等: summary={summary['total_funds']}, sum={sum_funds}"
    )
    assert summary["total_holdings_count"] == summary["total_funds"]

    # 5. 各账本内部自洽公式：total_equity == market_value + available_cash + in_transit_cash
    for l in ledgers:
        expected_eq = l["market_value"] + l["available_cash"] + l["in_transit_cash"]
        assert l["total_equity"] == pytest.approx(expected_eq, abs=0.05), (
            f"账本 {l['id']} 内部资金不自洽: total_equity={l['total_equity']}, 计算值={expected_eq}"
        )

    # 6. DataFrame 表格渲染对齐核验
    df = summary["df"]
    assert len(df) == len(ledgers)
    assert "总资产 (元)" in df.columns
    assert "持仓市值 (元)" in df.columns
    assert "累计浮动盈亏" in df.columns
    assert "持仓只数" in df.columns
