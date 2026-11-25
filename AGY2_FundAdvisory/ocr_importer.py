# -*- coding: utf-8 -*-
"""
AGY2 智能文本粘贴与长截图切片 OCR 导入引擎 (G45 Cut 1)
====================================================
从 portfolio_manager.py 拆离的独立领域模块，保留 100% 原始解析与全市场 28,177 基金模糊匹配逻辑。
"""

from typing import Dict, List, Optional, Tuple, Any
import io
import re
import numpy as np
import pandas as pd

import runtime_paths
from domain_models import CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG
from valuation_engine import fetch_realtime_fund_quote

WORKSPACE_ROOT = runtime_paths.get_workspace_root()


_LOCAL_FUND_CATALOG_CACHE: Optional[pd.DataFrame] = None


def search_funds_in_catalog(keyword: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    按基金代码、中文名、拼音缩写从本地 28,177 基金库中高速检索匹配标的
    """
    global _LOCAL_FUND_CATALOG_CACHE
    if not keyword or not str(keyword).strip():
        return []

    kw = str(keyword).strip().upper()

    if _LOCAL_FUND_CATALOG_CACHE is None:
        cat_file = runtime_paths.resolve_data_file("master/fund_catalog.parquet")
        if cat_file.exists():
            try:
                _LOCAL_FUND_CATALOG_CACHE = pd.read_parquet(cat_file)
            except Exception:
                _LOCAL_FUND_CATALOG_CACHE = pd.DataFrame()
        else:
            _LOCAL_FUND_CATALOG_CACHE = pd.DataFrame()

    results: List[Dict[str, str]] = []

    # 1. 优先查核心池与扩展池
    combined_pool = {**CORE_STRATEGY_POOL, **EXTENDED_FUND_CATALOG}
    for code, meta in combined_pool.items():
        fname = meta.get("fund_name", "")
        if kw in code or kw in fname.upper():
            style_val = meta.get("style", "公募基金")
            results.append({
                "fund_code": code,
                "fund_name": fname,
                "fund_type": style_val,
                "category": style_val,
                "share_class": meta.get("share_class", "A")
            })

    # 2. 从全量 parquet 库搜索
    if _LOCAL_FUND_CATALOG_CACHE is not None and not _LOCAL_FUND_CATALOG_CACHE.empty:
        df = _LOCAL_FUND_CATALOG_CACHE
        mask = (
            df['symbol'].str.contains(kw, na=False) |
            df['fund_name'].str.upper().str.contains(kw, na=False) |
            df['pinyin_abbr'].str.upper().str.contains(kw, na=False)
        )
        matched_df = df.loc[mask].head(limit * 2)
        for _, row in matched_df.iterrows():
            sym = str(row['symbol'])
            if not any(r['fund_code'] == sym for r in results):
                name = str(row['fund_name'])
                ftype = str(row.get('fund_type', '公募基金'))
                s_class = "C" if name.endswith("C") or sym.endswith("3") or sym.endswith("7") else "A"
                results.append({
                    "fund_code": sym,
                    "fund_name": name,
                    "fund_type": ftype,
                    "category": ftype,
                    "share_class": s_class
                })
            if len(results) >= limit:
                break

    return results[:limit]


def parse_smart_text_holdings(text: str, catalog_df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """
    智能文本粘贴一键识别引擎 (Smart Text Holdings Parser)
    用户直接粘贴如:
      100032 35000元
      华夏科创50C 20000 亏500
      005561 创金合信红利低波 50000
      易方达裕祥 20000元 盈利1200
      050025 1.5万
      富国中证红利 20000 成本1.05 现价1.20
    自动正则提取 6 位代码或模糊匹配基金中文名、金额/份额、浮盈亏/成本，
    自动联网拉取今日最新净值折算份额，生成规范的持仓字典列表。
    """
    if not text or not str(text).strip():
        return []

    raw_text = str(text).strip()

    if "\n" in raw_text:
        raw_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    elif "；" in raw_text:
        raw_lines = [l.strip() for l in raw_text.split("；") if l.strip()]
    elif ";" in raw_text:
        raw_lines = [l.strip() for l in raw_text.split(";") if l.strip()]
    else:
        raw_lines = [raw_text]

    # 智能跨行块聚合 (Fund Block Aggregation)
    def _line_has_id(s: str) -> bool:
        if re.search(r'\b\d{6}\b', s):
            return True
        clean_s = re.sub(r'[\s\(\)（）:：¥元,，]', '', s)
        # 1. 优先使用 fuzzy_match_fund_by_name 或基金核心关键词判断是否为有效基金行 (防单行含'持有金额'字样被误杀)
        try:
            f_test = fuzzy_match_fund_by_name(clean_s)
            if f_test and f_test.get("score", 0) >= 0.45:
                return True
        except Exception:
            pass
        if any(w in clean_s for w in [
            "ETF", "联接", "混合", "债券", "指数", "基金", "价值", "成长", "回报",
            "精选", "优势", "红利", "低波", "蓝筹", "标普", "纳指", "白酒", "新能源", "芯片", "半导体", "黄金", "纯债"
        ]):
            return True

        # 2. 纯属性/表头行拦截
        if any(stop in clean_s for stop in ["持有金额", "持有收益", "昨日收益", "累计收益", "日收益", "持有天数", "持仓份额"]):
            return False
        return False

    def _line_has_val(s: str) -> bool:
        rem = re.sub(r'\b\d{6}\b', '', s)
        return bool(re.search(r'\d+', rem))

    aggregated_blocks = []
    cur_blk = []

    for l in raw_lines:
        if not cur_blk:
            cur_blk.append(l)
            continue
        cur_has_id = any(_line_has_id(x) for x in cur_blk)
        cur_has_val = any(_line_has_val(x) for x in cur_blk)
        l_has_id = _line_has_id(l)

        if cur_has_id and cur_has_val and l_has_id:
            aggregated_blocks.append(" ".join(cur_blk))
            cur_blk = [l]
        elif l_has_id and not _line_has_val(l) and cur_has_id and not cur_has_val:
            if any(re.search(r'\b\d{6}\b', x) for x in cur_blk) and re.search(r'\b\d{6}\b', l):
                aggregated_blocks.append(" ".join(cur_blk))
                cur_blk = [l]
            else:
                cur_blk.append(l)
        else:
            cur_blk.append(l)

    if cur_blk:
        aggregated_blocks.append(" ".join(cur_blk))

    lines = aggregated_blocks

    parsed_results = []
    combined_pool = {**CORE_STRATEGY_POOL, **EXTENDED_FUND_CATALOG}

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue

        fund_code = None
        fund_name = None
        share_class = None

        # 0. 优先前置使用正则剥离昨日收益/日收益及其数值，防止昨日收益数字被误当成基金代码或金额
        remain_line = re.sub(r'(?:昨日收益|昨日盈亏|日收益)[:：\s]*[+-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?', ' ', cleaned_line)
        remain_line = re.sub(r'(?:昨日收益|昨日盈亏|日收益)', ' ', remain_line)

        # 1. 优先提取 6 位基金代码
        code_match = re.search(r'\b(\d{6})\b', remain_line)
        if code_match:
            fund_code = code_match.group(1)
            remain_line = remain_line.replace(fund_code, " ")
        else:
            # 2. 直接调用 fuzzy_match_fund_by_name 进行模糊与别名精准匹配
            f_match = fuzzy_match_fund_by_name(remain_line)
            if f_match and f_match.get("score", 0) >= 0.45:
                fund_code = f_match["fund_code"]
                fund_name = f_match["fund_name"]
                share_class = f_match.get("share_class", "A")
                remain_line = remain_line.replace(fund_code, " ")
                if fund_name in remain_line:
                    remain_line = remain_line.replace(fund_name, " ")
                if f_match.get("raw_keyword"):
                    remain_line = remain_line.replace(f_match["raw_keyword"], " ")

            # 3. 若仍未匹配，分词搜索全量库（严格排除纯数字 w.isdigit() 且长度 >= 2）
            if not fund_code:
                words = [w for w in re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', remain_line) if not w.isdigit() and len(w) >= 2]
                for w in words:
                    matches = search_funds_in_catalog(w, limit=1)
                    if matches:
                        fund_code = matches[0]["fund_code"]
                        fund_name = matches[0]["fund_name"]
                        remain_line = remain_line.replace(w, " ")
                        break

        if not fund_code:
            continue

        meta = combined_pool.get(fund_code, {})
        if not fund_name:
            fund_name = meta.get("fund_name", f"基金_{fund_code}")
        if not share_class:
            share_class = meta.get("share_class", "C" if fund_code.endswith("3") or fund_code.endswith("7") or "C" in fund_name else "A")

        # 将已识别的中文名与大盘缩写从 remain_line 中清理，避免基金名中的数字（如科创50的50、中证A500的500）被误识别为金额
        if fund_name in remain_line:
            remain_line = remain_line.replace(fund_name, " ")
        # 宽基指数代码与持有期数字扩充词表 (长词优先，彻底阻断数字污染)
        for alias_kw in [
            "中证2000", "中证1000", "中证800", "中证500", "沪深300", "中证A500", "A500", "A50",
            "科创100", "科创50", "创业板50", "标普500", "富时100", "富时A50", "日经225", "纳斯达克100", "纳指100", "纳指",
            "红利低波100", "红利低波", "中证红利", "裕祥回报", "华安黄金", "黄金ETF", "白酒",
            "集成电路", "动漫游戏", "新能源", "半导体", "人工智能", "芯片", "恒生科技", "恒生指数",
            "30天持有", "60天持有", "90天持有", "180天持有", "360天持有", "365天持有",
            "1年持有", "2年持有", "3年持有", "6个月持有", "3个月持有", "12个月持有",
            "ETF联接", "ETF", "联接", "A类", "C类", "E类"
        ]:
            remain_line = remain_line.replace(alias_kw, " ")

        # ── 提前解析并剥离持有天数与锁定天数 (彻底杜绝持有期天数误充当持仓金额) ──
        h_days = 30
        lock_match = re.search(r'[\(（]?(?:锁定|持有|已持|持仓|买了|买入|历时)?\s*(\d+)\s*(?:天|日)(?:持有)?[\)）]?', remain_line)
        if lock_match:
            h_days = int(lock_match.group(1))
            remain_line = remain_line.replace(lock_match.group(0), " ")
        elif re.search(r'[\(（]?(\d+)\s*(?:个)?月(?:持有)?[\)）]?', remain_line):
            m_m = re.search(r'[\(（]?(\d+)\s*(?:个)?月(?:持有)?[\)）]?', remain_line)
            h_days = int(m_m.group(1)) * 30
            remain_line = remain_line.replace(m_m.group(0), " ")
        elif re.search(r'[\(（]?(\d+)\s*年(?:持有)?[\)）]?', remain_line):
            y_m = re.search(r'[\(（]?(\d+)\s*年(?:持有)?[\)）]?', remain_line)
            h_days = int(y_m.group(1)) * 365
            remain_line = remain_line.replace(y_m.group(0), " ")
        elif any(k in cleaned_line for k in ["已持满", "满30天", "免赎回费", "免赎"]):
            h_days = 45
        elif any(k in cleaned_line for k in ["刚买", "未满7天", "不满7天", "新买"]):
            h_days = 3

        amount = 0.0
        shares = 0.0
        floating_pnl = 0.0
        explicit_cost_nav = None
        explicit_curr_nav = None

        # 检查“万”单位
        wan_match = re.search(r'(\d+(?:\.\d+)?)\s*万', remain_line)
        if wan_match:
            amount = float(wan_match.group(1)) * 10000.0
            remain_line = remain_line.replace(wan_match.group(0), " ")

        # 过滤昨日收益等干扰项
        remain_line = re.sub(r'(?:昨日收益|昨日盈亏|日收益)[^\d+-]*[+-]?[0-9,.]*', ' ', remain_line)

        # 检查显式成本/净值
        cost_match = re.search(r'(?:成本|买入净值|成本价)[:：\s]*(\d+\.\d+)', remain_line)
        if cost_match:
            explicit_cost_nav = float(cost_match.group(1))
            remain_line = remain_line.replace(cost_match.group(0), " ")

        curr_match = re.search(r'(?:现价|最新净值|当前净值)[:：\s]*(\d+\.\d+)', remain_line)
        if curr_match:
            explicit_curr_nav = float(curr_match.group(1))
            remain_line = remain_line.replace(curr_match.group(0), " ")

        # 检查百分比收益率 (如: +8.5%, -12.3%, 收益率-8.5%)
        explicit_pnl_pct = None
        pct_match = re.search(r'([+-]?\d+(?:\.\d+)?)\s*%', remain_line)
        if pct_match:
            explicit_pnl_pct = float(pct_match.group(1))
            remain_line = remain_line.replace(pct_match.group(0), " ")

        # 优先提取带“持有金额/金额/市值/资产”的数字 (支持千分符逗号)
        amt_match = re.search(r'(?:持有金额|金额|市值|持有资产|资产)[:：\s]*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', remain_line)
        if amt_match:
            amount = float(amt_match.group(1).replace(',', ''))
            remain_line = remain_line.replace(amt_match.group(0), " ")

        # 检查浮盈亏金额 (排除“收益率/盈利率/亏损率”，支持千分符逗号)
        loss_match = re.search(r'(?:亏损(?!率)|浮亏|亏|损|跌)[:：\s]*([+-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', remain_line)
        if loss_match:
            loss_val = abs(float(loss_match.group(1).replace(',', '')))
            floating_pnl = -loss_val
            remain_line = remain_line.replace(loss_match.group(0), " ")
        else:
            gain_match = re.search(r'(?:持有收益(?!率)|累计收益(?!率)|收益(?!率)|盈利(?!率)|浮盈|赚|盈|涨)[:：\s]*([+-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', remain_line)
            if gain_match:
                gain_val = float(gain_match.group(1).replace(',', ''))
                floating_pnl = gain_val
                remain_line = remain_line.replace(gain_match.group(0), " ")

        # 检查份额
        shares_match = re.search(r'([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:份|股)', remain_line)
        if shares_match:
            shares = float(shares_match.group(1).replace(',', ''))
            remain_line = remain_line.replace(shares_match.group(0), " ")

        # 显式优先匹配带“元”或“¥”的金额数字 (如 15,200.00元, 35000元)
        if amount <= 0:
            yuan_match = re.search(r'(?:¥|￥)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*元', remain_line)
            if yuan_match:
                amount = float(yuan_match.group(1).replace(',', ''))
                remain_line = remain_line.replace(yuan_match.group(0), " ")

        # 检查金额数字：提取剩余所有数字并取首个合理金额 (杜绝 >=100 过滤以精准识别百元以下尾仓零头)
        if amount <= 0:
            remaining_numbers = re.findall(r'([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', remain_line)
            valid_nums = []
            for n_s in remaining_numbers:
                try:
                    val = float(n_s.replace(',', ''))
                    if val > 0:
                        valid_nums.append(val)
                except Exception:
                    pass
            if valid_nums:
                amount = valid_nums[0]

        # 获取最新参考净值
        if explicit_curr_nav and explicit_curr_nav > 0:
            current_nav = explicit_curr_nav
        else:
            try:
                q = fetch_realtime_fund_quote(fund_code)
                current_nav = q.dwjz if (q and q.dwjz > 0) else 1.0000
            except Exception:
                current_nav = 1.0000

        if amount > 0 and shares <= 0:
            shares = round(amount / current_nav, 4)
        elif shares > 0 and amount <= 0:
            amount = round(shares * current_nav, 2)
        elif amount <= 0 and shares <= 0:
            amount = 10000.0
            shares = round(amount / current_nav, 4)

        market_value = round(amount, 2)

        if explicit_cost_nav and explicit_cost_nav > 0:
            cost_price = explicit_cost_nav
            cost_basis = round(shares * cost_price, 2)
            floating_pnl = round(market_value - cost_basis, 2)
            pnl_pct = round((market_value / cost_basis - 1.0) * 100.0, 2) if cost_basis > 0 else 0.0
        elif explicit_pnl_pct is not None and abs(floating_pnl) < 1e-4:
            pnl_pct = explicit_pnl_pct
            cost_price = round(current_nav / (1.0 + pnl_pct / 100.0), 4) if (1.0 + pnl_pct / 100.0) > 0 else current_nav
            cost_basis = round(shares * cost_price, 2)
            floating_pnl = round(market_value - cost_basis, 2)
        else:
            cost_basis = round(max(0.01, market_value - floating_pnl), 2)
            cost_price = round(cost_basis / shares, 4) if shares > 0 else current_nav
            pnl_pct = round((market_value / cost_basis - 1.0) * 100.0, 2) if cost_basis > 0 else 0.0

        if h_days < 7:
            h_tag = "<7d"
        elif h_days < 30:
            h_tag = "7-29d"
        else:
            h_tag = ">=30d"

        parsed_results.append({
            "fund_code": fund_code,
            "fund_name": fund_name,
            "share_class": share_class,
            "amount": market_value,
            "shares": shares,
            "cost_nav": cost_price,
            "current_nav": current_nav,
            "market_value": market_value,
            "cost_price": cost_price,
            "cost_basis": cost_basis,
            "pnl": floating_pnl,
            "floating_pnl": floating_pnl,
            "floating_pnl_pct": pnl_pct,
            "holding_days": h_days,
            "holding_tag": h_tag,
            "dividend_method": "cash" if share_class == "A" else "reinvest",
            "raw_line": cleaned_line
        })

    # 双通道单标的去重保护：按 fund_code 顺序去重
    seen_dedup = set()
    clean_dedup_results = []
    for item in parsed_results:
        fc = item.get("fund_code")
        if fc and fc not in seen_dedup:
            seen_dedup.add(fc)
            clean_dedup_results.append(item)
    return clean_dedup_results


parse_batch_fund_text_input = parse_smart_text_holdings


# =====================================================================
# 手机长截图高清无损切片 OCR 导入与全市场模糊匹配引擎 (G15 Phase 3)
# =====================================================================

_GLOBAL_CATALOG_DATA: Optional[List[Tuple[str, str, str]]] = None

def _load_fund_catalog_data() -> List[Tuple[str, str, str]]:
    """加载 28,177 基金大字典到内存单例"""
    global _GLOBAL_CATALOG_DATA
    if _GLOBAL_CATALOG_DATA is not None:
        return _GLOBAL_CATALOG_DATA

    cat_file = WORKSPACE_ROOT / "data" / "master" / "fund_catalog.parquet"
    res = []
    if cat_file.exists():
        try:
            df = pd.read_parquet(cat_file)
            for _, r in df.iterrows():
                sym = str(r['symbol']).strip().zfill(6)
                name = str(r['fund_name']).strip()
                pinyin = str(r.get('pinyin_abbr', '')).strip()
                res.append((sym, name, pinyin))
        except Exception:
            pass
    _GLOBAL_CATALOG_DATA = res
    return _GLOBAL_CATALOG_DATA


def slice_long_screenshot_for_ocr(
    image_bytes: bytes,
    target_height: int = 1000,
    overlap: int = 150
) -> List[Tuple[Any, int]]:
    """
    手机持仓长截图自适应无损横向切片算法：
    - 保持原始图片 100% 原始宽度不压缩；
    - 纵向按 target_height (默认 1000px)、上下重叠 overlap (默认 150px) 自动切分子图；
    - 返回 [(slice_image_PIL, y_offset), ...]
    """
    from PIL import Image
    import io

    if not image_bytes:
        return []

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return []

    if img.mode != 'RGB':
        img = img.convert('RGB')

    w, h = img.size
    if h <= target_height:
        return [(img, 0)]

    step = target_height - overlap
    if step <= 0:
        step = max(1, target_height // 2)

    slices = []
    cur_y = 0
    while cur_y < h:
        end_y = min(cur_y + target_height, h)
        cropped = img.crop((0, cur_y, w, end_y))
        slices.append((cropped, cur_y))
        if end_y >= h:
            break
        cur_y += step

    return slices


def fuzzy_match_fund_by_name(
    raw_name: str,
    preferred_share_class: Optional[str] = None,
    yesterday_return: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    全市场基金名称模糊匹配器：
    1. 去除省略号（..., … 等）与符号噪点；
    2. 提取并保留 A/C 份额特征；
    3. 优先匹配 6 位代码与经典核心/扩展字典；
    4. 本地 28,177 基金字典多级加权相似度匹配；
    5. 支持「名称关键字 + 昨日收益率（容差 ≤ 0.3%）」双因子交叉锁定。
    返回: {"fund_code": "005561", "fund_name": "...", "share_class": "A", "score": 1.0, "cross_check_verified": True}
    """
    if not raw_name or not str(raw_name).strip():
        return {}
    raw_str = str(raw_name).strip()

    # 1. 优先提取 6 位基金代码
    code_m = re.search(r'\b(\d{6})\b', raw_str)
    if code_m:
        c = code_m.group(1)
        # 查核心池与扩展库
        if c in CORE_STRATEGY_POOL:
            m = CORE_STRATEGY_POOL[c]
            return {
                "fund_code": c,
                "fund_name": m.get("fund_name", f"基金_{c}"),
                "share_class": preferred_share_class or m.get("share_class", "C" if c.endswith("3") or c.endswith("7") else "A"),
                "score": 1.0
            }
        cat_list = _load_fund_catalog_data()
        for sym, name, _ in cat_list:
            if sym == c:
                s_cls = preferred_share_class or ("C" if name.endswith("C") or sym.endswith("3") or sym.endswith("7") else "A")
                return {"fund_code": sym, "fund_name": name, "share_class": s_cls, "score": 1.0}

    # 2. 提取份额特征
    share_class = preferred_share_class
    if not share_class:
        if re.search(r'[CcCc]\b|[Cc]类', raw_str):
            share_class = "C"
        elif re.search(r'[AaAa]\b|[Aa]类', raw_str):
            share_class = "A"

    # 3. 去除省略号及标点
    clean_name = re.sub(r'[\.]{2,}|…|，|,|【|】|\[|\]|\(|\)|（|）|/|、', ' ', raw_str).strip()

    # 4. 29 只实战存量及核心策略池精准别名优先映射
    ALIAS_MAP = {
        "红利低波": "005561", "创金合信红利低波": "005561", "创金合信中证红利低波": "005561", "创金合信中证红利": "005561",
        "创金合信": "005561" if share_class != "C" else "005562", "创金合信红利": "005561" if share_class != "C" else "005562",
        "华泰柏瑞中证红利低波": "007467" if share_class == "C" else "007466", "华泰柏瑞红利低波": "007467" if share_class == "C" else "007466",
        "华泰柏瑞低波": "007467" if share_class == "C" else "007466", "华泰低波": "007467" if share_class == "C" else "007466", "低波": "005561",
        "沪深300": "110020" if share_class != "C" else "007339", "易方达沪深300": "110020" if share_class != "C" else "007339",
        "易方达300": "007339" if share_class == "C" else "110020", "300C": "007339",
        "广发纳斯达克100ETF联接": "006479" if share_class == "C" else "006075", "广发纳斯达克100": "006479" if share_class == "C" else "006075", "广发纳指": "006479" if share_class == "C" else "006075",
        "纳斯达克100": "017436", "华安纳斯达克100": "017436", "纳指": "017436", "纳斯达克": "017436",
        "裕祥回报": "002351" if share_class != "C" else "002352", "易方达裕祥": "002351" if share_class != "C" else "002352",
        "纯债": "002351" if share_class != "C" else "002352", "裕祥": "002351" if share_class != "C" else "002352",
        "富国中证红利": "100032" if share_class != "C" else "008682", "富国红利增强": "100032" if share_class != "C" else "008682",
        "富国红利": "100032" if share_class != "C" else "008682", "中证红利": "100032" if share_class != "C" else "008682",
        "科创50": "011613" if share_class == "C" else "011612", "华夏科创50": "011613" if share_class == "C" else "011612",
        "华夏上证科创板50": "011613" if share_class == "C" else "011612", "科创板50": "011613" if share_class == "C" else "011612",
        "博时黄金ETF联接": "002611" if share_class == "C" else "002610", "博时黄金ETF": "002611" if share_class == "C" else "002610", "博时黄金": "002611" if share_class == "C" else "002610",
        "华安黄金": "000216" if share_class != "C" else "000217", "黄金ETF联接": "000216" if share_class != "C" else "000217",
        "黄金ETF": "000216" if share_class != "C" else "000217", "黄金": "000216" if share_class != "C" else "000217",
        "招商中证白酒": "161725", "招商白酒": "161725", "中证白酒": "161725", "白酒": "161725",
        "易方达蓝筹": "005827", "蓝筹精选": "005827", "易方达蓝筹精选": "005827", "蓝筹": "005827",
        "银华集成电路": "013841" if share_class == "C" else "013840", "集成电路混合": "013841" if share_class == "C" else "013840",
        "集成电路": "013841" if share_class == "C" else "013840", "半导体": "013841" if share_class == "C" else "013840",
        "富国中证1000": "016634" if share_class == "C" else "016633", "1000C": "016634", "富国1000": "016634" if share_class == "C" else "016633",
        "华夏中证500": "001053" if share_class == "C" else "001052", "500C": "001053", "华夏500": "001053" if share_class == "C" else "001052",
        "博时标普500": "050025", "标普500ETF联接": "050025", "标普500": "050025", "博时标普": "050025", "标普": "050025",
        "华夏中证红利质量": "016441" if share_class == "C" else "016440", "红利质量": "016441" if share_class == "C" else "016440",
        "南方中证新能源": "012832" if share_class == "C" else "012831",
        "华夏中证动漫游戏": "012769" if share_class == "C" else "012768", "动漫游戏": "012769" if share_class == "C" else "012768",
        "富国周期优势": "019260",
        "华夏中小企业100ETF联接": "006163" if share_class == "C" else "000058", "华夏中小板ETF联接": "006163" if share_class == "C" else "000058", "华夏中小板": "006163" if share_class == "C" else "000058",
        "工银信用纯债": "002352" if share_class == "C" else "000086", "工银纯债": "002352" if share_class == "C" else "000086",
        "招商中证红利ETF联接": "012644" if share_class == "C" else "012643", "招商中证红利": "012644" if share_class == "C" else "012643", "招商红利": "012644" if share_class == "C" else "012643",
        "睿远稳益增强": "018757" if share_class == "C" else "018756", "稳益增强": "018757" if share_class == "C" else "018756",
        "摩根标普500": "001071", "摩根标普": "001071",
        "汇添富中证红利低波": "006113", "汇添富红利低波": "006113",
        "广发中证500": "004854",
        "华安安顺": "001595",
        "天弘中证500": "001551",
        "天弘国证生物医药": "011041" if share_class == "C" else "011040", "天弘中证医药": "011041" if share_class == "C" else "011040"
    }

    # 按别名长度降序优先匹配
    for k in sorted(ALIAS_MAP.keys(), key=len, reverse=True):
        if k in clean_name:
            code = ALIAS_MAP[k]
            fn = CORE_STRATEGY_POOL.get(code, {}).get("fund_name") or EXTENDED_FUND_CATALOG.get(code, {}).get("fund_name")
            if not fn:
                for sym, n, _ in _load_fund_catalog_data():
                    if sym == code:
                        fn = n
                        break
            if not fn:
                fn = f"{k}{share_class or ''}"
            s_cls = share_class or ("C" if "C" in fn or code.endswith("3") or code.endswith("7") else "A")
            ret_dict = {"fund_code": code, "fund_name": fn, "share_class": s_cls, "score": 0.95, "raw_keyword": k}
            if yesterday_return is not None:
                try:
                    q = fetch_realtime_fund_quote(code)
                    cand_ret = (float(q.gszzl) / 100.0) if (q and hasattr(q, "gszzl") and q.gszzl is not None) else None
                    if cand_ret is not None and abs(cand_ret - yesterday_return) <= 0.003:
                        ret_dict["cross_check_verified"] = True
                        ret_dict["yesterday_return_diff"] = round(abs(cand_ret - yesterday_return), 4)
                except Exception:
                    pass
            return ret_dict

    # 5. 全量 28,177 基金字典模糊匹配
    import difflib
    cat_list = _load_fund_catalog_data()
    if not cat_list:
        return {}

    bigrams = [clean_name[i:i+2] for i in range(len(clean_name)-1) if len(clean_name[i:i+2].strip()) == 2]

    candidates = []
    if bigrams:
        for sym, name, pinyin in cat_list:
            if any(bg in name for bg in bigrams):
                candidates.append((sym, name, pinyin))
    if not candidates:
        candidates = cat_list

    # 双因子交叉验真：若传入了昨日收益率 (yesterday_return)，针对候选标的交叉核对
    if yesterday_return is not None and candidates:
        top_candidates = []
        for sym, name, pinyin in candidates:
            name_class = "C" if name.endswith("C") or sym.endswith("3") or sym.endswith("7") else "A"
            class_bonus = 0.05 if (share_class and name_class == share_class) else 0.0
            score = difflib.SequenceMatcher(None, clean_name, name).ratio() + class_bonus
            if score >= 0.28:
                top_candidates.append((score, sym, name, name_class))
        top_candidates.sort(key=lambda x: x[0], reverse=True)

        for base_sc, sym, name, s_cls in top_candidates[:15]:
            try:
                q = fetch_realtime_fund_quote(sym)
                cand_ret = (float(q.gszzl) / 100.0) if (q and hasattr(q, "gszzl") and q.gszzl is not None) else None
            except Exception:
                cand_ret = None
            if cand_ret is not None:
                diff = abs(cand_ret - yesterday_return)
                if diff <= 0.003:  # 0.3% 容差交叉锁定
                    return {
                        "fund_code": sym,
                        "fund_name": name,
                        "share_class": share_class or s_cls,
                        "score": round(min(1.0, base_sc + 0.35), 2),
                        "cross_check_verified": True,
                        "yesterday_return_diff": round(diff, 4)
                    }

    best_match = None
    best_score = 0.0

    for sym, name, pinyin in candidates:
        name_class = "C" if name.endswith("C") or sym.endswith("3") or sym.endswith("7") else "A"
        class_bonus = 0.05 if (share_class and name_class == share_class) else 0.0
        score = difflib.SequenceMatcher(None, clean_name, name).ratio() + class_bonus
        if score > best_score:
            best_score = score
            best_match = (sym, name, name_class)

    if best_match and best_score >= 0.45:
        sym, name, s_cls = best_match
        return {
            "fund_code": sym,
            "fund_name": name,
            "share_class": share_class or s_cls,
            "score": round(best_score, 2),
            "cross_check_verified": False,
            "is_questionable": (best_score < 0.70)
        }

    return {}


def parse_screenshot_ocr_holdings(image_bytes: bytes) -> List[Dict[str, Any]]:
    """
    通过手机持仓长截图高清切片与 RapidOCR 提取结构化持仓：
    1. slice_long_screenshot_for_ocr 100% 原始宽度切片 (高度1000px, 重叠150px)；
    2. rapidocr_onnxruntime 执行纯本地离线 OCR；
    3. 全局 y 坐标对齐与去重聚合；
    4. 提取基金名称、持有金额、昨日收益、持有收益；
    5. 严格遵守会计恒等式：
       投入成本 (cost_basis) = 持有金额 (market_value) - 持有收益 (floating_pnl)
       持仓份额 (shares) = 持有金额 (market_value) / 最新净值 (current_nav)
       保留浮动盈亏原始正负号 (NO abs() 截断)；
    6. 百元以下尾仓完整保留 (无 >=100 过滤硬约束)。
    """
    if not image_bytes:
        return []
    slices = slice_long_screenshot_for_ocr(image_bytes, target_height=1000, overlap=150)
    if not slices:
        return []

    try:
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np
        ocr = RapidOCR()
    except Exception:
        return []

    all_ocr_items = []
    for slice_img, y_offset in slices:
        try:
            np_img = np.array(slice_img)
            ocr_res, _ = ocr(np_img)
            if not ocr_res:
                continue
            for box, text, conf in ocr_res:
                t = str(text).strip()
                if not t:
                    continue
                box_y = min(p[1] for p in box) + y_offset
                box_x = min(p[0] for p in box)
                all_ocr_items.append((box_y, box_x, t, float(conf)))
        except Exception:
            continue

    if not all_ocr_items:
        return []

    # 按纵向全局 y 坐标排序
    all_ocr_items.sort(key=lambda x: x[0])

    # 1. 通道一：以聚合成的完整多行文本直接送入 parse_smart_text_holdings 提取
    # 先将同一水平线 (abs(y1 - y2) <= 18px) 的左右多列 OCR 文本框按 x 坐标从左到右合并为同行
    merged_rows = []
    for y, x, text, conf in all_ocr_items:
        if merged_rows and abs(y - merged_rows[-1][0]) <= 18:
            prev_y, prev_x, prev_items, prev_confs = merged_rows[-1]
            prev_items.append((x, text))
            prev_confs.append(conf)
            merged_rows[-1] = ((prev_y + y) / 2.0, min(prev_x, x), prev_items, prev_confs)
        else:
            merged_rows.append((y, x, [(x, text)], [conf]))

    normalized_ocr_rows = []
    for r_y, r_x, r_items, r_confs in merged_rows:
        r_items.sort(key=lambda it: it[0])
        row_str = " ".join(it[1] for it in r_items)
        avg_c = sum(r_confs) / max(len(r_confs), 1)
        normalized_ocr_rows.append((r_y, r_x, row_str, avg_c))

    raw_lines = [item[2] for item in normalized_ocr_rows]
    aggregated_text = "\n".join(raw_lines)
    channel1_holdings = parse_smart_text_holdings(aggregated_text)

    # 2. 通道二：空间块聚类提取分支（基于合并后的视觉行 normalized_ocr_rows，绝不早退）
    blocks = []
    current_block = []
    for y, x, text, conf in normalized_ocr_rows:
        title_probe = re.sub(r'[+-]?\d+(?:,\d{3})*(?:\.\d+)?%?', ' ', text).strip()
        m = fuzzy_match_fund_by_name(title_probe if len(title_probe) >= 3 else text)
        is_header = (m.get("score", 0) >= 0.62 or bool(re.search(r'\b\d{6}\b', text)))
        if is_header and current_block:
            blocks.append(current_block)
            current_block = [(y, x, text, conf, m)]
        else:
            current_block.append((y, x, text, conf, m))
    if current_block:
        blocks.append(current_block)

    structured_holdings = []
    seen_codes = set()
    for blk in blocks:
        if not blk:
            continue
        blk_text = " ".join([b[2] for b in blk])

        # 提取昨日收益与持有金额，用于推导昨日收益率
        yesterday_pnl_val = 0.0
        y_pnl_m = re.search(r'(?:昨日收益|昨日盈亏|日收益)[:：\s]*([+-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', blk_text)
        if y_pnl_m:
            yesterday_pnl_val = float(y_pnl_m.group(1).replace(',', ''))

        pnl_val = 0.0
        mv_val = 0.0

        pnl_m = re.search(r'(?:持有收益|累计收益|收益|浮动盈亏)[:：\s]*([+-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', blk_text)
        if pnl_m:
            pnl_val = float(pnl_m.group(1).replace(',', ''))
        else:
            loss_m = re.search(r'(?:亏损|浮亏|亏)[:：\s]*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', blk_text)
            if loss_m:
                pnl_val = -abs(float(loss_m.group(1).replace(',', '')))

        amt_m = re.search(r'(?:持有金额|金额|市值|资产)[:：\s]*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', blk_text)
        if amt_m:
            mv_val = float(amt_m.group(1).replace(',', ''))
        else:
            nums = re.findall(r'([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', blk_text)
            valid_floats = []
            for n_s in nums:
                try:
                    val_f = float(n_s.replace(',', ''))
                    if val_f > 0:
                        valid_floats.append(val_f)
                except Exception:
                    pass
            if valid_floats:
                mv_val = valid_floats[0]

        yesterday_ret = None
        if yesterday_pnl_val != 0.0 and (mv_val - yesterday_pnl_val) > 0.01:
            yesterday_ret = yesterday_pnl_val / (mv_val - yesterday_pnl_val)

        f_info = {}
        for b in blk:
            if b[4] and b[4].get("fund_code"):
                f_info = b[4]
                break
        if not f_info:
            f_info = fuzzy_match_fund_by_name(blk_text, yesterday_return=yesterday_ret)

        fc = f_info.get("fund_code")
        if not fc or fc in seen_codes:
            continue

        fn = f_info.get("fund_name", f"基金_{fc}")
        s_cls = f_info.get("share_class", "A")

        if mv_val <= 0:
            continue

        cost_basis = round(max(0.01, mv_val - pnl_val), 2)
        pnl_pct = round((mv_val / cost_basis - 1.0) * 100.0, 2) if cost_basis > 0 else 0.0

        try:
            q = fetch_realtime_fund_quote(fc)
            cur_nav = float(q.dwjz if (q and q.dwjz > 0) else 1.0)
        except Exception:
            cur_nav = 1.0

        sh = round(mv_val / cur_nav, 4) if cur_nav > 0 else mv_val
        cp = round(cost_basis / sh, 4) if sh > 0 else cur_nav

        seen_codes.add(fc)
        structured_holdings.append({
            "fund_code": fc,
            "fund_name": fn,
            "raw_name": str(f_info.get("raw_name") or blk_text[:20]),
            "match_score": round(float(f_info.get("score", 1.0)), 2),
            "share_class": s_cls,
            "shares": sh,
            "cost_price": cp,
            "current_nav": cur_nav,
            "market_value": round(mv_val, 2),
            "cost_basis": cost_basis,
            "floating_pnl": round(pnl_val, 2),
            "floating_pnl_pct": pnl_pct,
            "yesterday_pnl": round(yesterday_pnl_val, 2),
            "yesterday_return": round(yesterday_ret, 4) if yesterday_ret is not None else None,
            "cross_check_verified": bool(f_info.get("cross_check_verified", False)),
            "is_questionable": bool(f_info.get("is_questionable", False)),
            "holding_days": 400,
            "holding_tag": ">=30d",
            "dividend_method": "cash" if s_cls == "A" else "reinvest",
            "raw_line": blk_text
        })

    # 3. ── 双通道并集融合与信息补全 (Dual-Channel Union Fusion) ──
    # 以 fund_code 为主键合并两路通道，互补空间块字段与文本流字段
    fused_map: Dict[str, Dict[str, Any]] = {}
    for h in channel1_holdings:
        code = h.get("fund_code")
        if code:
            # 修复持有天数覆盖 Bug: 通道一在截图未写出持有天数时默认赋值 30 天，
            # 但存量长跑组合应默认 400 天（满 1 年），除非原始文本明确含有短期标识
            if h.get("holding_days") == 30 and not any(k in str(h.get("raw_line", "")) for k in ["天", "日", "月", "刚买"]):
                h["holding_days"] = 400
                h["holding_tag"] = ">=30d"
            fused_map[code] = dict(h)

    for h in structured_holdings:
        code = h.get("fund_code")
        if not code:
            continue
        if code not in fused_map:
            fused_map[code] = dict(h)
        else:
            # 融合：优先保留或增强空间块特有的昨日收益、收益率、校验标记
            existing = fused_map[code]
            for k, v in h.items():
                if k not in existing or existing[k] is None or (existing[k] == 0.0 and v not in (0.0, None)):
                    existing[k] = v
                elif k in ("yesterday_pnl", "yesterday_return", "cross_check_verified") and v is not None:
                    existing[k] = v

    return list(fused_map.values())


parse_long_screenshot_holdings = parse_screenshot_ocr_holdings

