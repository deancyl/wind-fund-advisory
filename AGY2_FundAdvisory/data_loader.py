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


class DataLoader:
    """
    全收益标准化对齐数据加载器与交易算子引擎
    """

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
                'H00922': 'sh000015',
                'H30269': 'sh000015',
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
                url_sina = "https://hq.sinajs.cn/list=sh000300,sh000905,sh000852,sh000015,sh511010,sh000688,sh518880,gb_inx,fx_susdcny,sh513500"
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

                for s_code in ["sh000300", "sh000905", "sh000852", "sh000015", "sh511010", "sh000688"]:
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
                            s_class = DataLoader.SHARE_CLASS_MAP.get(a, 'C' if str(a).endswith('C') else 'A')
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
