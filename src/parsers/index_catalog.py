"""
A 股全市场指数代码字典与层级分类器 (IndexCatalog)：
汇聚上海证券交易所、深圳证券交易所及中证指数公司全量 A 股核心指数，
自动划分为核心宽基 (Tier 1)、主流行业与主题 (Tier 2) 及细分衍生指数 (Tier 3)，
提供标准 Wind 格式 (如 000001.SH, 399001.SZ) 与 akshare/新浪/同花顺代码的双向映射及本地落盘。
"""

from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

from ..storage.lakehouse import LakehouseManager


class IndexCatalog:
    """A 股全市场指数字典管理类"""

    # 核心宽基指数与基准关键词 (Tier 1)
    TIER_1_KEYWORDS = [
        "上证指数", "Ａ股指数", "上证50", "上证180", "上证380", "新综指",
        "沪深300", "中证500", "中证1000", "中证800", "中证2000", "中证A500", "红利指数",
        "深证成指", "中小100", "创业板指", "深证综指", "深成指", "创业板", "科创50", "国证2000"
    ]

    # 主流行业与核心主题关键词 (Tier 2)
    TIER_2_KEYWORDS = [
        "白酒", "酒", "医药", "医疗", "生物", "半导体", "芯片", "消费", "银行", "证券", "非银",
        "新能源", "军工", "国防", "光伏", "煤炭", "有色", "稀土", "计算机", "软件", "电子",
        "通信", "电池", "工业", "商业", "地产", "金融", "央企", "国企", "科技", "5G", "人工智能",
        "机器人", "智能制造", "农业", "养殖", "环保", "新材料", "钢铁", "化工", "交通", "电力"
    ]

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.master_dir = self.lakehouse.master_dir
        self.catalog_parquet = self.master_dir / "a_share_indices_catalog.parquet"
        self.catalog_csv = self.master_dir / "a_share_indices_catalog.csv"

    def build_catalog(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        构建或从本地加载全市场 A 股指数字典宽表
        """
        if not force_refresh and self.catalog_parquet.exists():
            try:
                df_cached = pd.read_parquet(self.catalog_parquet)
                if not df_cached.empty:
                    return df_cached
            except Exception:
                pass

        spot_dict: Dict[str, str] = {}
        info_dict: Dict[str, str] = {}

        # 1. 抓取新浪行情全量指数
        try:
            import akshare as ak
            df_spot = ak.stock_zh_index_spot_sina()
            if df_spot is not None and not df_spot.empty:
                for _, r in df_spot.iterrows():
                    raw_c = str(r["代码"]).strip().lower()
                    name = str(r["名称"]).strip()
                    spot_dict[raw_c] = name
        except Exception as e:
            pass

        # 2. 抓取中国指数名录库
        try:
            import akshare as ak
            df_info = ak.index_stock_info()
            if df_info is not None and not df_info.empty:
                for _, r in df_info.iterrows():
                    c = str(r["index_code"]).strip()
                    name = str(r["display_name"]).strip()
                    ak_c = f"sz{c}" if c.startswith("399") else f"sh{c}"
                    info_dict[ak_c] = name
        except Exception as e:
            pass

        # 3. 合并全量唯一指数
        all_keys = set(spot_dict.keys()) | set(info_dict.keys())
        if not all_keys:
            # 离线保底基础目录
            all_keys = {
                "sh000001", "sh000002", "sh000016", "sh000300", "sh000905", "sh000852",
                "sh000688", "sz399001", "sz399005", "sz399006", "sz399997", "sz399998"
            }
            spot_dict = {
                "sh000001": "上证指数", "sh000002": "A股指数", "sh000016": "上证50",
                "sh000300": "沪深300", "sh000905": "中证500", "sh000852": "中证1000",
                "sh000688": "科创50", "sz399001": "深证成指", "sz399005": "中小100",
                "sz399006": "创业板指", "sz399997": "中证白酒", "sz399998": "中证煤炭"
            }

        records = []
        for k in sorted(all_keys):
            market = "SH" if k.startswith("sh") else "SZ"
            code = k[2:]
            std_sym = f"{code}.{market}"
            name = spot_dict.get(k) or info_dict.get(k) or f"指数_{code}"

            # 分级研判
            if any(kw in name for kw in self.TIER_1_KEYWORDS):
                tier = "Tier 1"
                tier_desc = "核心宽基基准"
                priority = 1
            elif any(kw in name for kw in self.TIER_2_KEYWORDS):
                tier = "Tier 2"
                tier_desc = "主流行业主题"
                priority = 2
            else:
                tier = "Tier 3"
                tier_desc = "细分衍生指数"
                priority = 3

            records.append({
                "symbol": std_sym,
                "ak_symbol": k,
                "code": code,
                "name": name,
                "market": market,
                "tier": tier,
                "tier_desc": tier_desc,
                "priority": priority
            })

        df_catalog = pd.DataFrame(records)
        # 按优先级 (Tier 1 -> Tier 2 -> Tier 3) 排序
        df_catalog = df_catalog.sort_values(by=["priority", "symbol"]).reset_index(drop=True)

        # 保存至本地湖仓 master 目录
        self.catalog_parquet.parent.mkdir(parents=True, exist_ok=True)
        df_catalog.to_parquet(self.catalog_parquet, index=False, engine="pyarrow")
        df_catalog.to_csv(self.catalog_csv, index=False, encoding="utf-8-sig")

        return df_catalog

    def get_indices(self, tier: Optional[str] = None) -> List[Dict[str, str]]:
        """
        获取指定梯级或全部的指数列表
        tier 可选: 'tier_1', 'tier_2', 'tier_3', 'all' 或 None
        """
        df = self.build_catalog()
        if tier:
            t = tier.lower().replace("_", " ")
            if "1" in t:
                df = df[df["tier"] == "Tier 1"]
            elif "2" in t:
                df = df[df["tier"] == "Tier 2"]
            elif "3" in t:
                df = df[df["tier"] == "Tier 3"]
        return df.to_dict(orient="records")

    def get_name(self, symbol: str) -> str:
        """根据标准代码或 akshare 代码查询指数名称"""
        df = self.build_catalog()
        clean = symbol.strip().upper()
        matched = df[df["symbol"] == clean]
        if not matched.empty:
            return matched["name"].iloc[0]
        # 尝试 ak 格式匹配
        ak_clean = symbol.strip().lower()
        matched_ak = df[df["ak_symbol"] == ak_clean]
        if not matched_ak.empty:
            return matched_ak["name"].iloc[0]
        return clean
