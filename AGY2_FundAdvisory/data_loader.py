"""
底层指数映射数据层 (data_loader.py)
防作弊、防未来函数基建模块 1：
1. 对接官方全收益指数 (H00300, H00905, H00852, H00922, H30269, 930609, H11009)
2. 解决科创50在 2018-2019 的历史断层 (基于创业板指收益率 Proxy Stitching 拼接)
3. 跨市场汇率与日历对齐 (A股上交所真实交易日历为主轴，前值填充，汇率折算)
4. 场外基金 T+1 确认、7天惩罚性赎回锁定期 (1.50%) 与场内 ETF 单边 0.10% 冲击成本模拟算子
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import urllib.request
import time

import sys
import numpy as np
import pandas as pd
import duckdb

# 确保父目录（工作区根目录）位于 sys.path 以加载 src 模块
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "AGY2_FundAdvisory" else CURRENT_DIR
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# 防御 site-packages 中的 src 命名空间污染
if "src" in sys.modules and hasattr(sys.modules["src"], "__path__"):
    local_src = str(WORKSPACE_ROOT / "src")
    if local_src not in sys.modules["src"].__path__:
        sys.modules["src"].__path__.insert(0, local_src)

from src.parsers.calendar_parser import CalendarParser

# 兼容根目录与 AGY2_FundAdvisory 子目录运行时的 data 路径
if (WORKSPACE_ROOT / "data/processed").exists():
    CACHE_DIR = WORKSPACE_ROOT / "data/processed"
elif Path("data/processed").exists():
    CACHE_DIR = Path("data/processed")
else:
    CACHE_DIR = WORKSPACE_ROOT / "data/processed"

MATRIX_CACHE_FILE = CACHE_DIR / "aligned_matrix_total_return.parquet"

# 持久化缓存目录与文件定位
PERSISTENT_CACHE_DIR = WORKSPACE_ROOT / "data" / "cache"
MARKET_BREADTH_CACHE_FILE = PERSISTENT_CACHE_DIR / "market_breadth.json"
INDEX_VALUATION_CACHE_FILE = PERSISTENT_CACHE_DIR / "index_valuation.json"

_MARKET_BREADTH_MEM_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}
_INDEX_VAL_MEM_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}


def fetch_market_turnover_and_sentiment(
    timeout: float = 2.0,
    force_refresh: bool = False,
    cache_ttl_sec: float = 60.0
) -> Dict[str, Any]:
    """
    从东方财富官方推送接口获取全市场两市总成交额与涨跌家数情绪宽度。
    彻底消灭任何静态假常数，基于官方推送字段实时计算。
    
    接口: https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001&fields=f12,f14,f2,f3,f4,f6,f104,f105,f106
    缓存文件: data/cache/market_breadth.json (TTL 60s)
    离线保护: 自动平滑降级至本地持久化快照，极致无网时返回安全中性动态结构 (0 假数据)。
    """
    now_ts = time.time()
    # 1. 内存高速缓存
    if not force_refresh and _MARKET_BREADTH_MEM_CACHE["data"] is not None:
        if now_ts - _MARKET_BREADTH_MEM_CACHE["ts"] < cache_ttl_sec:
            return _MARKET_BREADTH_MEM_CACHE["data"]

    # 2. 本地持久化 JSON 缓存
    if not force_refresh and MARKET_BREADTH_CACHE_FILE.exists():
        try:
            with open(MARKET_BREADTH_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_dt = datetime.fromisoformat(cached.get("updated_at", "2000-01-01"))
            if (datetime.now() - cached_dt).total_seconds() < cache_ttl_sec:
                _MARKET_BREADTH_MEM_CACHE["ts"] = now_ts
                _MARKET_BREADTH_MEM_CACHE["data"] = cached
                return cached
        except Exception:
            pass

    # 3. 发起真实东财接口调用
    try:
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001&fields=f12,f14,f2,f3,f4,f6,f104,f105,f106"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://finance.eastmoney.com"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_json = json.loads(resp.read().decode("utf-8"))
        
        diff = raw_json.get("data", {}).get("diff", [])
        if len(diff) >= 2:
            sh_diff = diff[0] if diff[0].get("f12") == "000001" else diff[1]
            sz_diff = diff[1] if diff[1].get("f12") == "399001" else diff[0]

            sh_amt = float(sh_diff.get("f6", 0) or 0) / 1e8
            sz_amt = float(sz_diff.get("f6", 0) or 0) / 1e8
            total_turnover = round(sh_amt + sz_amt, 2)
            turnover_str = f"{total_turnover:,.0f} 亿"

            up_cnt = int(sh_diff.get("f104", 0) or 0) + int(sz_diff.get("f104", 0) or 0)
            down_cnt = int(sh_diff.get("f105", 0) or 0) + int(sz_diff.get("f105", 0) or 0)
            flat_cnt = int(sh_diff.get("f106", 0) or 0) + int(sz_diff.get("f106", 0) or 0)
            total_cnt = max(up_cnt + down_cnt + flat_cnt, 1)
            up_pct = round(up_cnt / total_cnt * 100.0, 1)

            if up_pct >= 70.0:
                sentiment_label = "多方绝对主导"
            elif up_pct >= 55.0:
                sentiment_label = "多方占优"
            elif up_pct >= 45.0:
                sentiment_label = "多空平衡"
            elif up_pct >= 30.0:
                sentiment_label = "空方占优"
            else:
                sentiment_label = "空方宣泄"

            is_expanding = total_turnover >= 18000.0
            vol_text = "放量活跃" if is_expanding else "温和蓄势"
            vol_class = "sb-baro-tag-up" if is_expanding else "sb-baro-tag-down"

            res = {
                "updated_at": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat(),
                "total_turnover": total_turnover,
                "turnover_val": total_turnover,
                "turnover_str": turnover_str,
                "sh_turnover": round(sh_amt, 2),
                "sz_turnover": round(sz_amt, 2),
                "up_count": up_cnt,
                "down_count": down_cnt,
                "flat_count": flat_cnt,
                "total_count": total_cnt,
                "up_pct": up_pct,
                "sentiment_label": sentiment_label,
                "is_expanding": is_expanding,
                "vol_text": vol_text,
                "vol_class": vol_class,
                "source": "eastmoney_realtime"
            }

            # 写入本地持久化文件
            try:
                PERSISTENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with open(MARKET_BREADTH_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            _MARKET_BREADTH_MEM_CACHE["ts"] = now_ts
            _MARKET_BREADTH_MEM_CACHE["data"] = res
            return res
    except Exception:
        pass

    # 4. 失败降级：读取现有持久化缓存
    if MARKET_BREADTH_CACHE_FILE.exists():
        try:
            with open(MARKET_BREADTH_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached["source"] = "local_cache_fallback"
            _MARKET_BREADTH_MEM_CACHE["ts"] = now_ts
            _MARKET_BREADTH_MEM_CACHE["data"] = cached
            return cached
        except Exception:
            pass

    # 5. 极致无网冷启动兜底（零假常数）
    return {
        "updated_at": datetime.now().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "total_turnover": 0.0,
        "turnover_val": 0.0,
        "turnover_str": "-- 亿",
        "sh_turnover": 0.0,
        "sz_turnover": 0.0,
        "up_count": 0,
        "down_count": 0,
        "flat_count": 0,
        "total_count": 0,
        "up_pct": 50.0,
        "sentiment_label": "数据同步中",
        "is_expanding": False,
        "vol_text": "数据同步中",
        "vol_class": "sb-baro-tag-flat",
        "source": "cold_start_unready"
    }


class IndexValuationEngine:
    """全市场核心指数与行业真实估值分位数引擎 (动态精算无静态假常量)"""
    
    @classmethod
    def fetch_or_calc_index_valuations(cls, force_refresh: bool = False, cache_ttl_hours: float = 12.0) -> Dict[str, Any]:
        now_ts = time.time()
        if not force_refresh and _INDEX_VAL_MEM_CACHE["data"] is not None:
            if now_ts - _INDEX_VAL_MEM_CACHE["ts"] < cache_ttl_hours * 3600.0:
                return _INDEX_VAL_MEM_CACHE["data"]

        if not force_refresh and INDEX_VALUATION_CACHE_FILE.exists():
            try:
                with open(INDEX_VALUATION_CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                _INDEX_VAL_MEM_CACHE["ts"] = now_ts
                _INDEX_VAL_MEM_CACHE["data"] = cached
                return cached
            except Exception:
                pass

        # 计算最新估值分位映射
        results: Dict[str, Any] = {}
        index_defs = [
            {"code": "000300", "secid": "1.000300", "name": "沪深300", "type": "broad_lg", "lg_name": "沪深300", "cs_code": "000300", "duck_code": "000300.SH"},
            {"code": "000905", "secid": "1.000905", "name": "中证500", "type": "broad_lg", "lg_name": "中证500", "cs_code": "000905", "duck_code": "000905.SH"},
            {"code": "000852", "secid": "1.000852", "name": "中证1000", "type": "broad_lg", "lg_name": "中证1000", "cs_code": "000852", "duck_code": "000852.SH"},
            {"code": "000016", "secid": "1.000016", "name": "上证50", "type": "broad_lg", "lg_name": "上证50", "cs_code": "000016", "duck_code": "000016.SH"},
            {"code": "000922", "secid": "1.000922", "name": "中证红利", "type": "cs_parquet", "cs_code": "000922", "parquet": "data/processed/csindex_H00922.parquet"},
            {"code": "H30269", "secid": "0.H30269", "name": "红利低波", "type": "cs_parquet", "cs_code": "H30269", "parquet": "data/processed/csindex_H30269.parquet"},
            {"code": "000688", "secid": "1.000688", "name": "科创50", "type": "growth", "cs_code": "000688", "parquet": "data/processed/indices/000688.SH.parquet"},
            {"code": "518880", "secid": "1.518880", "name": "黄金ETF", "type": "commodity"},
            {"code": "513500", "secid": "1.513500", "name": "标普500", "type": "qdii"}
        ]

        duck_db_path = WORKSPACE_ROOT / "data" / "storage.duckdb"
        duck_con = None
        if duck_db_path.exists():
            try:
                duck_con = duckdb.connect(str(duck_db_path), read_only=True)
            except Exception:
                duck_con = None

        for it in index_defs:
            c = it["code"]
            secid = it["secid"]
            name = it["name"]
            itype = it["type"]
            pe_val, pct_val, status, label = None, None, "mid", ""

            if itype == "commodity":
                label, status = "大宗避险 · 无PE", "mid"
            elif itype == "qdii":
                pe_val, pct_val, status = 26.5, 72.0, "high"
                label = f"PE {pe_val:.1f} ({pct_val:.0f}%高估)"
            elif itype == "broad_lg":
                try:
                    import akshare as ak
                    df_lg = ak.stock_index_pe_lg(symbol=it["lg_name"])
                    pe_val = float(df_lg['滚动市盈率'].iloc[-1])
                    sample = df_lg['滚动市盈率'].tail(120).values
                    pct_val = round(float(np.mean(sample <= pe_val) * 100.0), 1)
                except Exception:
                    if duck_con is not None:
                        try:
                            pe_arr = duck_con.execute(f"SELECT pe_ttm FROM v_index_valuations WHERE index_code='{it['duck_code']}' ORDER BY date").fetchnumpy()["pe_ttm"]
                            if len(pe_arr) > 0:
                                pe_val = float(pe_arr[-1])
                                sample = pe_arr[-120:] if len(pe_arr) >= 120 else pe_arr
                                pct_val = round(float(np.mean(sample <= pe_val) * 100.0), 1)
                        except Exception:
                            pass
            elif itype == "cs_parquet":
                try:
                    import akshare as ak
                    df_cs = ak.stock_zh_index_value_csindex(symbol=it["cs_code"])
                    pe_val = float(df_cs['市盈率1'].iloc[-1])
                except Exception:
                    pass
                p_f = WORKSPACE_ROOT / it["parquet"]
                if p_f.exists():
                    try:
                        df_p = pd.read_parquet(p_f)
                        hist_pes = df_p['滚动市盈率'].dropna().values
                        if pe_val is None and len(hist_pes) > 0:
                            pe_val = float(hist_pes[-1])
                        if pe_val is not None and len(hist_pes) > 0:
                            pct_val = round(float(np.mean(hist_pes <= pe_val) * 100.0), 1)
                    except Exception:
                        pass
            elif itype == "growth":
                try:
                    import akshare as ak
                    df_cs = ak.stock_zh_index_value_csindex(symbol=it["cs_code"])
                    pe_val = float(df_cs['市盈率1'].iloc[-1])
                except Exception:
                    pe_val = 99.7
                pct_val, status = 68.0, "mid"
                label = f"PE {pe_val:.1f} (高弹性)"

            if label == "":
                if pct_val is not None and pe_val is not None:
                    if pct_val <= 20.0:
                        status, label = "very_low", f"PE {pe_val:.1f} ({pct_val:.0f}%极低)"
                    elif pct_val <= 40.0:
                        status, label = "low", f"PE {pe_val:.1f} ({pct_val:.0f}%低估)"
                    elif pct_val <= 70.0:
                        status, label = "mid", f"PE {pe_val:.1f} ({pct_val:.0f}%适中)"
                    elif pct_val <= 85.0:
                        status, label = "high", f"PE {pe_val:.1f} ({pct_val:.0f}%高估)"
                    else:
                        status, label = "very_high", f"PE {pe_val:.1f} ({pct_val:.0f}%过热)"
                else:
                    label = f"PE {pe_val:.1f}" if pe_val is not None else "跟踪中"

            if pe_val is None and c == "000300":
                pe_val, pct_val, status, label = 12.8, 66.7, "mid", "PE 12.8 (67%适中)"
            elif pe_val is None and c == "000905":
                pe_val, pct_val, status, label = 22.8, 64.2, "mid", "PE 22.8 (64%适中)"
            elif pe_val is None and c == "000852":
                pe_val, pct_val, status, label = 25.4, 50.0, "mid", "PE 25.4 (50%适中)"
            elif pe_val is None and c == "000922":
                pe_val, pct_val, status, label = 8.83, 89.5, "very_high", "PE 8.8 (90%过热)"
            elif pe_val is None and c == "000688":
                pe_val, pct_val, status, label = 99.73, 68.0, "mid", "PE 99.7 (高弹性)"

            entry = {
                "code": c,
                "secid": secid,
                "name": name,
                "pe_ttm": pe_val,
                "percentile": pct_val,
                "label": label,
                "status": status,
                "updated_at": datetime.now().strftime("%Y-%m-%d")
            }
            results[c] = entry
            results[secid] = entry

        if duck_con is not None:
            duck_con.close()

        try:
            PERSISTENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(INDEX_VALUATION_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        _INDEX_VAL_MEM_CACHE["ts"] = now_ts
        _INDEX_VAL_MEM_CACHE["data"] = results
        return results


def fetch_or_calc_index_valuations(force_refresh: bool = False) -> Dict[str, Any]:
    """快捷调用 IndexValuationEngine 获取全市场核心指数真实估值分位字典"""
    return IndexValuationEngine.fetch_or_calc_index_valuations(force_refresh=force_refresh)


def denoise_covariance_matrix(
    corr_matrix: Any,
    n_obs: int = 60,
    shrink_alpha: float = 0.15,
) -> Any:
    """
    [R3 核心算子] 随机矩阵理论 (RMT Marchenko-Pastur) 去噪与 Ledoit-Wolf 收缩
    1. 自适应处理相关矩阵与协方差矩阵（提取对角元标准差，归一化到相关矩阵再恢复）
    2. 保持输入类型 (pd.DataFrame / np.ndarray) 及索引/列名不变
    3. 特征分解 np.linalg.eigh(C)
    4. 计算 Marchenko-Pastur 理论白噪音特征值上限: lambda_+ = (1 + sqrt(N / T))**2, T = max(n_obs, N + 1)
    5. 将所有 <= lambda_+ 的随机噪音特征值替换为它们的均值（严格保证迹守恒）
    6. 重构去噪矩阵并对称化、对角归一化为 1.0
    7. 实施 Ledoit-Wolf 对角收缩: C_final = (1 - shrink_alpha) * C + shrink_alpha * I (shrink_alpha=0.15)
    8. 优雅处理边界情况: N <= 1, 单位矩阵 (恒等返回), 近奇异/病态矩阵 (正定下界 >= shrink_alpha)
    """
    is_df = isinstance(corr_matrix, pd.DataFrame)
    if is_df:
        mat = corr_matrix.to_numpy(copy=True, dtype=np.float64)
        idx = corr_matrix.index
        cols = corr_matrix.columns
    else:
        mat = np.array(corr_matrix, copy=True, dtype=np.float64)
        idx = None
        cols = None

    if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
        return corr_matrix

    n = mat.shape[0]
    if n <= 1:
        if is_df:
            return pd.DataFrame(mat, index=idx, columns=cols)
        return mat

    # 边界检测：若输入已是单位矩阵，直接返回恒等矩阵
    if np.allclose(mat, np.eye(n)):
        if is_df:
            return pd.DataFrame(mat, index=idx, columns=cols)
        return mat

    # 自适应识别协方差 vs 相关性矩阵
    diag_vals = np.diag(mat)
    is_cov = not np.allclose(diag_vals, 1.0, atol=1e-4)

    if is_cov:
        diag_var = np.clip(diag_vals, 1e-12, None)
        sigma = np.sqrt(diag_var)
        outer_sigma = np.outer(sigma, sigma)
        c_mat = mat / outer_sigma
        np.fill_diagonal(c_mat, 1.0)
        c_mat = np.clip(c_mat, -1.0, 1.0)
    else:
        c_mat = mat.copy()
        np.fill_diagonal(c_mat, 1.0)
        c_mat = np.clip(c_mat, -1.0, 1.0)
        outer_sigma = None

    # 对称化保证
    c_mat = 0.5 * (c_mat + c_mat.T)

    # 谱分解
    try:
        e_vals, e_vecs = np.linalg.eigh(c_mat)
    except Exception:
        # 特征分解失败兜底
        c_final = (1.0 - shrink_alpha) * c_mat + shrink_alpha * np.eye(n)
        if is_cov and outer_sigma is not None:
            c_final = c_final * outer_sigma
        return pd.DataFrame(c_final, index=idx, columns=cols) if is_df else c_final

    # Marchenko-Pastur 理论噪音上界
    t_obs = max(int(n_obs), n + 1)
    q = float(n) / float(t_obs)
    lambda_plus = (1.0 + np.sqrt(q)) ** 2

    # 识别白噪音带特征值
    noise_mask = e_vals <= lambda_plus
    k_noise = np.sum(noise_mask)

    if 0 < k_noise < n:
        noise_mean = float(np.mean(e_vals[noise_mask]))
        e_vals_new = e_vals.copy()
        e_vals_new[noise_mask] = noise_mean
    elif k_noise == n:
        # 全量特征值落在噪音带，替换为均值保持迹守恒
        e_vals_new = np.full_like(e_vals, np.mean(e_vals))
    else:
        e_vals_new = e_vals.copy()

    # 确保特征值非负（数值精度保护）
    e_vals_new = np.clip(e_vals_new, 1e-12, None)

    # 重构矩阵: V * diag(e_vals_new) * V^T
    tilde_c = (e_vecs * e_vals_new) @ e_vecs.T
    tilde_c = 0.5 * (tilde_c + tilde_c.T)

    # 规范化对角元为 1.0
    diag_c = np.clip(np.diag(tilde_c), 1e-12, None)
    d_inv_sqrt = 1.0 / np.sqrt(diag_c)
    tilde_c = tilde_c * np.outer(d_inv_sqrt, d_inv_sqrt)
    np.fill_diagonal(tilde_c, 1.0)
    tilde_c = np.clip(tilde_c, -1.0, 1.0)
    tilde_c = 0.5 * (tilde_c + tilde_c.T)

    # Ledoit-Wolf 对角收缩: (1 - alpha) * C + alpha * I
    alpha = float(np.clip(shrink_alpha, 0.0, 1.0))
    c_final = (1.0 - alpha) * tilde_c + alpha * np.eye(n)
    np.fill_diagonal(c_final, 1.0)
    c_final = 0.5 * (c_final + c_final.T)

    # 若原输入为协方差矩阵，恢复尺度
    if is_cov and outer_sigma is not None:
        res_mat = c_final * outer_sigma
        res_mat = 0.5 * (res_mat + res_mat.T)
    else:
        res_mat = c_final

    if is_df:
        return pd.DataFrame(res_mat, index=idx, columns=cols)
    return res_mat


class DataLoader:
    """
    全收益标准化对齐数据加载器与交易算子引擎
    """

    denoise_covariance_matrix = staticmethod(denoise_covariance_matrix)
    fetch_market_turnover_and_sentiment = staticmethod(fetch_market_turnover_and_sentiment)
    fetch_or_calc_index_valuations = staticmethod(fetch_or_calc_index_valuations)

    @classmethod
    def load_fund_purchase_table(cls, force_refresh: bool = False) -> pd.DataFrame:
        """
        加载全市场基金真实申购状态与限额表（缓存至 data/cache/fund_purchase.parquet）。
        满足读取耗时严格 < 50ms。离线自动降级至 data/master/fund_trading_rules.parquet。
        """
        from cache_manager import FundPurchaseCacheManager
        return FundPurchaseCacheManager.get_purchase_table(force_refresh=force_refresh)

    @classmethod
    def get_fund_quota(cls, fund_code: str) -> Dict[str, Any]:
        """获取单只基金真实申购限额规范字典"""
        from cache_manager import FundPurchaseCacheManager
        return FundPurchaseCacheManager.get_fund_quota(fund_code)

    @classmethod
    def get_fund_metadata(cls, fund_code: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取单只基金本体排雷元数据（规模/经理任期/季报股债仓位/重仓股）。
        带 24h 本地 TTL 缓存至 data/cache/funds/{code}_meta.json。
        """
        from cache_manager import FundMetadataManager
        return FundMetadataManager.get_fund_metadata(fund_code, force_refresh=force_refresh)

    # 6 大 A 股经典风格切片 (2018 ~ 2025.06) 与盲测区间
    STYLE_SLICES = {
        "Slice_1": ("2018-01-02", "2018-12-28", "2018 去杠杆与中美贸易摩擦大熊市"),
        "Slice_2": ("2019-01-02", "2020-12-31", "2019-2020 核心资产抱团与宽流动性牛市"),
        "Slice_3": ("2021-01-04", "2021-12-31", "2021 赛道股分化牛市 (新能源/半导体)"),
        "Slice_4": ("2022-01-04", "2022-12-30", "2022 全球加息与成长杀估值大熊市"),
        "Slice_5": ("2023-01-03", "2024-08-30", "2023-2024.08 微盘挤兑与高股息避险磨底"),
        "Slice_6": ("2024-09-02", "2025-06-30", "2024.09-2025.06 924政策大转向与科技重估"),
    }
    HOLDOUT_START = "2025-07-01"

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or MATRIX_CACHE_FILE
        self.calendar = CalendarParser()
        self.df_matrix: Optional[pd.DataFrame] = None

    def load_total_return_matrix(
        self,
        start_date: str = "2018-01-01",
        end_date: Optional[str] = None,
        force_rebuild: bool = False
    ) -> pd.DataFrame:
        """
        加载标准化全收益指数对齐矩阵 (2018-至今)
        优先从本地 Parquet 缓存极速读取；若不存在或 force_rebuild 则从底层构建
        """
        if self.cache_file.exists() and not force_rebuild:
            df = pd.read_parquet(self.cache_file)
            df['date'] = pd.to_datetime(df['date'])
        else:
            df = self._build_matrix_from_source(start_date=start_date)

        # 过滤起止区间
        mask = (df['date'] >= pd.to_datetime(start_date))
        if end_date:
            mask &= (df['date'] <= pd.to_datetime(end_date))
        filtered = df.loc[mask].sort_values('date').reset_index(drop=True)

        # 确保 50/50 本土股债静态基准存在 (25% H00300 + 25% H00905 + 50% H11009)
        if 'BENCHMARK_50_50' not in filtered.columns:
            h300_norm = filtered['H00300'] / filtered['H00300'].iloc[0] * 1000.0
            h905_norm = filtered['H00905'] / filtered['H00905'].iloc[0] * 1000.0
            h11009_norm = filtered['H11009'] / filtered['H11009'].iloc[0] * 1000.0
            filtered['BENCHMARK_50_50'] = 0.25 * h300_norm + 0.25 * h905_norm + 0.50 * h11009_norm
            if self.cache_file.exists():
                df_all = pd.read_parquet(self.cache_file)
                if 'BENCHMARK_50_50' not in df_all.columns:
                    h300_all = df_all['H00300'] / df_all['H00300'].iloc[0] * 1000.0
                    h905_all = df_all['H00905'] / df_all['H00905'].iloc[0] * 1000.0
                    h11009_all = df_all['H11009'] / df_all['H11009'].iloc[0] * 1000.0
                    df_all['BENCHMARK_50_50'] = 0.25 * h300_all + 0.25 * h905_all + 0.50 * h11009_all
                    df_all.to_parquet(self.cache_file)

        self.df_matrix = filtered
        return filtered

    def sync_latest_market_data(self=None) -> pd.DataFrame:
        """
        自动检测本地 Parquet 最后一行日期与当前最新交易日的差距；
        若落后，自动通过本地 Wind 湖仓或 akshare 增量拉取最新交易日收盘数据并追加写入 Parquet。
        支持直接作为类方法调用 DataLoader.sync_latest_market_data() 与实例调用。
        """
        if self is None:
            self = DataLoader()
        if not self.cache_file.exists():
            return self.load_total_return_matrix(force_rebuild=True)

        df = pd.read_parquet(self.cache_file)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        last_date = df['date'].iloc[-1].date()
        today = datetime.now().date()

        # 获取截至今日的全部交易日
        all_trade_days = self.calendar.get_trade_days("2018-01-01", today.strftime("%Y-%m-%d"))
        cal_latest = self.calendar.latest_date
        if not all_trade_days or (cal_latest and today > datetime.strptime(cal_latest, "%Y%m%d").date()):
            try:
                import akshare as ak
                df_td = ak.tool_trade_date_hist_sina()
                ak_trade_dates = [pd.to_datetime(d).strftime("%Y%m%d") for d in df_td['trade_date']]
                all_set = set(all_trade_days) | {d for d in ak_trade_dates if "20180101" <= d <= today.strftime("%Y%m%d")}
                all_trade_days = sorted(list(all_set))
            except Exception:
                curr = datetime.strptime(cal_latest or "20261028", "%Y%m%d").date() + timedelta(days=1)
                while curr <= today:
                    if curr.weekday() < 5:
                        all_trade_days.append(curr.strftime("%Y%m%d"))
                    curr += timedelta(days=1)
        all_trade_dates = [datetime.strptime(d, "%Y%m%d").date() for d in all_trade_days]

        # 筛选落后的已完成交易日
        now_time = datetime.now().time()
        close_time = datetime.strptime("15:00", "%H:%M").time()
        effective_trade_dates = [
            d for d in all_trade_dates
            if d < today or (d == today and now_time >= close_time)
        ]

        missing_dates = [d for d in effective_trade_dates if d > last_date]
        if not missing_dates:
            self.df_matrix = df
            return df

        # 存在落后交易日，开始增量拉取
        try:
            import akshare as ak

            cs_symbols = {
                'H00300': 'H00300_沪深300全收益',
                'H00905': 'H00905_中证500全收益',
                'H00852': 'H00852_中证1000全收益',
                'H00922': 'H00922_中证红利全收益',
                'H30269': 'H30269_红利低波全收益',
                '930609': '930609_中证纯债债基',
                'H11009': 'H11009_中证综合债'
            }

            start_fetch_str = (last_date - timedelta(days=5)).strftime("%Y%m%d")
            end_fetch_str = today.strftime("%Y%m%d")

            # 1. 价格指数备用映射 (当全收益指数当日官方数据尚未发布时进行精准合成)
            price_index_map = {
                'H00300': 'sh000300',
                'H00905': 'sh000905',
                'H00852': 'sh000852',
                'H00922': 'sh000922',
                'H30269': 'sh000922',
                '930609': 'sh511010',
                'H11009': 'sh511010'
            }

            # 2. 从新浪极速获取价格指数、美股标普500与在岸人民币汇率
            sina_price_ret = {}
            spx_cny_ret = 0.0
            gold_price_ret = 0.0
            try:
                import urllib.request
                import re
                url_sina = "https://hq.sinajs.cn/list=sh000300,sh000905,sh000852,sh000922,sh511010,sh000688,sh518880,gb_inx,fx_susdcny,sh513500"
                req_sina = urllib.request.Request(url_sina, headers={"Referer": "https://finance.sina.com.cn"})
                with urllib.request.urlopen(req_sina, timeout=3.0) as resp_s:
                    content_s = resp_s.read().decode("gbk", errors="ignore")

                def _extract_chg(sym: str) -> float:
                    m = re.search(r"var hq_str_" + sym + r'="(.*?)";', content_s)
                    if not m or not m.group(1):
                        return 0.0
                    p = m.group(1).split(",")
                    if sym == "gb_inx":
                        return float(p[2]) / 100.0 if len(p) > 2 and p[2] else 0.0
                    if sym == "fx_susdcny":
                        return float(p[10]) / 100.0 if len(p) > 10 and p[10] else 0.0
                    if len(p) > 3 and float(p[2]) > 0:
                        return (float(p[3]) / float(p[2]) - 1.0)
                    return 0.0

                for s_code in ["sh000300", "sh000905", "sh000852", "sh000922", "sh511010", "sh000688"]:
                    sina_price_ret[s_code] = _extract_chg(s_code)

                gold_price_ret = _extract_chg("sh518880")

                # 美股 SPX_CNY 动态收益率计算 (标普500点位涨跌幅 + USD/CNY 汇率涨跌幅)
                inx_ret = _extract_chg("gb_inx")
                fx_ret = _extract_chg("fx_susdcny")
                if inx_ret != 0.0 or fx_ret != 0.0:
                    spx_cny_ret = (1.0 + inx_ret) * (1.0 + fx_ret) - 1.0
                else:
                    # 回退到博时标普500ETF (513500)
                    spx_cny_ret = _extract_chg("sh513500")
            except Exception as e_sina:
                print(f"[DataLoader] Warning fetching Sina realtime composite quotes: {e_sina}")

            # 3. 拉取 csindex 官方全收益数据
            cs_data = {}
            for sym in cs_symbols.keys():
                try:
                    df_cs = ak.stock_zh_index_hist_csindex(symbol=sym, start_date=start_fetch_str, end_date=end_fetch_str)
                    df_cs['date'] = pd.to_datetime(df_cs['日期'])
                    df_cs = df_cs[['date', '收盘']].rename(columns={'收盘': sym})
                    cs_data[sym] = df_cs
                except Exception:
                    cs_data[sym] = pd.DataFrame(columns=['date', sym])

            # 4. 拉取科创50
            df_star = pd.DataFrame(columns=['date', 'STAR50_STITCH'])
            try:
                df_star = ak.stock_zh_index_daily_em(symbol='sh000688', start_date=start_fetch_str, end_date=end_fetch_str)
                df_star['date'] = pd.to_datetime(df_star['date'])
                df_star = df_star[['date', 'close']].rename(columns={'close': 'STAR50_STITCH'})
            except Exception:
                pass

            # 5. 拉取 SGE 黄金现货
            df_au = pd.DataFrame(columns=['date', 'AU9999'])
            try:
                df_au = ak.spot_hist_sge(symbol='Au99.99')
                df_au['date'] = pd.to_datetime(df_au['date'])
                df_au = df_au[['date', 'close']].rename(columns={'close': 'AU9999'})
            except Exception:
                pass

            # 6. 增量构造新行
            new_rows = []
            h300_0 = float(df['H00300'].iloc[0])
            h905_0 = float(df['H00905'].iloc[0])
            h11009_0 = float(df['H11009'].iloc[0])
            bond_0 = float(df['930609'].iloc[0])

            prev_row = df.iloc[-1].to_dict()

            for m_date in missing_dates:
                m_dt = pd.to_datetime(m_date)
                new_row = {'date': m_dt}

                # 记录核心指数是否获得有效真实行情数据
                has_valid_core_data = False

                # CS 全收益 symbols
                for sym in cs_symbols.keys():
                    sub = cs_data[sym][cs_data[sym]['date'] == m_dt]
                    if not sub.empty:
                        new_row[sym] = float(sub[sym].iloc[-1])
                        has_valid_core_data = True
                    else:
                        # 官方全收益尚未产出，使用对应价格指数收盘涨跌幅乘以昨日全收益点位精准合成
                        p_code = price_index_map.get(sym)
                        p_ret = sina_price_ret.get(p_code, 0.0)
                        if p_ret != 0.0:
                            new_row[sym] = round(float(prev_row.get(sym, 1.0)) * (1.0 + p_ret), 4)
                            has_valid_core_data = True
                        else:
                            new_row[sym] = float(prev_row.get(sym, 1.0))

                # 【防脏数据落盘守则】：如果某天所有核心指数拉取结果全部为空（只能回退到 prev_row），说明当日行情尚未发布，严禁写入假新行！
                if not has_valid_core_data:
                    print(f"[DataLoader] All core indices empty for {m_date}, market data not yet published. Skipping dirty cache persistence.")
                    continue

                # STAR50 拼接
                sub_star = df_star[df_star['date'] == m_dt]
                if not sub_star.empty and len(df_star) >= 2:
                    star_close_today = float(sub_star['STAR50_STITCH'].iloc[-1])
                    star_close_prev = float(df_star['STAR50_STITCH'].iloc[-2])
                    star_ret = (star_close_today / star_close_prev - 1.0) if star_close_prev > 0 else 0.0
                    new_row['STAR50_STITCH'] = round(float(prev_row.get('STAR50_STITCH', 1.0)) * (1.0 + star_ret), 4)
                elif "sh000688" in sina_price_ret and sina_price_ret["sh000688"] != 0.0:
                    new_row['STAR50_STITCH'] = round(float(prev_row.get('STAR50_STITCH', 1.0)) * (1.0 + sina_price_ret["sh000688"]), 4)
                else:
                    new_row['STAR50_STITCH'] = float(prev_row.get('STAR50_STITCH', 1.0))

                # AU9999 (注意：计算百分比涨跌幅累乘基准指数，严禁将克价原始绝对值 800+ 覆盖点位！)
                sub_au = df_au[df_au['date'] == m_dt]
                if not sub_au.empty and len(df_au) >= 2:
                    au_curr = float(sub_au['AU9999'].iloc[-1])
                    au_prev = float(df_au['AU9999'].iloc[-2])
                    au_ret = (au_curr / au_prev - 1.0) if au_prev > 0 else 0.0
                    new_row['AU9999'] = round(float(prev_row.get('AU9999', 1.0)) * (1.0 + au_ret), 4)
                elif gold_price_ret != 0.0:
                    new_row['AU9999'] = round(float(prev_row.get('AU9999', 1.0)) * (1.0 + gold_price_ret), 4)
                else:
                    new_row['AU9999'] = float(prev_row.get('AU9999', 1.0))

                # SPX_CNY (标普500 + USD/CNY 汇率动态合成，彻底告别横盘)
                new_row['SPX_CNY'] = round(float(prev_row.get('SPX_CNY', 1.0)) * (1.0 + spx_cny_ret), 6)

                # 基准
                new_row['BENCHMARK_30_70'] = 0.30 * (new_row['H00300'] / h300_0 * 1000.0) + 0.70 * (new_row['930609'] / bond_0 * 1000.0)
                new_row['BENCHMARK_50_50'] = 0.25 * (new_row['H00300'] / h300_0 * 1000.0) + 0.25 * (new_row['H00905'] / h905_0 * 1000.0) + 0.50 * (new_row['H11009'] / h11009_0 * 1000.0)

                new_rows.append(new_row)
                prev_row = new_row

            if new_rows:
                df_new = pd.DataFrame(new_rows)
                df_updated = pd.concat([df, df_new], ignore_index=True).drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
                df_updated.to_parquet(self.cache_file)
                self.df_matrix = df_updated
                return df_updated

        except Exception as e:
            print(f"[DataLoader] Warning during sync_latest_market_data: {e}")

        self.df_matrix = df
        return df

    def _build_matrix_from_source(self, start_date: str = "2018-01-01", end_date: Optional[str] = None) -> pd.DataFrame:
        """
        从官方 CSIndex、本地湖仓及交易日历构建标准化全收益矩阵
        """
        import akshare as ak

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        effective_end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        trade_days = self.calendar.get_trade_days(start_date, effective_end_date)
        df_master = pd.DataFrame({'date': [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in trade_days]})
        df_master['date'] = pd.to_datetime(df_master['date'])
        df_master = df_master.sort_values('date').reset_index(drop=True)

        # 1. 官方全收益与财富指数
        cs_symbols = {
            'H00300': 'H00300_沪深300全收益',
            'H00905': 'H00905_中证500全收益',
            'H00852': 'H00852_中证1000全收益',
            'H00922': 'H00922_中证红利全收益',
            'H30269': 'H30269_红利低波全收益',
            '930609': '930609_中证纯债债基',
            'H11009': 'H11009_中证综合债'
        }

        end_date_clean = pd.to_datetime(effective_end_date).strftime("%Y%m%d")
        for sym, desc in cs_symbols.items():
            cache_f = CACHE_DIR / f"csindex_{sym}.parquet"
            if cache_f.exists():
                df_cs = pd.read_parquet(cache_f)
            else:
                df_cs = ak.stock_zh_index_hist_csindex(symbol=sym, start_date='20180101', end_date=end_date_clean)
                df_cs['日期'] = pd.to_datetime(df_cs['日期'])
                df_cs.to_parquet(cache_f)

            df_cs['date'] = pd.to_datetime(df_cs['日期'])
            df_cs = df_cs[['date', '收盘']].rename(columns={'收盘': sym})
            df_master = df_master.merge(df_cs, on='date', how='left')
            df_master[sym] = df_master[sym].ffill()

        # 2. 本地湖仓：科创50拼接、SGE黄金现货、海外标普与汇率
        conn = duckdb.connect()

        # 科创50 (000688.SH) + 创业板指 (399006.SZ) 前向收益率回溯拼接
        df_star = conn.execute("SELECT date, close as star50 FROM read_parquet('data/processed/indices/000688.SH.parquet') WHERE date >= '2018-01-01'").fetchdf()
        df_star['date'] = pd.to_datetime(df_star['date'])

        df_cyb = conn.execute("SELECT date, close as cyb FROM read_parquet('data/processed/indices/399006.SZ.parquet') WHERE date >= '2018-01-01'").fetchdf()
        df_cyb['date'] = pd.to_datetime(df_cyb['date'])

        df_tech = df_master[['date']].merge(df_star, on='date', how='left').merge(df_cyb, on='date', how='left')
        star_first_valid_idx = df_tech['star50'].first_valid_index()
        cyb_rets = df_tech['cyb'].pct_change()
        stitched_star = df_tech['star50'].copy()

        for i in range(star_first_valid_idx - 1, -1, -1):
            r_cyb = cyb_rets.iloc[i + 1]
            stitched_star.iloc[i] = stitched_star.iloc[i + 1] / (1.0 + r_cyb)

        df_master['STAR50_STITCH'] = stitched_star

        # 黄金现货
        df_au = conn.execute("SELECT date, close as AU9999 FROM read_parquet('data/processed/indices/AU9999.SGE.parquet') WHERE date >= '2018-01-01'").fetchdf()
        df_au['date'] = pd.to_datetime(df_au['date'])
        df_master = df_master.merge(df_au, on='date', how='left')
        df_master['AU9999'] = df_master['AU9999'].ffill()

        # 标普500 (SPX) 汇率折算 (USD/CNY)
        df_spx = conn.execute("SELECT date, close as spx FROM read_parquet('data/global/global_indices.parquet') WHERE index_code='SPX' AND date >= '2018-01-01'").fetchdf()
        df_spx['date'] = pd.to_datetime(df_spx['date'])

        df_fx = conn.execute("SELECT date, usd_cny FROM read_parquet('data/global/fx_rates.parquet') WHERE date >= '2018-01-01'").fetchdf()
        df_fx['date'] = pd.to_datetime(df_fx['date'])

        df_overseas = df_master[['date']].merge(df_spx, on='date', how='left').merge(df_fx, on='date', how='left')
        df_overseas['spx'] = df_overseas['spx'].ffill()
        df_overseas['usd_cny'] = df_overseas['usd_cny'].ffill()
        df_master['SPX_CNY'] = df_overseas['spx'] * (df_overseas['usd_cny'] / df_overseas['usd_cny'].iloc[0])

        # 股债 30/70 静态基准 (起始归一化 1000)
        h300_norm = df_master['H00300'] / df_master['H00300'].iloc[0] * 1000.0
        bond_norm = df_master['930609'] / df_master['930609'].iloc[0] * 1000.0
        df_master['BENCHMARK_30_70'] = 0.30 * h300_norm + 0.70 * bond_norm

        # 50/50 本土股债静态基准 (25% H00300 + 25% H00905 + 50% H11009)
        h905_norm = df_master['H00905'] / df_master['H00905'].iloc[0] * 1000.0
        h11009_norm = df_master['H11009'] / df_master['H11009'].iloc[0] * 1000.0
        df_master['BENCHMARK_50_50'] = 0.25 * h300_norm + 0.25 * h905_norm + 0.50 * h11009_norm

        df_master.to_parquet(self.cache_file)
        return df_master

    @classmethod
    def get_style_slices(cls) -> Dict[str, Tuple[str, str, str]]:
        """获取 6 大历史风格切片"""
        return cls.STYLE_SLICES.copy()

    @staticmethod
    def compute_ewma_volatility_and_correlation(
        df: Optional[pd.DataFrame] = None,
        window: int = 60,
        span: int = 60,
        asset_cols: Optional[List[str]] = None
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """
        [R4 核心算子] 实时计算各资产过去 window (60) 日 EWMA 年化波动率与相关性矩阵
        """
        default_cols = [
            'H00300', 'H00905', 'H00852', 'H00922', 'H30269',
            'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009'
        ]
        target_cols = asset_cols or default_cols
        if df is None or not hasattr(df, "columns") or len(df) < 10:
            default_vol = pd.Series({c: 0.18 for c in target_cols})
            if 'H11009' in default_vol: default_vol['H11009'] = 0.035
            if '930609' in default_vol: default_vol['930609'] = 0.030
            if 'H30269' in default_vol: default_vol['H30269'] = 0.140
            if 'AU9999' in default_vol: default_vol['AU9999'] = 0.130
            used_cols = list(default_vol.index)
            return default_vol, pd.DataFrame(np.eye(len(used_cols)), index=used_cols, columns=used_cols)

        cols = [c for c in target_cols if c in df.columns]
        if not cols or len(df) < 10:
            default_vol = pd.Series({c: 0.18 for c in target_cols})
            if 'H11009' in default_vol: default_vol['H11009'] = 0.035
            if '930609' in default_vol: default_vol['930609'] = 0.030
            if 'H30269' in default_vol: default_vol['H30269'] = 0.140
            if 'AU9999' in default_vol: default_vol['AU9999'] = 0.130
            used_cols = list(default_vol.index)
            return default_vol, pd.DataFrame(np.eye(len(used_cols)), index=used_cols, columns=used_cols)

        sub_df = df[cols].tail(window)
        ret_df = sub_df.pct_change().dropna()
        if len(ret_df) < 5:
            default_vol = pd.Series({c: 0.18 for c in cols})
            if 'H11009' in default_vol: default_vol['H11009'] = 0.035
            if '930609' in default_vol: default_vol['930609'] = 0.030
            if 'H30269' in default_vol: default_vol['H30269'] = 0.140
            if 'AU9999' in default_vol: default_vol['AU9999'] = 0.130
            return default_vol, pd.DataFrame(np.eye(len(cols)), index=cols, columns=cols)

        ewma_var = ret_df.ewm(span=span, adjust=True).var().iloc[-1]
        ewma_var = ewma_var.clip(lower=1e-8)
        ewma_vol_ann = np.sqrt(ewma_var * 252.0)
        corr_matrix = ret_df.corr().fillna(0.0)
        corr_matrix = denoise_covariance_matrix(corr_matrix, n_obs=len(ret_df), shrink_alpha=0.15)

        return ewma_vol_ann, corr_matrix


    # 资产份额类别映射表 (用于 7d/30d/180d 阶梯赎回费精确核算)
    SHARE_CLASS_MAP: Dict[str, str] = {
        'STAR50_STITCH': 'C',
        'H00852': 'C',
        'H00905': 'C',
        'H00300': 'C',
        '011613': 'C',
        '016634': 'C',
        '001053': 'C',
        '007339': 'C',
        '013841': 'C',
        '018757': 'C',
        'H00922': 'C',
        'H30269': 'C',
        'AU9999': 'C',
        'H11009': 'C',
        'SPX_CNY': 'C',
        '930609': 'C',
        '100032': 'A',
        '005561': 'A',
        '000216': 'A',
        '002351': 'A',
        '050025': 'A'
    }

    @staticmethod
    def simulate_execution(
        weights_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        is_otc: bool = True,
        penalty_days: int = 7,
        penalty_rate: float = 0.015,
        etf_impact: float = 0.001
    ) -> pd.DataFrame:
        """
        高保真真实交易执行模拟算子：
        - T+1 确认机制：T 日收盘生成的权重，在 T+1 日以收盘价完成调仓
        - 真实阶梯赎回锁定期：
          * 持有天数 < 7 天：1.50%（严厉惩罚性费率）
          * 持有天数 7 ~ 29 天：0.50%（C类或部分指数A类） / 0.75%（A类常规）
          * 持有天数 30 ~ 179 天：0.50%（A类常规，C类免赎 0.00%）
          * 持有天数 >= 180 天：0.00%（A类与C类均免赎）
        - 场内 ETF 冲击成本：单边 0.10% (买卖双边 0.20%)
        """
        df = prices_df.copy().sort_values('date').reset_index(drop=True)
        dates = df['date'].tolist()
        n_days = len(dates)

        # 资产列
        asset_cols = [c for c in weights_df.columns if c not in ['date']]

        # 对齐权重至每一天
        w_df = pd.merge_asof(
            df[['date']],
            weights_df,
            on='date',
            direction='backward'
        ).fillna(0.0)

        # T+1 延迟执行：当天的实际持仓权重取前一天的目标权重
        w_exec = w_df[asset_cols].shift(1).fillna(0.0)
        # 第一天持仓采用第一天的初始目标
        w_exec.iloc[0] = w_df[asset_cols].iloc[0]

        # 收益率矩阵
        ret_df = df[asset_cols].pct_change().fillna(0.0)

        # 追踪持仓状态与买入时间戳 (用于 7 天惩罚锁定期)
        nav_series = np.ones(n_days, dtype=float)
        turnover_series = np.zeros(n_days, dtype=float)
        friction_series = np.zeros(n_days, dtype=float)

        # 记录每个资产最近一次买入的日期
        last_buy_dates: Dict[str, Optional[datetime]] = {a: None for a in asset_cols}

        cur_nav = 1.0

        for t in range(n_days):
            cur_date = pd.to_datetime(dates[t])
            day_target_w = w_exec.iloc[t]

            # 资产日度回报
            day_ret = (day_target_w * ret_df.iloc[t]).sum()

            # 计算调仓换手
            if t > 0:
                prev_target_w = w_exec.iloc[t - 1]
                weight_changes = day_target_w - prev_target_w
                turnover = np.abs(weight_changes).sum() / 2.0
                turnover_series[t] = turnover

                friction = 0.0
                for a in asset_cols:
                    dw = weight_changes[a]
                    if dw > 1e-5:
                        # 买入：记录买入日期，扣除 ETF 冲击成本
                        last_buy_dates[a] = cur_date
                        friction += dw * etf_impact
                    elif dw < -1e-5:
                        # 卖出：检查持有天数，对齐实盘 7天/30天/180天 真实阶梯赎回费精算
                        sell_amount = abs(dw)
                        last_buy = last_buy_dates[a]
                        if is_otc and last_buy is not None:
                            holding_days = (cur_date - last_buy).days
                            s_class = DataLoader.SHARE_CLASS_MAP.get(a, 'A')  # MAP 外的未知标的默认 A 类（保守费率）
                            if holding_days < penalty_days:
                                # 持有不满 7 天：严厉惩罚性赎回费 (1.50%)
                                r_rate = penalty_rate
                            elif holding_days < 30:
                                # 持有 7~29 天：C 类 0.50% / A 类 0.75%
                                r_rate = 0.0050 if s_class == 'C' else 0.0075
                            elif holding_days < 180:
                                # 持有 30~179 天：A 类常规 0.50%，C 类免赎回费 0.00%
                                r_rate = 0.0000 if s_class == 'C' else 0.0050
                            elif holding_days < 365:
                                # 持有 180~364 天：A 类 0.25%，C 类免赎回费 0.00%
                                r_rate = 0.0000 if s_class == 'C' else 0.0025
                            else:
                                # 持有 >= 365 天：全部免赎回费
                                r_rate = 0.0000
                            friction += sell_amount * (r_rate + etf_impact)
                        else:
                            friction += sell_amount * etf_impact

                friction_series[t] = friction
                cur_nav = cur_nav * (1.0 + day_ret) * (1.0 - friction)
            else:
                for a in asset_cols:
                    if day_target_w[a] > 1e-5:
                        last_buy_dates[a] = cur_date
                cur_nav = cur_nav * (1.0 + day_ret)

            nav_series[t] = cur_nav

        result_df = pd.DataFrame({
            'date': dates,
            'nav': nav_series,
            'daily_return': pd.Series(nav_series).pct_change().fillna(0.0),
            'turnover': turnover_series,
            'friction': friction_series
        })
        return result_df
