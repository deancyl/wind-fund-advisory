import re
import difflib
import pandas as pd
from pathlib import Path

cat_file = Path("data/master/fund_catalog.parquet")
if cat_file.exists():
    df_cat = pd.read_parquet(cat_file)
else:
    df_cat = pd.DataFrame()

# Prebuild search index
catalog_list = []
for _, row in df_cat.iterrows():
    sym = str(row['symbol'])
    name = str(row['fund_name'])
    pinyin = str(row.get('pinyin_abbr', ''))
    catalog_list.append((sym, name, pinyin))

def fuzzy_match_fund_by_name(raw_name: str, preferred_share_class: str = None) -> dict:
    """
    模糊匹配基金名称到 6 位代码：
    1. 去除省略号（..., … 等）与标点
    2. 提取并保留 A/C 份额特征
    3. 核心关键字提取与多级匹配 (精确包含 > 编辑距离最长公共子序列)
    """
    if not raw_name:
        return {}
    
    clean_name = re.sub(r'[\.]{2,}|…|，|,|【|】|\[|\]|\(|\)|（|）', ' ', raw_name).strip()
    
    # 提取份额类别
    share_class = preferred_share_class
    if not share_class:
        if re.search(r'[CcCc]\b|[Cc]类', raw_name):
            share_class = "C"
        elif re.search(r'[AaAa]\b|[Aa]类', raw_name):
            share_class = "A"
            
    # 优先检查 6 位代码
    code_m = re.search(r'\b(\d{6})\b', raw_name)
    if code_m:
        c = code_m.group(1)
        for sym, name, _ in catalog_list:
            if sym == c:
                return {"fund_code": sym, "fund_name": name, "share_class": share_class or ("C" if "C" in name else "A"), "score": 1.0}

    # 别名映射
    ALIAS = {
        "红利低波": "005561", "创金合信红利低波": "005561", "创金合信中证红利低波": "005561",
        "沪深300": "110020" if share_class == "A" else "007339", "易方达沪深300": "110020",
        "纳斯达克100": "017436", "华安纳斯达克100": "017436", "纳指": "017436",
        "裕祥回报": "002351" if share_class != "C" else "002352", "易方达裕祥": "002351",
        "富国中证红利": "100032" if share_class != "C" else "008682", "富国红利增强": "100032",
        "科创50": "011612" if share_class == "A" else "011613", "华夏科创50": "011613" if share_class == "C" else "011612",
        "华夏上证科创板50": "011613" if share_class == "C" else "011612",
        "华安黄金": "000216" if share_class != "C" else "000217", "黄金ETF联接": "000216",
        "招商白酒": "161725", "白酒": "161725",
        "易方达蓝筹": "005827", "蓝筹精选": "005827",
        "银华集成电路": "013841", "集成电路": "013841"
    }
    
    # 检查别名
    for k, code in ALIAS.items():
        if k in clean_name:
            # 找到对应全称
            m_name = next((n for s, n, _ in catalog_list if s == code), k)
            return {"fund_code": code, "fund_name": m_name, "share_class": share_class or ("C" if "C" in m_name else "A"), "score": 0.95}

    # 去除常见类型后缀做核心词检索
    core_kw = re.sub(r'(?:ETF|联接|指数|混合|发起式|分级|增强|A类|C类|[ACac])', '', clean_name).strip()
    words = [w for w in re.split(r'\s+', core_kw) if len(w) >= 2]
    
    best_match = None
    best_score = 0.0
    
    for sym, name, pinyin in catalog_list:
        # 如果指定了份额类别，优先匹配同类份额
        if share_class:
            name_class = "C" if name.endswith("C") or sym.endswith("3") or sym.endswith("7") else "A"
            class_bonus = 0.05 if name_class == share_class else -0.05
        else:
            class_bonus = 0.0
            
        score = difflib.SequenceMatcher(None, clean_name, name).ratio() + class_bonus
        if score > best_score:
            best_score = score
            best_match = (sym, name)
            
    if best_match and best_score >= 0.5:
        sym, name = best_match
        s_cls = "C" if name.endswith("C") or sym.endswith("3") or sym.endswith("7") else "A"
        return {"fund_code": sym, "fund_name": name, "share_class": share_class or s_cls, "score": best_score}
        
    return {}

test_cases = [
    ("创金合信中证红利...", "A"),
    ("易方达沪深300ETF联接...", "A"),
    ("华安纳斯达克100ETF...", "A"),
    ("易方达裕祥回报债券A", "A"),
    ("富国中证红利指数增强A", "A"),
    ("华夏上证科创板50成份ETF联接C", "C"),
    ("招商中证白酒指数(LOF)A", "A"),
    ("华安黄金ETF联接C", "C"),
    ("银华集成电路混合C", "C"),
    ("富国中证1000ETF联接C", "C"),
    ("华夏中证500ETF联接C", "C"),
]

print("Testing fuzzy matching on sample test cases:")
for tc, sc in test_cases:
    res = fuzzy_match_fund_by_name(tc, preferred_share_class=sc)
    print(f"Input: {tc:30s} -> Matched: {res.get('fund_code')} {res.get('fund_name')} (score: {res.get('score', 0):.2f})")
