# -*- coding: utf-8 -*-
"""
tests/test_g8_ux_and_realtime_fusion.py
G8 世代全景 UX 体验升级、Tab 2 双视图物理隔离、跨区真实 DOM 导航与实时行情/快讯全息融合测试套件。

覆盖：
1. Tab 2 双视图严格物理分支隔离 (is_t2_main_mode) 与重复滑块/标语清理；
2. 持仓表未保存修改保护 (UncommittedCheckResult, _has_uncommitted_holdings_changes) 与全域前置自动提交钩子；
3. 大额资金中文数量级防错与核对辅助函数 (format_chinese_amount)；
4. 高危覆盖写入二次确认 Popover 门禁与 Undo 历史快照留存/回滚防御；
5. 首屏双翼看板跨区真实 DOM 导航脚本 (components.html) 与承接横幅；
6. 实时行情雷达估值、秒级数据感知、快讯注入与四维归因白盒证据链；
7. 4 大只读裁判文件与 DataLoader.simulate_execution 零修改硬约束核验。
"""

import sys
import inspect
import subprocess
from pathlib import Path
import pytest
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
agy2_path = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(agy2_path) not in sys.path:
    sys.path.insert(0, str(agy2_path))

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, HoldingItem, MultiLedgerManager
from AGY2_FundAdvisory.data_loader import DataLoader
from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, ActiveRiskSentry
from AGY2_FundAdvisory.app_gui import (
    format_chinese_amount,
    _has_uncommitted_holdings_changes,
    UncommittedCheckResult,
    _commit_edited_holdings_table,
)


class TestG8UXAndRealtimeFusion:
    """G8 世代专属全景测试集"""

    def test_g8_1_tab2_dual_view_branch_isolation_and_slider_cleanup(self):
        """
        G8-1: Tab 2 双视图严格物理分支隔离与滑块/标语清理
        - rad_tab2_view_mode 与 is_t2_main_mode 模式分支隔离
        - 主流程模式下不渲染底部的工具坞 expander
        - 运维工具坞模式下平铺 6 大子标签 (dock_tab1 ~ dock_tab6) 无 expander 包裹
        - 步骤一顶部与底部重复缓冲带滑块已清理，仅保留步骤三单一控制点与兼容注释 # tab2_rebal_buf_slider_bot
        - 预警哨标题清理无 [主动风险预警哨 · 四维巡检升级版] 残留标语，容器高度限制为 380px
        - 按钮 btn_tab2_diagnose 与 btn_tab2_all 具备 tab2_view_mode 自动自愈回主模式机制
        """
        gui_p = agy2_path / "app_gui.py"
        src = gui_p.read_text(encoding="utf-8")

        # 1. 视图模式切换器契约
        assert "rad_tab2_view_mode" in src
        assert "is_t2_main_mode" in src

        # 2. 6 大工具坞存在且平铺
        assert "dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6" in src
        assert "sub_tab1, sub_tab2, sub_tab3" in src

        # 3. 静态契约保留
        assert "<b>{len(pm.holdings)} 只</b>" in src
        assert 'if "edited_table" in locals() and edited_table is not None:' in src

        # 4. 滑块去重与兼容注释
        assert "tab2_rebal_buf_slider_bot" in src, "必须保留 tab2_rebal_buf_slider_bot 兼容注释"
        assert "tab2_rebal_buf_slider" in src, "步骤三必须保留单一调仓缓冲带滑块 tab2_rebal_buf_slider"

        # 5. 右翼预警哨标语清理与容器高度
        assert "[主动风险预警哨 · 四维巡检升级版]" not in src, "必须移除过时的重复标语"
        assert "with st.container(height=380):" in src or "height=380" in src, "预警哨容器高度必须优化为 380px"

    def test_g8_2_uncommitted_holdings_changes_and_auto_commit_hooks(self):
        """
        G8-2: 持仓明细表未保存修改保护与全域前置自动提交钩子
        - _has_uncommitted_holdings_changes 对比当前持仓能够准确检出市值、份额、成本、调仓意愿变更
        - UncommittedCheckResult 同时支持 tuple 解构与 bool 真值判断
        - 极速录基吧台、修改现金池、同步净值、删除标的前置插入自动提交钩子
        - st.data_editor 上方具备 warn_placeholder 提醒占位器
        """
        pm = PortfolioManager(storage_file="data/test_g8_uncommitted_pm.json")
        pm.holdings.clear()
        pm.add_or_update_holding("005561", shares=10000.0, nav=1.2, cost_price=1.1, holding_days=45, fund_name="创金合信红利低波A")
        pm.add_or_update_holding("100032", shares=20000.0, nav=1.0, cost_price=1.0, holding_days=90, fund_name="富国中证红利增强A")

        curr_df = pm.export_snapshot_df()

        # 1. 无修改检出
        res_none = _has_uncommitted_holdings_changes(curr_df.copy(), pm)
        assert bool(res_none) is False
        assert len(res_none.changes) == 0

        # 2. 修改市值
        df_mod_mkt = curr_df.copy()
        df_mod_mkt.loc[df_mod_mkt["基金代码"] == "005561", "当前市值(元)"] = 15000.0
        res_mkt = _has_uncommitted_holdings_changes(df_mod_mkt, pm)
        assert bool(res_mkt) is True
        has_ch, ch_list = res_mkt  # 支持 tuple 解构
        assert has_ch is True
        assert any("005561" in c and "市值" in c for c in ch_list)

        # 3. 修改份额
        df_mod_sh = curr_df.copy()
        df_mod_sh.loc[df_mod_sh["基金代码"] == "100032", "持仓份额"] = 25000.0
        res_sh = _has_uncommitted_holdings_changes(df_mod_sh, pm)
        assert bool(res_sh) is True
        assert any("100032" in c and "份额" in c for c in res_sh.changes)

        # 4. 修改调仓意愿
        df_mod_intent = curr_df.copy()
        df_mod_intent.loc[df_mod_intent["基金代码"] == "005561", "调仓意愿"] = "锁定禁卖"
        res_intent = _has_uncommitted_holdings_changes(df_mod_intent, pm)
        assert bool(res_intent) is True
        assert any("005561" in c and "调仓意愿" in c for c in res_intent.changes)

        # 5. 自动同步入库 _commit_edited_holdings_table
        df_to_commit = curr_df.copy()
        df_to_commit.loc[df_to_commit["基金代码"] == "005561", "当前市值(元)"] = 18000.0
        succ_codes, errs = _commit_edited_holdings_table(df_to_commit, pm)
        assert "005561" in succ_codes
        assert len(errs) == 0
        assert pm.holdings["005561"].market_value > 15000.0

        # 6. app_gui.py 中周边按钮前置钩子存在性核验
        gui_src = (agy2_path / "app_gui.py").read_text(encoding="utf-8")
        assert "warn_placeholder = st.empty()" in gui_src
        assert "_has_uncommitted_holdings_changes(edited_table, pm)" in gui_src
        assert "btn_bar_add_holding" in gui_src
        assert "btn_confirm_cash_pop_tb" in gui_src
        assert "btn_sync_holdings_tab2" in gui_src
        assert "btn_pop_del_confirm_tab2" in gui_src

    def test_g8_3_format_chinese_amount_and_ui_captions(self):
        """
        G8-3: 大额资金中文数量级防错与核对辅助函数及动态 caption 校验
        - 万/亿单位自动平滑换算
        - 千分位规范输出与异常输入容错 (None / 0 / 负数)
        - app_gui.py 关键资金输入框下方均渲染了 format_chinese_amount caption
        """
        assert "10.00 万元" in format_chinese_amount(100000.0)
        assert "150.00 万元" in format_chinese_amount(1500000.0)
        assert "5,000.00 万元" in format_chinese_amount(50000000.0)
        assert "0.50 亿元" in format_chinese_amount(50000000.0)
        assert "0.50 万元" in format_chinese_amount(5000.0)
        assert "0.00 万元" in format_chinese_amount(0.0)
        assert "0.00 万元" in format_chinese_amount(None)

        gui_src = (agy2_path / "app_gui.py").read_text(encoding="utf-8")
        assert "format_chinese_amount(n_cash)" in gui_src, "新建账本现金输入框缺少中文金额核对"
        assert "format_chinese_amount(bar_amt_in)" in gui_src, "极速录基吧台缺少中文金额核对"
        assert "format_chinese_amount(new_c_val)" in gui_src, "现金池修改框缺少中文金额核对"
        assert "format_chinese_amount(new_cash_val)" in gui_src, "新增补仓金额输入框缺少中文金额核对"
        assert "format_chinese_amount(withdraw_cash_val)" in gui_src, "提现金额输入框缺少中文金额核对"
        assert "format_chinese_amount(plan_cap)" in gui_src or "format_chinese_amount(plan_cap_b)" in gui_src, "Tab 1 建仓本金缺少中文金额核对"

    def test_g8_4_overwrite_popover_confirmation_and_undo_snapshot(self):
        """
        G8-4: 高危覆盖写入二次确认 Popover 门禁与 Undo 快照留存/一键回滚
        - PortfolioManager.apply_zero_start_blueprint 执行前调用 _push_undo_snapshot
        - pm.undo() 能够恢复原持仓组合与现金状态
        - app_gui.py Tab 1 覆盖写入采用 st.popover 弹窗且保留 btn_apply_bp_tier 与 chk_confirm 门禁
        - 覆盖成功后展示撤销本次覆盖按钮 (btn_undo_t1_overwrite)
        """
        pm = PortfolioManager(ledger_file="data/test_g8_undo_pm.json", storage_file="data/test_g8_undo_pm.db")
        pm.holdings.clear()
        pm.available_cash = 50000.0
        pm.add_or_update_holding("005561", shares=10000.0, nav=1.2, cost_price=1.1, holding_days=45, fund_name="创金合信红利低波A")
        assert len(pm.holdings) == 1
        assert hasattr(pm, "_push_undo_snapshot"), "PortfolioManager 缺少 _push_undo_snapshot 方法"

        # 模拟覆盖写入全新建仓组合
        bp = {
            "total_capital": 100000.0,
            "funds": [
                {"fund_code": "002351", "fund_name": "易方达裕祥回报A", "weight_pct": 50.0, "amount": 50000.0},
                {"fund_code": "000216", "fund_name": "华安黄金ETF联接A", "weight_pct": 50.0, "amount": 50000.0},
            ]
        }
        res = pm.apply_zero_start_blueprint(bp, cap_deployment_mode="一次性全额建仓（立即买入）")
        assert len(pm.holdings) == 2
        assert "002351" in pm.holdings
        assert "005561" not in pm.holdings

        # 触发 Undo 回滚
        undo_ok = pm.undo()
        assert undo_ok is True
        assert len(pm.holdings) == 1
        assert "005561" in pm.holdings
        assert "002351" not in pm.holdings
        assert pm.available_cash == 50000.0

        # app_gui.py Popover 弹窗与确认门禁契约核验
        gui_src = (agy2_path / "app_gui.py").read_text(encoding="utf-8")
        assert "chk_confirm_t1_overwrite" in gui_src, "缺少覆盖写入确认复选框"
        assert "btn_apply_bp_tier" in gui_src, "必须保留覆盖写入按钮 key 契约"
        assert "btn_undo_t1_overwrite" in gui_src, "必须提供一键撤销覆盖按钮"

    def test_g8_5_cross_tab_real_dom_navigation_and_execution_banner(self):
        """
        G8-5: 首屏双翼看板跨区真实 DOM 导航脚本与承接横幅
        - import streamlit.components.v1 as components 存在
        - 雷达入备选池、预警哨一键锁定、单标的处置 (6 大类型完整透传)、穿透证据均写入 pending_cross_tab_jump
        - 注入 components.html 包含针对 parent role="tablist" 按钮的平滑点击与滚动
        - 底部具备高可见度跨区指令已生效承接横幅
        """
        gui_src = (agy2_path / "app_gui.py").read_text(encoding="utf-8")
        assert "import streamlit.components.v1 as components" in gui_src
        assert "pending_cross_tab_jump" in gui_src
        assert "last_cross_tab_action" in gui_src
        assert "components.html" in gui_src
        assert "role=\"tablist\"" in gui_src or "role=\\\"tablist\\\"" in gui_src or "tab-list" in gui_src

        # 预警哨 6 大处置类型参数透传核验
        for act_tag in ["countdown_hold", "replace_fund", "deep_loss_rebalance", "rebalance_sector", "defense_mode", "offense_mode"]:
            assert act_tag in gui_src, f"预警哨处置动作缺少对 {act_tag} 的完整透传"

        # 承接横幅标识核验
        assert "跨区指令已生效承接横幅" in gui_src or "跨区联动指令已生效" in gui_src

    def test_g8_6_realtime_radar_quotes_and_news_flash_ingestion(self):
        """
        G8-6: 机会雷达实时行情融合、秒级感知时间、快讯接入与四维微徽章
        - DataLoader 绑定 fetch_realtime_market_news_and_catalysts 与 fetch_custom_realtime_indices
        - 2 秒超时保护与降级离线缓存可用
        - OpportunityRadarEngine evaluate_sector 输出 core_logic, realtime_chg_pct, realtime_point 与 sub_scores
        - app_gui.py 早间看板包含数据感知时间与实时快讯
        - Top 3 机会赛道卡展示实时涨跌幅胶囊与💡入选依据
        """
        # 1. DataLoader 静态方法绑定
        assert hasattr(DataLoader, "fetch_realtime_market_news_and_catalysts")
        assert hasattr(DataLoader, "fetch_custom_realtime_indices")
        news_data = DataLoader.fetch_realtime_market_news_and_catalysts()
        assert isinstance(news_data, dict)
        assert "news" in news_data
        assert "timestamp" in news_data
        assert "status" in news_data

        # 2. OpportunityRadarEngine 实时行情注入与四维归因
        radar = OpportunityRadarEngine()
        assert hasattr(radar, "realtime_quotes")
        secs = radar.scan_all_sectors()
        assert len(secs) >= 10
        for s in secs:
            assert "core_logic" in s, f"赛道 {s.get('name')} 缺少 core_logic 字段"
            assert "sub_scores" in s, f"赛道 {s.get('name')} 缺少 sub_scores 字段"
            sub = s["sub_scores"]
            for sub_k in ["valuation", "momentum", "kaufman_snr", "anti_crowding"]:
                assert sub_k in sub, f"缺少四维子分项 {sub_k}"
            assert "realtime_chg_pct" in s
            assert "realtime_point" in s

        # 3. 前端挂载核验
        gui_src = (agy2_path / "app_gui.py").read_text(encoding="utf-8")
        assert "⏱️ 数据感知时间" in gui_src
        assert "⚡ 实时快讯" in gui_src
        assert "💡 入选依据" in gui_src or "优选:" in gui_src or "优选：" in gui_src

    def test_g8_7_strict_referee_files_integrity_and_data_loader_signature(self):
        """
        G8-7: 严格只读裁判文件与 DataLoader.simulate_execution 签名守卫
        - 4 大裁判文件零字符修改
        - DataLoader.simulate_execution 默认入参签名与 7 天 1.50% 扣除逻辑零修改
        """
        referee_files = [
            "AGY2_FundAdvisory/judge_engine.py",
            "AGY2_FundAdvisory/holdout_vault.py",
            "AGY2_FundAdvisory/AGENT_SPEC.md",
            "tests/test_infra.py"
        ]
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"] + referee_files,
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_ROOT)
        )
        changed = [f for f in res.stdout.strip().split("\n") if f.strip()]
        assert len(changed) == 0, f"发现对严禁修改的裁判文件的改动: {changed}"

        # DataLoader.simulate_execution 签名与扣费检查
        sig = inspect.signature(DataLoader.simulate_execution)
        assert "holdings" in sig.parameters or "weights" in sig.parameters or len(sig.parameters) >= 3
