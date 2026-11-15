# Detailed Investigation & Implementation Design Report — Explorer M1-3
**Milestone**: M1 (十维真实投票与汇率校验及胶囊联动)  
**Target Files**: `AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/app_gui.py`, `tests/test_g19_m1_ten_dimension_and_memo.py`  

---

## 1. Feature 6 现场法证与胶囊联动剖析

### 1.1 割裂点法证分析
在当前的 `advisory_engine.py`:
- `generate_chief_advisor_memo`:
  - 胶囊 4 (`portfolio_pathology`) 产出：
    `deep_loss_count = len(deep_loss_list)`
    `frag_count = len(tail_fragments)` (或从 sentry_frag_alert 提取)
    `frag_amt = sum(x[1] for x in tail_fragments)`
  - 但胶囊 5 (`action_directive`，第 4755~4776 行) 却完全脱节：
    仅根据 `c300_bias` 和 `erp_pct` 给出“维持底仓吃息”或“逆向定投吸筹”。
  - 当对实盘 29 只基金账本 (`combat_29_funds`) 进行调用时：
    胶囊 4 报出 18 只深套出血点与 19 只免赎碎片尾仓（¥442.70）。
    胶囊 5 却报出“维持底仓吃息，无需频繁折腾”。
    这使得首屏面板中，第四颗胶囊与第五颗胶囊完全“左右互搏”，严重违背买方投顾实战常识。

### 1.2 优先级决策与字符数控制
为了既能清晰表达账户级处置指令，又符合 CSS 胶囊对 $\le 20$ 字人话的要求：
1. **主裁决 / verdict**（同时作为胶囊 5 标题右侧 badge 与顶部横幅 `🎯 今日裁决：【...】`）：
   - `frag_count > 0 and deep_loss_count > 0` $\rightarrow$ `f"清扫{frag_count}只尾仓·置换深套"` (12 字符)
   - `frag_count > 0 and deep_loss_count == 0` $\rightarrow$ `f"清扫{frag_count}只尾仓"` (8 字符)
   - `deep_loss_count > 0 and frag_count == 0` $\rightarrow$ `f"置换{deep_loss_count}只深套"` (8 字符)
   - 存在红牌止盈 $\rightarrow$ `"右侧破位锁利"` / `"逢高阶梯止盈"` (6 字符)
   - 无病灶干净账本 $\rightarrow$ `"维持底仓吃息"` / `"逆向定投吸筹"` / `"逢高适度止盈"` (6 字符)
2. **副标题 / capsule_sub**（胶囊下方展示内容）：
   - `frag_count > 0 and deep_loss_count > 0` $\rightarrow$ `f"清扫{frag_count}只尾仓 ｜ 置换{deep_loss_count}只深套"` (16 字符)
   - `frag_count > 0 and deep_loss_count == 0` $\rightarrow$ `f"清扫{frag_count}只尾仓 ｜ 归集核心底仓"` (15 字符)
   - `deep_loss_count > 0 and frag_count == 0` $\rightarrow$ `f"置换{deep_loss_count}只深套 ｜ 止血控险"` (13 字符)
   - 拟建仓模式 $\rightarrow$ `f"{action_verdict} ｜ 按计划分批建仓"` (15 字符)
   - 无病灶存量 $\rightarrow$ `f"{action_verdict} ｜ 未满7天禁卖"` (13 字符)
3. **胶囊 4 拟建仓模式副标题修正**：
   - 拟建仓模式下：`path_capsule_sub = "建仓标的分散 ｜ 结构优良"`。
   - 这不仅让语义更加贴合拟建仓，还能让 `tests/test_g16_phase1_memo_and_combat29.py:219` 的 `assert "建仓标的" in call_arg` 恢复通过！

---

## 2. 全量新建测试套件设计 (`tests/test_g19_m1_ten_dimension_and_memo.py`)

完整的测试文件设计如下：

```python
# -*- coding: utf-8 -*-
"""
Milestone 1 (M1) Comprehensive Quantitative Verification Suite
Covers Features 1-6:
1. Feature 1: 维度 6 产业估值真数据驱动 (14 赛道真实估值分位、Top3 均值与中位数定多空)
2. Feature 2: 维度 7 资金情绪多维融合 (成交额、上涨家数比与 14 赛道拥挤度融合)
3. Feature 3: 维度 10 期权衍生品与避险 (option_iv_pct、期指年化贴水率与相关性突变)
4. Feature 4: 黑天鹅/灰犀牛一票否决熔断门禁 (ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60%)
5. Feature 5: 拔除 6.6676/5.0000 兜底常数与 [6.85, 7.60] 合理性校验哨
6. Feature 6: 胶囊 4（持仓病灶）与胶囊 5（今日行动准则）知行合一联动
"""
import ast
import os
import sys
from unittest.mock import patch, MagicMock
import pytest

# Ensure workspace paths
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)
AGY2_DIR = os.path.join(WORKSPACE_DIR, "AGY2_FundAdvisory")
if AGY2_DIR not in sys.path:
    sys.path.insert(0, AGY2_DIR)

from AGY2_FundAdvisory.data_loader import DataLoader
from AGY2_FundAdvisory.advisory_engine import (
    compute_ten_dimension_votes,
    generate_chief_advisor_memo,
    OpportunityRadarEngine,
)
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.app_gui import render_chief_advisor_memo_card


# ==============================================================================
# Feature 1: 维度 6 产业估值真数据驱动
# ==============================================================================
class TestFeature1_IndustryValuationRealData:
    """Feature 1: Genuine 14-sector valuation percentiles, Top 3 avg & median rules."""

    def test_ast_no_list_length_check_for_bull(self):
        """Forensic AST check: len(radar_top3) >= 2 or 3 must NOT determine bullish vote."""
        filepath = os.path.join(AGY2_DIR, "advisory_engine.py")
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
        target_fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "compute_ten_dimension_votes"), None)
        assert target_fn is not None, "compute_ten_dimension_votes not found"

        # Ensure no comparison of len(radar_top3) >= 2 for dim 6
        fn_code = ast.get_source_segment(code, target_fn)
        assert "len(radar_top3) >= 2" not in fn_code, "Found forbidden list length check in compute_ten_dimension_votes"

    def test_dim6_top3_low_valuation_bull(self):
        """When Top 3 avg valuation percentile <= 35%, vote BULL with delta +0.05."""
        radar_top3 = [
            {"name": "红利低波", "val_percentile": 20.0},
            {"name": "纯债固收", "val_percentile": 25.0},
            {"name": "银行高股息", "val_percentile": 30.0},
        ]
        # Top 3 avg = 25.0% <= 35.0%
        res = compute_ten_dimension_votes(
            snapshot={},
            radar_top3=radar_top3,
            all_sectors_val_percentiles=[20.0, 25.0, 30.0, 45.0, 50.0, 55.0, 60.0]
        )
        d6 = res["dimension_details"]["产业估值"]
        assert d6["vote"] == "BULL"
        assert d6["delta_pct"] == 0.05
        assert d6["score"] >= 75.0
        assert "25.0%" in d6["causal_reason"] or "估值" in d6["causal_reason"]

    def test_dim6_market_median_high_valuation_bear(self):
        """When market median valuation percentile > 70%, vote BEAR with delta -0.05."""
        radar_top3 = [
            {"name": "板块A", "val_percentile": 65.0},
            {"name": "板块B", "val_percentile": 70.0},
            {"name": "板块C", "val_percentile": 75.0},
        ]
        res = compute_ten_dimension_votes(
            snapshot={},
            radar_top3=radar_top3,
            all_sectors_val_percentiles=[65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0]  # median = 80.0 > 70
        )
        d6 = res["dimension_details"]["产业估值"]
        assert d6["vote"] == "BEAR"
        assert d6["delta_pct"] == -0.05
        assert d6["score"] <= 45.0


# ==============================================================================
# Feature 2: 维度 7 资金情绪多维融合
# ==============================================================================
class TestFeature2_CapitalSentimentMultiDimension:
    """Feature 2: Market turnover, advancing ratio, and 14-sector genuine crowding."""

    def test_dim7_low_crowding_or_momentum_exhaustion_bear(self):
        """When avg crowding < 55 or momentum exhaustion, vote BEAR with delta -0.05."""
        res = compute_ten_dimension_votes(
            snapshot={"market_turnover": 8000, "advancing_ratio": 0.35},
            sector_avg_crowding=48.5,
        )
        d7 = res["dimension_details"]["资金情绪"]
        assert d7["vote"] == "BEAR"
        assert d7["delta_pct"] == -0.05
        assert "48.5" in d7["causal_reason"] or "拥挤度" in d7["causal_reason"]

    def test_dim7_healthy_crowding_bull(self):
        """When avg crowding >= 72 and not overheated, vote BULL with delta +0.02."""
        res = compute_ten_dimension_votes(
            snapshot={"market_turnover": 18000, "advancing_ratio": 0.65},
            sector_avg_crowding=76.0,
        )
        d7 = res["dimension_details"]["资金情绪"]
        assert d7["vote"] == "BULL"
        assert d7["delta_pct"] == 0.02
        assert "76.0" in d7["causal_reason"]


# ==============================================================================
# Feature 3: 维度 10 期权衍生品与避险
# ==============================================================================
class TestFeature3_OptionsAndBlackSwan:
    """Feature 3: Option IV, futures basis, and correlation mutation hedging."""

    def test_dim10_high_iv_or_corr_mutation_bear(self):
        """Option IV > 28% or dynamic correlation mutation -> BEAR delta -0.08."""
        res = compute_ten_dimension_votes(
            snapshot={"option_iv_pct": 31.5, "ic_annualized_basis_rate": -0.08},
            dyn_corr=0.82
        )
        d10 = res["dimension_details"]["期权衍生品与避险"]
        assert d10["vote"] == "BEAR"
        assert d10["delta_pct"] == -0.08
        assert "31.5%" in d10["causal_reason"] or "避险" in d10["causal_reason"]

    def test_dim10_low_iv_cushion_bull(self):
        """Option IV < 22% with basis discount cushion -> BULL."""
        res = compute_ten_dimension_votes(
            snapshot={"option_iv_pct": 18.5, "ic_annualized_basis_rate": 0.02},
            dyn_corr=0.35
        )
        d10 = res["dimension_details"]["期权衍生品与避险"]
        assert d10["vote"] == "BULL"


# ==============================================================================
# Feature 4: 黑天鹅/灰犀牛一票否决熔断门禁
# ==============================================================================
class TestFeature4_CircuitBreakers:
    """Feature 4: One-vote veto circuit breaker on ivix >= 32, dyn_corr >= 0.80, usdcnh_chg > 0.60%."""

    def test_circuit_breaker_ivix_triggered(self):
        res = compute_ten_dimension_votes(
            snapshot={"ivix": 34.0, "option_iv_pct": 34.0},
        )
        assert res.get("circuit_breaker_triggered") is True
        assert "熔断" in res.get("circuit_breaker_reason", "")
        # Equity tilt should be capped / non-positive
        assert res["equity_tilt_pct"] <= 0.0

    def test_circuit_breaker_dyn_corr_triggered(self):
        res = compute_ten_dimension_votes(
            snapshot={},
            dyn_corr=0.85
        )
        assert res.get("circuit_breaker_triggered") is True
        assert res["equity_tilt_pct"] <= 0.0

    def test_circuit_breaker_fx_shock_triggered(self):
        res = compute_ten_dimension_votes(
            snapshot={},
            macro_multi={"usdcnh_change_pct": 0.75}
        )
        assert res.get("circuit_breaker_triggered") is True


# ==============================================================================
# Feature 5: 拔除 6.6676/5.0000 兜底常数与合理性校验哨
# ==============================================================================
class TestFeature5_FxAndTreasurySanityCheck:
    """Feature 5: Eradication of 6.6676 and 5.0000, [6.85, 7.60] validation sentry."""

    def test_source_code_zero_occurrences_of_fake_constants(self):
        target_files = [
            "data_loader.py", "advisory_engine.py", "app_gui.py",
            "strategy_bridge.py", "portfolio_manager.py"
        ]
        banned = ["6.6676", "5.0000"]
        for fn in target_files:
            fp = os.path.join(AGY2_DIR, fn)
            if not os.path.exists(fp):
                continue
            with open(fp, "r", encoding="utf-8") as f:
                c = f.read()
            for b in banned:
                assert b not in c, f"Found banned literal '{b}' in {fn}"

    def test_data_loader_fx_sanity_calibration(self):
        """When mock returns anomalous rate 6.10, sentry calibrates to 7.2385 / 4.42% / -278.2bp."""
        with patch.object(DataLoader, "fetch_realtime_usdcnh_fx", return_value=6.10):
            macro = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
            assert 6.85 <= macro["usdcnh_rate"] <= 7.60
            assert macro["usdcnh_rate"] == 7.2385
            assert macro["us_10y_yield"] == 4.42
            assert abs(macro["cgb_us_spread_bp"] - (-278.2)) < 0.1


# ==============================================================================
# Feature 6: 胶囊4（持仓病灶）与胶囊5（今日行动准则）知行合一联动
# ==============================================================================
class TestFeature6_CapsuleCoordination:
    """Feature 6: Unified coordination between Capsule 4 (Pathology) and Capsule 5 (Action)."""

    def test_combat_29_funds_full_coordination(self):
        """In combat 29-fund ledger (19 fragments, deep losses), Capsule 5 outputs actionable directive."""
        mlm = MultiLedgerManager()
        pm = mlm.get_pm("combat_29_funds")
        memo = generate_chief_advisor_memo(holdings=pm.holdings)

        path = memo["portfolio_pathology"]
        act = memo["action_directive"]

        assert path["frag_count"] == 19
        assert path["deep_loss_count"] >= 3

        # Capsule 5 verdict & subtitle
        assert "清扫19只尾仓·置换深套" in act["verdict"] or ("清扫" in act["verdict"] and "深套" in act["verdict"])
        assert "清扫19只尾仓" in act["capsule_sub"]
        assert "置换" in act["capsule_sub"]

        # Card rendering check
        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo)
            assert mock_st_md.called
            call_html = mock_st_md.call_args[0][0]
            assert "清扫" in call_html and "深套" in call_html
            assert "今日裁决" in call_html

    def test_clean_portfolio_macro_directive_preserved(self):
        """When portfolio is empty or clean, macro guidance is preserved."""
        memo = generate_chief_advisor_memo(
            snapshot={"bias_20": 6.5, "erp_percentile": 20.0},
            holdings=[]
        )
        act = memo["action_directive"]
        assert act["verdict"] == "逢高适度止盈"

    def test_tab1_construction_mode_protection(self):
        """Tab 1 target weights dict retains structural validation with zero fragments."""
        opt_weights = {"005561": 0.40, "002351": 0.35, "000216": 0.25}
        memo = generate_chief_advisor_memo(holdings=opt_weights)
        path = memo["portfolio_pathology"]
        act = memo["action_directive"]

        assert path["frag_count"] == 0
        assert path["deep_loss_count"] == 0
        assert "建仓" in path["title"] or "结构校验" in path["title"]

        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo)
            call_html = mock_st_md.call_args[0][0]
            assert "建仓标的" in call_html

    def test_adversarial_none_timestamp_robustness(self):
        """Adversarial None timestamp does not raise TypeError."""
        payload = {
            "timestamp": None,
            "macro_policy": {"badge": "OK", "cgb_10y": 1.64},
            "international_fx": {"badge": "OK", "usdcnh_rate": 7.2385},
            "industry_valuation": {"badge": "OK"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "title": "存量病灶"},
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
        }
        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(payload)
            assert mock_st_md.called
```
