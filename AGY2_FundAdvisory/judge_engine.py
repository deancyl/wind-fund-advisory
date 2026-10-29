"""
铁血裁判引擎 (judge_engine.py)
防Agent作弊、防未来函数、防暴力穷举过拟合基建模块 2：
1. 检验A（未来函数因果探针）：10个随机历史截面 T 与 T+20 权重因果验证，浮点差 > 1e-7 即判定 FATAL
2. 检验A+（AST 静态反作弊扫描锁）：扫描源码 AST 常量，严禁出现 '2018'~'2025' 等具体日历年份/日期字面量
3. 检验B（6大A股历史风格切片全量回归）：Calmar, MaxDD, Monthly_Win_Rate, Profit_Factor 对比 50/50 基准
4. 检验C（参数±15%网格与拉丁超立方爆破）：K <= 6, 16组扰动邻居，存活率 < 80% 直接判孤岛过拟合死刑
5. 检验D（试错次数 DSR 递增惩罚计数器）：基于 evolution.db 试错次数 N，动态上调夏普门槛，封顶 1.10，超100次熔断
"""

import ast
import hashlib
import json
import math
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any, Union

import numpy as np
import pandas as pd
from scipy.stats import qmc
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from data_loader import DataLoader

DB_PATH = Path("evolution.db")
console = Console()


def compute_ast_hash(func_or_module: Any) -> str:
    """
    计算策略函数或代码 AST 语法树的规范化 SHA256 哈希
    剔除注释与 docstring，杜绝靠重命名变量或加注释作弊
    """
    import inspect
    import textwrap
    try:
        source = inspect.getsource(func_or_module)
        source = textwrap.dedent(source)
        tree = ast.parse(source)
        # 移除 docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                if (node.body and isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant)):
                    node.body.pop(0)
        norm_ast = ast.dump(tree, annotate_fields=False, include_attributes=False)
        return hashlib.sha256(norm_ast.encode('utf-8')).hexdigest()
    except Exception as e:
        # 兜底
        return hashlib.sha256(str(func_or_module).encode('utf-8')).hexdigest()


def scan_ast_for_calendar_cheating(strategy_fn: Callable) -> Tuple[bool, Optional[str]]:
    """
    检验A+：AST 静态反作弊扫描锁
    深度扫描策略函数源码语法树，严禁在策略逻辑中使用任何具体的历史日历年份或日期字符串字面量。
    凡是策略函数体内出现 '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'
    或匹配 'YYYY-MM-DD' 格式的字面量，一律判定 FATAL: Calendar Date Hardcoding Detected！
    策略必须完全基于纯内生量价、技术形态、波动率或宏观代理指标。
    """
    import inspect
    import re
    import textwrap
    try:
        source = inspect.getsource(strategy_fn)
        source = textwrap.dedent(source)
    except Exception as e:
        return False, f"FATAL: 无法获取策略函数源码以执行 AST 静态扫描: {e}"

    try:
        tree = ast.parse(source)
    except Exception as e:
        return False, f"FATAL: 策略函数 AST 语法树解析失败: {e}"

    banned_years = {'2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'}
    date_pattern = re.compile(r'20(1[8-9]|2[0-6])(-\d{2}-\d{2})?')

    # 剔除顶层 docstring
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(getattr(node.body[0], 'value', None), ast.Constant)):
                node.body.pop(0)

    for node in ast.walk(tree):
        val = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
        elif isinstance(node, getattr(ast, 'Str', type(None))):
            val = getattr(node, 's', '')

        if val and isinstance(val, str):
            for yr in banned_years:
                if yr in val:
                    return False, (
                        f"FATAL: Calendar Date Hardcoding Detected! 策略函数源码中发现违规历史日历年份字面量 '{yr}' (内容: '{val}')！"
                        "严禁靠偷看历史日历截面作弊，策略只能使用与时间轴无关的纯内生量价、动量与宏观序列！"
                    )
            match = date_pattern.search(val)
            if match:
                matched_str = match.group(0)
                return False, (
                    f"FATAL: Calendar Date Hardcoding Detected! 策略函数源码中发现违规日历日期字面量 '{matched_str}' (内容: '{val}')！"
                    "严禁硬编码日期切分，策略必须通过内生技术状态机实现全自动跨周期自适应！"
                )

    return True, None


class JudgeEngine:
    """
    铁血裁判引擎核心类
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.data_loader = DataLoader()
        self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 进化记忆库表结构"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trials (
                trial_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ast_hash TEXT,
                strategy_name TEXT,
                island TEXT,
                params_json TEXT,
                overall_sharpe REAL,
                overall_calmar REAL,
                overall_mdd REAL,
                survival_rate REAL,
                slice_scores_json TEXT,
                status TEXT,
                failure_reason TEXT,
                holdout_tested INTEGER DEFAULT 0,
                holdout_sharpe REAL DEFAULT NULL,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def get_total_trials(self) -> int:
        """获取累计历史试错回测次数"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM trials")
        row = cur.fetchone()
        conn.close()
        return int(row[0]) if row else 0

    def calculate_dsr_threshold(self, n_trials: int) -> float:
        """
        计算检验D动态综合夏普门槛：
        Threshold(N) = 0.55 + 0.02 * floor(N / 10) + 0.0005 * (N ** 1.1)
        封顶上限 1.10
        """
        base_sharpe = 0.55
        incr = 0.02 * math.floor(n_trials / 10.0) + 0.0005 * (n_trials ** 1.1)
        thresh = base_sharpe + incr
        return round(min(1.10, thresh), 4)

    def probe_look_ahead_bias(
        self,
        strategy_fn: Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, float]],
        params: Dict[str, Any],
        full_df: pd.DataFrame,
        n_samples: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """
        检验A：未来函数因果探针
        随机抽取 10 个历史截面 T，分别传入 df[:T] 与 df[:T+20] 计算 T 日权重。
        若两次输出差异 > 1e-7，立即判定 FATAL: Look-Ahead Bias Detected
        """
        # 截面抽取范围：2018年下半年至2025年上半年，留足回看窗口与+20探针窗口
        total_len = len(full_df)
        if total_len < 100:
            return True, None

        np.random.seed(42)  # 固定种子确保因果检验可确定性复现
        valid_indices = np.random.randint(60, total_len - 25, size=n_samples)

        for idx in valid_indices:
            t_date = full_df['date'].iloc[idx]
            has_td = ('target_date' in strategy_fn.__code__.co_varnames)

            # 1. 真实过去窗口 (截止到 T)
            df_t = full_df.iloc[:idx + 1].copy()
            w_t = strategy_fn(df_t, params, target_date=t_date) if has_td else strategy_fn(df_t, params)

            # 2. 注入未来 20 天窗口 (截止到 T+20)，要求计算 T 日权重
            df_future = full_df.iloc[:idx + 21].copy()
            w_future = strategy_fn(df_future, params, target_date=t_date) if has_td else strategy_fn(df_future, params)

            # 对比在 T 日的决策
            all_keys = set(w_t.keys()) | set(w_future.keys())
            for k in all_keys:
                val1 = w_t.get(k, 0.0)
                val2 = w_future.get(k, 0.0)
                diff = abs(val1 - val2)
                if diff > 1e-7:
                    msg = (
                        f"FATAL: Look-Ahead Bias Detected at T={t_date.strftime('%Y-%m-%d')} for asset '{k}'! "
                        f"w[:T]={val1:.8f} vs w[:T+20]={val2:.8f}, diff={diff:.2e} > 1e-7"
                    )
                    return False, msg

        return True, None

    def evaluate_strategy_on_slice(
        self,
        strategy_fn: Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, float]],
        params: Dict[str, Any],
        slice_df: pd.DataFrame,
        full_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        在单个历史切片上推演策略并对标 30/70 基准 (高性能 iloc 零拷贝切片)
        """
        slice_dates = slice_df['date'].tolist()
        full_dates = full_df['date'].tolist()
        date_to_idx = {d: i for i, d in enumerate(full_dates)}
        weight_rows = []

        # 逐日推演决策权重 (完全因果)
        for d in slice_dates:
            idx = date_to_idx[d]
            history_df = full_df.iloc[:idx + 1]
            w_dict = strategy_fn(history_df, params)
            row = {'date': d}
            row.update(w_dict)
            weight_rows.append(row)

        weights_df = pd.DataFrame(weight_rows)
        asset_cols = [c for c in weights_df.columns if c != 'date']

        # 真实模拟算子
        sim_res = self.data_loader.simulate_execution(
            weights_df=weights_df,
            prices_df=slice_df[['date'] + asset_cols]
        )

        nav_s = sim_res['nav']
        daily_ret = sim_res['daily_return']
        years = len(slice_df) / 252.0
        final_nav = float(nav_s.iloc[-1])
        cum_ret = (final_nav - 1.0) * 100.0
        ann_ret = (final_nav ** (1.0 / years) - 1.0) * 100.0 if years > 0 and final_nav > 0 else 0.0

        cummax = nav_s.cummax()
        mdd_s = (nav_s - cummax) / cummax
        mdd_pct = float(mdd_s.min() * 100.0)

        # Calmar
        calmar = abs(ann_ret / mdd_pct) if mdd_pct != 0 else 0.0

        # 月度胜率
        sim_res['month'] = pd.to_datetime(sim_res['date']).dt.to_period('M')
        monthly_ret = sim_res.groupby('month')['daily_return'].apply(lambda x: (1.0 + x).prod() - 1.0)
        monthly_win_rate = float((monthly_ret > 0).mean() * 100.0) if len(monthly_ret) > 0 else 0.0

        # 盈亏比 Profit Factor
        pos_sum = daily_ret[daily_ret > 0].sum()
        neg_sum = abs(daily_ret[daily_ret < 0].sum())
        profit_factor = float(pos_sum / neg_sum) if neg_sum > 0 else 99.0

        # 年化波动率与夏普比率 (扣除真实无风险利率 Rf = 2.0%)
        ann_vol = float(daily_ret.std() * (252.0 ** 0.5) * 100.0)
        sharpe = (ann_ret - 2.0) / ann_vol if ann_vol > 0 else 0.0

        # 对标 50/50 股债静态基准
        bench_nav = slice_df['BENCHMARK_50_50'] if 'BENCHMARK_50_50' in slice_df.columns else slice_df['BENCHMARK_30_70']
        bench_ret = float((bench_nav.iloc[-1] / bench_nav.iloc[0] - 1.0) * 100.0)
        excess_ret = cum_ret - bench_ret

        # 计算债券类资产 (930609 + H11009) 平均仓位
        bond_cols = [c for c in ['930609', 'H11009'] if c in weights_df.columns]
        if bond_cols:
            avg_bond_weight = float(weights_df[bond_cols].fillna(0.0).sum(axis=1).mean() * 100.0)
        else:
            avg_bond_weight = 0.0

        # 计算 A股本土权益资产 (H00300, H00905, H00852, STAR50_STITCH, H00922, H30269) 平均仓位
        ashare_cols = [c for c in ['H00300', 'H00905', 'H00852', 'STAR50_STITCH', 'H00922', 'H30269'] if c in weights_df.columns]
        avg_ashare_weight = float(weights_df[ashare_cols].fillna(0.0).sum(axis=1).mean() * 100.0) if ashare_cols else 0.0

        # 计算 非A股外援资产 (AU9999 + SPX_CNY)
        gold_cols = [c for c in ['AU9999'] if c in weights_df.columns]
        spx_cols = [c for c in ['SPX_CNY'] if c in weights_df.columns]
        offshore_cols = gold_cols + spx_cols
        max_daily_offshore = float(weights_df[offshore_cols].fillna(0.0).sum(axis=1).max() * 100.0) if offshore_cols else 0.0
        max_daily_spx = float(weights_df[spx_cols].fillna(0.0).sum(axis=1).max() * 100.0) if spx_cols else 0.0
        avg_offshore_weight = float(weights_df[offshore_cols].fillna(0.0).sum(axis=1).mean() * 100.0) if offshore_cols else 0.0

        return {
            'final_nav': round(final_nav, 4),
            'cum_return_pct': round(cum_ret, 2),
            'annualized_return_pct': round(ann_ret, 2),
            'annualized_vol_pct': round(ann_vol, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown_pct': round(mdd_pct, 2),
            'calmar_ratio': round(calmar, 2),
            'monthly_win_rate_pct': round(monthly_win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'benchmark_return_pct': round(bench_ret, 2),
            'excess_return_pct': round(excess_ret, 2),
            'avg_bond_weight_pct': round(avg_bond_weight, 2),
            'avg_ashare_weight_pct': round(avg_ashare_weight, 2),
            'avg_offshore_weight_pct': round(avg_offshore_weight, 2),
            'max_daily_offshore_pct': round(max_daily_offshore, 2),
            'max_daily_spx_pct': round(max_daily_spx, 2)
        }

    def perturb_parameters(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检验C参数±15%爆破样本生成器：
        K <= 4 参数上限；单参数正交边界 (2K) + 拉丁超立方采样补足至 16 个点
        """
        # 筛选数值型自由参数
        numeric_params = {k: v for k, v in params.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        k_count = len(numeric_params)

        if k_count == 0:
            return [params.copy()]
        if k_count > 6:
            raise ValueError(f"自由参数过多 (K={k_count} > 6)！严禁暴力穷举过拟合！")

        param_keys = list(numeric_params.keys())
        samples = []

        # 1. 2K 个正交单边扰动点
        for p_k in param_keys:
            orig_val = numeric_params[p_k]
            is_int = isinstance(orig_val, int)

            # +15% 扰动
            delta = max(1, round(0.15 * orig_val)) if is_int else (0.15 * orig_val)
            p_up = params.copy()
            p_up[p_k] = (orig_val + delta) if is_int else round(orig_val + delta, 4)
            samples.append(p_up)

            # -15% 扰动
            p_down = params.copy()
            p_down[p_k] = (orig_val - delta) if is_int else round(orig_val - delta, 4)
            samples.append(p_down)

        # 2. 拉丁超立方抽样 (LHS, seed=42) 补足至 16 组
        n_needed = max(0, 16 - len(samples))
        if n_needed > 0:
            sampler = qmc.LatinHypercube(d=k_count, seed=42)
            lhs_samples = sampler.random(n=n_needed)  # 0.0 ~ 1.0 范围

            for lhs_row in lhs_samples:
                p_lhs = params.copy()
                for idx, p_k in enumerate(param_keys):
                    orig_val = numeric_params[p_k]
                    is_int = isinstance(orig_val, int)
                    # 缩放至 [-15%, +15%]
                    scale = (lhs_row[idx] - 0.5) * 2.0 * 0.15
                    if is_int:
                        delta = round(scale * orig_val)
                        if delta == 0:
                            delta = 1 if scale > 0 else -1
                        p_lhs[p_k] = int(orig_val + delta)
                    else:
                        p_lhs[p_k] = round(orig_val * (1.0 + scale), 4)
                samples.append(p_lhs)

        return samples[:16]

    def run_judge(
        self,
        strategy_fn: Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, float]],
        strategy_name: str,
        island_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的铁血裁判全量四重核检流程
        """
        start_time = datetime.now()
        console.print(f"\n[bold cyan]⚖️  启动铁血裁判引擎考核：[/bold cyan] [bold white]{strategy_name}[/bold white] (流派: {island_name})")

        # 1. 试错次数与检验D门槛
        total_trials = self.get_total_trials()
        if total_trials >= 100:
            raise SystemExit("FATAL: evolution.db 试错总次数已达到 100 次硬上限！系统触发熔断终止！")

        threshold_sharpe = self.calculate_dsr_threshold(total_trials)
        console.print(f"[dim]当前历史试错次数 N = {total_trials}，动态综合夏普合格门槛 Threshold(N) = {threshold_sharpe:.4f}[/dim]")

        # 2. 参数处理与 AST 哈希
        p_eval = params if params is not None else getattr(sys.modules.get(strategy_fn.__module__), 'PARAMS', {})
        ast_hash = compute_ast_hash(strategy_fn)

        # 3. 数据集加载 (训练+切片，截断在 2025-06-30，绝不泄漏盲测)
        full_df = self.data_loader.load_total_return_matrix(end_date="2025-06-30")
        slices = self.data_loader.get_style_slices()

        # =========================================================================
        # 检验A：未来函数因果探针 (Look-Ahead Bias Probe)
        # =========================================================================
        console.print("[cyan]🔍 正在执行 [检验A]：未来函数因果探针 (10组随机截面 T vs T+20)...[/cyan]")
        passed_a, err_msg_a = self.probe_look_ahead_bias(strategy_fn, p_eval, full_df)
        if not passed_a:
            console.print(f"[bold red]❌ {err_msg_a}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=0.0, overall_calmar=0.0, overall_mdd=0.0,
                survival_rate=0.0, slice_scores={}, status="FAIL", failure_reason=err_msg_a
            )
            return {'status': 'FAIL', 'gate': 'A', 'reason': err_msg_a}
        console.print("[bold green]✓ 检验A通过：未探测到任何未来函数或前瞻偏差 (差异 <= 1e-7)[/bold green]")

        # =========================================================================
        # 检验A+：AST 静态反作弊扫描锁 (Calendar Date Anti-Cheating Lock)
        # =========================================================================
        console.print("[cyan]🛡️  正在执行 [检验A+]：AST 静态反作弊扫描锁 (检查日历年份与日期硬编码)...[/cyan]")
        passed_aplus, err_msg_aplus = scan_ast_for_calendar_cheating(strategy_fn)
        if not passed_aplus:
            console.print(f"[bold red]❌ {err_msg_aplus}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=0.0, overall_calmar=0.0, overall_mdd=0.0,
                survival_rate=0.0, slice_scores={}, status="FAIL", failure_reason=err_msg_aplus
            )
            return {'status': 'FAIL', 'gate': 'A+', 'reason': err_msg_aplus}
        console.print("[bold green]✓ 检验A+通过：AST静态扫描未发现任何历史年份或日期硬编码字面量，策略为纯内生量价/宏观驱动[/bold green]")

        # =========================================================================
        # 检验B：6 大 A 股历史风格切片全量回归 (Slice Regression)
        # =========================================================================
        console.print("[cyan]📊 正在执行 [检验B]：6大历史风格切片全景回归与基准对标...[/cyan]")
        slice_scores = {}
        slices_beating_bench = 0
        for s_key, (s_start, s_end, s_title) in slices.items():
            sub_df = full_df[(full_df['date'] >= s_start) & (full_df['date'] <= s_end)].copy().reset_index(drop=True)
            res = self.evaluate_strategy_on_slice(strategy_fn, p_eval, sub_df, full_df)
            res['title'] = s_title
            slice_scores[s_key] = res
            if res['excess_return_pct'] > 0:
                slices_beating_bench += 1

        # 全周期 (2018-01-02 ~ 2025-06-30) 综合指标计算
        full_res = self.evaluate_strategy_on_slice(strategy_fn, p_eval, full_df, full_df)
        overall_sharpe = full_res['sharpe_ratio']
        overall_calmar = full_res['calmar_ratio']
        overall_mdd = full_res['max_drawdown_pct']
        overall_cagr = full_res['annualized_return_pct']
        overall_excess = full_res['excess_return_pct']
        avg_bond_weight = full_res['avg_bond_weight_pct']

        overall_ashare_weight = full_res['avg_ashare_weight_pct']
        max_daily_offshore = full_res['max_daily_offshore_pct']
        max_daily_spx = full_res['max_daily_spx_pct']

        # 1. 非A股外援资产（黄金 + 海外QDII）仓位硬上限 (截面 <= 20.0%, SPX <= 10.0%)
        if max_daily_offshore > 20.05:
            reason = (
                f"任意交易日截面非A股外援资产 (AU9999 + SPX_CNY) 合计权重绝对不得超过 20.0%！"
                f"当前单日峰值达 {max_daily_offshore:.2f}%！严禁利用黄金与海外标普套利逃避A股配置！"
            )
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        if max_daily_spx > 10.05:
            reason = (
                f"任意交易日截面标普QDII (SPX_CNY) 单一品种权重不得超过 10.0% (当前单日峰值达 {max_daily_spx:.2f}%) "
                f"以匹配实盘QDII限购容量！"
            )
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 2. 纯债仓位上限硬红线 (全周期纯债平均 <= 50.0%)
        if avg_bond_weight > 50.0:
            reason = (
                f"全周期债券类资产平均仓位 ({avg_bond_weight:.1f}%) 超过 50.0% 限制！"
                "严禁纯债化套利逃避风险，权益资产全周期平均仓位必须 >= 50%！"
            )
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 2.1 切片纯债仓位上限校验 (极端熊市切片允许阶段性升至 80%，其余切片不得超过 50%)
        extreme_bear_slices = {'Slice_1', 'Slice_4'}
        for s_k, s_sc in slice_scores.items():
            s_bond = s_sc.get('avg_bond_weight_pct', 0.0)
            max_allowed = 80.0 if s_k in extreme_bear_slices else 50.0
            if s_bond > max_allowed:
                reason = (
                    f"切片 {s_k} 债券类资产平均仓位 ({s_bond:.1f}%) 超过 {max_allowed:.1f}% 上限！"
                    f"仅在极端熊市切片允许阶段性升至 80% 防御，非极端熊市切片必须 <= 50%！"
                )
                console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
                self._record_trial(
                    ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                    params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                    overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                    status="FAIL", failure_reason=reason
                )
                return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 3. A股本土权益资产仓位硬下限 (全周期均值 >= 55.0%, 牛市切片均值 >= 65.0%)
        if overall_ashare_weight < 55.0:
            reason = (
                f"全周期A股本土权益资产平均仓位 ({overall_ashare_weight:.1f}%) 未达到 55.0% 硬性底线！"
                "必须以A股本土资产轮动为核心驱动力！"
            )
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        offensive_slices = {'Slice_2', 'Slice_3', 'Slice_6'}
        for s_k in offensive_slices:
            s_ashare = slice_scores.get(s_k, {}).get('avg_ashare_weight_pct', 0.0)
            if s_ashare < 65.0:
                reason = (
                    f"进攻/结构牛市切片 {s_k} A股本土权益平均仓位 ({s_ashare:.1f}%) 未达到 65.0% 硬性下限！"
                )
                console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
                self._record_trial(
                    ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                    params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                    overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                    status="FAIL", failure_reason=reason
                )
                return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 4. 牛市切片累计收益与跑输指标 (Slice 2 >= +38.0%, Slice 6 >= +18.0%, 跑输不得超过 -5.0%)
        s2_cum = slice_scores.get('Slice_2', {}).get('cum_return_pct', 0.0)
        if s2_cum < 38.0:
            reason = f"牛市切片 Slice_2 累计收益率 ({s2_cum:.2f}%) 未达到 +38.0% 硬性门槛！"
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        s6_cum = slice_scores.get('Slice_6', {}).get('cum_return_pct', 0.0)
        if s6_cum < 18.0:
            reason = f"牛市切片 Slice_6 累计收益率 ({s6_cum:.2f}%) 未达到 +18.0% 硬性门槛！"
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        for bull_s in ['Slice_2', 'Slice_6']:
            s_exc = slice_scores.get(bull_s, {}).get('excess_return_pct', 0.0)
            if s_exc < -5.0:
                reason = f"牛市切片 {bull_s} 大幅跑输基准超过 -5.0% (当前超额: {s_exc:.2f}%)，判定为牛市严重踏空！"
                console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
                self._record_trial(
                    ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                    params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                    overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                    status="FAIL", failure_reason=reason
                )
                return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 5. 全周期复合年化收益率硬红线 (CAGR >= 11.5%)
        if overall_cagr < 11.5:
            reason = f"全周期复合年化收益率 CAGR ({overall_cagr:.2f}%) 未达到 11.5% 硬性底线！"
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 5.1 全周期最大回撤硬上限 (MaxDD <= 15.50%)
        if abs(overall_mdd) > 15.50:
            reason = f"全周期最大回撤 MaxDD ({abs(overall_mdd):.2f}%) 超过 15.50% 硬性上限！"
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 6. 风格切片跑赢 50/50 基准数量硬红线 (至少 5 个切片跑赢)
        if slices_beating_bench < 5:
            reason = f"6个历史风格切片中仅有 {slices_beating_bench} 个切片跑赢 50/50 基准，未达到至少 5 个切片的硬门槛！"
            console.print(f"[bold red]❌ 检验B未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B', 'reason': reason, 'scores': slice_scores}

        # 8. 检查检验D夏普门槛
        if overall_sharpe < threshold_sharpe:
            reason = f"综合夏普比率 ({overall_sharpe:.2f}) 未达到 DSR 动态门槛 ({threshold_sharpe:.2f})"
            console.print(f"[bold yellow]⚠️  检验B未通过：{reason}[/bold yellow]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'B/D', 'reason': reason, 'scores': slice_scores}

        console.print(
            f"[bold green]✓ 检验B通过：全周期 CAGR {overall_cagr:.2f}% >= 11.5%，MaxDD {abs(overall_mdd):.2f}% <= 15.50%，"
            f"A股均仓 {overall_ashare_weight:.1f}% >= 55.0%，债券均仓 {avg_bond_weight:.1f}% <= 50.0%，"
            f"外援峰值 {max_daily_offshore:.1f}% <= 20.0%，"
            f"{slices_beating_bench}/6 切片超额，综合夏普 {overall_sharpe:.2f} >= 门槛 {threshold_sharpe:.2f}[/bold green]"
        )

        # =========================================================================
        # 检验C：参数 ±15% 网格与拉丁超立方爆破 (Robustness Plateau)
        # =========================================================================
        console.print("[cyan]💣 正在执行 [检验C]：参数±15%扰动爆破与高原存活检验 (16组采样)...[/cyan]")
        try:
            perturbed_samples = self.perturb_parameters(p_eval)
        except ValueError as e:
            reason = str(e)
            console.print(f"[bold red]❌ {reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=0.0, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'C', 'reason': reason}

        survived_count = 0
        total_p_samples = len(perturbed_samples)

        for p_sample in perturbed_samples:
            # 测算样本指标
            p_slice_scores = {}
            p_pos_slices = 0
            worst_mdd = 0.0

            for s_key, (s_start, s_end, _) in slices.items():
                sub_df = full_df[(full_df['date'] >= s_start) & (full_df['date'] <= s_end)].copy().reset_index(drop=True)
                p_res = self.evaluate_strategy_on_slice(strategy_fn, p_sample, sub_df, full_df)
                p_slice_scores[s_key] = p_res
                if p_res['cum_return_pct'] > 0 or p_res['excess_return_pct'] > 0:
                    p_pos_slices += 1
                if abs(p_res['max_drawdown_pct']) > worst_mdd:
                    worst_mdd = abs(p_res['max_drawdown_pct'])

            # 样本全周期夏普与表现
            p_full_res = self.evaluate_strategy_on_slice(strategy_fn, p_sample, full_df, full_df)
            p_sharpe = p_full_res['sharpe_ratio']

            # 判定三条件：
            # 条件A: 夏普 >= 原夏普 * 0.80 且 >= 0.50
            cond_a = (p_sharpe >= overall_sharpe * 0.80) and (p_sharpe >= 0.50)
            # 条件B: worst_mdd <= min(18.0%, abs(overall_mdd) + 3.0%)
            cond_b = worst_mdd <= min(18.0, abs(overall_mdd) + 3.0)
            # 条件C: 至少 5 个切片保持正收益或跑赢 30/70
            cond_c = p_pos_slices >= 5

            if cond_a and cond_b and cond_c:
                survived_count += 1

        survival_rate = (survived_count / total_p_samples) * 100.0
        console.print(f"[dim]扰动样本存活数: {survived_count}/{total_p_samples} (存活率: {survival_rate:.1f}%)[/dim]")

        if survival_rate < 80.0:
            reason = f"参数邻域存活率 ({survival_rate:.1f}%) < 80.0% 阈值，判定为孤岛过拟合 (Isolated Overfitting Peak)"
            console.print(f"[bold red]❌ 检验C未通过：{reason}[/bold red]")
            self._record_trial(
                ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
                params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
                overall_mdd=overall_mdd, survival_rate=survival_rate, slice_scores=slice_scores,
                status="FAIL", failure_reason=reason
            )
            return {'status': 'FAIL', 'gate': 'C', 'reason': reason, 'survival_rate': survival_rate}

        console.print(f"[bold green]✓ 检验C通过：高原存活率 {survival_rate:.1f}% >= 80%，策略具备强参数稳健性[/bold green]")

        # =========================================================================
        # 全部考核通过，写入 SUCCESS 记录
        # =========================================================================
        trial_id = self._record_trial(
            ast_hash=ast_hash, strategy_name=strategy_name, island=island_name,
            params=p_eval, overall_sharpe=overall_sharpe, overall_calmar=overall_calmar,
            overall_mdd=overall_mdd, survival_rate=survival_rate, slice_scores=slice_scores,
            status="PASS", failure_reason=None
        )

        self._print_summary_table(
            strategy_name, island_name, overall_sharpe, overall_calmar, overall_mdd,
            overall_cagr, overall_excess, avg_bond_weight, survival_rate, slice_scores
        )

        return {
            'status': 'PASS',
            'trial_id': trial_id,
            'ast_hash': ast_hash,
            'strategy_name': strategy_name,
            'island': island_name,
            'overall_sharpe': round(overall_sharpe, 2),
            'overall_calmar': round(overall_calmar, 2),
            'overall_cagr_pct': round(overall_cagr, 2),
            'overall_excess_pct': round(overall_excess, 2),
            'avg_bond_weight_pct': round(avg_bond_weight, 2),
            'overall_mdd_pct': round(overall_mdd, 2),
            'survival_rate': round(survival_rate, 1),
            'slice_scores': slice_scores
        }

    def _record_trial(
        self,
        ast_hash: str,
        strategy_name: str,
        island: str,
        params: Dict[str, Any],
        overall_sharpe: float,
        overall_calmar: float,
        overall_mdd: float,
        survival_rate: float,
        slice_scores: Dict[str, Any],
        status: str,
        failure_reason: Optional[str]
    ) -> int:
        """持久化单次试错记录至 evolution.db"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO trials (
                ast_hash, strategy_name, island, params_json,
                overall_sharpe, overall_calmar, overall_mdd, survival_rate,
                slice_scores_json, status, failure_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ast_hash, strategy_name, island, json.dumps(params, ensure_ascii=False),
            round(overall_sharpe, 4), round(overall_calmar, 4), round(overall_mdd, 4),
            round(survival_rate, 2), json.dumps(slice_scores, ensure_ascii=False),
            status, failure_reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        trial_id = cur.lastrowid
        conn.commit()
        conn.close()
        return trial_id

    def _print_summary_table(
        self,
        strategy_name: str,
        island_name: str,
        sharpe: float,
        calmar: float,
        mdd: float,
        cagr: float,
        excess: float,
        bond_weight: float,
        survival_rate: float,
        slice_scores: Dict[str, Any]
    ) -> None:
        """渲染 Rich 彩色汇总研报表"""
        t = Table(title=f"🏆 铁血裁判综合考核报告: {strategy_name} ({island_name})", show_lines=True)
        t.add_column("切片编号与宏观背景", style="bold cyan")
        t.add_column("累计收益", justify="center", style="bold green")
        t.add_column("最大回撤", justify="center", style="bold yellow")
        t.add_column("卡玛比率", justify="center", style="white")
        t.add_column("月度胜率", justify="center", style="white")
        t.add_column("盈亏比", justify="center", style="white")
        t.add_column("50/50基准收益", justify="center", style="dim")
        t.add_column("相对超额", justify="center", style="bold magenta")

        for s_k, sc in slice_scores.items():
            t.add_row(
                f"{s_k}: {sc['title'][:14]}",
                f"{sc['cum_return_pct']:+.1f}%",
                f"{sc['max_drawdown_pct']:.1f}%",
                f"{sc['calmar_ratio']:.2f}",
                f"{sc['monthly_win_rate_pct']:.1f}%",
                f"{sc['profit_factor']:.2f}",
                f"{sc['benchmark_return_pct']:+.1f}%",
                f"{sc['excess_return_pct']:+.1f}%"
            )

        console.print(t)
        panel_text = (
            f"[bold green]✓ 综合状态: 全部检验严格通过 (STATUS: PASS)[/bold green]\n"
            f"• 全周期 CAGR: [bold green]{cagr:.2f}%[/bold green] (>= 11.5%)  "
            f"• 基准超额: [bold magenta]+{excess:.2f}%[/bold magenta]\n"
            f"• 债券均仓: [bold cyan]{bond_weight:.1f}%[/bold cyan] (<= 50.0%)  "
            f"• 综合夏普 (扣除Rf 2%): [bold cyan]{sharpe:.2f}[/bold cyan]  "
            f"• 卡玛比率: [bold cyan]{calmar:.2f}[/bold cyan]  "
            f"• 最大回撤: [bold yellow]{mdd:.2f}%[/bold yellow] (<= 15.50%)\n"
            f"• 参数高原存活率: [bold magenta]{survival_rate:.1f}%[/bold magenta] (>= 80% 杜绝孤岛过拟合)"
        )
        console.print(Panel(panel_text, title="🎯 综合结论", expand=False))


if __name__ == "__main__":
    # 简单自检执行
    from islands import island_erp
    judge = JudgeEngine()
    res = judge.run_judge(
        strategy_fn=island_erp.strategy_fn,
        strategy_name="宏观股债性价比动态倾斜策略",
        island_name="island_erp",
        params=island_erp.PARAMS
    )
    print("Judge output:", res)
