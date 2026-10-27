"""
Wind 投顾自选标的与工作台配置探索器 (UserWatchlistParser):
从当前登录的 Wind 投顾终端用户目录 (users/W36989091984) 中无感、安全地提取：
1. 最近调阅与高频盯盘标的 (latestvisit.hqv)
2. 智能检索与自选历史流 (smart_history.txt)
3. 机构与投资关注热词 (hotword_history2.txt)
4. 工作台激活标签页与历史调阅指令 (windtabsex1.xml)
5. BBQ 债券报价与监控配置 (BBQ/5ZBMW.ini)
6. 商品、期指与国债期货监控分类 (CmdtyQuotesSet.xml)
7. 自选技术指标与画线配置 (userline/ Mark files)
8. 终端核心个性化首选项 (UserConfig.ini)
全量数据标准化为 DataFrame 并支持一键增量沉淀至本地数据湖 (data/master/user_watchlist.parquet)。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import configparser
import re
import xml.etree.ElementTree as ET
import pandas as pd

from ..config import WIND_CONFIG
from ..parsers.master_dict_parser import MasterDictParser
from ..storage.lakehouse import LakehouseManager


@dataclass
class WatchlistItem:
    symbol: str
    name: str
    source: str          # latestvisit, smart_history, userline, tab
    asset_class: str     # stock, fund, index, bond, commodity, other
    market: str          # SH, SZ, CSI, WI, GI, CFE, etc.
    extra_info: str = ""
    updated_at: str = ""


class UserWatchlistParser:
    """Wind 终端用户自选资产与工作台配置解析引擎 (只读安全隔离)"""

    def __init__(
        self,
        users_dir: Optional[Union[str, Path]] = None,
        lakehouse: Optional[LakehouseManager] = None,
        master_dict: Optional[MasterDictParser] = None
    ):
        self.users_dir = Path(users_dir) if users_dir else WIND_CONFIG.users_dir
        self.lakehouse = lakehouse or LakehouseManager()
        self.master_dict = master_dict or MasterDictParser()

    def _get_active_user_dir(self) -> Optional[Path]:
        """定位当前登录投顾的主配置目录"""
        if not self.users_dir.exists():
            return None
        
        # 优先读取 user.config 中当前登录用户名对应的目录或寻找第一个 W 开头的用户目录
        current_user = WIND_CONFIG.current_user
        if current_user:
            target = self.users_dir / current_user
            if target.is_dir():
                return target

        # 候选用户目录遍历 (如 W36989091984)
        user_subdirs = [p for p in self.users_dir.iterdir() if p.is_dir() and p.name.startswith("W")]
        if user_subdirs:
            # 按最后修改时间排序，取最近活跃者
            user_subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return user_subdirs[0]

        return None

    def get_latest_visited_symbols(self) -> List[str]:
        """提取最近调阅标的代码列表 (latestvisit.hqv)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return []

        hq_file = user_dir / "latestvisit.hqv"
        if not hq_file.exists():
            return []

        try:
            content = hq_file.read_text(encoding="gbk", errors="ignore").strip()
            if not content:
                return []
            symbols = [s.strip() for s in content.split(",") if s.strip()]
            return symbols
        except Exception:
            return []

    def get_smart_search_history(self) -> List[Dict[str, str]]:
        """提取自选检索与智能输入流历史 (smart_history.txt)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return []

        hist_file = user_dir / "smart_history.txt"
        if not hist_file.exists():
            return []

        results = []
        try:
            content = hist_file.read_text(encoding="gbk", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                # 典型格式: M|!||!||!|931468.CSI|!|红利质量|!||!|9|20|0|...
                parts = [p.strip() for p in line.split("|!|") if p.strip()]
                code = ""
                name = ""
                for i, p in enumerate(parts):
                    if re.match(r"^[A-Za-z0-9\._]{4,15}$", p) and ("." in p or p.isdigit()):
                        code = p
                        if i + 1 < len(parts):
                            name = parts[i + 1]
                        break
                if code:
                    results.append({
                        "symbol": code,
                        "name": name,
                        "source": "smart_history"
                    })
        except Exception:
            pass
        return results

    def get_hotwords(self) -> List[str]:
        """提取用户关注热词与机构账户 (hotword_history2.txt)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return []

        hw_file = user_dir / "hotword_history2.txt"
        if not hw_file.exists():
            return []

        try:
            content = hw_file.read_text(encoding="gbk", errors="ignore")
            return [line.strip() for line in content.splitlines() if line.strip()]
        except Exception:
            return []

    def get_workbench_tabs(self) -> List[Dict[str, Any]]:
        """提取工作台标签页与历史调阅指令 (windtabsex1.xml)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return []

        tab_file = user_dir / "windtabsex1.xml"
        if not tab_file.exists():
            return []

        tabs = []
        try:
            tree = ET.parse(tab_file)
            root = tree.getroot()
            for tab in root.findall(".//tab"):
                caption = tab.attrib.get("caption", "").strip()
                cmd = tab.attrib.get("cmd", "")
                tab_id = tab.attrib.get("tabid", "")
                closetime = tab.attrib.get("closetime", "")
                param = tab.findtext("param") or ""
                
                close_dt = ""
                if closetime and closetime.isdigit():
                    try:
                        close_dt = datetime.fromtimestamp(int(closetime)).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass

                tabs.append({
                    "tab_id": tab_id,
                    "caption": caption,
                    "command_code": cmd,
                    "close_time": close_dt,
                    "param": param[:150]
                })
        except Exception:
            pass
        return tabs

    def get_bbq_schemes(self) -> Dict[str, Any]:
        """提取 BBQ (Best Bid & Quote) 债券报价方案与自选配置 (5ZBMW.ini)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return {}

        ini_path = user_dir / "BBQ" / "5ZBMW.ini"
        if not ini_path.exists():
            return {}

        cfg = configparser.ConfigParser()
        try:
            cfg.read(ini_path, encoding="gbk")
            schemes = {}
            for sec in cfg.sections():
                schemes[sec] = dict(cfg.items(sec))
            return schemes
        except Exception:
            return {}

    def get_user_preferences(self) -> Dict[str, str]:
        """提取用户终端个性化首选项配置 (UserConfig.ini)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return {}

        ini_path = user_dir / "UserConfig.ini"
        if not ini_path.exists():
            return {}

        cfg = configparser.ConfigParser()
        try:
            cfg.read(ini_path, encoding="gbk")
            prefs = {}
            if "Config" in cfg:
                prefs = dict(cfg.items("Config"))
            return prefs
        except Exception:
            return {}

    def get_futures_and_commodity_categories(self) -> List[Dict[str, Any]]:
        """提取大宗商品、股指期货与国债期货监控分类 (CmdtyQuotesSet.xml)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return []

        xml_path = user_dir / "CmdtyQuotesSet.xml"
        if not xml_path.exists():
            return []

        categories = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for cls in root.findall(".//Class"):
                name = cls.attrib.get("Name", "")
                name_en = cls.attrib.get("NameEn", "")
                items = [it.attrib.get("Code", "") for it in cls.findall("Item")]
                categories.append({
                    "category_name": name,
                    "category_en": name_en,
                    "codes": items
                })
        except Exception:
            pass
        return categories

    def get_marked_userlines(self) -> List[Dict[str, Any]]:
        """提取用户自定义技术指标线与图表标记 (全量递归扫描 Config/**/*.Mark 与 Config/PriceMarkLine/*.NewMark)"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return []

        config_dir = user_dir / "Config"
        if not config_dir.exists():
            return []

        marks = []
        try:
            # 1. 递归扫描所有指标画线 (*.Mark)
            for mark_file in config_dir.rglob("*.Mark"):
                if mark_file.name.endswith(".bak") or "_202" in mark_file.name:
                    continue
                symbol = mark_file.stem
                content = mark_file.read_bytes().decode("gbk", errors="ignore")
                param_match = re.search(r"param1=[^\s\x00]+", content)
                marks.append({
                    "symbol": symbol,
                    "file_name": mark_file.name,
                    "mark_type": "technical_indicator",
                    "params": param_match.group(0) if param_match else "",
                    "updated_time": datetime.fromtimestamp(mark_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })

            # 2. 扫描价格盯盘画线 (PriceMarkLine/*.NewMark)
            price_dir = config_dir / "PriceMarkLine"
            if price_dir.exists():
                for p_file in price_dir.glob("*.NewMark"):
                    symbol = p_file.stem
                    raw_text = p_file.read_bytes().decode("gbk", errors="ignore")
                    price_match = re.search(r"\b\d+\.\d+\b", raw_text)
                    price_val = price_match.group(0) if price_match else ""
                    marks.append({
                        "symbol": symbol,
                        "file_name": p_file.name,
                        "mark_type": "price_alert_line",
                        "params": f"目标盯盘预警线: {price_val}" if price_val else "价格预警标记",
                        "updated_time": datetime.fromtimestamp(p_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
        except Exception:
            pass
        return marks

    def get_advisor_profile(self) -> Dict[str, Any]:
        """从终端用户配置 (usermap.ini, UserWdid.dat, localcfg.ini) 提取当前登录投顾实名档案"""
        user_dir = self._get_active_user_dir()
        profile: Dict[str, Any] = {
            "user_id": user_dir.name if user_dir else "W36989091984",
            "name": "本地投顾",
            "en_name": "",
            "phone": "",
            "mail": "",
            "wdid": "",
            "locale": "zh-CN",
            "last_screen_id": 1
        }

        # 1. 读取 usermap.ini (UTF-8 编码)
        usermap_path = self.users_dir / "usermap.ini"
        if usermap_path.exists():
            try:
                cfg = configparser.ConfigParser()
                # 尝试以 UTF-8 读取
                content = usermap_path.read_bytes().decode("utf-8", errors="ignore")
                cfg.read_string(content)
                target_sec = profile["user_id"]
                if target_sec in cfg:
                    sec = dict(cfg.items(target_sec))
                    profile["name"] = sec.get("name", profile["name"])
                    profile["en_name"] = sec.get("enname", "")
                    profile["phone"] = sec.get("phone", "")
                    profile["mail"] = sec.get("mail", "")
            except Exception:
                pass

        # 2. 读取 UserWdid.dat
        wdid_path = self.users_dir / "UserWdid.dat"
        if wdid_path.exists():
            try:
                profile["wdid"] = wdid_path.read_text(encoding="gbk", errors="ignore").strip()
            except Exception:
                pass

        # 3. 读取 localcfg.ini
        if user_dir:
            local_ini = user_dir / "localcfg.ini"
            if local_ini.exists():
                try:
                    cfg_local = configparser.ConfigParser()
                    cfg_local.read(local_ini, encoding="gbk")
                    if "LOCALESETTING" in cfg_local:
                        profile["last_screen_id"] = int(cfg_local.get("LOCALESETTING", "LASTSCREENID", fallback="1"))
                except Exception:
                    pass

        return profile

    def get_investassist_config(self) -> Dict[str, Any]:
        """探索并提取投顾助手 (investassist) 本地策略与资产配置模型"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return {}
        ia_dir = user_dir / "investassist"
        if not ia_dir.exists():
            return {"status": "not_configured", "path": str(ia_dir)}

        files = [f.name for f in ia_dir.glob("*")]
        return {
            "status": "active" if files else "empty",
            "path": str(ia_dir),
            "files": files
        }

    def get_wdd_config(self) -> Dict[str, Any]:
        """探索并提取 Wind 数据下载器 (WDD) 本地批处理任务配置"""
        user_dir = self._get_active_user_dir()
        if not user_dir:
            return {}
        wdd_dir = user_dir / "WDD"
        if not wdd_dir.exists():
            return {"status": "not_configured", "path": str(wdd_dir)}

        files = [f.name for f in wdd_dir.glob("*")]
        return {
            "status": "active" if files else "empty",
            "path": str(wdd_dir),
            "files": files
        }

    def build_consolidated_watchlist(self) -> pd.DataFrame:
        """
        全量聚合构建投顾统一自选标的大宽表：
        整合最新调阅、智能检索、技术画线标的，并联动 MasterDict 补齐官方中文名与资产分类。
        """
        records: Dict[str, WatchlistItem] = {}
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. 最近调阅标的 (权重最高)
        for sym in self.get_latest_visited_symbols():
            sec = self.master_dict.get(sym) if self.master_dict else None
            name = sec.name if sec else sym
            asset_cls = sec.asset_class if (sec and sec.asset_class != "other") else self._infer_asset_class(sym)
            mkt = sym.split(".")[-1] if "." in sym else ""
            records[sym] = WatchlistItem(
                symbol=sym,
                name=name,
                source="latestvisit",
                asset_class=asset_cls,
                market=mkt,
                extra_info="最近终端调阅高频标的",
                updated_at=now_str
            )

        # 2. 智能搜索历史
        for item in self.get_smart_search_history():
            sym = item["symbol"]
            if sym not in records:
                sec = self.master_dict.get(sym) if self.master_dict else None
                name = item["name"] or (sec.name if sec else sym)
                asset_cls = sec.asset_class if (sec and sec.asset_class != "other") else self._infer_asset_class(sym)
                mkt = sym.split(".")[-1] if "." in sym else ""
                records[sym] = WatchlistItem(
                    symbol=sym,
                    name=name,
                    source="smart_history",
                    asset_class=asset_cls,
                    market=mkt,
                    extra_info="终端智能搜索关注标的",
                    updated_at=now_str
                )

        # 3. 自定义画线与技术指标标记标的
        for m in self.get_marked_userlines():
            sym = m["symbol"]
            p_desc = m.get("params", "")
            if sym in records:
                records[sym].extra_info += f" | {p_desc}"
            else:
                sec = self.master_dict.get(sym) if self.master_dict else None
                name = sec.name if sec else sym
                asset_cls = sec.asset_class if (sec and sec.asset_class != "other") else self._infer_asset_class(sym)
                mkt = sym.split(".")[-1] if "." in sym else ""
                records[sym] = WatchlistItem(
                    symbol=sym,
                    name=name,
                    source="userline",
                    asset_class=asset_cls,
                    market=mkt,
                    extra_info=p_desc,
                    updated_at=now_str
                )

        if not records:
            return pd.DataFrame(columns=[
                "symbol", "name", "source", "asset_class", "market", "extra_info", "updated_at"
            ])

        df = pd.DataFrame([asdict(r) for r in records.values()])
        return df

    def _infer_asset_class(self, symbol: str) -> str:
        """根据标的代码规则精确推断资产大类"""
        sym = symbol.strip().upper()
        if sym.endswith(".OF"):
            return "fund"

        # 上交所标的
        if sym.endswith(".SH"):
            clean = sym.replace(".SH", "")
            if clean.startswith("000"):
                return "index"  # 上证核心指数系列 (000001, 000016, 000300, 000852, 000905, 000688 等)
            if clean.startswith(("01", "11", "12", "13", "14")):
                return "bond"   # 国债与可转债/企债
            if clean.startswith(("51", "56", "58")):
                return "etf"    # 场内交易型开放式指数基金
            if clean.startswith("50"):
                return "fund"   # 封闭式/LOF基金
            if clean.startswith(("60", "68", "900")):
                return "stock"  # 主板、科创板、B股
            return "stock"

        # 深交所标的
        if sym.endswith(".SZ"):
            clean = sym.replace(".SZ", "")
            if clean.startswith("399"):
                return "index"  # 深证核心指数系列 (399001, 399005, 399006, 399300 等)
            if clean.startswith(("10", "12")):
                return "bond"   # 转债/国债
            if clean.startswith("15"):
                return "etf"    # 场内 ETF
            if clean.startswith(("16", "18")):
                return "fund"   # LOF/封闭基金
            if clean.startswith(("00", "30", "20")):
                return "stock"  # 主板、创业板、B股
            return "stock"

        # 北交所标的
        if sym.endswith(".BJ"):
            clean = sym.replace(".BJ", "")
            if clean.startswith("899"):
                return "index"  # 北证50等
            return "stock"      # 8xxxxx, 4xxxxx, 920xxx

        if sym.endswith((".CSI", ".CNI", ".WI", ".GI")):
            return "index"
        if sym.endswith((".CFE", ".SHF", ".CZC", ".DCE", ".INE")):
            return "futures"
        if sym.endswith(".HK"):
            return "hk_stock"

        # 全球宏观通用代码 (如 SPX, IXIC, DJI, NDX)
        if any(g in sym for g in ["SPX", "IXIC", "DJI", "NDX", "HSI", "N225", "FTSE"]):
            return "index"

        return "other"

    def sync_to_lakehouse(self) -> int:
        """将全量用户自选与工作台资产落盘入湖并更新 DuckDB 视图"""
        df = self.build_consolidated_watchlist()
        if df.empty:
            return 0
        self.lakehouse.upsert_user_watchlist(df)
        return len(df)
