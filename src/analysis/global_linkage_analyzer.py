"""
全球市场联动与宏观传导分析引擎 (GlobalLinkageAnalyzer)：
1. 测算 A 股核心宽基 (沪深300、创业板指) 与全球核心市场 (标普500、纳斯达克、恒生指数) 的滚动相关性与时滞传导。
2. 构建三大外生宏观修正因子：
   - fx_pressure_factor: 人民币汇率波动与在离岸汇差压力修正项 (-10 ~ +10)
   - us_yield_spread_factor: 中美基准国债利差倒挂修正项 (-10 ~ +10)
   - risk_sentiment_factor: 全球避险情绪 (黄金/原油/美元指数) 修正项 (-10 ~ +10)
3. 沉淀分析指标库至 data/mart/global_linkage_metrics.parquet，供估值温度计与资产配置罗盘调用。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from ..storage.lakehouse import LakehouseManager


@dataclass
class GlobalLinkageMetrics:
    """全球联动与宏观传导指标快照"""
    eval_date: str
    # 滚动相关性 (30日 / 90日)
    corr_hs300_spx_30d: float
    corr_hs300_spx_90d: float
    corr_hs300_hsi_30d: float
    corr_hs300_hsi_90d: float
    corr_chinext_nasdaq_30d: float
    corr_chinext_nasdaq_90d: float
    # 宏观传导状态
    usd_cny_latest: float
    usd_cnh_latest: float
    cnh_cny_spread: float       # 在离岸价差
    usd_cny_20d_pct: float      # 人民币近20日涨跌幅 %
    cn_us_spread_10y: float     # 中美10Y国债利差 (%)
    gold_close: float           # 国际黄金最新价
    gold_20d_pct: float         # 黄金近20日涨幅 %
    crude_oil_close: float      # WTI原油最新价
    dxy_close: float            # 美元指数最新价
    # 三大外生调节因子
    fx_pressure_factor: float       # 汇率压力调节项 (-10 ~ +10)
    us_yield_spread_factor: float   # 中美利差倒挂调节项 (-10 ~ +10)
    risk_sentiment_factor: float    # 全球避险调节项 (-10 ~ +10)
    total_external_adjustment: float # 外生合计调节分 (-15 ~ +15)
    macro_regime_desc: str          # 宏观环境定性研判


class GlobalLinkageAnalyzer:
    """全球宏观资产联动与风险外生传导分析器"""

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.global_dir = self.lakehouse.data_dir / "global"
        self.macro_dir = self.lakehouse.data_dir / "macro"
        self.mart_dir = self.lakehouse.mart_dir
        self.output_parquet = self.mart_dir / "global_linkage_metrics.parquet"

    def analyze(self) -> Optional[GlobalLinkageMetrics]:
        """测算全量全球联动指标与外生调节因子"""
        indices_path = self.global_dir / "global_indices.parquet"
        fx_path = self.global_dir / "fx_rates.parquet"
        comm_path = self.global_dir / "commodities.parquet"
        rates_path = self.macro_dir / "bond_zh_us_rate.parquet"

        if not fx_path.exists() or not rates_path.exists():
            return None

        # 1. 读取各维度数据
        df_fx = pd.read_parquet(fx_path).sort_values("date").reset_index(drop=True)
        df_rates = pd.read_parquet(rates_path).sort_values("date").reset_index(drop=True)
        df_global_idx = pd.read_parquet(indices_path) if indices_path.exists() else pd.DataFrame()
        df_comm = pd.read_parquet(comm_path) if comm_path.exists() else pd.DataFrame()

        # 读取 A 股核心指数 (沪深300 与 创业板指)
        df_hs300 = self.lakehouse.get_index_series("000300.SH")
        if df_hs300 is None:
            df_hs300 = self.lakehouse.get_index_series("000001.SH")
        df_chinext = self.lakehouse.get_index_series("399006.SZ")
        if df_chinext is None:
            df_chinext = df_hs300

        # 最新评估基准日期
        eval_date = df_fx.iloc[-1]["date"] if not df_fx.empty else datetime.now().strftime("%Y-%m-%d")

        # -------------------------------------------------------------
        # 2. 测算跨市场滚动相关性
        # -------------------------------------------------------------
        corr_hs300_spx_30d, corr_hs300_spx_90d = 0.25, 0.28
        corr_hs300_hsi_30d, corr_hs300_hsi_90d = 0.55, 0.58
        corr_chinext_nasdaq_30d, corr_chinext_nasdaq_90d = 0.35, 0.38

        if df_hs300 is not None and not df_global_idx.empty:
            df_a = df_hs300[["date", "daily_return"]].rename(columns={"daily_return": "ret_a"}).copy()
            df_a["date"] = pd.to_datetime(df_a["date"]).dt.strftime("%Y-%m-%d")

            # 标普500
            df_spx = df_global_idx[df_global_idx["index_code"] == "SPX"][["date", "daily_return"]].rename(columns={"daily_return": "ret_spx"})
            if not df_spx.empty:
                m_spx = pd.merge(df_a, df_spx, on="date", how="inner").sort_values("date")
                if len(m_spx) >= 30:
                    corr_hs300_spx_30d = round(float(m_spx["ret_a"].tail(30).corr(m_spx["ret_spx"].tail(30))), 2)
                if len(m_spx) >= 90:
                    corr_hs300_spx_90d = round(float(m_spx["ret_a"].tail(90).corr(m_spx["ret_spx"].tail(90))), 2)

            # 恒生指数
            df_hsi = df_global_idx[df_global_idx["index_code"] == "HSI"][["date", "daily_return"]].rename(columns={"daily_return": "ret_hsi"})
            if not df_hsi.empty:
                m_hsi = pd.merge(df_a, df_hsi, on="date", how="inner").sort_values("date")
                if len(m_hsi) >= 30:
                    corr_hs300_hsi_30d = round(float(m_hsi["ret_a"].tail(30).corr(m_hsi["ret_hsi"].tail(30))), 2)
                if len(m_hsi) >= 90:
                    corr_hs300_hsi_90d = round(float(m_hsi["ret_a"].tail(90).corr(m_hsi["ret_hsi"].tail(90))), 2)

            # 创业板 vs 纳斯达克
            if df_chinext is not None:
                df_c = df_chinext[["date", "daily_return"]].rename(columns={"daily_return": "ret_chinext"}).copy()
                df_c["date"] = pd.to_datetime(df_c["date"]).dt.strftime("%Y-%m-%d")
                df_ixic = df_global_idx[df_global_idx["index_code"] == "IXIC"][["date", "daily_return"]].rename(columns={"daily_return": "ret_ixic"})
                if not df_ixic.empty:
                    m_ixic = pd.merge(df_c, df_ixic, on="date", how="inner").sort_values("date")
                    if len(m_ixic) >= 30:
                        corr_chinext_nasdaq_30d = round(float(m_ixic["ret_chinext"].tail(30).corr(m_ixic["ret_ixic"].tail(30))), 2)
                    if len(m_ixic) >= 90:
                        corr_chinext_nasdaq_90d = round(float(m_ixic["ret_chinext"].tail(90).corr(m_ixic["ret_ixic"].tail(90))), 2)

        # -------------------------------------------------------------
        # 3. 提取最新宏观指标
        # -------------------------------------------------------------
        latest_fx = df_fx.iloc[-1]
        usd_cny_latest = float(latest_fx.get("usd_cny", 7.10))
        usd_cnh_latest = float(latest_fx.get("usd_cnh", 7.11))
        cnh_cny_spread = float(latest_fx.get("cnh_cny_spread", usd_cnh_latest - usd_cny_latest))

        # 计算人民币近 20 日动量
        if len(df_fx) >= 20:
            cny_20d_ago = float(df_fx.iloc[-20]["usd_cny"])
            usd_cny_20d_pct = round((usd_cny_latest / cny_20d_ago - 1.0) * 100.0, 2)
        else:
            usd_cny_20d_pct = 0.0

        # 美元指数
        dxy_close = float(latest_fx.get("dxy_close", 102.0))

        # 中美 10Y 国债利差
        latest_rate = df_rates.iloc[-1]
        cn_us_spread_10y = float(latest_rate.get("cn_us_spread_10y", -1.80))

        # 大宗商品 (黄金与原油)
        gold_close, gold_20d_pct = 2650.0, 2.5
        crude_oil_close = 75.0
        if not df_comm.empty:
            df_gc = df_comm[df_comm["commodity_code"] == "GC"].sort_values("date")
            if not df_gc.empty:
                gold_close = round(float(df_gc.iloc[-1]["close"]), 2)
                if len(df_gc) >= 20:
                    gold_20d_ago = float(df_gc.iloc[-20]["close"])
                    gold_20d_pct = round((gold_close / gold_20d_ago - 1.0) * 100.0, 2)
            df_cl = df_comm[df_comm["commodity_code"] == "CL"].sort_values("date")
            if not df_cl.empty:
                crude_oil_close = round(float(df_cl.iloc[-1]["close"]), 2)

        # -------------------------------------------------------------
        # 4. 构建三大外生宏观修正因子
        # -------------------------------------------------------------
        # (1) 汇率压力调节项 (-10 ~ +10 分)
        # 逻辑：USD/CNY 急涨 (贬值) 且 CNH-CNY 价差扩大 -> 推高温度 (外资流出/资产承压)；稳健升值 -> 降低温度 (资金回流)
        fx_pressure = 0.0
        if usd_cny_20d_pct > 1.5:  # 快速贬值
            fx_pressure += 3.0
            if usd_cny_20d_pct > 3.0:
                fx_pressure += 2.5
        elif usd_cny_20d_pct < -1.0: # 升值周期
            fx_pressure -= 3.0

        if cnh_cny_spread > 0.015:  # 离岸贬值预期显著高于在岸
            fx_pressure += 2.0
        elif cnh_cny_spread < -0.010:
            fx_pressure -= 1.5
        fx_pressure_factor = round(float(np.clip(fx_pressure, -10.0, 10.0)), 1)

        # (2) 中美利差倒挂调节项 (-10 ~ +10 分)
        # 逻辑：利差倒挂越深，国内降息受掣肘，资金外流压力大；利差收窄或回正，货币空间充裕
        spread_factor = 0.0
        if cn_us_spread_10y < -2.0:   # 深度倒挂超 200bp
            spread_factor = 5.0
        elif cn_us_spread_10y < -1.5: # 倒挂 150~200bp
            spread_factor = 3.5
        elif cn_us_spread_10y < -0.8: # 适度倒挂 80~150bp
            spread_factor = 1.5
        elif cn_us_spread_10y >= 0.0: # 利差正向
            spread_factor = -3.0
        us_yield_spread_factor = round(float(np.clip(spread_factor, -10.0, 10.0)), 1)

        # (3) 全球避险情绪调节项 (-10 ~ +10 分)
        # 逻辑：黄金大涨、美元指数高企 -> 避险情绪浓厚 (Risk-Off)，增加风险温度并提示增配黄金
        risk_sentiment = 0.0
        if gold_20d_pct > 5.0:
            risk_sentiment += 3.0
        elif gold_20d_pct > 2.0:
            risk_sentiment += 1.5

        if dxy_close > 104.0:
            risk_sentiment += 2.5
        elif dxy_close < 99.0:
            risk_sentiment -= 2.0
        risk_sentiment_factor = round(float(np.clip(risk_sentiment, -10.0, 10.0)), 1)

        # 合计外生调节量 (截断在 -15 ~ +15)
        total_external_adjustment = round(float(np.clip(
            fx_pressure_factor + us_yield_spread_factor + risk_sentiment_factor, -15.0, 15.0
        )), 1)

        # 定性宏观传导研判
        if total_external_adjustment >= 8.0:
            regime = "全球强防御/资本外流压制期 (利差倒挂+强美元+避险高企，建议保守防御增配黄金)"
        elif total_external_adjustment >= 3.0:
            regime = "外部偏紧中性偏压制 (存在一定汇率或利差约束，权益资产保持理性底仓)"
        elif total_external_adjustment >= -2.0:
            regime = "外部环境总体平衡温和 (海外影响处于良性震荡区间，以本土估值和基本面为主导)"
        else:
            regime = "外部流动性宽松利多期 (人民币企稳升值+利差收窄，外资做多中国意愿增强)"

        metrics = GlobalLinkageMetrics(
            eval_date=eval_date,
            corr_hs300_spx_30d=corr_hs300_spx_30d,
            corr_hs300_spx_90d=corr_hs300_spx_90d,
            corr_hs300_hsi_30d=corr_hs300_hsi_30d,
            corr_hs300_hsi_90d=corr_hs300_hsi_90d,
            corr_chinext_nasdaq_30d=corr_chinext_nasdaq_30d,
            corr_chinext_nasdaq_90d=corr_chinext_nasdaq_90d,
            usd_cny_latest=round(usd_cny_latest, 4),
            usd_cnh_latest=round(usd_cnh_latest, 4),
            cnh_cny_spread=round(cnh_cny_spread, 5),
            usd_cny_20d_pct=usd_cny_20d_pct,
            cn_us_spread_10y=round(cn_us_spread_10y, 2),
            gold_close=gold_close,
            gold_20d_pct=gold_20d_pct,
            crude_oil_close=crude_oil_close,
            dxy_close=round(dxy_close, 2),
            fx_pressure_factor=fx_pressure_factor,
            us_yield_spread_factor=us_yield_spread_factor,
            risk_sentiment_factor=risk_sentiment_factor,
            total_external_adjustment=total_external_adjustment,
            macro_regime_desc=regime
        )

        # 沉淀至 Parquet
        df_out = pd.DataFrame([{
            "eval_date": metrics.eval_date,
            "corr_hs300_spx_30d": metrics.corr_hs300_spx_30d,
            "corr_hs300_spx_90d": metrics.corr_hs300_spx_90d,
            "corr_hs300_hsi_30d": metrics.corr_hs300_hsi_30d,
            "corr_hs300_hsi_90d": metrics.corr_hs300_hsi_90d,
            "corr_chinext_nasdaq_30d": metrics.corr_chinext_nasdaq_30d,
            "corr_chinext_nasdaq_90d": metrics.corr_chinext_nasdaq_90d,
            "usd_cny": metrics.usd_cny_latest,
            "usd_cnh": metrics.usd_cnh_latest,
            "cnh_cny_spread": metrics.cnh_cny_spread,
            "usd_cny_20d_pct": metrics.usd_cny_20d_pct,
            "cn_us_spread_10y": metrics.cn_us_spread_10y,
            "gold_close": metrics.gold_close,
            "gold_20d_pct": metrics.gold_20d_pct,
            "crude_oil_close": metrics.crude_oil_close,
            "dxy_close": metrics.dxy_close,
            "fx_pressure_factor": metrics.fx_pressure_factor,
            "us_yield_spread_factor": metrics.us_yield_spread_factor,
            "risk_sentiment_factor": metrics.risk_sentiment_factor,
            "total_external_adjustment": metrics.total_external_adjustment,
            "macro_regime": metrics.macro_regime_desc,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df_out.to_parquet(self.output_parquet, index=False, engine="pyarrow")
        return metrics
