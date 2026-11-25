# -*- coding: utf-8 -*-
"""
AGY2 Layer-0 零业务依赖领域数据模型与静态基金词典 (domain_models.py)
====================================================================
铁律：本模块仅允许导入 Python 标准库（dataclasses, typing, math, re, sys），
严禁导入任何项目内业务模块或第三方重依赖，作为全局 DAG 最底层共享叶子节点。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
import re
import sys

_CLASSIFY_ASSET_CLASS_CACHE: Dict[Tuple[str, str], str] = {}


def _safe_float(val: Any, default: float = 0.0) -> float:
    """安全解析浮点数/整型，防御 None, NaN 及异常字符串（如 'N/A', '--'）"""
    if val is None:
        return default
    try:
        if val != val:  # NaN / pd.NA check
            return default
        f = float(val)
        if math.isnan(f):
            return default
        return f
    except Exception:
        return default


STOCK_NAME_TO_SYMBOL_MAP: Dict[str, str] = {
    # 核心蓝筹与白马标的
    "贵州茅台": "600519.SH",
    "宁德时代": "300750.SZ",
    "中芯国际": "688981.SH",
    "海光信息": "688041.SH",
    "中国神华": "601088.SH",
    "比亚迪": "002594.SZ",
    "招商银行": "600036.SH",
    "中国平安": "601318.SH",
    "五粮液": "000858.SZ",
    "立讯精密": "002475.SZ",
    "紫金矿业": "601899.SH",
    "恒瑞医药": "600276.SH",
    "迈瑞医疗": "300760.SZ",
    "美的集团": "000333.SZ",
    "长江电力": "600900.SH",
    "东方财富": "300059.SZ",
    "陕西煤业": "601225.SH",
    "唐山港": "601000.SH",
    "鲁西化工": "000830.SZ",
    "江苏银行": "600919.SH",
    "农业银行": "601288.SH",
    "交通银行": "601328.SH",
    "中国石化": "600028.SH",
    "北京银行": "601169.SH",
    "渝农商行": "601077.SH",
    "川投能源": "600674.SH",
    "华能水电": "600025.SH",
    "浙商银行": "601916.SH",
    "中微公司": "688012.SH",
    "澜起科技": "688008.SH",
    "寒武纪": "688256.SH",
    "传音控股": "688036.SH",
    "金山办公": "688111.SH",
    "联影医疗": "688271.SH",
    "晶科能源": "688223.SH",
    "天合光能": "688599.SH",
    "九号公司": "689009.SH",
    "润泽科技": "300442.SZ",
    "江淮汽车": "600418.SH",
    "百济神州": "688235.SH",
    "华测检测": "300012.SZ",
    "恺英网络": "002517.SZ",
    "神州泰岳": "300002.SZ",
    "胜宏科技": "300476.SZ",
    "安克创新": "300866.SZ",
    "东山精密": "002384.SZ",
    "新易盛": "300502.SZ",
    "思源电气": "002028.SZ",
    "天孚通信": "300394.SZ",
    "赛轮轮胎": "601058.SH",
    "宇通客车": "600066.SH",
    "银轮股份": "002126.SZ",
    "石头科技": "688169.SH",
    "圣泉集团": "605589.SH",
    "西部矿业": "601168.SH",
    "生益科技": "600183.SH",
    "兴业银行": "601166.SH",
    "韦尔股份": "603501.SH",
    "北方华创": "002371.SZ",
    "圣邦股份": "300661.SZ",
    "兆易创新": "603986.SH",
    "卓胜微": "300782.SZ",
    "长电科技": "600584.SH",
    "格力电器": "000651.SZ",
    "伊利股份": "600887.SH",
    "海尔智家": "600690.SH",
    "海天味业": "603288.SH",
    "片仔癀": "600436.SH",
    "云南白药": "000538.SZ",
    "东阿阿胶": "000423.SZ",
    "万科A": "000002.SZ",
    "科大讯飞": "002230.SZ",
    "*ST三房": "600370.SH",
    "海德股份": "000567.SZ",
    "ST雪发": "002485.SZ",
    "金徽股份": "603132.SH",
    "深华发A": "000020.SZ",
    "*ST九鼎": "600053.SH",
    "中央商场": "600280.SH",
    "南京新百": "600682.SH",
    "恩威医药": "301331.SZ",
}


# 核心数据模型 (Data Models)
# =====================================================================

@dataclass
class HoldingBatch:
    """FIFO 份额批次定义"""
    batch_id: str
    buy_date: str                 # 确认申购/买入日期 (YYYY-MM-DD)
    shares: float                 # 剩余份额
    cost_nav: float               # 买入确认净值 (成本价)
    fee: float = 0.0              # 申购手续费
    holding_days: int = 0         # 持有自然日天数
    safety_lock: bool = False     # 7天安全观察锁 (未满7天或冷启动缺省)
    notes: str = ""               # 批次备注


@dataclass
class FundHolding:
    """单只基金持仓全景画像"""
    fund_code: str                # 6 位基金代码
    fund_name: str                # 基金名称
    share_class: str = "A"        # A 或 C
    shares: float = 0.0           # 总持仓份额
    cost_price: float = 1.0       # 加权平均成本价
    current_nav: float = 1.0      # 当前最新净值
    market_value: float = 0.0     # 当前持仓市值 (元)
    cost_basis: float = 0.0       # 成本总金额 (元)
    floating_pnl: float = 0.0     # 浮动盈亏额 (元)
    floating_pnl_pct: float = 0.0 # 浮动盈亏率 (%)
    first_buy_date: str = ""      # 最早建仓日期
    dividend_method: str = "cash" # cash: 现金分红 | reinvest: 红利再投资
    batches: List[HoldingBatch] = field(default_factory=list)
    company: str = ""             # 基金公司
    is_core_strategy: bool = False # 是否属于 AGY2 核心策略池
    transition_tag: str = ""      # 换仓过渡标签
    rebalance_intent: str = "normal" # 调仓意愿: normal(正常参与) | lock(锁定禁卖) | liquidate(优先清仓)
    cost_nav: float = 0.0         # 兼容参数别名 (等同 cost_price)

    def __post_init__(self):
        if self.fund_code == "017436" and ("华宝" in self.fund_name or not self.fund_name):
            self.fund_name = "华安纳斯达克100ETF联接A"
        if self.cost_nav and self.cost_price == 1.0 and self.cost_nav != 1.0:
            self.cost_price = self.cost_nav
        if self.market_value <= 0.0 and self.shares > 0.0:
            self.market_value = round(self.shares * self.current_nav, 2)
        if self.cost_basis <= 0.0 and self.shares > 0.0:
            self.cost_basis = round(self.shares * self.cost_price, 2)
        if self.cost_basis > 0.0 and self.floating_pnl == 0.0 and self.market_value > 0.0:
            self.floating_pnl = round(self.market_value - self.cost_basis, 2)
            self.floating_pnl_pct = round((self.floating_pnl / self.cost_basis) * 100.0, 2)

    @property
    def holding_days(self) -> int:
        """悲观最短持有天数 (FIFO 惩罚锁防线)"""
        if getattr(self, "batches", None):
            return min((b.holding_days for b in self.batches), default=30)
        return 30

    @holding_days.setter
    def holding_days(self, val: int):
        val = int(val)
        if getattr(self, "batches", None):
            for b in self.batches:
                b.holding_days = val
                b.safety_lock = (val < 7)
        else:
            self.batches = [
                HoldingBatch(
                    batch_id=f"B_{self.fund_code}_001",
                    buy_date="",
                    shares=self.shares,
                    cost_nav=self.cost_price,
                    holding_days=val,
                    safety_lock=(val < 7)
                )
            ]


# 全局兼容类型别名，确保 HoldingItem 与 FundHolding 完全等价
HoldingItem = FundHolding


@dataclass
class PendingOrder:
    """在途待确认订单定义"""
    order_id: str
    created_at: str               # 申报时间 (YYYY-MM-DD HH:MM:SS)
    effective_trade_date: str     # 生效交易日 T
    action: str                   # BUY / SELL / SWITCH / BUY_PENDING_ARRIVAL
    fund_code: str                # 原标的代码
    fund_name: str                # 原标的名称
    target_fund_code: str = ""    # 转换目标基金代码 (仅 SWITCH)
    target_fund_name: str = ""    # 转换目标基金名称
    amount: float = 0.0           # 申购/转换金额 (元)
    shares: float = 0.0           # 赎回/转换份额 (份)
    est_nav: float = 1.0          # 预估成交净值
    est_fee: float = 0.0          # 预估手续费 (元)
    est_confirm_date: str = ""    # 预计确认日 T+1
    est_cash_arrive_date: str = ""# 预计资金到账日 T+2/T+3
    route_priority: str = "CASH_ADVANCE" # SWITCH / CASH_ADVANCE / TWO_STEP / SELL_TO_CASH
    status: str = "PENDING"       # PENDING / CONFIRMED / CANCELLED
    notes: str = ""


# =====================================================================
# AGY2 核心策略池与全市场公募基金元数据
# =====================================================================

CORE_STRATEGY_POOL: Dict[str, Dict[str, Any]] = {
    "100032": {
        "fund_name": "富国中证红利指数增强A",
        "company": "富国基金",
        "share_class": "A",
        "alt_code": "008682", # C 类对应代码
        "daily_limit": 1e11,
        "fallback_code": "090010",
        "style": "高股息/红利价值",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "008682": {
        "fund_name": "富国中证红利指数增强C",
        "company": "富国基金",
        "share_class": "C",
        "alt_code": "100032",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "高股息/红利价值波段",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "090010": {
        "fund_name": "大成中证红利指数A",
        "company": "大成基金",
        "share_class": "A",
        "alt_code": "091010",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "老牌纯正高股息代表",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "091010": {
        "fund_name": "大成中证红利指数C",
        "company": "大成基金",
        "share_class": "C",
        "alt_code": "090010",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "老牌纯正高股息代表C类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "012643": {
        "fund_name": "招商中证红利ETF联接A",
        "company": "招商基金",
        "share_class": "A",
        "alt_code": "012644",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "低费率中证红利纯跟踪",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "012644": {
        "fund_name": "招商中证红利ETF联接C",
        "company": "招商基金",
        "share_class": "C",
        "alt_code": "012643",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "低费率中证红利纯跟踪C类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "005561": {
        "fund_name": "创金合信中证红利低波动指数A",
        "company": "创金合信基金",
        "share_class": "A",
        "alt_code": "005562",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "红利低波/防御中枢",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "005562": {
        "fund_name": "创金合信中证红利低波动指数C",
        "company": "创金合信基金",
        "share_class": "C",
        "alt_code": "005561",
        "daily_limit": 1e11,
        "fallback_code": "005561",
        "style": "红利低波/防御中枢C类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "016440": {
        "fund_name": "华夏中证红利质量ETF发起式联接A",
        "company": "华夏基金",
        "share_class": "A",
        "alt_code": "016441",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "高股息/消费质量",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "016441": {
        "fund_name": "华夏中证红利质量ETF发起式联接C",
        "company": "华夏基金",
        "share_class": "C",
        "alt_code": "016440",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "高股息/消费质量C类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "000216": {
        "fund_name": "华安黄金ETF联接A",
        "company": "华安基金",
        "share_class": "A",
        "alt_code": "000217",
        "daily_limit": 1e11,
        "fallback_code": "002610",
        "style": "黄金抗通胀/全天候对冲",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "000217": {
        "fund_name": "华安黄金ETF联接C",
        "company": "华安基金",
        "share_class": "C",
        "alt_code": "000216",
        "daily_limit": 1e11,
        "fallback_code": "000216",
        "style": "黄金抗通胀/短期波段对冲",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "002610": {
        "fund_name": "博时黄金ETF联接A",
        "company": "博时基金",
        "share_class": "A",
        "alt_code": "002611",
        "daily_limit": 1e11,
        "fallback_code": "000216",
        "style": "主流黄金ETF对冲标的",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "002611": {
        "fund_name": "博时黄金ETF联接C",
        "company": "博时基金",
        "share_class": "C",
        "alt_code": "002610",
        "daily_limit": 1e11,
        "fallback_code": "000216",
        "style": "黄金现货波段对冲C类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "002351": {
        "fund_name": "易方达裕祥回报债券A",
        "company": "易方达基金",
        "share_class": "A",
        "alt_code": "002352",
        "daily_limit": 1e11,
        "fallback_code": "000086",
        "style": "纯债稳健/压舱石",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "002352": {
        "fund_name": "易方达裕祥回报债券C",
        "company": "易方达基金",
        "share_class": "C",
        "alt_code": "002351",
        "daily_limit": 1e11,
        "fallback_code": "002351",
        "style": "纯债稳健固收/0申购费免赎债基",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "000086": {
        "fund_name": "工银瑞信信用纯债债券A",
        "company": "工银瑞信基金",
        "share_class": "A",
        "alt_code": "000087",
        "daily_limit": 1e11,
        "fallback_code": "002351",
        "style": "纯债稳健固收/高信用标杆",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "000087": {
        "fund_name": "工银信用纯债债券C",
        "company": "工银瑞信基金",
        "share_class": "C",
        "alt_code": "000086",
        "daily_limit": 1e11,
        "fallback_code": "002351",
        "style": "纯债稳健固收C类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "018757": {
        "fund_name": "睿远稳益增强30天持有债券C",
        "company": "睿远基金",
        "share_class": "C",
        "alt_code": "018756",
        "daily_limit": 1e11,
        "fallback_code": "002351",
        "style": "稀缺限购稳健债基",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "018756": {
        "fund_name": "睿远稳益增强30天持有债券A",
        "company": "睿远基金",
        "share_class": "A",
        "alt_code": "018757",
        "daily_limit": 1e11,
        "fallback_code": "002351",
        "style": "稀缺限购稳健债基A类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "050025": {
        "fund_name": "博时标普500ETF联接A",
        "company": "博时基金",
        "share_class": "A",
        "alt_code": "006075",
        "daily_limit": 1e11,
        "fallback_code": "001071", # 摩根标普500备选
        "style": "海外美股/全球跨资产对冲",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+4"
    },
    "001071": {
        "fund_name": "摩根标普500指数(QDII)人民币A",
        "company": "摩根基金",
        "share_class": "A",
        "alt_code": "001071",
        "daily_limit": 1e11,
        "fallback_code": "050025",
        "style": "海外美股/全球对冲(限购拆单备选)",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+4"
    },
    "006075": {
        "fund_name": "广发纳斯达克100ETF联接A",
        "company": "广发基金",
        "share_class": "A",
        "alt_code": "006479",
        "daily_limit": 1e11,
        "fallback_code": "001071",
        "style": "美股硬核科技宽基对冲",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+4"
    },
    "017436": {
        "fund_name": "华安纳斯达克100ETF联接A",
        "company": "华安基金",
        "share_class": "A",
        "alt_code": "017437",
        "daily_limit": 1e11,
        "fallback_code": "001071",
        "style": "海外科技成长",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+4"
    },
    "011612": {
        "fund_name": "华夏科创50ETF联接A",
        "company": "华夏基金",
        "share_class": "A",
        "alt_code": "011613",
        "daily_limit": 1e11,
        "fallback_code": "016633",
        "style": "科技成长进攻/主升浪弹性",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "011613": {
        "fund_name": "华夏上证科创板50成份ETF联接C",
        "company": "华夏基金",
        "share_class": "C",
        "alt_code": "011612",
        "daily_limit": 1e11,
        "fallback_code": "016634",
        "style": "硬科技与成长主升浪(赛道冠军)",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "016633": {
        "fund_name": "富国中证1000ETF联接A",
        "company": "富国基金",
        "share_class": "A",
        "alt_code": "016634",
        "daily_limit": 1e11,
        "fallback_code": "161017",
        "style": "小盘弹性/成长反弹",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "016634": {
        "fund_name": "富国中证1000ETF联接C",
        "company": "富国基金",
        "share_class": "C",
        "alt_code": "016633",
        "daily_limit": 1e11,
        "fallback_code": "001053",
        "style": "小盘弹性进攻/波段高弹性",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "161017": {
        "fund_name": "富国中证500指数增强(LOF)A",
        "company": "富国基金",
        "share_class": "A",
        "alt_code": "013035",
        "daily_limit": 1e11,
        "fallback_code": "110020",
        "style": "中盘均衡/超额增强",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "013035": {
        "fund_name": "富国中证500指数增强(LOF)C",
        "company": "富国基金",
        "share_class": "C",
        "alt_code": "161017",
        "daily_limit": 1e11,
        "fallback_code": "110020",
        "style": "中盘均衡/超额增强C类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "001053": {
        "fund_name": "华夏中证500ETF联接C",
        "company": "华夏基金",
        "share_class": "C",
        "alt_code": "001052",
        "daily_limit": 1e11,
        "fallback_code": "161017",
        "style": "中盘成长/风格分化轮动",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "001052": {
        "fund_name": "华夏中证500ETF联接A",
        "company": "华夏基金",
        "share_class": "A",
        "alt_code": "001053",
        "daily_limit": 1e11,
        "fallback_code": "161017",
        "style": "中盘成长A类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "013841": {
        "fund_name": "银华集成电路混合C",
        "company": "银华基金",
        "share_class": "C",
        "alt_code": "013840",
        "daily_limit": 1e11,
        "fallback_code": "011613",
        "style": "硬科技与半导体细分进攻",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "013840": {
        "fund_name": "银华集成电路混合A",
        "company": "银华基金",
        "share_class": "A",
        "alt_code": "013841",
        "daily_limit": 1e11,
        "fallback_code": "011613",
        "style": "硬科技与半导体细分A类",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "110020": {
        "fund_name": "易方达沪深300ETF联接A",
        "company": "易方达基金",
        "share_class": "A",
        "alt_code": "007339",
        "daily_limit": 1e11,
        "fallback_code": "100032",
        "style": "核心蓝筹/宽基底仓",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    },
    "007339": {
        "fund_name": "易方达沪深300ETF联接C",
        "company": "易方达基金",
        "share_class": "C",
        "alt_code": "110020",
        "daily_limit": 1e11,
        "fallback_code": "110020",
        "style": "大盘蓝筹进攻/顺势脉冲",
        "confirm_cycle": "T+1",
        "arrive_cycle": "T+2"
    }
}

# 扩展非标常见映射（用于智能识别与归类）
EXTENDED_FUND_CATALOG: Dict[str, Dict[str, Any]] = {
    "005827": {"fund_name": "易方达蓝筹精选混合", "company": "易方达基金", "share_class": "A", "style": "主动偏股/蓝筹成长", "daily_limit": 1e11},
    "000058": {"fund_name": "华夏中小板ETF联接A", "company": "华夏基金", "share_class": "A", "style": "指数/中小板联接", "daily_limit": 1e11},
}

# =====================================================================
# 全市场选基赛道画像与冠军标的推荐理由 (Selection Funnel & Champions)
# =====================================================================

SECTOR_FUND_SELECTION: Dict[str, Dict[str, Any]] = {
    "CORE_DIVIDEND": {
        "sector_id": "CORE_DIVIDEND",
        "sector_name": "高股息与红利价值赛道",
        "champion_code": "100032",
        "champion_name": "富国中证红利指数增强A",
        "champion_reason": "全市场红利增强规模第一梯队，过去5年相对基准累计超额 +32.4%，长期持有A类免销售服务费，复利效应显著。",
        "alternatives": [
            {"code": "100032", "name": "富国中证红利指数增强A (冠军)", "share_class": "A", "tag": "红利增强龙头 / 长期首选"},
            {"code": "090010", "name": "大成中证红利指数A", "share_class": "A", "tag": "老牌纯正高股息代表"},
            {"code": "012643", "name": "招商中证红利ETF联接A", "share_class": "A", "tag": "低费率中证红利纯跟踪"},
            {"code": "008682", "name": "富国中证红利指数增强C", "share_class": "C", "tag": "0申购满30天免赎波段"}
        ],
        "top_alternatives": [
            {"code": "090010", "name": "大成中证红利指数A", "share_class": "A", "tag": "老牌纯正高股息代表"},
            {"code": "012643", "name": "招商中证红利ETF联接A", "share_class": "A", "tag": "低费率中证红利纯跟踪"},
            {"code": "008682", "name": "富国中证红利指数增强C", "share_class": "C", "tag": "0申购满30天免赎波段"}
        ]
    },
    "BOND_SHIELD": {
        "sector_id": "BOND_SHIELD",
        "sector_name": "纯债稳健固收压舱石赛道",
        "champion_code": "002351",
        "champion_name": "易方达裕祥回报债券A",
        "champion_reason": "百亿级公募稳健纯债旗舰，历史回撤极低仅 -2.1%，票息累积扎实，大熊市避险压舱第一首选。",
        "alternatives": [
            {"code": "002351", "name": "易方达裕祥回报债券A (冠军)", "share_class": "A", "tag": "百亿纯债旗舰 / 回撤极小"},
            {"code": "000086", "name": "工银信用纯债债券A", "share_class": "A", "tag": "高信用等级债券标杆"},
            {"code": "018757", "name": "睿远稳益增强30天持有C", "share_class": "C", "tag": "稀缺限购稳健债基"},
            {"code": "002352", "name": "易方达裕祥回报债券C", "share_class": "C", "tag": "0申购费满30天免赎债基"}
        ],
        "top_alternatives": [
            {"code": "000086", "name": "工银信用纯债债券A", "share_class": "A", "tag": "高信用等级债券标杆"},
            {"code": "018757", "name": "睿远稳益增强30天持有C", "share_class": "C", "tag": "稀缺限购稳健债基"},
            {"code": "002352", "name": "易方达裕祥回报债券C", "share_class": "C", "tag": "0申购费满30天免赎债基"}
        ]
    },
    "GOLD_HEDGE": {
        "sector_id": "GOLD_HEDGE",
        "sector_name": "黄金现货全天候对冲赛道",
        "champion_code": "000216",
        "champion_name": "华安易富黄金ETF联接A",
        "champion_reason": "国内管理规模最大、流动性最好的黄金ETF联接基金，紧密跟踪 SGE 黄金现货，避险抗通胀首选。",
        "alternatives": [
            {"code": "000216", "name": "华安易富黄金ETF联接A (冠军)", "share_class": "A", "tag": "全市场最大黄金联接"},
            {"code": "002610", "name": "博时黄金ETF联接A", "share_class": "A", "tag": "主流黄金ETF对冲标的"},
            {"code": "000217", "name": "华安易富黄金ETF联接C", "share_class": "C", "tag": "短期黄金波段对冲"},
            {"code": "002611", "name": "博时黄金ETF联接C", "share_class": "C", "tag": "黄金现货波段对冲C类"}
        ],
        "top_alternatives": [
            {"code": "002610", "name": "博时黄金ETF联接A", "share_class": "A", "tag": "主流黄金ETF对冲标的"},
            {"code": "000217", "name": "华安易富黄金ETF联接C", "share_class": "C", "tag": "短期黄金波段对冲"},
            {"code": "002611", "name": "博时黄金ETF联接C", "share_class": "C", "tag": "黄金现货波段对冲C类"}
        ]
    },
    "TECH_GROWTH": {
        "sector_id": "TECH_GROWTH",
        "sector_name": "硬科技与成长主升浪赛道",
        "champion_code": "011613",
        "champion_name": "华夏上证科创板50成份ETF联接C",
        "champion_reason": "硬科技核心宽基代表，强制选 C 类 0 申购费且满 30 天免赎，顺势主升浪进攻爆发力最强。",
        "alternatives": [
            {"code": "011613", "name": "华夏科创50ETF联接C (冠军)", "share_class": "C", "tag": "0申购满30天免赎 / 科技爆发第一"},
            {"code": "016634", "name": "富国中证1000ETF联接C", "share_class": "C", "tag": "小盘高弹性进攻波段仓"},
            {"code": "001053", "name": "华夏中证500ETF联接C", "share_class": "C", "tag": "中盘风格分化轮动"},
            {"code": "013841", "name": "银华集成电路混合C", "share_class": "C", "tag": "半导体细分高弹性龙头"}
        ],
        "top_alternatives": [
            {"code": "016634", "name": "富国中证1000ETF联接C", "share_class": "C", "tag": "小盘高弹性进攻波段仓"},
            {"code": "001053", "name": "华夏中证500ETF联接C", "share_class": "C", "tag": "中盘风格分化轮动"},
            {"code": "013841", "name": "银华集成电路混合C", "share_class": "C", "tag": "半导体细分高弹性龙头"}
        ]
    },
    "GLOBAL_HEDGE": {
        "sector_id": "GLOBAL_HEDGE",
        "sector_name": "海外跨市场多元对冲赛道",
        "champion_code": "050025",
        "champion_name": "博时标普500ETF联接A",
        "champion_reason": "标普500核心蓝筹直连，有效平抑单一 A 股本土系统性风险，费率低廉，跟踪误差行业前列。",
        "alternatives": [
            {"code": "050025", "name": "博时标普500ETF联接A (冠军)", "share_class": "A", "tag": "美股大盘蓝筹基准 (单日限额500)"},
            {"code": "001071", "name": "摩根标普500指数A (备选)", "share_class": "A", "tag": "大额不限购标普替代方案"},
            {"code": "017436", "name": "华安纳斯达克100ETF联接A", "share_class": "A", "tag": "海外高科技成长跨市场"},
            {"code": "006075", "name": "广发纳斯达克100ETF联接A", "share_class": "A", "tag": "美股硬核科技宽基对冲"}
        ],
        "top_alternatives": [
            {"code": "001071", "name": "摩根标普500指数A (备选)", "share_class": "A", "tag": "大额不限购标普替代方案"},
            {"code": "017436", "name": "华安纳斯达克100ETF联接A", "share_class": "A", "tag": "海外高科技成长跨市场"},
            {"code": "006075", "name": "广发纳斯达克100ETF联接A", "share_class": "A", "tag": "美股硬核科技宽基对冲"}
        ]
    }
}



class FundQuote(dict):
    """
    兼容字典索引、属性访问与 5 元组解构的基金实时行情数据模型 (G26 双轨对账增强版)
    同时独立承载：
    1. 当日实时估算轨 (est_gsz, est_gszzl, tiantian_gszzl, penetration_gszzl, est_source)
    2. 官方公布净值轨 (official_nav, official_chg_pct/official_chg, prev_official_chg_pct, official_pdate/official_date, is_official_nav)
    3. 官方 vs 估算对比摘要 (est_diff, val_compare_str)
    """
    def __init__(
        self,
        name: str,
        dwjz: float,
        gsz: float,
        gszzl: float,
        gztime: str,
        fund_code: str = "",
        valuation_corrected: bool = False,
        is_official_nav: bool = False,
        real_tiantian_live: bool = False,
        est_gsz: Optional[float] = None,
        est_gszzl: Optional[float] = None,
        tiantian_gszzl: Optional[float] = None,
        penetration_gszzl: Optional[float] = None,
        official_nav: Optional[float] = None,
        official_chg_pct: Optional[float] = None,
        official_chg: Optional[float] = None,
        prev_official_chg_pct: Optional[float] = None,
        official_pdate: str = "",
        official_date: str = "",
        est_source: str = "",
        val_compare_str: str = "",
        is_dividend_event: bool = False,
        accum_nav: Optional[float] = None
    ):
        _gsz_f = float(gsz)
        _gszzl_f = float(gszzl)
        _est_gsz_f = float(est_gsz) if est_gsz is not None else _gsz_f
        _est_gszzl_f = round(float(est_gszzl), 2) if est_gszzl is not None else round(_gszzl_f, 2)
        # 反作弊守卫：当官方净值公布且未显式传入 est_gszzl 时，优先从盘中定格估算归档检索，绝不默认退化为官方涨跌制造假0误差
        if est_gszzl is None and is_official_nav and fund_code and hasattr(sys, "_AGY2_SHARED_TODAY_EST_ARCHIVE"):
            _arch_map = getattr(sys, "_AGY2_SHARED_TODAY_EST_ARCHIVE", {})
            if fund_code in _arch_map:
                _arch = _arch_map[fund_code]
                _est_gsz_f = float(_arch[1])
                _est_gszzl_f = round(float(_arch[2]), 2)
                if not est_source and len(_arch) > 3 and _arch[3]:
                    est_source = str(_arch[3])
        _off_nav_f = float(official_nav) if official_nav is not None else float(dwjz)
        _raw_off_chg = official_chg_pct if official_chg_pct is not None else official_chg
        _off_chg_f = round(float(_raw_off_chg), 2) if _raw_off_chg is not None else (round(_gszzl_f, 2) if is_official_nav else None)
        _prev_off_f = round(float(prev_official_chg_pct), 2) if prev_official_chg_pct is not None else (_off_chg_f if _off_chg_f is not None else None)
        _pdate_s = str(official_pdate or official_date or "")

        # 计算同日估算偏差 est_diff = round(est_gszzl - official_chg, 2)（仅当今日官方净值已公布时有值）
        _est_diff_f: Optional[float] = None
        if is_official_nav and _off_chg_f is not None:
            _est_diff_f = round(_est_gszzl_f - _off_chg_f, 2)

        if not val_compare_str:
            if is_official_nav and _off_chg_f is not None and _est_diff_f is not None:
                _abs_d = abs(_est_diff_f)
                _badge = "🟢" if _abs_d <= 0.15 else ("🟡" if _abs_d <= 0.40 else "🔴")
                val_compare_str = f"{_badge} {_off_chg_f:+.2f}% (差{_est_diff_f:+.2f}%)"
            else:
                _p_tag = _pdate_s[-5:] if len(_pdate_s) >= 5 else "待更"
                if _prev_off_f is not None:
                    val_compare_str = f"⏳待出 ({_p_tag}官 {_prev_off_f:+.2f}%)"
                else:
                    val_compare_str = f"⏳待出 ({_p_tag})"

        super().__init__(
            name=name,
            dwjz=float(dwjz),
            gsz=_gsz_f,
            gszzl=_gszzl_f,
            gztime=str(gztime),
            fund_code=str(fund_code),
            valuation_corrected=bool(valuation_corrected),
            is_official_nav=bool(is_official_nav),
            real_tiantian_live=bool(real_tiantian_live),
            est_gsz=_est_gsz_f,
            est_gszzl=_est_gszzl_f,
            tiantian_gszzl=round(float(tiantian_gszzl), 2) if tiantian_gszzl is not None else None,
            penetration_gszzl=round(float(penetration_gszzl), 2) if penetration_gszzl is not None else None,
            official_nav=_off_nav_f,
            official_chg_pct=_off_chg_f,
            official_chg=_off_chg_f if _off_chg_f is not None else (_prev_off_f if _prev_off_f is not None else 0.0),
            prev_official_chg_pct=_prev_off_f,
            official_pdate=_pdate_s,
            official_date=_pdate_s,
            est_diff=_est_diff_f,
            est_source=str(est_source or ""),
            val_compare_str=str(val_compare_str),
            is_dividend_event=bool(is_dividend_event),
            accum_nav=float(accum_nav) if accum_nav is not None else None
        )

    @property
    def accum_nav(self) -> Optional[float]: return self.get("accum_nav")
    @property
    def name(self) -> str: return str(self.get("name", ""))
    @property
    def dwjz(self) -> float: return float(self.get("dwjz", 1.0))
    @property
    def gsz(self) -> float: return float(self.get("gsz", 1.0))
    @property
    def gszzl(self) -> float: return float(self.get("gszzl", 0.0))
    @property
    def gztime(self) -> str: return str(self.get("gztime", ""))
    @property
    def fund_code(self) -> str: return str(self.get("fund_code", ""))
    @property
    def valuation_corrected(self) -> bool: return bool(self.get("valuation_corrected", False))
    @property
    def is_official_nav(self) -> bool: return bool(self.get("is_official_nav", False))
    @property
    def real_tiantian_live(self) -> bool: return bool(self.get("real_tiantian_live", False))
    @property
    def est_gsz(self) -> float: return float(self.get("est_gsz", self.gsz))
    @property
    def est_gszzl(self) -> float: return float(self.get("est_gszzl", self.gszzl))
    @property
    def tiantian_gszzl(self) -> Optional[float]:
        v = self.get("tiantian_gszzl")
        return float(v) if v is not None else None
    @property
    def penetration_gszzl(self) -> Optional[float]:
        v = self.get("penetration_gszzl")
        return float(v) if v is not None else None
    @property
    def official_nav(self) -> float: return float(self.get("official_nav", self.dwjz))
    @property
    def official_chg_pct(self) -> Optional[float]:
        v = self.get("official_chg_pct")
        return float(v) if v is not None else None
    @property
    def official_chg(self) -> float:
        v = self.get("official_chg")
        return float(v) if v is not None else 0.0
    @property
    def prev_official_chg_pct(self) -> Optional[float]:
        v = self.get("prev_official_chg_pct")
        return float(v) if v is not None else None
    @property
    def official_pdate(self) -> str: return str(self.get("official_pdate", ""))
    @property
    def official_date(self) -> str: return str(self.get("official_date", self.get("official_pdate", "")))
    @property
    def est_diff(self) -> Optional[float]:
        v = self.get("est_diff")
        return float(v) if v is not None else None
    @property
    def est_source(self) -> str: return str(self.get("est_source", ""))
    @property
    def val_compare_str(self) -> str: return str(self.get("val_compare_str", ""))
    @property
    def is_dividend_event(self) -> bool: return bool(self.get("is_dividend_event", False))

    def __iter__(self):
        return iter([self.name, self.dwjz, self.gsz, self.gszzl, self.gztime])

    def __getitem__(self, key):
        if isinstance(key, int):
            return [self.name, self.dwjz, self.gsz, self.gszzl, self.gztime][key]
        return super().__getitem__(key)

    def to_list(self) -> List[Any]:
        return [self.name, self.dwjz, self.gsz, self.gszzl, self.gztime]



FUND_ALIAS_EXPLICIT_MAP: Dict[str, str] = {
    "005561": "创金红利低波",
    "100032": "富国中证红利",
    "002351": "易方达裕祥债",
    "000216": "华安黄金ETF",
    "017436": "华安纳指100",
    "017437": "华安纳指100C",
    "011613": "华夏科创50C",
    "011612": "华夏科创50A",
    "161725": "招商中证白酒",
    "161726": "招商生物医药",
    "160418": "华安中证银行",
    "013402": "华夏恒生科技",
    "001053": "华夏中证500C",
    "001071": "摩根标普500A",
    "050025": "博时标普500A",
    "006075": "广发纳斯达克100A",
    "518880": "华安黄金现货",
    "159919": "嘉实沪深300",
    "510300": "华泰柏瑞300",
    "510500": "南方中证500"
}

def get_fund_short_alias(code: str, full_name: str = "") -> str:
    """
    智能图表简称提纯函数：
    去除“中证/上证/国证/ETF联接/指数增强/发起式/人民币/A/C”等冗余词，精准提炼为高辨识度 5~6 字优雅简称。
    彻底杜绝 fund_name[:6] 暴力机械截断造成的“半截话”废话。
    """
    c = str(code).strip().zfill(6)
    if c in FUND_ALIAS_EXPLICIT_MAP:
        return FUND_ALIAS_EXPLICIT_MAP[c]
    
    nm = str(full_name or "").strip()
    if not nm or nm == f"公募基金_{c}":
        return f"标的{c}"
    
    # 清理各类冗余后缀与模式
    nm = re.sub(r"\(QDII\)|（QDII）|\(LOF\)|（LOF）|\(ETF\)|（ETF）", "", nm)
    nm = re.sub(r"\(人民币\)|（人民币）|\(人民币份额\)|（人民币份额）", "", nm)
    
    share_sfx = ""
    if nm.endswith(("A", "C", "E", "H")):
        share_sfx = nm[-1]
        nm = nm[:-1].strip()
    elif nm.endswith(("A类", "C类")):
        share_sfx = nm[-2]
        nm = nm[:-2].strip()

    redundant_patterns = [
        "ETF联接", "发起式联接", "联接", "指数增强", "增强型", "指数证券投资基金",
        "证券投资基金", "发起式", "开放式", "股票型", "债券型", "混合型"
    ]
    for p in redundant_patterns:
        nm = nm.replace(p, "")

    nm = nm.strip()
    if len(nm) > 6:
        nm = nm.replace("发起", "").replace("精选", "").replace("成长", "").strip()
    
    res = f"{nm[:6]}{share_sfx}" if share_sfx and not nm.endswith(share_sfx) else nm[:6]
    return res.strip() or f"标的{c}"

