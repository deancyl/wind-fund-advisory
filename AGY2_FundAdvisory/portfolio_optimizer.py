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

from winrate_engine import WinRateEngine, HOLDING_PERIODS
from cache_manager import SmartCacheManager


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
        """
        self.nav_matrix = nav_matrix
        self.candidate_info = candidate_info
        self.holding_days = holding_days
        self.target_return = target_annual_return
        self.tier = tier
        self.constraints = {**DEFAULT_CONSTRAINTS, **(constraints or {})}
        self.max_dd = MAX_DRAWDOWN_BY_TIER.get(tier, 0.18)

        # 预计算个体指标
        self._individual_metrics: Optional[pd.DataFrame] = None

    # ─── 预计算个体指标 ─────────────────────────────────────────

    def _precompute_individual_metrics(
        self, progress_callback: Optional[Callable] = None
    ) -> pd.DataFrame:
        """
        预计算每只候选基金的个体指标。
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

            # 快速胜率
            win_rate = WinRateEngine.quick_screening_score(
                nav_s, self.holding_days, self.target_return
            )

            # 不亏损率
            buy = nav[:n - self.holding_days]
            sell = nav[self.holding_days:]
            no_loss = float(np.mean(sell >= buy)) if len(buy) > 0 else 0.0

            # 获取 bucket
            info_row = self.candidate_info[self.candidate_info["fund_code"] == code]
            bucket = info_row.iloc[0]["bucket"] if not info_row.empty else "other"

            metrics.append({
                "fund_code": code,
                "bucket": bucket,
                "sharpe": sharpe,
                "max_dd": max_dd_val,
                "annual_return": ann_ret,
                "volatility": float(np.std(daily_ret, ddof=1) * np.sqrt(250)),
                "win_rate": win_rate,
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

        # 预选
        n_funds_min, n_funds_max = self.constraints["n_funds_range"]
        diverse_codes = self._select_diverse_candidates(
            n_target=min(30, len(metrics)), progress_callback=progress_callback
        )

        if len(diverse_codes) < n_funds_min:
            return self._empty_result(f"有效候选不足 {n_funds_min} 只")

        if progress_callback:
            progress_callback(2, 5, f"对 {len(diverse_codes)} 只候选优化权重...")

        # 准备 NAV 子矩阵
        sub_nav = self.nav_matrix[diverse_codes].dropna()
        if len(sub_nav) < self.holding_days + 10:
            return self._empty_result("NAV 数据长度不足")

        # 尝试不同基金数量，选最优
        best_result = None
        best_winrate = -1.0

        for n_funds in range(n_funds_min, min(n_funds_max + 1, len(diverse_codes) + 1)):
            result = self._optimize_fixed_n(
                diverse_codes, sub_nav, n_funds, quota_info, progress_callback
            )
            if result and result.get("portfolio_metrics", {}).get("win_rate", 0) > best_winrate:
                best_winrate = result["portfolio_metrics"]["win_rate"]
                best_result = result

        if best_result is None:
            return self._empty_result("优化器未找到可行解")

        if progress_callback:
            progress_callback(3, 5, "计算 Monte Carlo 置信区间...")

        # 对最优解计算完整的组合胜率（含 MC）
        composite = WinRateEngine.portfolio_composite_winrate(
            sub_nav,
            best_result["optimal_weights"],
            self.holding_days,
            self.target_return,
        )

        best_result["portfolio_metrics"]["monte_carlo_prob"] = (
            composite.get("monte_carlo", {}).get("prob_reach_target", 0.0)
        )
        best_result["portfolio_metrics"]["no_loss_rate"] = (
            composite.get("rolling_winrate", {}).get("no_loss_rate", 0.0)
        )
        best_result["monte_carlo_detail"] = composite.get("monte_carlo", {})
        best_result["component_winrates"] = composite.get("component_winrates", {})

        if progress_callback:
            progress_callback(4, 5, "生成基金详细信息...")

        # 补充基金详细信息
        best_result["fund_details"] = self._build_fund_details(
            best_result["optimal_weights"], metrics
        )
        best_result["holding_period"] = self._holding_period_label()
        best_result["target_return"] = self.target_return
        best_result["tier"] = self.tier

        elapsed = _time.monotonic() - t0
        best_result["optimization_metadata"] = {
            "candidates_screened": len(metrics),
            "candidates_entered_optimizer": len(diverse_codes),
            "optimization_time_seconds": round(elapsed, 2),
            "method": "greedy_init + SLSQP + local_search",
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

        # 贪心选初始基金组合
        sorted_by_wr = metrics[metrics["fund_code"].isin(all_codes)].sort_values(
            "win_rate", ascending=False
        )

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

        # SLSQP 优化权重
        optimal_weights = self._slsqp_optimize(selected_codes, nav_df, quota_info)

        if optimal_weights is None:
            # 等权回退
            eq_w = 1.0 / n_funds
            optimal_weights = {c: eq_w for c in selected_codes}

        # 计算组合胜率
        wr = WinRateEngine.rolling_target_winrate(
            self._build_portfolio_nav(nav_df, optimal_weights),
            self.holding_days,
            self.target_return,
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
            "optimal_weights": optimal_weights,
            "portfolio_metrics": {
                "win_rate": wr["win_rate"],
                "no_loss_rate": wr["no_loss_rate"],
                "monte_carlo_prob": 0.0,  # 后续补充
                "expected_return_annualized": ann_ret,
                "max_drawdown": max_dd_val,
                "sharpe_ratio": sharpe,
                "volatility_annualized": ann_vol,
            },
        }

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

        def objective(w):
            """目标：最小化 -胜率"""
            portfolio_nav = nav_arr @ w
            T = len(portfolio_nav)
            hd = min(self.holding_days, T - 1)
            if hd <= 0:
                return 0.0

            buy = portfolio_nav[:T - hd]
            sell = portfolio_nav[hd:]
            total_ret = sell / buy - 1.0
            years = hd / 250.0
            ann_ret = np.sign(total_ret + 1) * (np.abs(total_ret + 1) ** (1 / years)) - 1.0
            wr = np.mean(ann_ret >= self.target_return)

            # 限购惩罚
            penalty = 0.0
            if quota_info:
                pen_coef = self.constraints["purchase_limit_penalty"]
                for i, code in enumerate(valid_codes):
                    qi = quota_info.get(code, {})
                    if qi.get("is_limited", False):
                        penalty += pen_coef * w[i]

            return -(wr - penalty)

        # 初始等权
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
                w = w / w.sum()  # 归一化
                return {code: float(w[i]) for i, code in enumerate(valid_codes)}
        except Exception:
            pass

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
                                opt_nav, self.holding_days, self.target_return
                            )
                            if full_wr["win_rate"] > best_wr:
                                best_codes = trial_codes
                                best_weights = opt_w
                                best_wr = full_wr["win_rate"]
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

            if diff < 0:  # 需要赎回
                # 检查锁定期
                if h_days < 7:
                    locked_funds.append(f"{code}: 持有 {h_days} 天，< 7 天惩罚期")
                    continue

                redeem_fee = _get_redemption_fee(h_days)
                redeem_amount = abs(diff) * total_value
                fee = redeem_amount * redeem_fee
                total_friction += fee

                rebalance_actions.append({
                    "action": "SELL",
                    "fund_code": code,
                    "amount": round(redeem_amount, 2),
                    "current_weight": round(cur_w * 100, 1),
                    "target_weight": round(tgt_w * 100, 1),
                    "holding_days": h_days,
                    "redemption_fee_rate": redeem_fee,
                    "estimated_fee": round(fee, 2),
                })
            else:  # 需要申购
                buy_amount = diff * total_value

                rebalance_actions.append({
                    "action": "BUY",
                    "fund_code": code,
                    "amount": round(buy_amount, 2),
                    "current_weight": round(cur_w * 100, 1),
                    "target_weight": round(tgt_w * 100, 1),
                    "estimated_fee": round(buy_amount * 0.0015, 2),  # A类申购费
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
    ) -> Dict[str, Any]:
        """与专家精选池的组合对比"""
        # AI 优化组合
        ai_wr = WinRateEngine.rolling_target_winrate(
            self._build_portfolio_nav(self.nav_matrix, expert_weights),
            self.holding_days, self.target_return,
        ) if expert_weights else {"win_rate": 0, "no_loss_rate": 0}

        return {
            "expert_pool": {
                "win_rate": ai_wr.get("win_rate", 0),
                "no_loss_rate": ai_wr.get("no_loss_rate", 0),
                "avg_return": ai_wr.get("avg_return_annualized", 0),
            }
        }
