# -*- coding: utf-8 -*-
"""
Adversarial Verification Suite for Milestone 1 (M1)
Challenger 2 (teamwork_challenger)

Tests coverage:
1. 规模反查与清盘告警对抗探针 (AUM Inspection & Liquidation Defense)
2. 适当性越界与盘中异动对抗探针 (Suitability & Intraday Shock Defense)
3. 雷达末端重算与信源验真对抗探针 (Radar Recalculation & News Verification)
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import pytest

# Ensure workspace root and AGY2_FundAdvisory are in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from advisory_engine import ActiveRiskSentry, OpportunityRadarEngine, RADAR_SECTOR_CATALOG
from data_loader import DataLoader, _REALTIME_NEWS_MEM_CACHE, REALTIME_NEWS_CACHE_FILE


# ==============================================================================
# 1. 规模反查与清盘告警对抗探针 (AUM Inspection & Liquidation Defense)
# ==============================================================================
class TestAUMInspectionAndLiquidationDefense:
    """对抗验证：彻底杜绝 2.5 亿元假兜底，实装三级穿透反查、真实迷你基清盘警戒与未知代码待核验黄色告警"""

    def test_real_mini_fund_triggers_liquidation_danger_without_metadata(self):
        """
        对抗场景 1a:
        持有一只本地主数据中真实存在、规模低于 0.5 亿元的迷你基金 (如 007738 淳厚稳惠债券A，规模 0.01 亿)，
        且完全不向 inspect_portfolio 传入 fund_metadata。
        断言：
        1. 必须穿透反查到其真实微小规模 (<0.50 亿)；
        2. 触发红色清盘警戒告警；
        3. aum_status == 'LIQUIDATION_DANGER'，action_type == 'replace_fund'；
        4. 总体状态标记 has_danger=True, all_passed=False。
        """
        sentry = ActiveRiskSentry()
        holdings = [
            {
                "code": "007738",
                "name": "淳厚稳惠债券A",
                "market_value": 15000.0,
                "holding_days": 45,
                "share_class": "A",
                "pnl_pct": 1.2,
            }
        ]

        # 显式不传 fund_metadata，强制触发底层穿透反查
        report = sentry.inspect_portfolio(holdings, fund_metadata=None)

        assert report["all_passed"] is False, "迷你基持仓严禁标记为全通通过！"
        assert report["has_danger"] is True, "规模 < 0.5 亿必须触发红色清盘警戒！"

        liquidation_alerts = [
            a for a in report["alerts"]
            if a.get("dimension") == "本体排雷" and a.get("aum_status") == "LIQUIDATION_DANGER"
        ]
        assert len(liquidation_alerts) == 1, f"未触发预期的清盘警戒告警，实际告警: {report['alerts']}"

        alert = liquidation_alerts[0]
        assert alert["level"] == "red"
        assert alert["fund_code"] == "007738"
        assert alert["aum_billion"] is not None and alert["aum_billion"] < 0.50
        assert "<0.5亿清盘警戒线" in alert["title"]
        assert "清盘终止运作" in alert["desc"]
        assert alert["action_type"] == "replace_fund"

    def test_synthesized_mini_fund_0_35_billion_triggers_liquidation_alert(self):
        """
        对抗场景 1b:
        模拟接口反查返回规模 0.35 亿元的标的（不传 fund_metadata），
        断言必须精确识别 0.35 亿并在标题和字段中呈现清盘风险。
        """
        sentry = ActiveRiskSentry()
        holdings = [
            {
                "code": "019999",
                "name": "测试迷你成长混合A",
                "market_value": 20000.0,
                "holding_days": 60,
                "share_class": "A",
            }
        ]

        with patch("data_loader.DataLoader.get_fund_metadata", return_value={"aum": 0.35}):
            report = sentry.inspect_portfolio(holdings, fund_metadata=None)

        alerts = [
            a for a in report["alerts"]
            if a.get("dimension") == "本体排雷" and a.get("aum_status") == "LIQUIDATION_DANGER"
        ]
        assert len(alerts) == 1
        assert alerts[0]["aum_billion"] == 0.35
        assert "规模仅 0.35 亿元 (<0.5亿清盘警戒线)" in alerts[0]["title"]
        assert alerts[0]["level"] == "red"

    def test_unknown_fund_999999_triggers_pending_verification_yellow_alert(self):
        """
        对抗场景 1c:
        构造未知代码 999999（各级湖仓与接口均无规模记录），且不传 fund_metadata。
        断言：
        1. 绝不允许使用 else: aum = 2.5 静默兜底使其蒙混过关！
        2. aum_billion 必须为 None；
        3. aum_status 必须为 'PENDING_VERIFICATION'；
        4. level 必须为 'yellow'，包含“规模待核验”字样；
        5. all_passed 必须为 False。
        """
        sentry = ActiveRiskSentry()
        holdings = [
            {
                "code": "999999",
                "name": "虚构未知全市场基金",
                "market_value": 30000.0,
                "holding_days": 40,
                "share_class": "A",
            }
        ]

        report = sentry.inspect_portfolio(holdings, fund_metadata=None)

        assert report["all_passed"] is False, "未知基金严禁标记为全通通过！"
        assert report["has_warning"] is True, "未知基金必须触发黄色规模待核验警告！"

        pending_alerts = [
            a for a in report["alerts"]
            if a.get("dimension") == "本体排雷" and a.get("aum_status") == "PENDING_VERIFICATION"
        ]
        assert len(pending_alerts) == 1, f"未触发规模待核验告警，实际告警: {report['alerts']}"

        alert = pending_alerts[0]
        assert alert["level"] == "yellow"
        assert alert["aum_billion"] is None, "规模未知时严禁赋予 2.5 亿元伪常数！"
        assert "【虚构未知全市场基金 (999999)】规模待核验" in alert["title"]
        assert "未能从多级数据湖仓或实时接口获取到该基金最新资产规模" in alert["desc"]
        assert alert["action_type"] == "replace_fund"


# ==============================================================================
# 2. 适当性越界与盘中异动对抗探针 (Suitability & Intraday Shock Defense)
# ==============================================================================
class TestSuitabilityAndIntradayShockDefense:
    """对抗验证：投资者适当性（C1-C5）权益上限及高波违规主动巡检，盘中异动安全垫消耗传导"""

    def test_c1_investor_with_60pct_tech_triggers_red_suitability_alert(self):
        """
        对抗场景 2a:
        设定账本档位为 C1 (安稳保守型，权益上限 20%)，
        实盘持仓配置 60% 科技成长标的 (013841 中韩半导体ETF联接A，市值 60,000 元)
        以及 40% 纯债标的 (002351 易方达裕祥回报债券A，市值 40,000 元)。
        断言：
        1. 抛出 dimension='投资者适当性' 的红色违规预警 (level='red')；
        2. title 包含 '【C1 安稳保守型】权益持仓占比 60.0% 超标 (上限 20%)'；
        3. 明确指出低风险客户持有高波科技/科创标的，超配 ¥40,000.00；
        4. action 提供一键降波纠偏建议平移至纯债 (002351)；
        5. action_type == 'rebalance_sector'。
        """
        sentry = ActiveRiskSentry()
        holdings = [
            {
                "code": "013841",
                "name": "中韩半导体ETF联接A",
                "market_value": 60000.0,
                "holding_days": 40,
                "share_class": "A",
                "pnl_pct": 5.0,
            },
            {
                "code": "002351",
                "name": "易方达裕祥回报债券A",
                "market_value": 40000.0,
                "holding_days": 40,
                "share_class": "A",
                "pnl_pct": 2.0,
            },
        ]

        report = sentry.inspect_portfolio(
            holdings=holdings,
            investor_risk_tier="C1",
            snapshot={}
        )

        suitability_alerts = [
            a for a in report["alerts"]
            if a.get("dimension") == "投资者适当性"
        ]
        assert len(suitability_alerts) == 1, f"未触发适当性越界告警: {report['alerts']}"

        alert = suitability_alerts[0]
        assert alert["level"] == "red", "C1 持有高波科技且大幅超配权益，必须升级为红色严重违规！"
        assert "【C1 安稳保守型】" in alert["title"]
        assert "权益持仓占比 60.0% 超标" in alert["title"]
        assert alert["equity_ratio"] == 0.6
        assert alert["max_equity_ratio"] == 0.2
        assert alert["excess_equity_amount"] == 40000.0
        assert "低风险客户持有高波科技/科创标的" in alert["desc"]
        assert "启动一键降波纠偏" in alert["action"]
        assert "002351" in alert["action"]
        assert alert["action_type"] == "rebalance_sector"

    def test_intraday_valuation_drop_triggers_cushion_consumption_defense(self):
        """
        对抗场景 2b:
        实盘组合持有资产且具备安全垫，传入盘中估值异动 gszzl = -3.5% (科技标的 013841 发生急跌)。
        断言：
        1. 预警哨捕获单基急跌 >= 2.0% 与组合整体下挫；
        2. 触发 dimension='盘中异动安全垫传导' 预警；
        3. title 与 desc 包含 '盘中异动下挫' 与 '安全垫实时消耗'；
        4. action_type == 'defense_mode'；
        5. 提示启动盘中防守机制，待 14:30 尾盘估值锚定企稳。
        """
        sentry = ActiveRiskSentry()
        holdings = [
            {
                "code": "013841",
                "name": "中韩半导体ETF联接A",
                "market_value": 60000.0,
                "holding_days": 40,
                "share_class": "A",
                "pnl_pct": 5.0,  # 浮盈提供安全垫
            },
            {
                "code": "002351",
                "name": "易方达裕祥回报债券A",
                "market_value": 40000.0,
                "holding_days": 40,
                "share_class": "A",
                "pnl_pct": 2.0,  # 浮盈提供安全垫
            },
        ]

        # 模拟盘中实时估值 013841 大跌 -3.5%
        snapshot = {
            "fund_quotes": {
                "013841": {"gszzl": -3.5}
            }
        }

        report = sentry.inspect_portfolio(
            holdings=holdings,
            investor_risk_tier="C3",
            snapshot=snapshot
        )

        shock_alerts = [
            a for a in report["alerts"]
            if a.get("dimension") == "盘中异动安全垫传导"
        ]
        assert len(shock_alerts) == 1, f"未触发盘中异动传导预警: {report['alerts']}"

        alert = shock_alerts[0]
        assert alert["dimension"] == "盘中异动安全垫传导"
        assert "盘中异动下挫" in alert["title"]
        assert "安全垫实时消耗" in alert["title"]
        assert alert["intraday_chg_pct"] == -2.10
        assert alert["intraday_pnl_sum"] == -2100.0
        assert alert["consumed_cushion_ratio"] > 0
        assert alert["action_type"] == "defense_mode"
        assert "14:30" in alert["action"]

    def test_c5_investor_under_equity_cap_no_suitability_violation(self):
        """
        对抗场景 2c (边界鲁棒性):
        C5 进取追击型投资者 (权益上限 95%)，持有 60% 权益标的，
        断言：绝对不触发适当性超配告警（不制造虚假告警）。
        """
        sentry = ActiveRiskSentry()
        holdings = [
            {
                "code": "013841",
                "name": "中韩半导体ETF联接A",
                "market_value": 60000.0,
                "holding_days": 40,
                "share_class": "A",
                "pnl_pct": 5.0,
            },
            {
                "code": "002351",
                "name": "易方达裕祥回报债券A",
                "market_value": 40000.0,
                "holding_days": 40,
                "share_class": "A",
                "pnl_pct": 2.0,
            },
        ]

        report = sentry.inspect_portfolio(
            holdings=holdings,
            investor_risk_tier="C5",
            snapshot={}
        )

        suitability_alerts = [
            a for a in report["alerts"]
            if a.get("dimension") == "投资者适当性"
        ]
        assert len(suitability_alerts) == 0, "C5 客户 60% 权益持仓未超标，严禁误报适当性超限！"


# ==============================================================================
# 3. 雷达末端重算与信源验真对抗探针 (Radar Recalculation & News Verification)
# ==============================================================================
class TestRadarRecalculationAndNewsVerification:
    """对抗验证：机会雷达盘中最新价末端 K 线全套重算，快讯离线兜底严禁 datetime.now() 伪造"""

    def test_radar_evaluate_sector_recalculates_last_kline(self):
        """
        对抗场景 3a:
        调用 OpportunityRadarEngine.evaluate_sector，
        对比静态评估基线 与 传入盘中实时涨跌幅 +5.0% 时的重算结果。
        断言：
        1. 废除粗暴算术相加：bias_20 绝不等于 old_bias + 5.0；
        2. slope_20 与 er_20 均由新序列重算生成，与旧值不同；
        3. vol_20 与 mdd_20 存在且处于合理的正数波动区间；
        4. core_logic 包含自洽的【量化因果链】。
        """
        radar = OpportunityRadarEngine()
        meta = RADAR_SECTOR_CATALOG["csi_300"]

        # 1. 无实时行情的基础评估
        base_eval = radar.evaluate_sector("csi_300", meta)
        base_bias = base_eval["bias_20"]
        base_slope = base_eval["slope_20"]
        base_er = base_eval["er_20"]

        # 2. 融入盘中实时涨幅 +5.0%
        rt_eval = radar.evaluate_sector(
            "csi_300",
            meta,
            realtime_quotes={"csi_300": {"change_pct": 5.0}}
        )
        rt_bias = rt_eval["bias_20"]
        rt_slope = rt_eval["slope_20"]
        rt_er = rt_eval["er_20"]

        # 3. 严格因果律检验：
        # 若旧实现粗暴叠加，则 rt_bias == base_bias + 5.0；
        # 新实现将末端价格乘以 1.05 后重算 MA20 与 Bias20，Bias20 必然不同于简单算术和。
        assert rt_bias != base_bias + 5.0, (
            f"检测到粗暴算术叠加残留缺陷！rt_bias ({rt_bias}) == base_bias ({base_bias}) + 5.0"
        )
        assert rt_slope != base_slope, "slope_20 未随末端价格更新而动态重算！"
        assert rt_er != base_er, "er_20 考夫曼信噪比未随末端价格更新而动态重算！"

        # 4. 风险指标对称披露
        assert "vol_20" in rt_eval and rt_eval["vol_20"] > 0, "缺少 20 日年化波动率！"
        assert "mdd_20" in rt_eval and rt_eval["mdd_20"] >= 0, "缺少 20 日最大回撤！"

        # 5. 量化因果证据链
        assert "core_logic" in rt_eval
        assert "【量化因果链】" in rt_eval["core_logic"], (
            f"core_logic 缺少动态量化因果链标注: {rt_eval.get('core_logic')}"
        )

    def test_news_fetch_offline_cached_fallback_preserves_original_timestamp(self):
        """
        对抗场景 3b:
        模拟网络连接彻底断开 (urlopen 抛出 OSError)，读取本地快照缓存。
        断言：
        1. 返回字典的 is_realtime 必须为 False；
        2. source 必须包含“离线”字样 (如 '离线本地缓存快照')；
        3. timestamp 绝不等于当前的系统精确时间（杜绝 datetime.now() 伪造实时时间）。
        """
        # 清空内存缓存以确保进入网络/磁盘逻辑
        _REALTIME_NEWS_MEM_CACHE["data"] = None

        with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
            res = DataLoader.fetch_realtime_market_news_and_catalysts(force_refresh=True)

        assert res["is_realtime"] is False, "网络断开时 is_realtime 严禁标记为 True！"
        assert "离线" in res["source"], f"source 必须明确标注离线状态，实际 source: {res.get('source')}"

        # 验证时间戳不是假装的当前秒数
        current_second_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        res_timestamp = res.get("timestamp", "")
        assert res_timestamp != current_second_str, (
            f"检测到伪造实时时间戳违规！离线降级时 timestamp ({res_timestamp}) == datetime.now()"
        )

    def test_news_fetch_cold_start_fallback_preserves_offline_baseline(self):
        """
        对抗场景 3c:
        网络断开且本地无磁盘缓存文件（冷启动极致降级）。
        断言：
        1. is_realtime 必须为 False；
        2. source 必须为 '系统离线预置基线'；
        3. timestamp 必须带有 '(离线预置)' 标识；
        4. 绝对未调用 datetime.now() 冒充实时。
        """
        _REALTIME_NEWS_MEM_CACHE["data"] = None

        with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
            with patch.object(Path, "exists", return_value=False):
                res = DataLoader.fetch_realtime_market_news_and_catalysts(force_refresh=True)

        assert res["is_realtime"] is False
        assert res["source"] == "系统离线预置基线"
        assert "离线预置" in res["timestamp"]
        current_second_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        assert res["timestamp"] != current_second_str
