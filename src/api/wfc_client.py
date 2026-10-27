"""
Wind 投顾终端 (WFC) REST API 客户端：封装基金业绩比对、产品货架、
投顾资讯与客户画像服务，支持云端接口与本地缓存离线双轨自愈。
"""

from typing import List, Dict, Any, Optional
import requests
import urllib3
import pandas as pd

from ..config import WIND_CONFIG
from ..core.session_manager import SessionManager
from ..parsers.cef_cache_parser import CEFCacheParser
from ..storage.lakehouse import LakehouseManager

urllib3.disable_warnings()


class WFCClient:
    """Wind Financial Client 投顾数据访问客户端"""

    def __init__(
        self,
        config=WIND_CONFIG,
        session_mgr: Optional[SessionManager] = None,
        cache_parser: Optional[CEFCacheParser] = None,
        lakehouse: Optional[LakehouseManager] = None
    ):
        self.config = config
        self.session_mgr = session_mgr or SessionManager(config)
        self.cache_parser = cache_parser or CEFCacheParser(config.cef_cache_dir)
        self.lakehouse = lakehouse or LakehouseManager()
        self.base_url = f"https://{self.config.default_web_server}"

    def _get_headers(self) -> Dict[str, str]:
        sid = self.session_mgr.get_session_id() or ""
        return {
            "wind.sessionid": sid,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.120 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{self.base_url}/WFC-WEB/WFCPC/home/index.html",
        }

    def get_fund_performance_yield_chart(
        self,
        wind_codes: List[str],
        start_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        获取公募基金收益率曲线。
        优先请求云端接口；若云端未授权或离线，自动无缝提取本地 CEF 缓存。
        """
        # 先尝试本地缓存中是否已具备
        cached_funds = self.cache_parser.extract_fund_yield_charts()
        matched = {code: cached_funds[code] for code in wind_codes if code in cached_funds}

        if len(matched) == len(wind_codes):
            return matched

        # 请求云端补充
        sid = self.session_mgr.get_session_id()
        if sid:
            url = f"{self.base_url}/pac-web/api/product/getFundPerformanceYieldChart5"
            params = {
                "windCodes": ",".join(wind_codes),
                "startDate": start_date or "2024-01-01"
            }
            try:
                resp = requests.get(url, headers=self._get_headers(), params=params, verify=False, timeout=5)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    for code, series in data.items():
                        if series and isinstance(series, list):
                            pts = series[0].get("data", [])
                            name = series[0].get("name", "")
                            recs = [
                                {
                                    "date": pd.to_datetime(p["x"], unit="ms").strftime("%Y-%m-%d"),
                                    "yield_pct": float(p["y"]),
                                    "fund_code": code,
                                    "fund_name": name
                                }
                                for p in pts if "x" in p and "y" in p
                            ]
                            if recs:
                                matched[code] = pd.DataFrame(recs).sort_values("date").reset_index(drop=True)
            except Exception:
                pass

        # 若仍有缺失标的，自动回退查询本地 Parquet 湖仓 (100% 离线脱机支持)
        for code in wind_codes:
            if code not in matched:
                df_lake = self.lakehouse.get_fund_series(code)
                if df_lake is not None and not df_lake.empty:
                    matched[code] = df_lake

        return matched

    def get_homepage_fund_info(self) -> Dict[str, Any]:
        """获取投顾首页优选基金池概览"""
        url = f"{self.base_url}/pac-web/api/product/getHomePageFundInfo?a=1"
        try:
            resp = requests.get(url, headers=self._get_headers(), verify=False, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"status": "offline", "data": []}

    def get_user_company_info(self) -> Dict[str, Any]:
        """获取当前登录投顾机构与认证信息"""
        url = f"{self.base_url}/pac-web/api/crm/getUserCompanyInfo"
        try:
            resp = requests.get(url, headers=self._get_headers(), verify=False, timeout=4)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {
            "company": self.config._parsed_user_info.get("company", "机构自营"),
            "user": self.config._parsed_user_info.get("login_name", "本地投顾"),
            "online": False
        }
