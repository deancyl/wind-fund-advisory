"""
Challenger Deep Adversarial Stress Suite for M3-R2
Target: MultiLedgerManager isolation & Combat 29 Funds Ledger
"""

import sys
import json
import shutil
import hashlib
import sqlite3
from pathlib import Path
import pytest

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager, WORKSPACE_ROOT
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry


class TestChallengerTemporaryWorkspaceIsolation:
    """实证对抗测试 1: 临时工作区隔离与生产挂载幂等性"""

    def test_temp_workspace_never_injects_combat_ledger(self, tmp_path):
        """无论如何初始化临时工作区，绝不自动注入 combat_29_funds"""
        temp_ws = tmp_path / "temp_env_alpha"
        temp_ws.mkdir()

        mlm = MultiLedgerManager(workspace_root=temp_ws)
        ledgers = mlm.list_ledgers()

        # 必须仅有 1 个主实盘账本，绝对不包含 combat_29_funds
        assert len(ledgers) == 1, f"临时工作区账本数应为 1，实际为 {len(ledgers)}"
        assert ledgers[0]["id"] == "main_live"
        assert not (temp_ws / "data" / "ledgers" / "combat_29_funds.json").exists()

    def test_temp_workspace_path_case_and_slash_variants(self, tmp_path):
        """验证路径大小写与斜杠变体下的隔离准确性"""
        temp_ws = tmp_path / "case_test_WS"
        temp_ws.mkdir()

        # 传入字符串形态与末尾斜杠
        path_str = str(temp_ws) + "\\"
        mlm = MultiLedgerManager(workspace_root=path_str)
        assert len(mlm.list_ledgers()) == 1
        assert mlm.get_ledger_meta("combat_29_funds") is None

    def test_production_workspace_mount_idempotency_and_preservation(self, tmp_path):
        """
        验证在模拟的生产环境下（或者当 root 等同于模拟目标时）的挂载幂等性：
        1. 首次加载自动挂载 combat_29_funds
        2. 若用户修改了 combat_29_funds（如添加一笔现金或备注），再次实例化 MultiLedgerManager 绝不重置冲刷用户修改！
        """
        # 我们用 monkeypatch 或子目录模拟生产 root
        fake_prod = tmp_path / "fake_production"
        fake_prod.mkdir()

        # 先复制一份生产结构
        import AGY2_FundAdvisory.multi_ledger_manager as mlm_module
        orig_ws_root = mlm_module.WORKSPACE_ROOT

        try:
            # 临时将 WORKSPACE_ROOT 设定为 fake_prod
            mlm_module.WORKSPACE_ROOT = fake_prod

            mlm1 = MultiLedgerManager(workspace_root=fake_prod)
            assert mlm1.get_ledger_meta("combat_29_funds") is not None
            c_json = fake_prod / "data" / "ledgers" / "combat_29_funds.json"
            assert c_json.exists()

            # 用户对 combat_29_funds 进行业务修改（例如新增 500 元现金与自定义备注）
            with open(c_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["available_cash"] = 1500.0
            data["user_custom_note"] = "CHALLENGER_CUSTOM_NOTE_12345"
            with open(c_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 再次多次初始化 MultiLedgerManager（模拟热重载/刷新）
            for _ in range(5):
                mlm_reloaded = MultiLedgerManager(workspace_root=fake_prod)
                assert mlm_reloaded.get_ledger_meta("combat_29_funds") is not None

            # 核验：用户的自定义修改必须完整保留，绝未被 _init_preset_combat_29_ledger 暴力覆写！
            with open(c_json, "r", encoding="utf-8") as f:
                data_after = json.load(f)
            assert data_after["available_cash"] == 1500.0, "幂等性失效：用户修改被重新初始化的预置数据覆盖！"
            assert data_after.get("user_custom_note") == "CHALLENGER_CUSTOM_NOTE_12345"

        finally:
            mlm_module.WORKSPACE_ROOT = orig_ws_root

    def test_production_workspace_self_healing_if_json_deleted(self, tmp_path):
        """验证自愈性：若 combat_29_funds.json 意外损坏或丢失，重新初始化能够自动自愈重构"""
        fake_prod = tmp_path / "fake_prod_heal"
        fake_prod.mkdir()

        import AGY2_FundAdvisory.multi_ledger_manager as mlm_module
        orig_ws_root = mlm_module.WORKSPACE_ROOT

        try:
            mlm_module.WORKSPACE_ROOT = fake_prod
            mlm = MultiLedgerManager(workspace_root=fake_prod)
            c_json = fake_prod / "data" / "ledgers" / "combat_29_funds.json"
            assert c_json.exists()

            # 模拟意外丢失 json 文件
            c_json.unlink()
            assert not c_json.exists()

            # 重新初始化
            mlm2 = MultiLedgerManager(workspace_root=fake_prod)
            assert c_json.exists(), "自愈失效：丢失 combat_29_funds.json 后未自动重新生成！"
            assert mlm2.get_ledger_meta("combat_29_funds") is not None

        finally:
            mlm_module.WORKSPACE_ROOT = orig_ws_root


class TestChallengerCombat29FundsIntegrity:
    """实证对抗测试 2: 29基实战账本持有天数、零赎回费与分厘平账"""

    def test_production_combat_ledger_holding_days_and_penalty_rate(self):
        """真实生产账本 29 只基金持有天数严格 >= 365 且赎回费严格为 0"""
        mlm = MultiLedgerManager.get_instance()
        pm = mlm.get_pm("combat_29_funds")

        assert len(pm.holdings) == 29

        for code, h in pm.holdings.items():
            # 1. 验证批次
            assert len(h.batches) >= 1, f"标的 {code} 缺少批次！"
            # 悲观天数校验
            min_days = min((b.holding_days for b in h.batches), default=0)
            assert min_days >= 365, f"标的 {code} 悲观最小持有天数 {min_days} < 365天，存在赎回费风险！"

            # 2. 验证免惩罚可赎份额
            free_sh = pm.get_penalty_free_redeemable_shares(code)
            assert free_sh == pytest.approx(h.shares, abs=1e-4), f"标的 {code} 免惩罚份额 {free_sh} != 持仓份额 {h.shares}"

            # 3. 验证安全锁均为 False
            for b in h.batches:
                assert not b.safety_lock, f"标的 {code} 批次安全锁未解锁！"

    def test_production_combat_ledger_exact_market_value(self):
        """验证真实生产账本精确总市值 ¥26,615.10 与三分类平账"""
        mlm = MultiLedgerManager.get_instance()
        pm = mlm.get_pm("combat_29_funds")

        all_mvs = [round(h.market_value, 2) for h in pm.holdings.values()]
        total_mv = round(sum(all_mvs), 2)
        assert total_mv == 26615.10, f"生产账本市值总计 {total_mv} != 26615.10"

        # 核心 7 只
        core_codes = ["005561", "110020", "017436", "002351", "100032", "011613", "000216"]
        core_sum = round(sum(pm.holdings[c].market_value for c in core_codes), 2)
        assert core_sum == 25128.29, f"核心 7 只合计 {core_sum} != 25128.29"

        # 腰部 3 只
        waist_codes = ["161725", "000217", "005827"]
        waist_sum = round(sum(pm.holdings[c].market_value for c in waist_codes), 2)
        assert waist_sum == 1044.11, f"腰部 3 只合计 {waist_sum} != 1044.11"

        # 尾部 19 只
        tail_codes = [
            "016634", "001053", "050025", "002352", "016441", "013841", "012832", "012769",
            "008682", "011612", "002611", "019260", "000086", "018757", "001071", "006113",
            "004854", "001595", "001551"
        ]
        tail_sum = round(sum(pm.holdings[c].market_value for c in tail_codes), 2)
        assert tail_sum == 442.70, f"尾部 19 只合计 {tail_sum} != 442.70"

        assert round(core_sum + waist_sum + tail_sum, 2) == 26615.10

    def test_sweep_tail_simulation_zero_friction_and_exact_redeem(self):
        """模拟尾仓清扫调仓：全额 442.70 清扫，零赎回费，精准沉淀至底仓"""
        mlm = MultiLedgerManager.get_instance()
        pm = mlm.get_pm("combat_29_funds")

        plan = pm.generate_scenario_rebalance_plan({}, scenario_mode="sweep_tail_and_c_class", core_anchor_code="002351")
        assert len(plan["sell_actions"]) == 19
        assert round(plan["total_sell_amount"], 2) == 442.70
        assert plan["total_redemption_fee"] == 0.00
        assert round(plan["total_buy_amount"], 2) == 442.70

    def test_combat_clone_isolation_and_no_bleed_to_main(self, tmp_path):
        """克隆 combat_29_funds 并进行大规模清扫与修改，验证与原 combat_29_funds 及 main_live 互不影响"""
        mlm = MultiLedgerManager.get_instance()
        main_pm = mlm.get_pm("main_live")
        combat_pm = mlm.get_pm("combat_29_funds")

        main_mv_orig = main_pm.total_market_value
        combat_mv_orig = combat_pm.total_market_value

        # 克隆出临时测试账本
        clone_id = mlm.clone_ledger("combat_29_funds", "实战演练压力测试副本")
        clone_pm = mlm.get_pm(clone_id)

        try:
            assert len(clone_pm.holdings) == 29
            assert round(clone_pm.total_market_value, 2) == 26615.10

            # 对克隆账本执行清扫 19 只尾仓操作
            tail_codes = [
                "016634", "001053", "050025", "002352", "016441", "013841", "012832", "012769",
                "008682", "011612", "002611", "019260", "000086", "018757", "001071", "006113",
                "004854", "001595", "001551"
            ]
            for tc in tail_codes:
                clone_pm.holdings.pop(tc, None)
            clone_pm.available_cash += 442.70
            clone_pm._recalculate_totals()
            clone_pm.save_state()

            # 核验克隆账本状态
            assert len(clone_pm.holdings) == 10
            assert round(clone_pm.total_market_value, 2) == pytest.approx(26615.10 - 442.70, abs=0.01)

            # 核心断言：原 combat_29_funds 与 main_live 保持绝对原样，毫无渗透污染！
            assert len(combat_pm.holdings) == 29
            assert round(combat_pm.total_market_value, 2) == pytest.approx(combat_mv_orig, abs=0.01)
            assert round(main_pm.total_market_value, 2) == pytest.approx(main_mv_orig, abs=0.01)

        finally:
            mlm.delete_ledger(clone_id)
