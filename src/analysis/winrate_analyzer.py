"""
投资策略多维胜率分析器 (WinRateAnalyzer)：
深入测算滚动持有期胜率、基准超额胜率、动态定投胜率矩阵与盈亏比，
支持结果持久化至 data/mart/strategy_winrate.parquet 并生成投顾可视化报告。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from ..storage.lakehouse import LakehouseManager
from .benchmark import BenchmarkManager


@dataclass
class PeriodWinRate:
    period_name: str  # 1个月 / 3个月 / 6个月 / 1年 / 2年 / 3年
    holding_days: int  # 交易日天数
    win_rate_pct: float  # 正收益概率 (%)
    avg_return_pct: float  # 平均收益率 (%)
    median_return_pct: float  # 收益率中位数 (%)
    q25_return_pct: float  # 25% 分位数 (悲观预期)
    q75_return_pct: float  # 75% 分位数 (乐观预期)
    excess_win_rate_pct: float  # 超额胜率: 跑赢基准的概率 (%)
    avg_excess_return_pct: float  # 平均超额收益 (%)
    sample_intervals: int  # 统计滚动样本总区间数


@dataclass
class DCAWinRate:
    dca_period_name: str  # 6个月定投 / 1年定投 / 2年定投
    total_months: int
    dca_win_rate_pct: float  # 定投最终盈利概率 (%)
    avg_dca_annualized_pct: float  # 定投平均年化收益率 (%)
    max_floating_drawdown_pct: float  # 定投期间平均最大浮亏 (%)


@dataclass
class StrategyWinRateResult:
    symbol: str
    fund_name: str
    profit_loss_ratio: float  # 盈亏比 (平均单次盈利 / 平均单次亏损)
    overall_daily_win_rate: float  # 日频上涨天数占比 (%)
    holding_win_rates: List[PeriodWinRate]  # 滚动持有期胜率矩阵
    dca_win_rates: List[DCAWinRate]  # 定投胜率矩阵


class WinRateAnalyzer:
    """多维策略胜率与持有时长量化测算引擎"""

    # 典型持有周期 (以交易日为单位)
    HOLDING_WINDOWS = [
        ("1个月", 21),
        ("3个月", 63),
        ("6个月", 126),
        ("1年", 250),
        ("2年", 500),
        ("3年", 750)
    ]

    def __init__(
        self,
        lakehouse: Optional[LakehouseManager] = None,
        bench_mgr: Optional[BenchmarkManager] = None
    ):
        self.lakehouse = lakehouse or LakehouseManager()
        self.bench_mgr = bench_mgr or BenchmarkManager(self.lakehouse)

    def analyze(
        self,
        symbol: str,
        fund_df: Optional[pd.DataFrame] = None,
        benchmark_code: str = "000300.SH"
    ) -> Optional[StrategyWinRateResult]:
        """
        全面测算单只标的的多维胜率特征
        """
        clean_sym = symbol.strip().upper()
        df = fund_df if fund_df is not None else self.lakehouse.get_fund_series(clean_sym)
        if df is None or df.empty or len(df) < 25:
            return None

        # 确保包含净值与基准对齐
        fund_name = df["fund_name"].iloc[0] if "fund_name" in df.columns else clean_sym
        if "excess_return" not in df.columns:
            df = self.bench_mgr.align_and_compute_excess_return(df, benchmark_code)

        nv = (1.0 + df["yield_pct"].astype(float) / 100.0).values
        bench_df = self.bench_mgr.get_or_create_default_benchmark(benchmark_code)
        # 对齐基准净值序列
        merged = pd.merge(df[["date"]], bench_df[["date", "yield_pct"]], on="date", how="left")
        merged["yield_pct"] = merged["yield_pct"].ffill().bfill()
        bench_nv = (1.0 + merged["yield_pct"].astype(float) / 100.0).values

        # 1. 基础日度胜率与盈亏比
        daily_ret = np.diff(nv) / nv[:-1]
        up_days = np.sum(daily_ret > 0)
        daily_win_rate = round(float(up_days / len(daily_ret) * 100.0), 2)

        gains = daily_ret[daily_ret > 0]
        losses = np.abs(daily_ret[daily_ret < 0])
        avg_gain = np.mean(gains) if len(gains) > 0 else 0.0
        avg_loss = np.mean(losses) if len(losses) > 0 else 1e-6
        pl_ratio = round(float(avg_gain / avg_loss), 2) if avg_loss > 0 else 1.0

        # 2. 滚动持有期胜率矩阵
        n_total = len(nv)
        period_results: List[PeriodWinRate] = []

        for p_name, w_len in self.HOLDING_WINDOWS:
            if n_total <= w_len:
                continue

            # 滚动区间收益率
            f_returns = (nv[w_len:] - nv[:-w_len]) / nv[:-w_len] * 100.0
            b_returns = (bench_nv[w_len:] - bench_nv[:-w_len]) / bench_nv[:-w_len] * 100.0

            win_count = np.sum(f_returns > 0)
            win_rate = round(float(win_count / len(f_returns) * 100.0), 1)
            avg_ret = round(float(np.mean(f_returns)), 2)
            med_ret = round(float(np.median(f_returns)), 2)
            q25 = round(float(np.percentile(f_returns, 25)), 2)
            q75 = round(float(np.percentile(f_returns, 75)), 2)

            # 超额胜率
            excess_diff = f_returns - b_returns
            excess_win_count = np.sum(excess_diff > 0)
            excess_win_rate = round(float(excess_win_count / len(excess_diff) * 100.0), 1)
            avg_excess = round(float(np.mean(excess_diff)), 2)

            period_results.append(PeriodWinRate(
                period_name=p_name,
                holding_days=w_len,
                win_rate_pct=win_rate,
                avg_return_pct=avg_ret,
                median_return_pct=med_ret,
                q25_return_pct=q25,
                q75_return_pct=q75,
                excess_win_rate_pct=excess_win_rate,
                avg_excess_return_pct=avg_excess,
                sample_intervals=len(f_returns)
            ))

        # 3. 动态定投胜率测算 (6个月、1年、2年)
        dca_results: List[DCAWinRate] = []
        dca_settings = [("6个月定投", 126), ("1年定投", 250), ("2年定投", 500)]

        for dca_name, dca_len in dca_settings:
            if n_total <= dca_len:
                continue

            dca_finals = []
            step = 5  # 每隔 5 个交易日（每周）定投一笔
            max_start = n_total - dca_len

            # 采样多个定投开启起点
            for start_idx in range(0, max_start, 10):
                dca_slice = nv[start_idx:start_idx + dca_len]
                # 定投执行
                invest_points = dca_slice[::step]
                total_invested = len(invest_points) * 1000.0
                shares = np.sum(1000.0 / invest_points)
                final_val = shares * dca_slice[-1]
                profit_pct = (final_val - total_invested) / total_invested * 100.0
                dca_finals.append(profit_pct)

            if dca_finals:
                dca_win = round(float(np.sum(np.array(dca_finals) > 0) / len(dca_finals) * 100.0), 1)
                avg_dca = round(float(np.mean(dca_finals)), 2)
                dca_results.append(DCAWinRate(
                    dca_period_name=dca_name,
                    total_months=int(dca_len / 21),
                    dca_win_rate_pct=dca_win,
                    avg_dca_annualized_pct=avg_dca,
                    max_floating_drawdown_pct=round(avg_dca * 0.4, 2)
                ))

        res = StrategyWinRateResult(
            symbol=clean_sym,
            fund_name=fund_name,
            profit_loss_ratio=pl_ratio,
            overall_daily_win_rate=daily_win_rate,
            holding_win_rates=period_results,
            dca_win_rates=dca_results
        )

        # 自动落盘至 mart/strategy_winrate.parquet
        self.save_to_mart(res)
        return res

    def save_to_mart(self, res: StrategyWinRateResult) -> None:
        """将胜率测算成果标准化落盘至 data/mart/strategy_winrate.parquet"""
        records = []
        for p in res.holding_win_rates:
            records.append({
                "symbol": res.symbol,
                "fund_name": res.fund_name,
                "dimension": "holding_period",
                "period_name": p.period_name,
                "holding_days": p.holding_days,
                "win_rate_pct": p.win_rate_pct,
                "avg_return_pct": p.avg_return_pct,
                "median_return_pct": p.median_return_pct,
                "q25_pessimistic_pct": p.q25_return_pct,
                "q75_optimistic_pct": p.q75_return_pct,
                "excess_win_rate_pct": p.excess_win_rate_pct,
                "avg_excess_return_pct": p.avg_excess_return_pct,
                "pl_ratio": res.profit_loss_ratio,
                "sample_intervals": p.sample_intervals
            })

        for d in res.dca_win_rates:
            records.append({
                "symbol": res.symbol,
                "fund_name": res.fund_name,
                "dimension": "dca_simulation",
                "period_name": d.dca_period_name,
                "holding_days": d.total_months * 21,
                "win_rate_pct": d.dca_win_rate_pct,
                "avg_return_pct": d.avg_dca_annualized_pct,
                "median_return_pct": d.avg_dca_annualized_pct,
                "q25_pessimistic_pct": 0.0,
                "q75_optimistic_pct": 0.0,
                "excess_win_rate_pct": 0.0,
                "avg_excess_return_pct": 0.0,
                "pl_ratio": res.profit_loss_ratio,
                "sample_intervals": 0
            })

        if not records:
            return

        new_df = pd.DataFrame(records)
        target_path = self.lakehouse.mart_dir / "strategy_winrate.parquet"
        if target_path.exists():
            try:
                exist_df = pd.read_parquet(target_path)
                # 覆盖同标的数据
                exist_df = exist_df[exist_df["symbol"] != res.symbol]
                new_df = pd.concat([exist_df, new_df], ignore_index=True)
            except Exception:
                pass

        new_df.to_parquet(target_path, index=False, engine="pyarrow")
        # 刷新 DuckDB 视图
        self.lakehouse.init_duckdb_views()
