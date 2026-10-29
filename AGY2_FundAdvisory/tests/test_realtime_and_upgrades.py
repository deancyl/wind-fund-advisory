"""
单元测试集：5 大实战化改造核心功能校验 (tests/test_realtime_and_upgrades.py)
验证：
1. FundQuote 数据模型与 fetch_realtime_fund_quote 联网/缓存/解构/纯债回退机制；
2. 从 0 起步建仓清单生成 (StrategyBridge.generate_zero_start_blueprint) 与一键写入初始持仓；
3. 14:30 尾盘变盘信号推演 (StrategyBridge.evaluate_intraday_signal)；
4. 历史相似行情匹配器 (StrategyBridge.find_historical_analogs)；
5. 实盘影响预估对比引擎 (StrategyBridge.estimate_rebalance_impact)；
6. 分时段实操指引与盘后三步走规矩 (TradingClock.get_action_guidance_for_window)；
7. 明日盯盘待办预案的持久化存储、读取与清理 (save_next_day_plan / get_latest_next_day_plan / clear_next_day_plans)。
"""

import sys
from pathlib import Path
from datetime import datetime, date, time
import urllib.error
from unittest.mock import patch
import pytest

# 确保 AGY2 模块位于 sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_AGY2_DIR = _CURRENT_DIR.parent
_WORKSPACE_ROOT = _AGY2_DIR.parent
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from trading_clock_fee import TradingClock
from portfolio_manager import (
    PortfolioManager,
    FundQuote,
    fetch_realtime_fund_quote,
    fetch_realtime_index_quote,
    clear_realtime_cache,
    _REALTIME_QUOTE_CACHE,
    _REALTIME_INDEX_CACHE
)
from strategy_bridge import StrategyBridge


@pytest.fixture
def temp_pm(tmp_path):
    db_file = tmp_path / "test_upgrades_state.db"
    json_file = tmp_path / "test_upgrades_ledger.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# =====================================================================
# 1. 痛点 1：FundQuote 数据模型与实时估值拉取机制
# =====================================================================

def test_fund_quote_data_model():
    """验证 FundQuote 兼容字典索引、对象属性访问及 5 元组解构"""
    q = FundQuote(
        name="富国中证红利指数增强A",
        dwjz=0.9530,
        gsz=0.9580,
        gszzl=0.52,
        gztime="2026-10-28 14:45",
        fund_code="100032"
    )

    # 1. 字典索引
    assert q["name"] == "富国中证红利指数增强A"
    assert q["dwjz"] == 0.9530
    assert q["gsz"] == 0.9580
    assert q["gszzl"] == 0.52
    assert q["gztime"] == "2026-10-28 14:45"
    assert q["fund_code"] == "100032"

    # 2. 对象属性访问
    assert q.name == "富国中证红利指数增强A"
    assert q.dwjz == 0.9530
    assert q.gsz == 0.9580
    assert q.gszzl == 0.52
    assert q.gztime == "2026-10-28 14:45"
    assert q.fund_code == "100032"

    # 3. 序列解构 [name, dwjz, gsz, gszzl, gztime]
    name, dwjz, gsz, gszzl, gztime = q
    assert name == "富国中证红利指数增强A"
    assert dwjz == 0.9530
    assert gsz == 0.9580
    assert gszzl == 0.52
    assert gztime == "2026-10-28 14:45"

    # 4. 整数索引
    assert q[0] == "富国中证红利指数增强A"
    assert q[3] == 0.52


def test_fetch_realtime_fund_quote_online_and_cache():
    """验证实时行情拉取、15秒防抖缓存与纯债/QDII跟踪指数回退"""
    # 1. 测试拉取富国红利 (100032)
    quote_100032 = fetch_realtime_fund_quote("100032", use_cache=False)
    assert isinstance(quote_100032, FundQuote)
    assert quote_100032.dwjz > 0
    assert quote_100032.gsz > 0
    assert quote_100032.fund_code == "100032"
    assert len(quote_100032.name) > 0

    # 2. 验证防抖缓存：15秒内再次拉取直接命中缓存对象
    quote_cached = fetch_realtime_fund_quote("100032", use_cache=True)
    assert quote_cached is quote_100032

    # 3. 测试纯债基金 002351（新浪通常无 fu 盘中估值，验证优雅联动跟踪基准估算）
    quote_bond = fetch_realtime_fund_quote("002351", use_cache=False)
    assert isinstance(quote_bond, FundQuote)
    assert quote_bond.dwjz > 0
    assert quote_bond.gsz > 0
    assert "002351" in quote_bond.fund_code
    assert "易方达" in quote_bond.name

    # 4. 验证网络异常下的离线湖仓/基准兜底
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network Unreachable")):
        quote_offline = fetch_realtime_fund_quote("005561", use_cache=False)
        assert isinstance(quote_offline, FundQuote)
        assert quote_offline.dwjz > 0
        assert "创金合信" in quote_offline.name


def test_fetch_realtime_index_quote_and_cache_clearing():
    """验证大盘实时指数行情拉取与防抖缓存清空"""
    # 1. 拉取沪深300指数实时点位
    idx_q = fetch_realtime_index_quote("sh000300", use_cache=False)
    assert "point" in idx_q
    assert idx_q["point"] > 0
    assert "change_pct" in idx_q
    assert "time_str" in idx_q

    # 2. 命中缓存
    idx_cached = fetch_realtime_index_quote("sh000300", use_cache=True)
    assert idx_cached["point"] == idx_q["point"]

    # 3. 清空缓存验证
    assert len(_REALTIME_INDEX_CACHE) > 0
    assert len(_REALTIME_QUOTE_CACHE) > 0
    clear_realtime_cache()
    assert len(_REALTIME_INDEX_CACHE) == 0
    assert len(_REALTIME_QUOTE_CACHE) == 0


# =====================================================================
# 2. 痛点 2：从 0 开始建仓清单与初始持仓写入
# =====================================================================

def test_generate_zero_start_blueprint():
    """验证从 0 开始建仓方案生成、5 只核心基金选型、现金分红要求与限额替代"""
    blueprint = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0)

    assert blueprint["total_capital"] == 100000.0
    assert blueprint["allocated_sum"] + blueprint["remaining_cash"] == 100000.0
    items = blueprint["items"]
    assert len(items) >= 5

    items_by_code = {it["fund_code"]: it for it in items}

    # 验证 100032 富国红利与 005561 创金红利低波
    assert "100032" in items_by_code
    assert items_by_code["100032"]["share_class"] == "A"
    assert items_by_code["100032"]["require_cash_dividend"] is True
    assert "现金分红" in items_by_code["100032"]["dividend_advice"]
    assert "A 类" in items_by_code["100032"]["why_share_class"]

    assert "005561" in items_by_code
    assert items_by_code["005561"]["share_class"] == "A"
    assert items_by_code["005561"]["require_cash_dividend"] is True
    assert "现金分红" in items_by_code["005561"]["dividend_advice"]

    # 验证 050025 博时标普500 限额 500 元及备选提示
    assert "050025" in items_by_code
    assert items_by_code["050025"]["share_class"] == "A"
    assert "500" in items_by_code["050025"]["quota_fallback"]
    assert "001071" in items_by_code["050025"]["quota_fallback"] or "513500" in items_by_code["050025"]["quota_fallback"]


def test_apply_zero_start_blueprint_to_portfolio(temp_pm):
    """验证一键将建仓方案写入当前持仓账本"""
    blueprint = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0)
    res = temp_pm.apply_zero_start_blueprint(blueprint)

    assert res["status"] == "SUCCESS"
    assert res["total_capital"] == 100000.0
    assert res["funds_count"] >= 5
    assert abs(temp_pm.baseline_equity - 100000.0) <= 0.05
    assert temp_pm.takeover_mode == "A"

    # 验证持仓中的分红方式正确设置
    h_100032 = temp_pm.holdings["100032"]
    assert h_100032.dividend_method == "cash"
    h_005561 = temp_pm.holdings["005561"]
    assert h_005561.dividend_method == "cash"

    # 验证可用现金精确补齐
    assert temp_pm.available_cash == blueprint["remaining_cash"]


# =====================================================================
# 3. 痛点 1 & 3：14:30 尾盘变盘信号推演与分时段实操指引
# =====================================================================

def test_evaluate_intraday_signal():
    """验证 14:30~15:00 尾盘变盘信号推演引擎"""
    # 1. 默认盘中点位评估
    eval_res = StrategyBridge.evaluate_intraday_signal()
    assert "realtime_c300" in eval_res
    assert "m20" in eval_res
    assert "bias_m20" in eval_res
    assert "current_state" in eval_res
    assert "simulated_state" in eval_res
    assert isinstance(eval_res["is_state_changed"], bool)
    assert eval_res["action_urgency"] in ["URGENT_CHANGE", "STABLE_HOLD"]
    assert len(eval_res["trigger_warning_text"]) > 0

    # 2. 模拟大幅向上突破（例如代入远高于 MA20 的点位）
    m20_val = eval_res["m20"]
    eval_breakout = StrategyBridge.evaluate_intraday_signal(realtime_c300=m20_val * 1.20)
    assert eval_breakout["bias_m20"] > 5.0

    # 3. 模拟大幅下挫（例如代入远低于 MA20 的点位）
    eval_crash = StrategyBridge.evaluate_intraday_signal(realtime_c300=m20_val * 0.80)
    assert eval_crash["bias_m20"] < -5.0


def test_trading_clock_action_guidance():
    """验证 09:30~14:30 观察期、14:30~14:55 黄金窗口与 15:00 后盘后三步走指引"""
    clock = TradingClock()
    trade_date = date(2026, 10, 26) # 星期一

    # 1. 观察期 (11:00)
    dt_obs = datetime.combine(trade_date, time(11, 0, 0))
    g_obs = clock.get_action_guidance_for_window(dt_obs)
    assert g_obs["stage"] == "OBSERVATION"
    assert not g_obs["allow_immediate_exec"]
    assert "只看不动" in g_obs["message"]
    assert "盘中观察中" in g_obs["button_text"]

    # 2. 黄金窗口 (14:35)
    dt_golden = datetime.combine(trade_date, time(14, 35, 0))
    g_golden = clock.get_action_guidance_for_window(dt_golden)
    assert g_golden["stage"] == "GOLDEN_WINDOW"
    assert g_golden["allow_immediate_exec"]
    assert "立即按今日盘中估值执行调仓" in g_golden["button_text"]

    # 3. 盘后锁定期 (15:30)
    dt_post = datetime.combine(trade_date, time(15, 30, 0))
    g_post = clock.get_action_guidance_for_window(dt_post)
    assert g_post["stage"] == "POST_MARKET"
    assert not g_post["allow_immediate_exec"]
    assert "保存为明日 14:30 盯盘待办预案" in g_post["button_text"]
    assert "盘后三步走规矩" in g_post["message"]
    assert "严禁今晚提前挂单买入" in g_post["message"]


# =====================================================================
# 4. 痛点 4：历史相似行情匹配器
# =====================================================================

def test_find_historical_analogs():
    """验证 4 维特征历史行情匹配、间隔>=60日、未来20d/60d收益与回撤"""
    analogs = StrategyBridge.find_historical_analogs(top_k=3, min_gap_days=60)

    assert "matches" in analogs
    matches = analogs["matches"]
    assert len(matches) == 3
    assert len(analogs["summary_text"]) > 0

    # 校验每个匹配项的指标字段
    for m in matches:
        assert isinstance(m["date"], str)
        assert 50.0 <= m["similarity_pct"] <= 99.0
        assert isinstance(m["h300_ret_20d"], float)
        assert isinstance(m["h300_ret_60d"], float)
        assert isinstance(m["strategy_ret_20d"], float)
        assert isinstance(m["strategy_ret_60d"], float)
        assert isinstance(m["strategy_mdd_60d"], float)
        assert len(m["alloc_desc"]) > 0

    # 校验文案格式包含“【XXXX年XX月】”中文大白话
    assert "年" in analogs["summary_text"] and "月" in analogs["summary_text"]
    assert "相似度" in analogs["summary_text"]

    # 校验两两之间的时间跨度间隔 >= 60 日
    dates = [datetime.strptime(m["date"], "%Y-%m-%d").date() for m in matches]
    for i in range(len(dates)):
        for j in range(i + 1, len(dates)):
            diff_days = abs((dates[i] - dates[j]).days)
            assert diff_days >= 60, f"日期 {dates[i]} 与 {dates[j]} 间隔不足 60 日"


def test_cold_start_resolves_realtime_nav(temp_pm):
    """验证极简冷启动未提供 nav 或 nav<=0 时，自动联网拉取真实净值而非硬编码 1.0"""
    items = [
        {"fund_code": "100032", "amount": 38000.0, "nav": 0.0, "holding_tag": ">=30d"},
        {"fund_code": "002351", "amount": 12000.0, "holding_tag": ">=30d"}
    ]
    res = temp_pm.takeover_mode_a(items, available_cash=5000.0)
    assert res["status"] == "SUCCESS"
    h_100032 = temp_pm.holdings["100032"]
    # 真实净值绝非 1.0
    assert h_100032.current_nav > 0
    assert h_100032.cost_price == h_100032.current_nav
    # 份额应按实际净值准确折算
    expected_shares = round(38000.0 / h_100032.current_nav, 2)
    assert abs(h_100032.shares - expected_shares) < 0.05


# =====================================================================
# 5. 痛点 5：实盘影响预估对比引擎
# =====================================================================

def test_estimate_rebalance_impact(temp_pm):
    """验证调仓前后波动率、股息率/防御垫及回本天数对比"""
    # 模拟存量组合：全仓 100032
    temp_pm.add_or_update_holding(
        fund_code="100032",
        shares=100000.0,
        nav=1.0,
        cost_price=1.0,
        holding_days=60,
        holding_tag=">=30d"
    )
    temp_pm.baseline_equity = 100000.0
    temp_pm._recalculate_totals()

    snapshot = StrategyBridge.get_latest_market_snapshot()
    tgt_w = snapshot["target_weights_funds"]
    rebalance_items = [
        {"fund_code": "002351", "est_fee": 12.5},
        {"fund_code": "000216", "est_fee": 15.0}
    ]

    impact = StrategyBridge.estimate_rebalance_impact(
        current_holdings=temp_pm.holdings,
        target_weights_funds=tgt_w,
        total_equity=100000.0,
        rebalance_items=rebalance_items
    )

    assert "vol_before" in impact
    assert "vol_after" in impact
    assert "vol_diff" in impact
    assert "div_before" in impact
    assert "div_after" in impact
    assert "div_diff" in impact
    assert impact["total_fee"] == 27.5
    assert impact["payback_days"] >= 0
    assert "天" in impact["payback_desc"] or "即时" in impact["payback_desc"]


# =====================================================================
# 6. 盘后预案生命周期管理 (save_next_day_plan, get, clear)
# =====================================================================

def test_next_day_plan_lifecycle(temp_pm):
    """验证盘后盯盘待办预案的写入、读取与清理生命周期"""
    # 1. 初始应无预案
    assert temp_pm.get_latest_next_day_plan() is None

    # 2. 保存预案
    test_plan = {
        "target_weights": {"100032": 0.25, "005561": 0.25, "002351": 0.50},
        "reason": "15:00 盘后锁定待办"
    }
    plan_id = temp_pm.save_next_day_plan(test_plan)
    assert plan_id.startswith("PLAN_")

    # 3. 读取最新预案
    latest = temp_pm.get_latest_next_day_plan()
    assert latest is not None
    assert latest["plan_id"] == plan_id
    assert latest["plan"]["target_weights"]["100032"] == 0.25
    assert "target_date" in latest

    # 4. 清理预案
    temp_pm.clear_next_day_plans()
    assert temp_pm.get_latest_next_day_plan() is None
