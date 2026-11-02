"""
全市场基金智能漏斗筛选器 (market_screener.py)
阶段三核心模块：从 28,177 只全市场公募基金中，通过多级智能漏斗
筛选出约 200~500 只高质量候选基金，供胜率优化器使用。

漏斗流程:
  Step 1: 全市场预筛 (28,177 → ~3,000~5,000)
          规模 > 2 亿、成立 > 3 年、非清盘
  Step 2: 分桶排名 (~5,000 → ~200~500)
          按类型分桶 → 每桶按夏普/回撤/年化综合评分 Top N
  Step 3: 批量获取候选基金 NAV 矩阵
          本地缓存 + akshare 增量同步
"""

import time
import datetime
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# 本地模块
import sys
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

_WORKSPACE_ROOT = _THIS_DIR.parent if _THIS_DIR.name == "AGY2_FundAdvisory" else _THIS_DIR

from cache_manager import SmartCacheManager


# ══════════════════════════════════════════════════════════════════
#  基金类型分桶映射
# ══════════════════════════════════════════════════════════════════

BUCKET_MAP: Dict[str, List[str]] = {
    "equity": [
        "指数型-股票", "混合型-偏股", "股票型", "混合型-灵活", "混合型-平衡",
    ],
    "bond": [
        "债券型-长债", "债券型-混合二级", "债券型-混合一级",
        "债券型-中短债", "债券型-信用债", "债券型-利率债", "指数型-固收",
    ],
    "overseas": [
        "指数型-海外股票", "QDII-混合偏股", "QDII-普通股票",
        "QDII-混合灵活", "QDII-混合债", "QDII-混合平衡", "QDII-FOF",
    ],
    "commodity": ["QDII-商品", "商品", "QDII-REITs", "Reits", "指数型-其他"],
    "money": ["货币型-普通货币", "货币型-浮动净值"],
    "fof": ["FOF-稳健型", "FOF-均衡型", "FOF-进取型"],
    "balanced_debt": ["混合型-偏债", "混合型-绝对收益", "QDII-纯债"],
}

# 反向映射：fund_type → bucket
_TYPE_TO_BUCKET: Dict[str, str] = {}
for bucket, types in BUCKET_MAP.items():
    for t in types:
        _TYPE_TO_BUCKET[t] = bucket


def _assign_bucket(fund_type: str) -> str:
    """将 fund_type 映射到 bucket，未知类型归入 'other'"""
    ft = str(fund_type).strip() if fund_type else ""
    if not ft:
        return "other"
    return _TYPE_TO_BUCKET.get(ft, "other")


# ══════════════════════════════════════════════════════════════════
#  核心筛选器
# ══════════════════════════════════════════════════════════════════

class MarketScreener:
    """全市场基金智能漏斗筛选器"""

    # fund_catalog.parquet 路径
    CATALOG_PATH = _WORKSPACE_ROOT / "data" / "master" / "fund_catalog.parquet"

    # ─── Step 1: 全市场预筛 ─────────────────────────────────────

    @classmethod
    def build_candidate_pool(
        cls,
        as_of_date: Optional[datetime.date] = None,
        min_aum_billion: float = 2.0,
        min_years: float = 3.0,
        exclude_liquidated: bool = True,
        force_rebuild: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> pd.DataFrame:
        """
        Step 1: 全市场预筛。

        1. 读取 fund_catalog.parquet (28,177 只)
        2. 通过 akshare 获取基金规模、成立日期、状态
        3. 过滤：规模 >= min_aum_billion、成立 >= min_years、未清盘
        4. 分桶标注

        Parameters
        ----------
        as_of_date : 筛选基准日期，默认 today()
        min_aum_billion : 最低规模（亿元）
        min_years : 最低成立年限
        force_rebuild : 跳过周缓存

        Returns
        -------
        pd.DataFrame with columns:
            fund_code, fund_name, fund_type, bucket, aum_billion,
            inception_date, status, share_class, ac_pair_code
        """
        if as_of_date is None:
            as_of_date = datetime.date.today()

        # 检查缓存
        if not force_rebuild:
            cached = SmartCacheManager.get_candidate_pool(
                min_aum=float(min_aum_billion), min_years=float(min_years)
            )
            if cached is not None:
                if progress_callback:
                    progress_callback(1, 1, f"从缓存加载候选池: {len(cached)} 只基金")
                return cached

        if progress_callback:
            progress_callback(0, 4, "读取全市场基金目录...")

        # 1. 读取本地 catalog
        if not cls.CATALOG_PATH.exists():
            raise FileNotFoundError(f"基金目录文件不存在: {cls.CATALOG_PATH}")

        catalog_df = pd.read_parquet(cls.CATALOG_PATH)

        if progress_callback:
            progress_callback(1, 4, f"全市场 {len(catalog_df):,} 只基金，正在获取规模和成立日期...")

        # 2. 通过 akshare 获取基金信息（带规模和成立日期）
        fund_info_df = cls._fetch_fund_info_batch(catalog_df, progress_callback)

        if progress_callback:
            progress_callback(2, 4, "过滤：规模、成立年限、清盘状态...")

        # 3. 合并并过滤
        merged = catalog_df.merge(
            fund_info_df,
            left_on="symbol",
            right_on="fund_code",
            how="inner",
        )

        # 过滤条件
        cutoff_date = as_of_date - datetime.timedelta(days=int(min_years * 365.25))
        mask = pd.Series(True, index=merged.index)

        if "aum_billion" in merged.columns:
            if merged["aum_billion"].notna().any():
                mask &= merged["aum_billion"].fillna(0) >= min_aum_billion
            else:
                warnings.warn("规模数据完全缺失（降级模式），跳过规模过滤")

        if "inception_date" in merged.columns:
            merged["inception_date"] = pd.to_datetime(merged["inception_date"], errors="coerce")
            mask &= merged["inception_date"] <= pd.Timestamp(cutoff_date)

        if exclude_liquidated and "status" in merged.columns:
            mask &= ~merged["status"].str.contains("清盘|终止|到期", na=False)

        filtered = merged.loc[mask].copy()

        # 4. 分桶
        filtered["bucket"] = filtered["fund_type"].apply(_assign_bucket)

        # 5. A/C 类标注
        filtered["share_class"] = filtered["fund_name"].apply(cls._detect_share_class)
        filtered["ac_pair_code"] = ""  # 后续补充配对

        # 去重：保留 A 类（回测用 A 类，输出时按持有期推荐）
        filtered = cls._deduplicate_ac_classes(filtered)

        # 整理输出列
        result_cols = [
            "fund_code", "fund_name", "fund_type", "bucket",
            "aum_billion", "inception_date", "status",
            "share_class", "ac_pair_code",
        ]
        for col in result_cols:
            if col not in filtered.columns:
                filtered[col] = ""

        result = filtered[result_cols].reset_index(drop=True)

        if progress_callback:
            progress_callback(3, 4, f"预筛完成: {len(result):,} 只候选基金")

        # 保存缓存
        SmartCacheManager.save_candidate_pool(
            result, min_aum=float(min_aum_billion), min_years=float(min_years)
        )

        if progress_callback:
            progress_callback(4, 4, f"候选池已缓存: {len(result):,} 只")

        return result

    @classmethod
    def _fetch_fund_info_batch(
        cls,
        catalog_df: pd.DataFrame,
        progress_callback: Optional[Callable] = None,
    ) -> pd.DataFrame:
        """
        批量获取基金规模和成立日期。
        优先使用 akshare 的 fund_name_em() 一次性获取全量。
        """
        try:
            import akshare as ak

            if progress_callback:
                progress_callback(1, 4, "从东方财富获取全市场基金列表...")

            # fund_name_em 一次性返回全市场基金列表（含规模、成立日期等）
            df_all = ak.fund_name_em()

            # 标准化列名
            col_map = {}
            for col in df_all.columns:
                if "代码" in col or "基金代码" in col:
                    col_map[col] = "fund_code"
                elif "成立日期" in col or "成立" in col:
                    col_map[col] = "inception_date"
                elif "基金简称" in col or "名称" in col:
                    col_map[col] = "fund_name_em"
                elif "类型" in col:
                    col_map[col] = "fund_type_em"

            df_all = df_all.rename(columns=col_map)

            if "fund_code" not in df_all.columns:
                # 尝试用第一列作为 fund_code
                df_all = df_all.rename(columns={df_all.columns[0]: "fund_code"})

            df_all["fund_code"] = df_all["fund_code"].astype(str).str.strip()

            # 获取规模信息
            aum_data = cls._fetch_aum_data(progress_callback)
            if aum_data is not None and not aum_data.empty:
                df_all = df_all.merge(aum_data, on="fund_code", how="left")
            else:
                df_all["aum_billion"] = np.nan

            # 状态标注
            if "status" not in df_all.columns:
                df_all["status"] = "正常"

            return df_all[["fund_code", "inception_date", "aum_billion", "status"]].drop_duplicates(subset=["fund_code"])

        except Exception as e:
            warnings.warn(f"akshare 获取基金信息失败: {e}，使用本地 catalog 降级")
            # 降级：仅使用本地 catalog 数据
            result = pd.DataFrame({
                "fund_code": catalog_df["symbol"].astype(str),
                "inception_date": pd.NaT,
                "aum_billion": np.nan,  # 降级：规模未知，由过滤逻辑决定是否跳过
                "status": "正常",
            })
            return result

    @classmethod
    def _fetch_aum_data(
        cls, progress_callback: Optional[Callable] = None
    ) -> Optional[pd.DataFrame]:
        """获取基金规模数据"""
        try:
            import akshare as ak
            if progress_callback:
                progress_callback(1, 4, "获取基金规模数据...")

            # 尝试使用 fund_aum_em
            df_aum = ak.fund_aum_em()
            col_map = {}
            for col in df_aum.columns:
                if "代码" in col:
                    col_map[col] = "fund_code"
                elif "规模" in col or "资产" in col:
                    col_map[col] = "aum"
            df_aum = df_aum.rename(columns=col_map)
            if "fund_code" in df_aum.columns and "aum" in df_aum.columns:
                df_aum["fund_code"] = df_aum["fund_code"].astype(str).str.strip()
                df_aum["aum_billion"] = pd.to_numeric(df_aum["aum"], errors="coerce") / 1e8
                return df_aum[["fund_code", "aum_billion"]].drop_duplicates(subset=["fund_code"])
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_share_class(fund_name: str) -> str:
        """检测 A/C 类"""
        name = str(fund_name).strip()
        if name.endswith("C") or name.endswith("C类"):
            return "C"
        if name.endswith("B") or name.endswith("B类"):
            return "B"
        if name.endswith("E") or name.endswith("E类"):
            return "E"
        return "A"

    @classmethod
    def _deduplicate_ac_classes(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        A/C 类去重：同一基金只保留 A 类用于回测，记录 C 类配对代码。
        去重逻辑：按基金名（去掉尾部 A/C/B/E 标识）分组，
        优先保留 A 类，记录 C 类代码。
        """
        if df.empty:
            return df

        # 生成基础名（去掉尾部份额类标识）
        def base_name(name: str) -> str:
            n = str(name).strip()
            for suffix in ["C类", "A类", "B类", "E类", "C", "A", "B", "E"]:
                if n.endswith(suffix):
                    return n[:-len(suffix)]
            return n

        df = df.copy()
        df["_base_name"] = df["fund_name"].apply(base_name)

        # 分组处理
        keep_indices = []
        for _, group in df.groupby("_base_name"):
            if len(group) == 1:
                keep_indices.append(group.index[0])
                continue

            # 优先 A 类
            a_rows = group[group["share_class"] == "A"]
            c_rows = group[group["share_class"] == "C"]

            if not a_rows.empty:
                idx = a_rows.index[0]
                if not c_rows.empty:
                    df.loc[idx, "ac_pair_code"] = str(c_rows.iloc[0].get("fund_code", ""))
                keep_indices.append(idx)
            elif not c_rows.empty:
                keep_indices.append(c_rows.index[0])
            else:
                keep_indices.append(group.index[0])

        result = df.loc[keep_indices].drop(columns=["_base_name"]).reset_index(drop=True)
        return result

    # ─── Step 2: 分桶排名 ──────────────────────────────────────

    @classmethod
    def rank_and_select_top_n(
        cls,
        candidate_df: pd.DataFrame,
        top_n_per_bucket: int = 80,
        lookback_years: float = 3.0,
        progress_callback: Optional[Callable] = None,
    ) -> pd.DataFrame:
        """
        Step 2: 分桶排名。

        1. 获取候选基金的历史 NAV
        2. 计算夏普率、最大回撤、年化收益率
        3. 综合评分排名
        4. 每桶取 Top N

        Parameters
        ----------
        candidate_df : Step 1 的输出
        top_n_per_bucket : 每桶取前 N 只
        lookback_years : 评估回看年数

        Returns
        -------
        pd.DataFrame with additional columns: sharpe, max_dd, annual_return, composite_score
        """
        if candidate_df.empty:
            return candidate_df

        if progress_callback:
            progress_callback(0, 3, "获取候选基金历史净值用于排名...")

        # 获取 NAV 数据
        codes = candidate_df["fund_code"].tolist()
        start_date = (
            datetime.date.today() - datetime.timedelta(days=int(lookback_years * 365.25))
        ).isoformat()

        nav_data = cls._fetch_nav_for_ranking(codes, start_date, progress_callback)

        if progress_callback:
            progress_callback(1, 3, "计算夏普率、最大回撤、年化收益...")

        # 计算指标
        metrics = []
        for code in codes:
            if code not in nav_data or len(nav_data[code]) < 60:
                metrics.append({
                    "fund_code": code, "sharpe": -999, "max_dd": -1,
                    "annual_return": -999, "composite_score": -999,
                })
                continue

            nav = np.array(nav_data[code], dtype=np.float64)
            daily_ret = nav[1:] / nav[:-1] - 1.0
            n_days = len(nav)

            # 年化收益
            total_ret = nav[-1] / nav[0] - 1.0
            years = n_days / 250.0
            ann_ret = (1.0 + total_ret) ** (1.0 / max(years, 0.1)) - 1.0 if total_ret > -1 else -1.0

            # 夏普率（无风险利率取 2%）
            rf_daily = 0.02 / 250.0
            excess = daily_ret - rf_daily
            sharpe = float(np.mean(excess) / max(np.std(excess, ddof=1), 1e-10) * np.sqrt(250))

            # 最大回撤
            cummax = np.maximum.accumulate(nav)
            drawdowns = (nav - cummax) / cummax
            max_dd = float(np.min(drawdowns))

            metrics.append({
                "fund_code": code,
                "sharpe": sharpe,
                "max_dd": max_dd,
                "annual_return": ann_ret,
                "composite_score": 0.0,  # 后面计算
            })

        metrics_df = pd.DataFrame(metrics)

        if progress_callback:
            progress_callback(2, 3, "综合评分与分桶排名...")

        # 合并
        result = candidate_df.merge(metrics_df, on="fund_code", how="left")
        result = result.dropna(subset=["sharpe"])
        result = result[result["composite_score"] != -999].copy()

        # 归一化评分（按桶内归一化）
        ranked_parts = []
        for bucket, grp in result.groupby("bucket"):
            if grp.empty:
                continue
            grp = grp.copy()

            # Min-Max 归一化
            def _norm(col):
                mn, mx = col.min(), col.max()
                return (col - mn) / max(mx - mn, 1e-10)

            s_sharpe = _norm(grp["sharpe"])
            s_dd = 1.0 - _norm(grp["max_dd"].abs())  # 回撤越小越好
            s_ret = _norm(grp["annual_return"])

            grp["composite_score"] = 0.35 * s_sharpe + 0.30 * s_dd + 0.35 * s_ret
            grp = grp.sort_values("composite_score", ascending=False)
            ranked_parts.append(grp.head(top_n_per_bucket))

        if not ranked_parts:
            return pd.DataFrame()

        final = pd.concat(ranked_parts, ignore_index=True)

        if progress_callback:
            progress_callback(3, 3, f"分桶排名完成: {len(final)} 只候选基金")

        return final

    @classmethod
    def _fetch_nav_for_ranking(
        cls,
        fund_codes: List[str],
        start_date: str,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, List[float]]:
        """
        获取多只基金的 NAV 数据用于排名。
        优先读缓存，缺失的从 akshare 拉取。
        """
        nav_data: Dict[str, List[float]] = {}
        to_fetch = []

        for code in fund_codes:
            cached = SmartCacheManager.get_nav_cache(code)
            if cached is not None and not cached.empty and len(cached) > 60:
                nav_col = "nav" if "nav" in cached.columns else cached.columns[-1]
                nav_data[code] = cached[nav_col].tolist()
            else:
                to_fetch.append(code)

        if to_fetch:
            total_to_fetch = len(to_fetch)
            if progress_callback:
                progress_callback(0, total_to_fetch, f"需从网络获取 {total_to_fetch} 只基金净值...")

            try:
                import akshare as ak
                import threading
                from concurrent.futures import ThreadPoolExecutor

                lock = threading.Lock()
                completed_count = 0
                t0 = time.time()

                def _fetch_single_fund(code: str):
                    try:
                        df = ak.fund_open_fund_daily_em(
                            fund=code,
                            start_date=start_date.replace("-", ""),
                        )
                        if df is not None and not df.empty:
                            df_clean = pd.DataFrame()
                            for col in df.columns:
                                if "日期" in col or "date" in col.lower():
                                    df_clean["date"] = pd.to_datetime(df[col])
                                elif "累计" in col:
                                    continue  # 跳过累计净值
                                elif "净值" in col or "nav" in col.lower():
                                    df_clean["nav"] = pd.to_numeric(df[col], errors="coerce")

                            if "date" in df_clean.columns and "nav" in df_clean.columns:
                                df_clean = df_clean.dropna().sort_values("date").reset_index(drop=True)
                                if len(df_clean) > 0:
                                    return code, df_clean["nav"].tolist(), df_clean
                    except Exception:
                        pass
                    return None

                def _worker(code: str):
                    nonlocal completed_count
                    res = _fetch_single_fund(code)
                    with lock:
                        completed_count += 1
                        if res is not None:
                            c, nav_list, df_clean = res
                            nav_data[c] = nav_list
                            try:
                                SmartCacheManager.save_nav_cache(c, df_clean)
                            except Exception:
                                pass
                        if progress_callback:
                            elapsed = max(time.time() - t0, 0.1)
                            pct = int(completed_count / total_to_fetch * 100)
                            rate = completed_count / elapsed
                            remaining_sec = max(0, int((total_to_fetch - completed_count) / rate)) if rate > 0 else 0
                            msg = f"已完成 {completed_count} / {total_to_fetch} 只 ({pct}%) ｜ 已耗时 {elapsed:.1f}s ｜ 预计剩余 ~{remaining_sec}s"
                            try:
                                progress_callback(completed_count, total_to_fetch, msg)
                            except Exception:
                                pass

                with ThreadPoolExecutor(max_workers=12) as executor:
                    futures = [executor.submit(_worker, code) for code in to_fetch]
                    for f in futures:
                        try:
                            f.result()
                        except Exception:
                            pass

            except ImportError:
                warnings.warn("akshare 未安装，无法获取 NAV 数据")

        return nav_data

    # ─── Step 3: 获取候选池 NAV 对齐矩阵 ─────────────────────

    @classmethod
    def fetch_candidate_nav_matrix(
        cls,
        candidate_codes: List[str],
        start_date: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> pd.DataFrame:
        """
        Step 3: 获取候选池 NAV 对齐矩阵。

        1. 检查矩阵缓存
        2. 对每只候选基金获取 NAV（缓存+网络）
        3. 对齐到统一日期轴，前值填充
        4. 返回 DatetimeIndex × fund_code 的 DataFrame
        """
        if start_date is None:
            start_date = (
                datetime.date.today() - datetime.timedelta(days=int(5 * 365.25))
            ).isoformat()
        # 检查矩阵缓存
        cache_key = SmartCacheManager._matrix_cache_key(candidate_codes, start_date)
        cached = SmartCacheManager.get_nav_matrix_cache(cache_key)
        if cached is not None:
            if progress_callback:
                progress_callback(1, 1, f"从缓存加载 NAV 矩阵: {cached.shape}")
            return cached

        if progress_callback:
            progress_callback(0, len(candidate_codes), "获取候选基金 NAV 数据...")

        # 获取单只 NAV
        nav_dict = cls._fetch_nav_for_ranking(candidate_codes, start_date, progress_callback)

        if not nav_dict:
            return pd.DataFrame()

        # 构建对齐矩阵
        all_series = {}
        for code, navs in nav_dict.items():
            cached_df = SmartCacheManager.get_nav_cache(code)
            if cached_df is not None and "date" in cached_df.columns and "nav" in cached_df.columns:
                s = cached_df.set_index("date")["nav"]
                s.index = pd.to_datetime(s.index)
                mask = s.index >= pd.Timestamp(start_date)
                all_series[code] = s[mask]

        if not all_series:
            return pd.DataFrame()

        matrix = pd.DataFrame(all_series)
        matrix.index = pd.to_datetime(matrix.index)
        matrix = matrix.sort_index()

        # 前值填充
        matrix = matrix.ffill()

        # 保存缓存
        SmartCacheManager.save_nav_matrix_cache(cache_key, matrix)

        if progress_callback:
            progress_callback(
                len(candidate_codes), len(candidate_codes),
                f"NAV 矩阵构建完成: {matrix.shape[0]} 天 × {matrix.shape[1]} 只基金"
            )

        return matrix

    # ─── 便利方法：完整流水线 ──────────────────────────────────

    @classmethod
    def run_full_pipeline(
        cls,
        as_of_date: Optional[datetime.date] = None,
        min_aum_billion: float = 2.0,
        min_years: float = 3.0,
        top_n_per_bucket: int = 80,
        force_rebuild: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        一键运行完整筛选流水线。

        Returns
        -------
        (candidate_pool_df, nav_matrix_df)
        """
        # Step 1
        pool = cls.build_candidate_pool(
            as_of_date=as_of_date,
            min_aum_billion=min_aum_billion,
            min_years=min_years,
            force_rebuild=force_rebuild,
            progress_callback=progress_callback,
        )

        # Step 2
        ranked = cls.rank_and_select_top_n(
            pool,
            top_n_per_bucket=top_n_per_bucket,
            progress_callback=progress_callback,
        )

        # Step 3
        nav_matrix = cls.fetch_candidate_nav_matrix(
            ranked["fund_code"].tolist(),
            progress_callback=progress_callback,
        )

        return ranked, nav_matrix

    # ─── 漏斗统计（替代原有硬编码文案）─────────────────────────

    @classmethod
    def get_funnel_stats(cls, candidate_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        返回真实的漏斗统计数据（替代原有 get_fund_selection_funnel_stats 的硬编码文案）
        """
        total = 28177
        if cls.CATALOG_PATH.exists():
            try:
                cat = pd.read_parquet(cls.CATALOG_PATH)
                total = len(cat)
            except Exception:
                pass

        pool_count = 0
        ranked_count = 0
        if candidate_df is not None:
            ranked_count = len(candidate_df)

        cached_pool = SmartCacheManager.get_candidate_pool()
        if cached_pool is not None:
            pool_count = len(cached_pool)

        return {
            "total_market_funds": total,
            "pre_screened": pool_count,
            "ranked_candidates": ranked_count,
            "funnel_text": (
                f"全市场 {total:,} 只基金 → "
                f"规模>2亿·成立>3年预筛 {pool_count:,} 只 → "
                f"分桶综合评分 Top N 精选 {ranked_count} 只候选"
            ),
        }
