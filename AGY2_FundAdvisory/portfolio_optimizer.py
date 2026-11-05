"""
最大化胜率组合优化器 (portfolio_optimizer.py)
阶段三核心模块：给定候选基金池和目标参数，
搜索使滚动持有胜率最大化的基金组合权重分配。

优化策略:
  1. 预选约 30 只多样化候选（桶间均衡 + 相关性去冗余）
  2. 贪心构造初始解
  3. SLSQP 优化权重
  4. 局部搜索改进基金选择
"""

import datetime
import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from scipy.optimize import minimize

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from winrate_engine import WinRateEngine, HOLDING_PERIODS, simulate_black_swan_stress
from cache_manager import SmartCacheManager
from data_loader import denoise_covariance_matrix

__all__ = [
    "WinRateOptimizer",
    "DEFAULT_CONSTRAINTS",
    "MAX_DRAWDOWN_BY_TIER",
    "QUANT_MODELS_CATALOG",
    "recommend_model_for_regime",
    "execute_market_optimization_flow",
    "simulate_black_swan_stress",
    "_normalize_weights_strict",
]


def _normalize_weights_strict(weights: Dict[str, float]) -> Dict[str, float]:
    """确保权重非负、无 NaN，且严格闭合至 1.000000 (浮点误差 < 1e-6)"""
    cleaned = {k: max(0.0, float(v)) for k, v in weights.items() if np.isfinite(v)}
    tot = sum(cleaned.values())
    if tot <= 1e-12:
        n = max(1, len(weights))
        return {k: round(1.0 / n, 6) for k in weights}
    normed = {k: float(v) / tot for k, v in cleaned.items()}
    keys = list(normed.keys())
    if keys:
        diff = 1.0 - sum(normed.values())
        normed[keys[0]] += diff
    return normed


# ─── 七大机构级量化定权模型目录（名称严格 ≤ 6 字） ────────────────────
QUANT_MODELS_CATALOG: Dict[str, Dict[str, Any]] = {
    "hrp_robust": {
        "key": "hrp_robust",
        "name": "鲁棒双核HRP",
        "badge": "🛡️ 机构首选·高确定性",
        "principle": "层次风险平价(HRP)聚类树分配 + 极值CVaR尾部风险约束，融合条件胜率先验。",
        "advantage": "无需协方差求逆，彻底根除单一赛道押注与历史过拟合，跨周期稳健性最高。",
        "suitable_when": "震荡磨底期、行业快速轮动期、构建全天候高确定性底仓。",
        "source": "De Prado (2016) / 华泰证券人工智能系列",
    },
    "core_satellite": {
        "key": "core_satellite",
        "name": "核心卫星杠铃",
        "badge": "⚖️ 攻守两极·底仓压舱",
        "principle": "70%~80% 纯债红利核心底仓(等方差/逆波动配置) + 20%~30% 高弹性成长/雷达精选卫星仓(信噪比动量加权)。",
        "advantage": "两极配置锁死下行防守底线，同时保留高弹性进攻抓手，兼顾稳健分红与超额收益。",
        "suitable_when": "稳健增值诉求、震荡市防守反击、期望长钱底仓安心吃息。",
        "source": "先锋领航 (Vanguard) 经典核心-卫星架构",
    },
    "all_weather": {
        "key": "all_weather",
        "name": "全天候平价",
        "badge": "🌍 跨周期风险等权",
        "principle": "风险平价(Equal Risk Contribution)规划求解，跨A股宽基、红利、纯债、黄金、海外QDII均衡分配风险边际贡献。",
        "advantage": "消除单一资产周期性崩溃风险，无论经济通胀/紧缩或增长/衰退均具备自适应防御力。",
        "suitable_when": "宏观牛熊不确定、跨大类资产长期配置、防范极端黑天鹅。",
        "source": "桥水基金 (Bridgewater Associates) 达利欧全天候策略",
    },
    "black_litterman": {
        "key": "black_litterman",
        "name": "BL观点融合",
        "badge": "🧬 主客观贝叶斯后验",
        "principle": "以市场均衡配置为先验基准，贝叶斯融合机会雷达Top赛道高信噪比主观观点矩阵与置信度协方差。",
        "advantage": "克服传统均值-方差对期望收益极度敏感的极端权重陷阱，在基准锚定与主动alpha间实现数学最优折中。",
        "suitable_when": "机会雷达主线明确、结构性牛市、存在清晰高胜率赛道观点时。",
        "source": "高盛资产管理 (Goldman Sachs) Black & Litterman (1992)",
    },
    "conditional_winrate": {
        "key": "conditional_winrate",
        "name": "条件胜率最优",
        "badge": "🎯 同温层状态匹配",
        "principle": "当下T_now五维宏观状态向量高斯核加权 + SLSQP非线性规划最大化目标年化达标胜率。",
        "advantage": "直接以目标收益达成概率为优化目标，精准匹配历史宏观同温层样本。",
        "suitable_when": "宏观估值明确、对特定目标年化收益率有刚性达标诉求时。",
        "source": "Wind 智能投顾同温层状态机引擎",
    },
    "cvar_tail": {
        "key": "cvar_tail",
        "name": "尾部风控CVaR",
        "badge": "⚓ 极小化极端回撤",
        "principle": "Rockafellar-Uryasev 95%条件风险价值(CVaR)极小化 + 索提诺下行方差控制，严控5%最恶劣亏损。",
        "advantage": "优先锁死极端暴跌情景下的最大账面浮亏，最小化水下回本天数。",
        "suitable_when": "大盘破位恐慌、期权隐含波动率飙升、极度厌恶深度回撤的避险阶段。",
        "source": "Rockafellar & Uryasev (2000) 凸优化风险测度",
    },
    "kelly_momentum": {
        "key": "kelly_momentum",
        "name": "凯利动量增强",
        "badge": "⚡ 右侧复利进攻",
        "principle": "半凯利准则(Half-Kelly对数期望增长率最大化) + 考夫曼信噪比(Kaufman Efficiency Ratio)动量增强。",
        "advantage": "在防范破产边界的前提下最大化长期几何复利斜率，兼具超买均值回归折价惩罚。",
        "suitable_when": "ERP处于底部高性价比击球区、大盘放量突破MA20生命线的主升浪。",
        "source": "J.L. Kelly (1956) / 动量自适应半凯利公式",
    },
}

# 别名注册，确保现有与未来调用双向兼容
QUANT_MODELS_CATALOG["hrp_cvar"] = QUANT_MODELS_CATALOG["hrp_robust"]
QUANT_MODELS_CATALOG["cond_winrate"] = QUANT_MODELS_CATALOG["conditional_winrate"]
QUANT_MODELS_CATALOG["min_cvar"] = QUANT_MODELS_CATALOG["cvar_tail"]


def recommend_model_for_regime(
    market_snapshot: Optional[Dict[str, Any]] = None,
    target_return_pct: float = 12.0,
) -> Dict[str, Any]:
    """
    根据当下实时市场环境（四维状态：ERP估值分位、MA20乖离率、DR007利率、iVIX期权波动率）
    自动识别所处市场阶段并推荐最匹配的机构级量化模型。
    """
    snap = market_snapshot or {}
    erp_pct = float(snap.get("erp_percentile", 75.0))
    bias_20 = float(snap.get("bias_20", 0.5))
    dr007 = float(snap.get("dr007_7d_ma", 1.65))
    ivix = float(snap.get("option_iv_pct", snap.get("ivix_index", 18.5)))
    m_state = str(snap.get("market_state", "震荡收息期"))
    snr = float(snap.get("er_snr", 0.55))

    if ivix > 26.0 or bias_20 < -2.8 or erp_pct < 35.0 or "防守" in m_state or "避险" in m_state:
        regime_name = "高波防御避险期"
        rec_key = "cvar_tail"
        reason = (
            f"当前期权波动率({ivix:.1f}%)/均线乖离({bias_20:+.2f}%)显示市场处于尾部波动敏感期，"
            f"使用【尾部风控CVaR】可锁死最差5%极端行情的下行底线，严防深套。"
        )
    elif erp_pct >= 65.0 and 0.3 <= bias_20 <= 5.5 and ("进攻" in m_state or "突破" in m_state or target_return_pct >= 18.0):
        regime_name = "底部右侧突破期"
        rec_key = "kelly_momentum"
        reason = (
            f"当前ERP估值分位高达 {erp_pct:.1f}%（权益极度便宜）且站稳MA20均线({bias_20:+.2f}%)，"
            f"使用【凯利动量增强】可顺势捕捉右侧主升浪复利弹性。"
        )
    elif target_return_pct <= 9.0 or "固收" in m_state or "保守" in m_state:
        regime_name = "稳健防守固收期"
        rec_key = "core_satellite"
        reason = (
            f"当前投资画像偏向稳健收息（目标年化 {target_return_pct:.0f}%），"
            f"使用【核心卫星杠铃】以75%~80%纯债红利为压舱底仓，20%卫星仓捕获成长弹性，兼顾安全与收息。"
        )
    elif abs(bias_20) > 3.0 or ivix > 22.0 or erp_pct < 50.0 or "平衡" in m_state:
        regime_name = "宏观变盘平衡期"
        rec_key = "all_weather"
        reason = (
            f"当前大盘乖离率({bias_20:+.2f}%)与期权波动({ivix:.1f}%)显示多资产分化明显，"
            f"使用【全天候平价】跨宽基、红利、纯债、黄金等权均衡风险边际贡献，免疫周期变盘。"
        )
    elif "主线" in m_state or "结构" in m_state or snr > 0.60:
        regime_name = "结构分化主线期"
        rec_key = "black_litterman"
        reason = (
            f"当前市场处于结构性主线分化行情（信噪比 {snr:.2f}），"
            f"使用【BL观点融合】以全市场均衡配置为先验，贝叶斯融入高信噪比赛道主观观点，兼顾胜率与超额。"
        )
    elif erp_pct >= 60.0 and abs(bias_20) <= 2.5:
        regime_name = "高性价比磨底期"
        rec_key = "hrp_robust"
        reason = (
            f"当前ERP处于 {erp_pct:.1f}% 高性价比区、均线窄幅震荡({bias_20:+.2f}%)、DR007利率 {dr007:.2f}% 充裕，"
            f"使用【鲁棒双核HRP】可通过层次聚类均衡配置多资产，消除单一赛道过拟合，确定性最高。"
        )
    else:
        regime_name = "同温层状态匹配期"
        rec_key = "conditional_winrate"
        reason = (
            f"当前市场处于【{m_state}】（ERP分位 {erp_pct:.1f}%，MA20乖离 {bias_20:+.2f}%），"
            f"使用【条件胜率最优】可在历史同温层样本中精准锁定达标率最高的组合。"
        )

    rec_meta = QUANT_MODELS_CATALOG[rec_key]
    return {
        "regime_name": regime_name,
        "recommended_model_key": rec_key,
        "recommended_model_name": rec_meta["name"],
        "reason": reason,
        "erp_percentile": erp_pct,
        "bias_20": bias_20,
        "dr007": dr007,
        "ivix": ivix,
        "models_catalog": QUANT_MODELS_CATALOG,
    }


# ══════════════════════════════════════════════════════════════════
#  约束与参数
# ══════════════════════════════════════════════════════════════════

DEFAULT_CONSTRAINTS = {
    "max_single_weight": 0.30,
    "min_single_weight": 0.05,
    "max_sector_exposure": 0.40,
    "n_funds_range": (5, 8),
    "purchase_limit_penalty": 0.10,
}

MAX_DRAWDOWN_BY_TIER = {
    "C1": 0.05,
    "C2": 0.10,
    "C3": 0.18,
    "C4": 0.25,
    "C5": 0.35,
}


# ══════════════════════════════════════════════════════════════════
#  优化器
# ══════════════════════════════════════════════════════════════════

class WinRateOptimizer:
    """最大化胜率组合优化器"""

    def __init__(
        self,
        nav_matrix: pd.DataFrame,
        candidate_info: pd.DataFrame,
        holding_days: int,
        target_annual_return: float,
        tier: str = "C3",
        constraints: Optional[dict] = None,
        market_snapshot: Optional[Dict[str, Any]] = None,
        target_num_funds: Optional[int] = None,
        model_type: str = "cond_winrate",
    ):
        """
        Parameters
        ----------
        nav_matrix : DatetimeIndex × fund_code 的 NAV 矩阵
        candidate_info : 候选基金信息，含 fund_code, bucket, fund_name 等
        holding_days : 持有交易日数
        target_annual_return : 目标年化收益率 (0.08 = 8%)
        tier : 风险档位 C1~C5
        constraints : 自定义约束条件
        market_snapshot : 当下市场状态快照 (ERP分位、Bias20、Mom60、EWMA波动率、DR007利差)
        """
        self.nav_matrix = nav_matrix
        self.candidate_info = candidate_info
        self.holding_days = holding_days
        self.target_return = target_annual_return
        self.tier = tier
        self.constraints = {**DEFAULT_CONSTRAINTS, **(constraints or {})}
        self.model_type = model_type if model_type in QUANT_MODELS_CATALOG else "hrp_robust"
        self.target_num_funds = int(max(3, min(15, target_num_funds))) if target_num_funds is not None else None
        if self.target_num_funds is not None:
            n_f = self.target_num_funds
            self.constraints["n_funds_range"] = (n_f, n_f)
            self.constraints["max_single_weight"] = float(min(0.55, max(0.15, round(2.2 / n_f, 2))))
            self.constraints["min_single_weight"] = float(max(0.02, min(0.08, round(0.45 / n_f, 3))))
        self.max_dd = MAX_DRAWDOWN_BY_TIER.get(tier, 0.18)
        self.market_snapshot = market_snapshot
        if self.market_snapshot is None:
            try:
                from strategy_bridge import StrategyBridge
                self.market_snapshot = StrategyBridge.get_latest_market_snapshot()
            except Exception:
                self.market_snapshot = None

        # 预计算个体指标
        self._individual_metrics: Optional[pd.DataFrame] = None

    # ─── 预计算个体指标 ─────────────────────────────────────────

    def _precompute_individual_metrics(
        self, progress_callback: Optional[Callable] = None
    ) -> pd.DataFrame:
        """
        预计算每只候选基金的个体指标（含条件胜率与均值回归修正）。
        """
        if self._individual_metrics is not None:
            return self._individual_metrics

        codes = [c for c in self.candidate_info["fund_code"]
                 if c in self.nav_matrix.columns]

        metrics = []
        total = len(codes)
        for i, code in enumerate(codes):
            nav_s = self.nav_matrix[code].dropna()
            if len(nav_s) < self.holding_days + 10:
                continue

            nav = nav_s.values
            n = len(nav)

            # 基本指标
            daily_ret = nav[1:] / nav[:-1] - 1.0
            total_ret = nav[-1] / nav[0] - 1.0
            years = n / 250.0
            ann_ret = (1 + total_ret) ** (1 / max(years, 0.1)) - 1.0 if total_ret > -1 else -1.0

            rf_daily = 0.02 / 250.0
            excess = daily_ret - rf_daily
            std = np.std(excess, ddof=1)
            sharpe = float(np.mean(excess) / max(std, 1e-10) * np.sqrt(250))

            cummax = np.maximum.accumulate(nav)
            dd = (nav - cummax) / cummax
            max_dd_val = float(np.min(dd))

            # 条件胜率与不亏损率
            wr_dict = WinRateEngine.rolling_target_winrate(
                nav_s, self.holding_days, self.target_return,
                include_friction=True,
                market_snapshot=self.market_snapshot,
            )
            cond_wr = wr_dict.get("conditional_win_rate", wr_dict["win_rate"])
            uncond_wr = wr_dict.get("unconditional_win_rate", wr_dict["win_rate"])
            no_loss = wr_dict.get("no_loss_rate", 0.0)

            # 获取 bucket 与元数据
            info_row = self.candidate_info[self.candidate_info["fund_code"] == code]
            bucket = info_row.iloc[0]["bucket"] if not info_row.empty else "other"
            fund_name = str(info_row.iloc[0].get("fund_name", "")) if not info_row.empty else ""

            # 短期超买与估值高位惩罚 (均值回归修正)
            ret_1y = float(nav[-1] / nav[max(0, n - 250)] - 1.0) if n >= 20 else ann_ret
            ma20_last = float(np.mean(nav[-20:])) if n >= 20 else nav[-1]
            bias20_last = float((nav[-1] / ma20_last - 1.0) * 100.0) if ma20_last > 0 else 0.0

            if ret_1y > 0.35 and bias20_last > 6.0:
                # 均值回归扣减与超买惩罚
                ann_ret = max(-0.5, ann_ret - 0.05)
                cond_wr = max(0.01, cond_wr - 0.08)

            # 估值底部高性价比安全垫奖励
            erp_now = float((self.market_snapshot or {}).get("erp_percentile", 50.0))
            if erp_now >= 75.0:
                if bucket in ["balanced_debt", "fof"] or "红利" in fund_name or "价值" in fund_name:
                    cond_wr = min(0.99, cond_wr + 0.05)

            metrics.append({
                "fund_code": code,
                "bucket": bucket,
                "sharpe": sharpe,
                "max_dd": max_dd_val,
                "annual_return": ann_ret,
                "volatility": float(np.std(daily_ret, ddof=1) * np.sqrt(250)),
                "win_rate": cond_wr,
                "conditional_win_rate": cond_wr,
                "unconditional_win_rate": uncond_wr,
                "no_loss_rate": no_loss,
            })

            if progress_callback and (i + 1) % 20 == 0:
                progress_callback(i + 1, total, f"个体指标计算: {i+1}/{total}")

        self._individual_metrics = pd.DataFrame(metrics)
        return self._individual_metrics

    # ─── 多样化预选 ────────────────────────────────────────────

    def _select_diverse_candidates(
        self, n_target: int = 30, progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """
        从候选池中预选约 n_target 只进入优化器：
        1. 每个 bucket 至少选 2 只
        2. 优先选胜率高的
        3. 剔除相关系数 > 0.85 的冗余基金
        """
        metrics = self._precompute_individual_metrics(progress_callback)
        if metrics.empty:
            return []

        # 按胜率排序
        metrics_sorted = metrics.sort_values("win_rate", ascending=False)

        selected: List[str] = []
        selected_set = set()

        # Phase 1: 每桶至少选 2 只最佳
        for bucket, grp in metrics_sorted.groupby("bucket"):
            top = grp.head(3)
            for _, row in top.iterrows():
                code = row["fund_code"]
                if code not in selected_set and len(selected) < n_target:
                    selected.append(code)
                    selected_set.add(code)

        # Phase 2: 按全局胜率填充至 n_target
        for _, row in metrics_sorted.iterrows():
            code = row["fund_code"]
            if code in selected_set:
                continue
            if len(selected) >= n_target:
                break

            # 检查与已选基金的相关性
            if self._is_redundant(code, selected, threshold=0.85):
                continue

            selected.append(code)
            selected_set.add(code)

        return selected

    def _is_redundant(
        self, code: str, selected: List[str], threshold: float = 0.85
    ) -> bool:
        """检查 code 是否与已选基金高度相关"""
        if not selected or code not in self.nav_matrix.columns:
            return False

        nav_new = self.nav_matrix[code].dropna()
        for s_code in selected:
            if s_code not in self.nav_matrix.columns:
                continue
            nav_existing = self.nav_matrix[s_code].dropna()
            # 对齐
            common_idx = nav_new.index.intersection(nav_existing.index)
            if len(common_idx) < 60:
                continue
            corr = np.corrcoef(nav_new[common_idx].values, nav_existing[common_idx].values)[0, 1]
            if abs(corr) > threshold:
                return True
        return False

    # ─── 主优化函数 ────────────────────────────────────────────

    def optimize(
        self,
        quota_info: Optional[Dict[str, Dict]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        主优化函数。

        返回最优组合的权重、胜率、指标和详细信息。
        """
        import time as _time
        t0 = _time.monotonic()

        if progress_callback:
            progress_callback(0, 5, "预计算个体指标...")

        metrics = self._precompute_individual_metrics(progress_callback)
        if metrics.empty:
            return self._empty_result("无有效候选基金")

        if progress_callback:
            progress_callback(1, 5, "多样化预选...")

        # 预选（随用户设定基金数 N∈[3,15] 自适应扩容候选池）
        n_funds_min, n_funds_max = self.constraints["n_funds_range"]
        pool_target = min(max(30, n_funds_max * 3), len(metrics))
        diverse_codes = self._select_diverse_candidates(
            n_target=pool_target, progress_callback=progress_callback
        )
        # 若相关性过滤后不足 n_funds_max，按评分依序补足确保 3~15 只全覆盖
        if len(diverse_codes) < min(n_funds_max, len(metrics)):
            for _fc in metrics.sort_values("win_rate", ascending=False)["fund_code"]:
                if _fc not in diverse_codes:
                    diverse_codes.append(_fc)
                if len(diverse_codes) >= min(max(n_funds_max + 4, 15), len(metrics)):
                    break

        if len(diverse_codes) < n_funds_min:
            return self._empty_result(f"有效候选不足 {n_funds_min} 只")

        if progress_callback:
            progress_callback(2, 5, f"对 {len(diverse_codes)} 只候选优化权重...")

        # 准备 NAV 子矩阵
        sub_nav = self.nav_matrix[diverse_codes].dropna()
        if len(sub_nav) < self.holding_days + 10:
            return self._empty_result("NAV 数据长度不足")

        # 样本外稳健性切分 (Out-of-Sample Split: 前 70% 训练，后 30% 验证)
        n_nav = len(sub_nav)
        split_idx = max(int(n_nav * 0.70), self.holding_days + 10)
        train_nav = sub_nav.iloc[:split_idx]
        val_nav = sub_nav.iloc[split_idx:]

        # 尝试不同基金数量，选最优
        best_result = None
        best_winrate = -1.0

        for n_funds in range(n_funds_min, min(n_funds_max + 1, len(diverse_codes) + 1)):
            result = self._optimize_fixed_n(
                diverse_codes, sub_nav, n_funds, quota_info, progress_callback
            )
            if result:
                res_metric = result.get("portfolio_metrics", {})
                res_wr = float(res_metric.get("conditional_win_rate", res_metric.get("win_rate", 0)))
                if res_wr > best_winrate:
                    best_winrate = res_wr
                    best_result = result

        if best_result is None:
            return self._empty_result("优化器未找到可行解")

        if progress_callback:
            progress_callback(3, 5, "计算 Monte Carlo 置信区间与样本外验证...")

        # 对最优解计算完整的组合胜率（含 MC 与条件胜率）
        composite = WinRateEngine.portfolio_composite_winrate(
            sub_nav,
            best_result["optimal_weights"],
            self.holding_days,
            self.target_return,
            market_snapshot=self.market_snapshot,
        )
        r_wr = composite.get("rolling_winrate", {})
        cond_wr = float(r_wr.get("conditional_win_rate", r_wr.get("win_rate", 0.0)))
        uncond_wr = float(r_wr.get("unconditional_win_rate", r_wr.get("win_rate", 0.0)))

        # 样本外 (OOS) 验证集胜率
        val_wr = cond_wr
        if len(val_nav) > 20:
            val_hdays = min(self.holding_days, len(val_nav) - 5)
            if val_hdays > 0:
                val_comp = WinRateEngine.portfolio_composite_winrate(
                    val_nav,
                    best_result["optimal_weights"],
                    val_hdays,
                    self.target_return,
                    market_snapshot=self.market_snapshot,
                )
                val_wr = float(val_comp.get("rolling_winrate", {}).get("conditional_win_rate", cond_wr))

        def _clamp_rate(v: Any) -> float:
            try:
                return float(min(1.0, max(0.0, float(v))))
            except Exception:
                return 0.0

        best_result["portfolio_metrics"]["win_rate"] = _clamp_rate(cond_wr)
        best_result["portfolio_metrics"]["conditional_win_rate"] = _clamp_rate(cond_wr)
        best_result["portfolio_metrics"]["unconditional_win_rate"] = _clamp_rate(uncond_wr)
        best_result["portfolio_metrics"]["oos_win_rate"] = _clamp_rate(val_wr)
        best_result["portfolio_metrics"]["monte_carlo_prob"] = _clamp_rate(
            composite.get("monte_carlo", {}).get("prob_reach_target", 0.0)
        )
        best_result["portfolio_metrics"]["no_loss_rate"] = _clamp_rate(
            composite.get("rolling_winrate", {}).get("no_loss_rate", 0.0)
        )
        best_result["monte_carlo_detail"] = composite.get("monte_carlo", {})
        best_result["component_winrates"] = composite.get("component_winrates", {})

        if progress_callback:
            progress_callback(4, 5, "生成基金详细信息...")

        best_result["optimal_weights"] = _normalize_weights_strict(best_result["optimal_weights"])
        # 补充基金详细信息与日度组合净值序列
        best_result["fund_details"] = self._build_fund_details(
            best_result["optimal_weights"], metrics
        )
        try:
            best_result["portfolio_nav_series"] = self._build_portfolio_nav(nav_df, best_result["optimal_weights"])
        except Exception:
            best_result["portfolio_nav_series"] = None

        # 双向兼容顶层字段，彻底根治 0.0% 回显
        best_result["portfolio_annual_return"] = float(best_result.get("portfolio_metrics", {}).get("expected_return_annualized", 0.0))
        best_result["win_rate"] = float(best_result.get("portfolio_metrics", {}).get("conditional_win_rate", best_result.get("portfolio_metrics", {}).get("win_rate", 0.0)))
        best_result["holding_period"] = self._holding_period_label()
        best_result["target_return"] = self.target_return
        best_result["tier"] = self.tier

        elapsed = _time.monotonic() - t0
        model_meta = QUANT_MODELS_CATALOG.get(self.model_type, QUANT_MODELS_CATALOG["hrp_robust"])
        best_result["model_type"] = self.model_type
        best_result["model_name"] = model_meta["name"]
        best_result["model_principle"] = model_meta["principle"]
        best_result["optimization_metadata"] = {
            "candidates_screened": len(metrics),
            "candidates_entered_optimizer": len(diverse_codes),
            "optimization_time_seconds": round(elapsed, 2),
            "method": f"{model_meta['name']} ({self.model_type})",
            "target_num_funds": self.target_num_funds or len(best_result.get("optimal_weights", {})),
        }

        if progress_callback:
            progress_callback(5, 5, "优化完成！")

        return best_result

    def _optimize_fixed_n(
        self,
        all_codes: List[str],
        nav_df: pd.DataFrame,
        n_funds: int,
        quota_info: Optional[Dict[str, Dict]],
        progress_callback: Optional[Callable],
    ) -> Optional[Dict[str, Any]]:
        """对固定 n_funds 只基金做优化"""
        metrics = self._individual_metrics
        if metrics is None:
            return None

        # 根据所选机构模型对候选基金进行特征排序
        sub_m = metrics[metrics["fund_code"].isin(all_codes)].copy()
        m_t = self.model_type
        if m_t in ("cvar_tail", "min_cvar"):
            sub_m["_model_rank_score"] = (
                0.45 * sub_m["no_loss_rate"]
                + 0.35 * (1.0 - np.clip(np.abs(sub_m["max_dd"]) / max(self.max_dd * 1.5, 0.05), 0.0, 1.0))
                + 0.20 * sub_m["win_rate"]
            )
        elif m_t in ("kelly_momentum",):
            sub_m["_model_rank_score"] = (
                0.50 * np.clip(sub_m["annual_return"] / max(self.target_return, 0.05), -0.5, 2.0)
                + 0.30 * sub_m["win_rate"]
                + 0.20 * np.clip(sub_m["sharpe"] / 2.0, -0.5, 1.5)
            )
        elif m_t in ("hrp_robust", "hrp_cvar"):
            sub_m["_model_rank_score"] = (
                0.40 * sub_m["win_rate"]
                + 0.35 * np.clip(sub_m["sharpe"] / 2.0, 0.0, 1.5)
                + 0.25 * (1.0 - np.clip(np.abs(sub_m["max_dd"]) / max(self.max_dd * 1.5, 0.05), 0.0, 1.0))
            )
        elif m_t in ("core_satellite",):
            is_core = sub_m["bucket"].isin(["pure_bond", "fixed_income_plus", "dividend_value", "gold"])
            sub_m["_model_rank_score"] = np.where(
                is_core,
                0.55 * sub_m["no_loss_rate"] + 0.45 * (1.0 - np.clip(np.abs(sub_m["max_dd"]) / 0.10, 0.0, 1.0)),
                0.50 * sub_m["win_rate"] + 0.50 * np.clip(sub_m["sharpe"] / 1.5, 0.0, 1.5),
            )
        elif m_t in ("all_weather",):
            sub_m["_model_rank_score"] = (
                0.40 * np.clip(sub_m["sharpe"] / 2.0, 0.0, 1.5)
                + 0.35 * sub_m["no_loss_rate"]
                + 0.25 * sub_m["win_rate"]
            )
        elif m_t in ("black_litterman",):
            sub_m["_model_rank_score"] = (
                0.45 * sub_m["win_rate"]
                + 0.35 * np.clip(sub_m["sharpe"] / 2.0, -0.2, 1.5)
                + 0.20 * np.clip(sub_m["annual_return"] / max(self.target_return, 0.05), 0.0, 2.0)
            )
        else:  # conditional_winrate / cond_winrate
            sub_m["_model_rank_score"] = sub_m.get("conditional_win_rate", sub_m["win_rate"])
        sorted_by_wr = sub_m.sort_values("_model_rank_score", ascending=False)

        initial_codes: List[str] = []
        buckets_used = set()
        max_sector = self.constraints["max_sector_exposure"]

        for _, row in sorted_by_wr.iterrows():
            code = row["fund_code"]
            bucket = row["bucket"]

            # 同桶数量检查
            same_bucket_count = sum(
                1 for c in initial_codes
                if metrics[metrics["fund_code"] == c].iloc[0]["bucket"] == bucket
            ) if initial_codes else 0

            # 粗略检查同桶不超过比例限制允许的数量
            if same_bucket_count >= max(2, int(n_funds * max_sector)):
                continue

            # 回撤约束
            if abs(row["max_dd"]) > self.max_dd * 1.5:  # 个体允许 1.5 倍组合约束
                continue

            initial_codes.append(code)
            buckets_used.add(bucket)

            if len(initial_codes) >= n_funds:
                break

        if len(initial_codes) < n_funds:
            # 放松约束补充
            for _, row in sorted_by_wr.iterrows():
                if row["fund_code"] not in initial_codes:
                    initial_codes.append(row["fund_code"])
                    if len(initial_codes) >= n_funds:
                        break

        if len(initial_codes) < n_funds:
            return None

        selected_codes = initial_codes[:n_funds]

        # 按所选机构模型求解最优权重 (HRP / 条件胜率 / 尾部CVaR / 凯利动量)
        optimal_weights = self._optimize_by_model_type(selected_codes, nav_df, quota_info)

        if optimal_weights is None:
            # 等权回退
            eq_w = 1.0 / n_funds
            optimal_weights = {c: eq_w for c in selected_codes}
        optimal_weights = _normalize_weights_strict(optimal_weights)

        # 计算组合胜率（接入当下 market_snapshot 条件胜率）
        wr = WinRateEngine.rolling_target_winrate(
            self._build_portfolio_nav(nav_df, optimal_weights),
            self.holding_days,
            self.target_return,
            market_snapshot=self.market_snapshot,
        )

        # 计算组合指标
        pnav = self._build_portfolio_nav(nav_df, optimal_weights).values
        daily_ret = pnav[1:] / pnav[:-1] - 1.0
        cummax = np.maximum.accumulate(pnav)
        dd = (pnav - cummax) / cummax
        max_dd_val = float(np.min(dd))
        ann_vol = float(np.std(daily_ret, ddof=1) * np.sqrt(250))
        total_ret = pnav[-1] / pnav[0] - 1.0
        years = len(pnav) / 250.0
        ann_ret = (1 + total_ret) ** (1 / max(years, 0.1)) - 1.0 if total_ret > -1 else -1.0
        sharpe = (ann_ret - 0.02) / max(ann_vol, 1e-10)

        # 局部搜索改进
        improved = self._local_search(
            selected_codes, optimal_weights, all_codes, nav_df,
            current_winrate=wr["win_rate"], quota_info=quota_info,
        )
        if improved:
            selected_codes, optimal_weights, wr = improved
            optimal_weights = _normalize_weights_strict(optimal_weights)
            pnav = self._build_portfolio_nav(nav_df, optimal_weights).values
            daily_ret = pnav[1:] / pnav[:-1] - 1.0
            cummax = np.maximum.accumulate(pnav)
            dd = (pnav - cummax) / cummax
            max_dd_val = float(np.min(dd))
            ann_vol = float(np.std(daily_ret, ddof=1) * np.sqrt(250))
            total_ret = pnav[-1] / pnav[0] - 1.0
            years = len(pnav) / 250.0
            ann_ret = (1 + total_ret) ** (1 / max(years, 0.1)) - 1.0 if total_ret > -1 else -1.0
            sharpe = (ann_ret - 0.02) / max(ann_vol, 1e-10)

        return {
            "optimal_weights": _normalize_weights_strict(optimal_weights),
            "portfolio_metrics": {
                "win_rate": float(min(1.0, max(0.0, float(wr.get("conditional_win_rate", wr["win_rate"]))))),
                "conditional_win_rate": float(min(1.0, max(0.0, float(wr.get("conditional_win_rate", wr["win_rate"]))))),
                "unconditional_win_rate": float(min(1.0, max(0.0, float(wr.get("unconditional_win_rate", wr["win_rate"]))))),
                "no_loss_rate": float(min(1.0, max(0.0, float(wr["no_loss_rate"])))),
                "monte_carlo_prob": 0.0,  # 后续补充
                "expected_return_annualized": ann_ret,
                "max_drawdown": max_dd_val,
                "sharpe_ratio": sharpe,
                "volatility_annualized": ann_vol,
            },
        }

    def _compute_hrp_weights(self, codes: List[str], nav_df: pd.DataFrame) -> Dict[str, float]:
        """
        层次风险平价 (Hierarchical Risk Parity - Lopez de Prado) + Black-Litterman 状态倾斜
        1. 计算日收益率相关性距离矩阵 D = sqrt(0.5 * (1 - Corr))
        2. 凝聚层次聚类准对角化 (Quasi-Diagonalization)
        3. 递归二分逆下行半方差分配 (Recursive Bisection with Downside Risk)
        """
        from scipy.cluster.hierarchy import linkage, leaves_list
        from scipy.spatial.distance import squareform

        n = len(codes)
        if n <= 1:
            return {codes[0]: 1.0} if n == 1 else {}

        sub_nav = nav_df[codes].dropna()
        if len(sub_nav) < 30:
            return {c: 1.0 / n for c in codes}

        ret_df = sub_nav.pct_change().dropna()
        corr = ret_df.corr().fillna(0.0).to_numpy(copy=True)
        np.fill_diagonal(corr, 1.0)
        corr = np.clip(corr, -1.0, 1.0)
        corr = denoise_covariance_matrix(corr, n_obs=len(ret_df), shrink_alpha=0.15)

        dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
        np.fill_diagonal(dist, 0.0)
        try:
            condensed = squareform(dist, checks=False)
            link = linkage(condensed, method="single")
            sort_ix = list(leaves_list(link))
        except Exception:
            sort_ix = list(range(n))

        ordered_codes = [codes[i] for i in sort_ix]
        cov = ret_df[ordered_codes].cov().values * 250.0
        cov = denoise_covariance_matrix(cov, n_obs=len(ret_df), shrink_alpha=0.15)

        def _get_cluster_var(cov_mat: np.ndarray, c_items: List[int]) -> float:
            cov_slice = cov_mat[np.ix_(c_items, c_items)]
            ivp = 1.0 / np.maximum(np.diag(cov_slice), 1e-8)
            ivp /= np.sum(ivp)
            return float(np.dot(ivp, np.dot(cov_slice, ivp)))

        weights = pd.Series(1.0, index=range(n))
        clusters = [list(range(n))]
        while len(clusters) > 0:
            clusters = [
                i[j:k]
                for i in clusters
                for j, k in ((0, len(i) // 2), (len(i) // 2, len(i)))
                if len(i) > 1
            ]
            for i in range(0, len(clusters), 2):
                if i + 1 >= len(clusters):
                    break
                c0 = clusters[i]
                c1 = clusters[i + 1]
                v0 = _get_cluster_var(cov, c0)
                v1 = _get_cluster_var(cov, c1)
                alpha = 1.0 - v0 / max(v0 + v1, 1e-10)
                weights[c0] *= alpha
                weights[c1] *= (1.0 - alpha)

        # 融合 Black-Litterman 当下条件胜率主观视图 (70% HRP风险底盘 + 30% 同温层胜率倾斜)
        metrics = self._individual_metrics
        raw_w = {}
        for idx_pos, c in enumerate(ordered_codes):
            w_hrp = float(weights.iloc[idx_pos])
            wr_prior = 0.5
            if metrics is not None and not metrics.empty:
                m_row = metrics[metrics["fund_code"] == c]
                if not m_row.empty:
                    wr_prior = float(m_row.iloc[0].get("conditional_win_rate", 0.5))
            raw_w[c] = w_hrp * (0.70 + 0.60 * wr_prior)

        # 投影到单基上下限约束 [min_w, max_w]
        max_w = self.constraints["max_single_weight"]
        min_w = self.constraints["min_single_weight"]
        w_arr = np.array([raw_w[c] for c in codes], dtype=float)
        w_arr = w_arr / max(np.sum(w_arr), 1e-10)
        for _ in range(5):
            w_arr = np.clip(w_arr, min_w, max_w)
            s = np.sum(w_arr)
            if s > 0:
                w_arr /= s
        return _normalize_weights_strict({c: float(w) for c, w in zip(codes, w_arr)})

    def _compute_core_satellite_weights(
        self,
        codes: List[str],
        nav_df: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        核心-卫星杠铃模型 (Core-Satellite Barbell)
        1. 划分核心底仓 (纯债固收、红利价值、黄金) 与卫星仓 (成长科技、海外QDII、宽基核心)
        2. 依据风险档位设定杠铃比例：核心 70%~80%，卫星 20%~30%
        3. 核心仓内按逆波动/逆下行风险配置，卫星仓内按考夫曼信噪比/夏普比率加权
        4. 满足单基权重约束并严格归一化 (sum == 1.0)
        """
        n = len(codes)
        if n <= 1:
            return {codes[0]: 1.0} if n == 1 else {}

        sub_nav = nav_df[codes].dropna()
        if len(sub_nav) < 10:
            return _normalize_weights_strict({c: 1.0 / n for c in codes})

        ret_df = sub_nav.pct_change().dropna()
        vols = ret_df.std().values * np.sqrt(250.0)
        vol_map = {c: max(float(v), 0.01) for c, v in zip(codes, vols)}

        core_buckets = {"pure_bond", "fixed_income_plus", "dividend_value", "gold", "bond", "dividend"}
        core_codes = []
        sat_codes = []

        m_dict = {}
        if self._individual_metrics is not None and not self._individual_metrics.empty:
            m_dict = {r["fund_code"]: r for _, r in self._individual_metrics.iterrows()}

        for c in codes:
            b = "other"
            if not self.candidate_info.empty:
                c_row = self.candidate_info[self.candidate_info["fund_code"] == c]
                if not c_row.empty:
                    b = str(c_row.iloc[0].get("bucket", "other"))
            if b in core_buckets:
                core_codes.append(c)
            else:
                sat_codes.append(c)

        if not core_codes or not sat_codes:
            sorted_by_vol = sorted(codes, key=lambda c: vol_map.get(c, 0.1))
            split_pt = max(1, len(codes) // 2)
            core_codes = sorted_by_vol[:split_pt]
            sat_codes = sorted_by_vol[split_pt:]

        tier_core_map = {"C1": 0.85, "C2": 0.80, "C3": 0.75, "C4": 0.70, "C5": 0.65}
        w_core_target = tier_core_map.get(str(self.tier).upper(), 0.75)
        w_sat_target = 1.0 - w_core_target

        inv_vols_core = {c: 1.0 / vol_map[c] for c in core_codes}
        sum_inv_core = sum(inv_vols_core.values())
        core_weights = {c: (inv_vols_core[c] / max(sum_inv_core, 1e-12)) * w_core_target for c in core_codes}

        sat_scores = {}
        for c in sat_codes:
            sh = float(m_dict.get(c, {}).get("sharpe", 0.5))
            wr = float(m_dict.get(c, {}).get("win_rate", 0.5))
            sat_scores[c] = max(0.1, sh + 0.5) * (0.8 + 0.4 * wr)
        sum_sat_score = sum(sat_scores.values())
        sat_weights = {c: (sat_scores[c] / max(sum_sat_score, 1e-12)) * w_sat_target for c in sat_codes}

        combined = {**core_weights, **sat_weights}
        min_w = self.constraints.get("min_single_weight", 0.04)
        max_w = self.constraints.get("max_single_weight", 0.40)
        w_arr = np.array([combined.get(c, 1.0 / n) for c in codes], dtype=float)
        for _ in range(5):
            w_arr = np.clip(w_arr, min_w, max_w)
            s = np.sum(w_arr)
            if s > 0:
                w_arr /= s

        res = {c: float(w) for c, w in zip(codes, w_arr)}
        return _normalize_weights_strict(res)

    def _compute_all_weather_weights(
        self,
        codes: List[str],
        nav_df: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        全天候风险平价模型 (All-Weather Equal Risk Contribution)
        求解使组合中各资产风险边际贡献相等的权重向量:
        min sum_i sum_j (w_i * (Sigma * w)_i - w_j * (Sigma * w)_j)^2
        s.t. sum(w) = 1, min_w <= w_i <= max_w
        """
        n = len(codes)
        if n <= 1:
            return {codes[0]: 1.0} if n == 1 else {}

        sub_nav = nav_df[codes].dropna()
        if len(sub_nav) < 15:
            return _normalize_weights_strict({c: 1.0 / n for c in codes})

        ret_df = sub_nav.pct_change().dropna()
        cov = ret_df.cov().values * 250.0
        cov = denoise_covariance_matrix(cov, n_obs=len(ret_df), shrink_alpha=0.15)
        vols = np.sqrt(np.maximum(np.diag(cov), 1e-8))

        inv_v = 1.0 / vols
        x0 = inv_v / np.sum(inv_v)

        min_w = self.constraints.get("min_single_weight", 0.04)
        max_w = self.constraints.get("max_single_weight", 0.40)
        bounds = [(min_w, max_w)] * n

        def erc_objective(w):
            w = np.asarray(w, dtype=np.float64)
            sigma_w = cov @ w
            trc = w * sigma_w
            diffs = trc[:, None] - trc[None, :]
            return float(np.sum(diffs ** 2)) * 1e4

        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        try:
            res = minimize(
                erc_objective,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=cons,
                options={"maxiter": 150, "ftol": 1e-8},
            )
            if res.success or res.fun < erc_objective(x0):
                w_opt = res.x
            else:
                w_opt = x0
        except Exception:
            w_opt = x0

        w_opt = np.clip(w_opt, min_w, max_w)
        w_opt /= np.sum(w_opt)
        return _normalize_weights_strict({c: float(w) for c, w in zip(codes, w_opt)})

    def _compute_black_litterman_weights(
        self,
        codes: List[str],
        nav_df: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        Black-Litterman 主客观观点融合模型
        1. 先验基准：市场均衡期望收益 Pi = lambda * Sigma * w_eq
        2. 机会雷达与胜率观点构建：P, Q, Omega
        3. 贝叶斯后验期望：E[R] = [ (tau*Sigma)^-1 + P^T Omega^-1 P ]^-1 * [ (tau*Sigma)^-1 Pi + P^T Omega^-1 Q ]
        4. 均值-方差优化求解最优权重并严格归一化
        """
        n = len(codes)
        if n <= 1:
            return {codes[0]: 1.0} if n == 1 else {}

        sub_nav = nav_df[codes].dropna()
        if len(sub_nav) < 15:
            return _normalize_weights_strict({c: 1.0 / n for c in codes})

        ret_df = sub_nav.pct_change().dropna()
        cov = ret_df.cov().values * 250.0
        cov = denoise_covariance_matrix(cov, n_obs=len(ret_df), shrink_alpha=0.15)
        vols = np.sqrt(np.maximum(np.diag(cov), 1e-8))

        risk_aversion = 2.5
        w_eq = 1.0 / (vols ** 2)
        w_eq /= np.sum(w_eq)
        pi = risk_aversion * (cov @ w_eq)

        tau = 0.05
        m_dict = {}
        if self._individual_metrics is not None and not self._individual_metrics.empty:
            m_dict = {r["fund_code"]: r for _, r in self._individual_metrics.iterrows()}

        ann_ret = (sub_nav.iloc[-1] / sub_nav.iloc[0]) ** (250.0 / len(sub_nav)) - 1.0
        sharpes = np.array([float(m_dict.get(c, {}).get("sharpe", float(ann_ret.get(c, 0.08)) / max(vols[i], 0.01))) for i, c in enumerate(codes)])
        winrates = np.array([float(m_dict.get(c, {}).get("conditional_win_rate", m_dict.get(c, {}).get("win_rate", 0.5))) for c in codes])

        P = np.eye(n)
        mean_sh = np.mean(sharpes)
        tilt = 0.04 * np.tanh(sharpes - mean_sh) + 0.03 * (winrates - 0.5)
        Q = pi + tilt
        omega = np.diag(np.diag(P @ (tau * cov) @ P.T)) + 1e-5 * np.eye(n)

        tau_cov_inv = np.linalg.pinv(tau * cov)
        omega_inv = np.linalg.pinv(omega)
        post_cov_inv = tau_cov_inv + P.T @ omega_inv @ P
        post_cov = np.linalg.pinv(post_cov_inv)
        er_post = post_cov @ (tau_cov_inv @ pi + P.T @ omega_inv @ Q)

        min_w = self.constraints.get("min_single_weight", 0.04)
        max_w = self.constraints.get("max_single_weight", 0.40)
        bounds = [(min_w, max_w)] * n

        def bl_objective(w):
            w = np.asarray(w, dtype=np.float64)
            port_ret = np.dot(w, er_post)
            port_var = w @ cov @ w
            return -(port_ret - 0.5 * risk_aversion * port_var)

        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        x0 = w_eq
        try:
            res = minimize(
                bl_objective,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=cons,
                options={"maxiter": 150, "ftol": 1e-8},
            )
            w_opt = res.x if res.success else x0
        except Exception:
            w_opt = x0

        w_opt = np.clip(w_opt, min_w, max_w)
        w_opt /= np.sum(w_opt)
        return _normalize_weights_strict({c: float(w) for c, w in zip(codes, w_opt)})

    def _optimize_by_model_type(
        self,
        codes: List[str],
        nav_df: pd.DataFrame,
        quota_info: Optional[Dict[str, Dict]],
    ) -> Optional[Dict[str, float]]:
        """根据 self.model_type 调度七大机构级量化模型求解权重"""
        m_t = getattr(self, "model_type", "hrp_robust")
        if m_t in ("hrp_robust", "hrp_cvar"):
            hrp_w = self._compute_hrp_weights(codes, nav_df)
            slsqp_w = self._slsqp_optimize(codes, nav_df, quota_info)
            if slsqp_w is not None and hrp_w:
                # 双核融合：60% 层次风险平价 + 40% CVaR-胜率规划
                blended = {c: 0.60 * hrp_w.get(c, 1.0 / len(codes)) + 0.40 * slsqp_w.get(c, 1.0 / len(codes)) for c in codes}
                return _normalize_weights_strict(blended)
            return _normalize_weights_strict(hrp_w) if hrp_w else self._slsqp_optimize(codes, nav_df, quota_info)
        elif m_t == "core_satellite":
            cs_w = self._compute_core_satellite_weights(codes, nav_df)
            return _normalize_weights_strict(cs_w)
        elif m_t == "all_weather":
            aw_w = self._compute_all_weather_weights(codes, nav_df)
            return _normalize_weights_strict(aw_w)
        elif m_t == "black_litterman":
            bl_w = self._compute_black_litterman_weights(codes, nav_df)
            return _normalize_weights_strict(bl_w)
        elif m_t in ("cvar_tail", "min_cvar", "kelly_momentum", "conditional_winrate", "cond_winrate"):
            w = self._slsqp_optimize(codes, nav_df, quota_info)
            if w is not None:
                return _normalize_weights_strict(w)
            return _normalize_weights_strict(self._compute_hrp_weights(codes, nav_df))
        else:
            w = self._slsqp_optimize(codes, nav_df, quota_info)
            return _normalize_weights_strict(w) if w else None

    def _slsqp_optimize(
        self,
        codes: List[str],
        nav_df: pd.DataFrame,
        quota_info: Optional[Dict[str, Dict]],
    ) -> Optional[Dict[str, float]]:
        """使用 SLSQP 优化权重"""
        n = len(codes)
        if n == 0:
            return None

        max_w = self.constraints["max_single_weight"]
        min_w = self.constraints["min_single_weight"]

        # 准备 NAV 子矩阵
        valid_codes = [c for c in codes if c in nav_df.columns]
        if len(valid_codes) < n:
            valid_codes = valid_codes[:n] if valid_codes else codes[:n]
            n = len(valid_codes)

        sub_nav = nav_df[valid_codes].dropna()
        if len(sub_nav) < self.holding_days + 10:
            return None

        # 归一化
        norm_nav = sub_nav / sub_nav.iloc[0]
        nav_arr = norm_nav.values  # (T, n)
        T = len(nav_arr)
        hd = min(self.holding_days, T - 1)
        M = T - hd
        split_M = int(M * 0.70) if M > 20 else M

        # 若有 market_snapshot，预计算核权重
        state_vec = WinRateEngine.extract_state_vector(self.market_snapshot)
        if state_vec is not None and M > 0:
            avg_nav = pd.Series(norm_nav.mean(axis=1).values)
            hist_feat = WinRateEngine.compute_historical_feature_matrix(avg_nav, hd)
            kw = WinRateEngine.compute_kernel_weights(hist_feat, state_vec)
        else:
            kw = np.full(M, 1.0 / M, dtype=np.float64) if M > 0 else np.array([])

        # 构建候选基金指标映射
        m_dict = {}
        if self._individual_metrics is not None and not self._individual_metrics.empty:
            m_dict = {r["fund_code"]: r for _, r in self._individual_metrics.iterrows()}

        def objective(w):
            """目标：最小化 -(0.65*训练集条件胜率 + 0.35*验证集胜率 - 限购惩罚)"""
            portfolio_nav = nav_arr @ w
            if hd <= 0 or M <= 0:
                return 0.0

            buy = portfolio_nav[:M]
            sell = portfolio_nav[hd:hd + M]
            total_ret = sell / np.maximum(buy, 1e-8) - 1.0
            years = hd / 250.0
            ann_ret = np.sign(total_ret + 1.0) * (np.abs(total_ret + 1.0) ** (1.0 / years)) - 1.0

            # 平滑可导 Sigmoid 胜率代理 (tau = 0.025)
            tau = 0.025
            diff = (ann_ret - self.target_return) / tau
            smooth_win = 1.0 / (1.0 + np.exp(-np.clip(diff, -50.0, 50.0)))

            if len(kw) == M:
                if split_M < M:
                    kw_train = kw[:split_M] / (np.sum(kw[:split_M]) + 1e-12)
                    wr_train = float(np.sum(kw_train * smooth_win[:split_M]))
                    wr_val = float(np.mean(smooth_win[split_M:]))
                    wr = 0.65 * wr_train + 0.35 * wr_val
                else:
                    wr = float(np.sum(kw * smooth_win))
            else:
                wr = float(np.mean(smooth_win))

            # 限购惩罚
            penalty = 0.0
            if quota_info:
                pen_coef = self.constraints["purchase_limit_penalty"]
                for i, code in enumerate(valid_codes):
                    qi = quota_info.get(code, {})
                    if qi.get("is_limited", False):
                        penalty += pen_coef * w[i]

            m_type = getattr(self, "model_type", "conditional_winrate")
            if m_type in ("min_cvar", "cvar_tail"):
                p5 = float(np.percentile(ann_ret, 5)) if len(ann_ret) > 0 else 0.0
                tail_losses = np.maximum(0.0, p5 - ann_ret)
                smooth_cvar = p5 - float(np.mean(tail_losses)) / 0.05
                down_vol = float(np.sqrt(np.mean(np.minimum(0.0, ann_ret) ** 2)))
                return -(0.55 * smooth_cvar - 0.35 * down_vol * 2.0 + 0.10 * wr - penalty)
            elif m_type in ("kelly_momentum",):
                safe_r = np.clip(0.5 * ann_ret, -0.45, 2.0)
                kelly_g = float(np.mean(np.log1p(safe_r)))
                sharpes = np.array([float(m_dict.get(c, {}).get("sharpe", 0.5)) for c in valid_codes])
                mom_tilt = float(np.dot(w, sharpes))
                return -(0.60 * kelly_g + 0.25 * mom_tilt * 0.1 + 0.15 * wr - penalty)
            elif m_type in ("hrp_cvar", "hrp_robust"):
                p5 = float(np.percentile(ann_ret, 5)) if len(ann_ret) > 0 else 0.0
                smooth_cvar = p5 - float(np.mean(np.maximum(0.0, p5 - ann_ret))) / 0.05
                return -(0.50 * wr + 0.50 * smooth_cvar - penalty)

            # 默认 cond_winrate / conditional_winrate / 其他
            mu = float(np.mean(ann_ret))
            vol = float(np.std(ann_ret) + 1e-4)
            omega_bonus = (mu - self.target_return) / vol
            return -(0.75 * wr + 0.25 * np.clip(omega_bonus * 0.1, -0.5, 0.5) - penalty)

        # 初始权重根据所选机构模型提供智能先验倾斜 (Prior Tilt)，避免机械 1/N
        m_type = getattr(self, "model_type", "conditional_winrate")
        if m_type in ("min_cvar", "cvar_tail"):
            priors = np.array([1.0 / max(0.04, abs(float(m_dict.get(c, {}).get("max_dd", 0.15)))) for c in valid_codes], dtype=float)
        elif m_type in ("kelly_momentum",):
            priors = np.array([max(0.1, float(m_dict.get(c, {}).get("sharpe", 0.5)) + 1.0) for c in valid_codes], dtype=float)
        elif m_type in ("hrp_cvar", "hrp_robust"):
            hrp_init = self._compute_hrp_weights(valid_codes, nav_df)
            priors = np.array([hrp_init.get(c, 1.0 / n) for c in valid_codes], dtype=float)
        elif m_type in ("core_satellite",):
            cs_init = self._compute_core_satellite_weights(valid_codes, nav_df)
            priors = np.array([cs_init.get(c, 1.0 / n) for c in valid_codes], dtype=float)
        elif m_type in ("all_weather",):
            aw_init = self._compute_all_weather_weights(valid_codes, nav_df)
            priors = np.array([aw_init.get(c, 1.0 / n) for c in valid_codes], dtype=float)
        elif m_type in ("black_litterman",):
            bl_init = self._compute_black_litterman_weights(valid_codes, nav_df)
            priors = np.array([bl_init.get(c, 1.0 / n) for c in valid_codes], dtype=float)
        else:  # conditional_winrate / cond_winrate
            priors = np.array([float(m_dict.get(c, {}).get("conditional_win_rate", m_dict.get(c, {}).get("win_rate", 0.5))) ** 1.8 for c in valid_codes], dtype=float)

        if len(priors) == n and np.all(np.isfinite(priors)) and priors.sum() > 0:
            x0 = priors / priors.sum()
            for _ in range(5):
                x0 = np.clip(x0, min_w, max_w)
                s = x0.sum()
                if s > 0:
                    x0 /= s
        else:
            x0 = np.full(n, 1.0 / n)

        bounds = [(min_w, max_w)] * n
        constraints_list = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # 同桶约束
        bucket_indices = {}
        for i, code in enumerate(valid_codes):
            info = self.candidate_info[self.candidate_info["fund_code"] == code]
            bucket = info.iloc[0]["bucket"] if not info.empty else "other"
            bucket_indices.setdefault(bucket, []).append(i)

        max_sector = self.constraints["max_sector_exposure"]
        for bucket, indices in bucket_indices.items():
            if len(indices) > 1:
                constraints_list.append({
                    "type": "ineq",
                    "fun": lambda w, idx=indices: max_sector - sum(w[i] for i in idx),
                })

        try:
            result = minimize(
                objective, x0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints_list,
                options={"maxiter": 200, "ftol": 1e-8},
            )
            if result.success or result.fun < objective(x0):
                w = result.x
                w = np.clip(w, min_w, max_w)
                return _normalize_weights_strict({code: float(w[i]) for i, code in enumerate(valid_codes)})
            elif np.all(np.isfinite(x0)) and x0.sum() > 0:
                # 即使 SLSQP 无法进一步改善，x0 也是有效先验倾斜解
                return _normalize_weights_strict({code: float(x0[i]) for i, code in enumerate(valid_codes)})
        except Exception:
            if np.all(np.isfinite(x0)) and x0.sum() > 0:
                return _normalize_weights_strict({code: float(x0[i]) for i, code in enumerate(valid_codes)})

        return None

    def _build_portfolio_nav(
        self, nav_df: pd.DataFrame, weights: Dict[str, float]
    ) -> pd.Series:
        """构建组合 NAV 序列"""
        valid = [c for c in weights if c in nav_df.columns]
        if not valid:
            return pd.Series(dtype=float)
        sub = nav_df[valid].dropna()
        norm = sub / sub.iloc[0]
        w = np.array([weights[c] for c in valid])
        w = w / w.sum()
        return pd.Series(norm.values @ w, index=sub.index, name="portfolio")

    def _local_search(
        self,
        current_codes: List[str],
        current_weights: Dict[str, float],
        all_codes: List[str],
        nav_df: pd.DataFrame,
        current_winrate: float,
        quota_info: Optional[Dict[str, Dict]],
        max_iter: int = 10,
    ) -> Optional[Tuple[List[str], Dict[str, float], Dict]]:
        """
        局部搜索：尝试替换每只基金看是否能提升胜率。
        """
        best_codes = list(current_codes)
        best_weights = dict(current_weights)
        best_wr = current_winrate
        improved = False

        candidates = [c for c in all_codes if c not in current_codes]

        for iteration in range(max_iter):
            made_swap = False
            for i, old_code in enumerate(best_codes):
                for new_code in candidates:
                    trial_codes = list(best_codes)
                    trial_codes[i] = new_code

                    # 快速检查新基金是否有效
                    if new_code not in nav_df.columns:
                        continue

                    # 等权试算
                    n = len(trial_codes)
                    trial_w = {c: 1.0 / n for c in trial_codes}
                    trial_nav = self._build_portfolio_nav(nav_df, trial_w)
                    if len(trial_nav) < self.holding_days + 10:
                        continue

                    wr = WinRateEngine.quick_screening_score(
                        trial_nav, self.holding_days, self.target_return
                    )

                    if wr > best_wr + 0.005:  # 至少提升 0.5%
                        # 用 SLSQP 优化权重
                        opt_w = self._slsqp_optimize(trial_codes, nav_df, quota_info)
                        if opt_w:
                            opt_nav = self._build_portfolio_nav(nav_df, opt_w)
                            full_wr = WinRateEngine.rolling_target_winrate(
                                opt_nav, self.holding_days, self.target_return,
                                market_snapshot=self.market_snapshot,
                            )
                            cur_score = float(full_wr.get("conditional_win_rate", full_wr["win_rate"]))
                            if cur_score > best_wr:
                                best_codes = trial_codes
                                best_weights = opt_w
                                best_wr = cur_score
                                candidates = [c for c in all_codes if c not in best_codes]
                                made_swap = True
                                improved = True
                                break
                if made_swap:
                    break
            if not made_swap:
                break

        if improved:
            full_wr = WinRateEngine.rolling_target_winrate(
                self._build_portfolio_nav(nav_df, best_weights),
                self.holding_days, self.target_return,
                market_snapshot=self.market_snapshot,
            )
            return best_codes, best_weights, full_wr

        return None

    def _build_fund_details(
        self, weights: Dict[str, float], metrics_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """构建每只基金的详细信息"""
        details = []
        for code, weight in sorted(weights.items(), key=lambda x: -x[1]):
            row = metrics_df[metrics_df["fund_code"] == code]
            info_row = self.candidate_info[self.candidate_info["fund_code"] == code]

            detail = {
                "fund_code": code,
                "fund_name": info_row.iloc[0]["fund_name"] if not info_row.empty else code,
                "weight": round(weight, 4),
                "weight_pct": f"{weight*100:.1f}%",
                "bucket": row.iloc[0]["bucket"] if not row.empty else "unknown",
                "win_rate": round(row.iloc[0]["win_rate"], 4) if not row.empty else 0.0,
                "max_dd": round(row.iloc[0]["max_dd"], 4) if not row.empty else 0.0,
                "sharpe": round(row.iloc[0]["sharpe"], 2) if not row.empty else 0.0,
                "annual_return": round(row.iloc[0]["annual_return"], 4) if not row.empty else 0.0,
                "share_class_recommendation": self._recommend_share_class(),
                "ac_pair_code": info_row.iloc[0].get("ac_pair_code", "") if not info_row.empty else "",
            }
            details.append(detail)
        return details

    def _recommend_share_class(self) -> str:
        """根据持有期推荐 A 或 C 类"""
        if self.holding_days <= 150:  # ~6 个月
            return "C"
        return "A"

    def _holding_period_label(self) -> str:
        """返回持有期文字标签"""
        for key, cfg in HOLDING_PERIODS.items():
            if self.holding_days <= cfg["trading_days"]:
                return cfg["label"]
        return "长期3~5年"

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """空结果模板"""
        return {
            "optimal_weights": {},
            "fund_details": [],
            "portfolio_metrics": {
                "win_rate": 0.0,
                "no_loss_rate": 0.0,
                "monte_carlo_prob": 0.0,
                "expected_return_annualized": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "volatility_annualized": 0.0,
            },
            "holding_period": self._holding_period_label(),
            "target_return": self.target_return,
            "tier": self.tier,
            "optimization_metadata": {"error": reason},
        }

    # ─── 存量持仓调仓路径 ──────────────────────────────────────

    def optimize_rebalance_path(
        self,
        current_holdings: Dict[str, Dict],
        optimal_weights: Dict[str, float],
        total_value: float,
    ) -> Dict[str, Any]:
        """
        存量持仓调仓路径优化。

        Parameters
        ----------
        current_holdings : fund_code → {shares, nav, cost, holding_days}
        optimal_weights : fund_code → target weight
        total_value : 当前持仓总市值
        """
        from winrate_engine import _get_redemption_fee

        rebalance_actions = []
        total_friction = 0.0
        locked_funds = []
        seat_warnings = []

        # 计算当前权重
        current_weights = {}
        for code, info in current_holdings.items():
            value = info.get("shares", 0) * info.get("nav", 1.0)
            current_weights[code] = value / total_value if total_value > 0 else 0.0

        # 对比差异
        all_codes = set(list(current_weights.keys()) + list(optimal_weights.keys()))

        for code in all_codes:
            cur_w = current_weights.get(code, 0.0)
            tgt_w = optimal_weights.get(code, 0.0)
            diff = tgt_w - cur_w

            if abs(diff) < 0.01:  # 差异 < 1% 不动
                continue

            holding_info = current_holdings.get(code, {})
            h_days = holding_info.get("holding_days", 0)
            nav = float(holding_info.get("nav", 1.0) or 1.0)
            if nav <= 0:
                nav = 1.0
            penalty_free_shares = holding_info.get("penalty_free_shares", None)

            if diff < 0:  # 需要赎回
                redeem_amount = abs(diff) * total_value
                if penalty_free_shares is not None:
                    if float(penalty_free_shares) <= 1e-4:
                        locked_funds.append(f"{code}: 持有 < 7 天惩罚期（免惩罚可赎回份额为 0）")
                        continue
                    desired_shares = redeem_amount / nav
                    safe_sell_shares = min(desired_shares, float(penalty_free_shares))
                    if safe_sell_shares <= 1e-4:
                        locked_funds.append(f"{code}: 持有 < 7 天惩罚期（免惩罚可赎回份额不足）")
                        continue

                    actual_redeem_amount = safe_sell_shares * nav
                    note = ""
                    if desired_shares > float(penalty_free_shares) + 1e-4:
                        locked_diff = desired_shares - safe_sell_shares
                        note = f"仅卖出持有≥7天的安全份额 {safe_sell_shares:.1f} 份，剩余未满7天份额已保护锁仓"
                        locked_funds.append(f"{code}: 包含未满 7 天锁定份额 {locked_diff:.1f} 份（已保护锁仓）")

                    safe_h_days = holding_info.get("safe_holding_days", max(7, h_days))
                    effective_h_days = max(7, safe_h_days)
                    f_class = str(holding_info.get("share_class", "A")).upper().strip()
                    redeem_fee = _get_redemption_fee(effective_h_days, fund_type=f_class)
                    fee = actual_redeem_amount * redeem_fee
                    total_friction += fee

                    rebalance_actions.append({
                        "action": "SELL",
                        "fund_code": code,
                        "amount": round(actual_redeem_amount, 2),
                        "shares": round(safe_sell_shares, 2),
                        "current_weight": round(cur_w * 100, 1),
                        "target_weight": round(tgt_w * 100, 1),
                        "holding_days": h_days,
                        "effective_holding_days": effective_h_days,
                        "redemption_fee_rate": redeem_fee,
                        "estimated_fee": round(fee, 2),
                        "note": note,
                    })
                else:
                    # 检查锁定期 (原有逻辑兜底)
                    if h_days < 7:
                        locked_funds.append(f"{code}: 持有 {h_days} 天，< 7 天惩罚期")
                        continue

                    redeem_fee = _get_redemption_fee(h_days)
                    fee = redeem_amount * redeem_fee
                    total_friction += fee

                    rebalance_actions.append({
                        "action": "SELL",
                        "fund_code": code,
                        "amount": round(redeem_amount, 2),
                        "shares": round(redeem_amount / nav, 2),
                        "current_weight": round(cur_w * 100, 1),
                        "target_weight": round(tgt_w * 100, 1),
                        "holding_days": h_days,
                        "effective_holding_days": h_days,
                        "redemption_fee_rate": redeem_fee,
                        "estimated_fee": round(fee, 2),
                        "note": "",
                    })
            else:  # 需要申购
                buy_amount = diff * total_value

                rebalance_actions.append({
                    "action": "BUY",
                    "fund_code": code,
                    "amount": round(buy_amount, 2),
                    "shares": round(buy_amount / nav, 2),
                    "current_weight": round(cur_w * 100, 1),
                    "target_weight": round(tgt_w * 100, 1),
                    "holding_days": 0,
                    "effective_holding_days": 0,
                    "redemption_fee_rate": 0.0,
                    "estimated_fee": round(buy_amount * 0.0015, 2),  # A类申购费
                    "note": "",
                })
                total_friction += buy_amount * 0.0015

        # 席位丢失警告
        for code in current_holdings:
            if code not in optimal_weights or optimal_weights.get(code, 0) < 0.01:
                info_row = self.candidate_info[self.candidate_info["fund_code"] == code]
                if not info_row.empty:
                    status = info_row.iloc[0].get("status", "")
                    if "暂停" in str(status) or "限制" in str(status):
                        seat_warnings.append(
                            f"⚠️ {code} 当前暂停/限购，赎回后可能无法回购！"
                        )

        # 估算完成天数
        n_sells = sum(1 for a in rebalance_actions if a["action"] == "SELL")
        n_buys = sum(1 for a in rebalance_actions if a["action"] == "BUY")
        est_days = max(2, n_sells + 1)  # 赎回 T+1 到账后再买

        return {
            "rebalance_actions": rebalance_actions,
            "total_friction_cost": round(total_friction, 2),
            "estimated_days": est_days,
            "locked_funds": locked_funds,
            "seat_warnings": seat_warnings,
            "n_sells": n_sells,
            "n_buys": n_buys,
        }

    # ─── 与专家精选池对比 ──────────────────────────────────────

    def compare_with_expert_pool(
        self,
        expert_weights: Dict[str, float],
        expert_nav_matrix: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """与专家精选池的组合对比。

        Parameters
        ----------
        expert_weights : 专家池基金等权权重
        expert_nav_matrix : 专家池基金独立 NAV 矩阵（可选）。
            如果提供，则用该矩阵计算专家池胜率（解决专家池基金不在候选 NAV 矩阵中的问题）。
            如果不提供，回退到 self.nav_matrix（仅当专家基金恰好在候选池中才有效）。
        """
        nav_source = expert_nav_matrix if expert_nav_matrix is not None else self.nav_matrix
        if not expert_weights:
            return {"expert_pool": {"win_rate": 0, "no_loss_rate": 0, "avg_return": 0}}

        portfolio_nav = self._build_portfolio_nav(nav_source, expert_weights)
        if portfolio_nav.empty or len(portfolio_nav) < self.holding_days + 10:
            return {"expert_pool": {"win_rate": 0, "no_loss_rate": 0, "avg_return": 0,
                                    "note": "专家池 NAV 数据不足，无法同口径对比"}}

        expert_wr = WinRateEngine.rolling_target_winrate(
            portfolio_nav, self.holding_days, self.target_return,
        )

        return {
            "expert_pool": {
                "win_rate": expert_wr.get("win_rate", 0),
                "no_loss_rate": expert_wr.get("no_loss_rate", 0),
                "avg_return": expert_wr.get("avg_return_annualized", 0),
            }
        }


# ══════════════════════════════════════════════════════════════════
#  全市场选基一键闭环调度器
# ══════════════════════════════════════════════════════════════════

def execute_market_optimization_flow(
    target_pct: float,
    horizon_label: str,
    capital: float,
    min_aum: float = 2.0,
    min_years: float = 3.0,
    top_n: int = 80,
    force_rebuild: bool = False,
    progress_cb: Optional[Callable] = None,
    pm: Optional[Any] = None,
    snapshot: Optional[Dict[str, Any]] = None,
    precomputed_ranked: Optional[pd.DataFrame] = None,
    precomputed_nav: Optional[pd.DataFrame] = None,
    target_num_funds: Optional[int] = None,
    model_type: str = "hrp_cvar",
    **kwargs
) -> Dict[str, Any]:
    """
    全市场胜率最优选基流水线一键闭环调度器：
    全市场漏斗 ➔ NAV矩阵 ➔ 胜率优化 ➔ 专家池对比 ➔ 限额拆单表 ➔ 存量调仓路径
    """
    import math as _math
    from datetime import date, datetime
    import portfolio_manager as _pmq
    from market_screener import MarketScreener
    from strategy_bridge import StrategyBridge, strategy_fn_for_tier

    def _map_slider_to_tier(ret: float) -> str:
        if ret <= 8.0:
            return "C1"
        elif ret <= 12.0:
            return "C2"
        elif ret <= 18.0:
            return "C3"
        elif ret <= 30.0:
            return "C4"
        else:
            return "C5"

    _mo_today = date.today()
    _mo_hmap = {"短期(3~6月)": "short", "中期(1~2年)": "medium", "长期(3~5年)": "long"}
    mo_period_key = _mo_hmap.get(horizon_label, "medium")
    mo_holding_days = HOLDING_PERIODS[mo_period_key]["trading_days"]
    mo_tier = _map_slider_to_tier(target_pct)

    if snapshot is None:
        try:
            snapshot = StrategyBridge.get_latest_market_snapshot()
        except Exception:
            snapshot = {}

    if pm is None:
        try:
            import streamlit as _st
            if hasattr(_st, "session_state") and "pm" in _st.session_state:
                pm = _st.session_state.pm
        except Exception:
            pm = None
        if pm is None:
            try:
                pm = _pmq.PortfolioManager()
            except Exception:
                pm = None


    # 1. 漏斗与 NAV（支持分步预计算直接复用）
    if precomputed_ranked is not None and not precomputed_ranked.empty and precomputed_nav is not None and not precomputed_nav.empty:
        mo_ranked = precomputed_ranked
        mo_nav = precomputed_nav
        if progress_cb:
            progress_cb(1, 1, "复用已有候选池与 NAV 矩阵...")
    else:
        mo_ranked, mo_nav = MarketScreener.run_full_pipeline(
            as_of_date=_mo_today,
            min_aum_billion=float(min_aum),
            min_years=float(min_years),
            top_n_per_bucket=int(top_n),
            force_rebuild=bool(force_rebuild),
            progress_callback=progress_cb,
        )
    if mo_ranked is None or mo_ranked.empty or mo_nav is None or mo_nav.empty:
        raise RuntimeError("候选池或 NAV 矩阵为空（可能数据源暂不可用）")

    # 2. 多模型量化定权优化 (支持 3~15 只基金自由调节与四大专业模型)
    mo_optimizer = WinRateOptimizer(
        nav_matrix=mo_nav,
        candidate_info=mo_ranked,
        holding_days=mo_holding_days,
        target_annual_return=target_pct / 100.0,
        tier=mo_tier,
        market_snapshot=snapshot,
        target_num_funds=target_num_funds,
        model_type=model_type,
    )
    mo_result = mo_optimizer.optimize(progress_callback=progress_cb)

    # 3. 专家精选池同口径对比
    mo_expert_cmp = None
    try:
        _all_expert = list(getattr(_pmq, "CORE_STRATEGY_POOL", {}).keys())
        _expert_a = [c for c in _all_expert
                     if not getattr(_pmq, "CORE_STRATEGY_POOL", {}).get(c, {}).get("share_class", "A") == "C"]
        if not _expert_a:
            _expert_a = _all_expert
        _tier_w = {}
        try:
            if mo_tier == "C3":
                _tier_w_raw = dict((snapshot.get("target_weights_funds", {}) or {}) if snapshot else {})
            else:
                _tier_w_raw = dict(StrategyBridge.map_index_weights_to_funds(
                    strategy_fn_for_tier(StrategyBridge.load_matrix(), tier=mo_tier)
                ))
            _tier_w = {str(c): float(w) for c, w in _tier_w_raw.items() if float(w) > 1e-4}
        except Exception:
            _tier_w = {}
        if _tier_w:
            _expert_a = list(_tier_w.keys())
        _in_nav = [c for c in _expert_a if c in mo_nav.columns]
        _expert_nav = None
        if len(_in_nav) >= max(1, int(len(_expert_a) * 0.8)):
            _expert_codes = _in_nav
        else:
            if progress_cb:
                progress_cb(0, 1, "获取专家池基金 NAV 用于同口径对比...")
            _expert_nav = MarketScreener.fetch_candidate_nav_matrix(_expert_a)
            _expert_codes = [c for c in _expert_a if c in _expert_nav.columns] if _expert_nav is not None else []
        if _expert_codes:
            if _tier_w:
                _w_sum = sum(_tier_w[c] for c in _expert_codes)
                _ew = {c: _tier_w[c] / _w_sum for c in _expert_codes} if _w_sum > 0 else {}
            else:
                _ew = {}
            _weight_mode = f"{mo_tier} 档位策略配比" if _ew else "等权兜底"
            if not _ew:
                _ew = {c: 1.0 / len(_expert_codes) for c in _expert_codes}
            mo_expert_cmp = mo_optimizer.compare_with_expert_pool(
                _ew, expert_nav_matrix=_expert_nav
            )
            mo_expert_cmp["n_funds"] = len(_expert_codes)
            mo_expert_cmp["weight_mode"] = _weight_mode
    except Exception as _e_cmp:
        mo_expert_cmp = {"error": str(_e_cmp)}

    # 4. 自动生成实盘下单拆单表 (消灭套娃按钮)
    order_sheet = []
    fund_details = mo_result.get("fund_details", [])
    for d in fund_details:
        _code = str(d.get("fund_code", "")).strip()
        _amt = round(float(capital) * float(d.get("weight", 0.0)), 2)
        try:
            _q = _pmq.fetch_realtime_fund_quota(_code)
        except Exception:
            _q = {"status": "未知(查询失败)", "daily_limit": 1e11, "is_limited": False}
        _lim = float(_q.get("daily_limit", 1e11) or 0.0)
        _st = str(_q.get("status", ""))
        if _lim <= 0:
            _days, _day1 = None, 0.0
            _alt = d.get("ac_pair_code") or ""
            _note = "⛔ 暂停申购，无法买入" + (f"；可考虑 C 类配对码 {_alt}" if _alt else "；建议替换为同类型次优基金")
        else:
            _ceil_days = int(_math.ceil(_amt / _lim)) if _amt > 0 else 0
            _days = _ceil_days if _ceil_days >= 1 else (1 if _amt > 0 else 0)
            _day1 = min(_amt, _lim)
            if _days <= 1:
                _note = "✅ 今日可一次买齐"
            elif _days <= 20:
                _note = f"🟡 限额 ¥{_lim:,.0f}/日，需分 {_days} 个交易日买齐"
            else:
                _note = f"🔴 限额 ¥{_lim:,.0f}/日，需 {_days} 个交易日，周期过长建议替换"
        try:
            from cache_manager import FundMetadataManager
            _meta = FundMetadataManager.get_fund_metadata(_code)
            if _meta.get("liquidation_risk", False):
                _aum = _meta.get("aum", 0.0)
                _note = f"🚨【清盘预警】规模仅 {_aum:.2f} 亿；" + _note
        except Exception:
            pass
        order_sheet.append({
            "基金代码": _code,
            "基金名称": d.get("fund_name", ""),
            "目标金额(元)": round(_amt, 2),
            "申购状态": _st,
            "日限额(元)": None if _lim >= 1e10 else round(_lim, 2),
            "今日可买(元)": round(_day1, 2),
            "所需交易日": _days,
            "执行建议": _note,
        })

    # 5. 自动核算存量持仓调仓路径 (消灭套娃按钮，安全批次与 <7天 防御)
    rebalance_path = None
    if pm is not None and hasattr(pm, "holdings") and pm.holdings and len(pm.holdings) > 0 and mo_result.get("optimal_weights"):
        _rb_holdings = {}
        _rb_total_val = 0.0
        for _h_code, _h_obj in pm.holdings.items():
            _h_shares = float(getattr(_h_obj, "shares", 0) or 0)
            _h_nav = float(getattr(_h_obj, "current_nav", 1.0) or 1.0)
            _h_cost = float(getattr(_h_obj, "cost_price", _h_nav) or _h_nav)
            _h_batches = getattr(_h_obj, "batches", []) or []
            _h_days = min((getattr(b, "holding_days", 0) or 0 for b in _h_batches), default=30)
            _h_penalty_free = pm.get_penalty_free_redeemable_shares(_h_code) if hasattr(pm, "get_penalty_free_redeemable_shares") else _h_shares
            _safe_batches = [b for b in _h_batches if getattr(b, "holding_days", 0) >= 7 and not getattr(b, "safety_lock", False)]
            _h_safe_days = max((getattr(b, "holding_days", 0) or 0 for b in _safe_batches), default=_h_days)
            _rb_holdings[str(_h_code).strip()] = {
                "shares": _h_shares, "nav": _h_nav,
                "cost": _h_cost, "holding_days": _h_days,
                "safe_holding_days": _h_safe_days,
                "penalty_free_shares": _h_penalty_free,
                "share_class": getattr(_h_obj, "share_class", "A"),
            }
            _rb_total_val += _h_shares * _h_nav

        if _rb_total_val > 0:
            rebalance_path = mo_optimizer.optimize_rebalance_path(
                current_holdings=_rb_holdings,
                optimal_weights=mo_result.get("optimal_weights", {}),
                total_value=_rb_total_val,
            )

    full_payload = {
        "result": mo_result,
        "expert": mo_expert_cmp,
        "funnel": MarketScreener.get_funnel_stats(mo_ranked),
        "capital": float(capital),
        "target_pct": float(target_pct),
        "horizon": horizon_label,
        "tier": mo_tier,
        "as_of": _mo_today.isoformat(),
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_sheet": order_sheet,
        "rebalance_path": rebalance_path,
    }
    return full_payload

