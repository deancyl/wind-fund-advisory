from pathlib import Path

# 1. Fix data_loader.py: ensure "news" key is ALWAYS present in every code path of fetch_realtime_market_news_and_catalysts
dl_p = Path("AGY2_FundAdvisory/data_loader.py")
dl_src = dl_p.read_text(encoding="utf-8")

# In memory cache return
old_mem_ret = '''    if not force_refresh and _REALTIME_NEWS_MEM_CACHE["data"] is not None:
        if now_ts - _REALTIME_NEWS_MEM_CACHE["ts"] < cache_ttl_sec:
            return _REALTIME_NEWS_MEM_CACHE["data"]'''

new_mem_ret = '''    if not force_refresh and _REALTIME_NEWS_MEM_CACHE["data"] is not None:
        if now_ts - _REALTIME_NEWS_MEM_CACHE["ts"] < cache_ttl_sec:
            cached_data = _REALTIME_NEWS_MEM_CACHE["data"]
            if "news" not in cached_data:
                cached_data["news"] = cached_data.get("flash_news", [])
            return cached_data'''

assert old_mem_ret in dl_src, "old_mem_ret not found"
dl_src = dl_src.replace(old_mem_ret, new_mem_ret, 1)

# In disk cache return
old_disk_ret = '''            cached_dt = datetime.fromisoformat(cached.get("updated_at", "2000-01-01"))
            if (datetime.now() - cached_dt).total_seconds() < cache_ttl_sec:
                cached["news"] = cached.get("news") or cached.get("flash_news", [])
                _REALTIME_NEWS_MEM_CACHE["ts"] = now_ts
                _REALTIME_NEWS_MEM_CACHE["data"] = cached
                return cached'''

new_disk_ret = '''            cached_dt = datetime.fromisoformat(cached.get("updated_at", "2000-01-01"))
            if (datetime.now() - cached_dt).total_seconds() < cache_ttl_sec:
                if "news" not in cached:
                    cached["news"] = cached.get("flash_news", [])
                _REALTIME_NEWS_MEM_CACHE["ts"] = now_ts
                _REALTIME_NEWS_MEM_CACHE["data"] = cached
                return cached'''

if old_disk_ret in dl_src:
    dl_src = dl_src.replace(old_disk_ret, new_disk_ret, 1)

dl_p.write_text(dl_src, encoding="utf-8")
print("Updated data_loader.py news key handling")

# Remove any old cache file on disk
cache_f = Path("data/cache/realtime_news_cache.json")
if cache_f.exists():
    cache_f.unlink()
    print("Deleted old realtime_news_cache.json")


# 2. Fix portfolio_manager.py: add record_snapshot flag to add_or_update_holding
# and pass record_snapshot=False in apply_zero_start_blueprint
pm_p = Path("AGY2_FundAdvisory/portfolio_manager.py")
pm_src = pm_p.read_text(encoding="utf-8")

old_aouh_sig = '''    def add_or_update_holding(
        self,
        fund_code: str,
        shares: Optional[float] = None,
        amount: Optional[float] = None,
        nav: float = 1.0,
        cost_price: Optional[float] = None,
        holding_tag: Optional[str] = None,
        holding_days: Optional[int] = None,
        dividend_method: str = "cash",
        notes: str = "手动新增持仓",
        append_batch: bool = False,
        fund_name: Optional[str] = None
    ) -> Dict[str, Any]:'''

new_aouh_sig = '''    def add_or_update_holding(
        self,
        fund_code: str,
        shares: Optional[float] = None,
        amount: Optional[float] = None,
        nav: float = 1.0,
        cost_price: Optional[float] = None,
        holding_tag: Optional[str] = None,
        holding_days: Optional[int] = None,
        dividend_method: str = "cash",
        notes: str = "手动新增持仓",
        append_batch: bool = False,
        fund_name: Optional[str] = None,
        record_snapshot: bool = True
    ) -> Dict[str, Any]:'''

assert old_aouh_sig in pm_src, "old_aouh_sig not found"
pm_src = pm_src.replace(old_aouh_sig, new_aouh_sig, 1)

# In add_or_update_holding bottom:
old_aouh_save = '''        self._recalculate_totals()
        self._evaluate_all_transition_tags()
        self.save_state(record_snapshot=True)'''

new_aouh_save = '''        self._recalculate_totals()
        self._evaluate_all_transition_tags()
        self.save_state(record_snapshot=record_snapshot)'''

assert old_aouh_save in pm_src, "old_aouh_save not found"
pm_src = pm_src.replace(old_aouh_save, new_aouh_save, 1)

# In apply_zero_start_blueprint calls to add_or_update_holding:
old_call1 = '''                self.add_or_update_holding(
                    fund_code=code,
                    shares=shares1,
                    nav=nav1,
                    cost_price=nav1,
                    holding_days=0,
                    holding_tag="<7d",
                    dividend_method=div_method,
                    notes=note_str,
                    append_batch=False
                )'''

new_call1 = '''                self.add_or_update_holding(
                    fund_code=code,
                    shares=shares1,
                    nav=nav1,
                    cost_price=nav1,
                    holding_days=0,
                    holding_tag="<7d",
                    dividend_method=div_method,
                    notes=note_str,
                    append_batch=False,
                    record_snapshot=False
                )'''

assert old_call1 in pm_src, "old_call1 not found"
pm_src = pm_src.replace(old_call1, new_call1, 1)

old_call2 = '''                    self.add_or_update_holding(
                        fund_code=fb_code,
                        shares=shares2,
                        nav=nav2,
                        cost_price=nav2,
                        holding_days=0,
                        holding_tag="<7d",
                        dividend_method=div_method,
                        notes=note_fb,
                        append_batch=False
                    )'''

new_call2 = '''                    self.add_or_update_holding(
                        fund_code=fb_code,
                        shares=shares2,
                        nav=nav2,
                        cost_price=nav2,
                        holding_days=0,
                        holding_tag="<7d",
                        dividend_method=div_method,
                        notes=note_fb,
                        append_batch=False,
                        record_snapshot=False
                    )'''

assert old_call2 in pm_src, "old_call2 not found"
pm_src = pm_src.replace(old_call2, new_call2, 1)

old_call3 = '''                self.add_or_update_holding(
                    fund_code=code,
                    shares=shares,
                    nav=nav,
                    cost_price=nav,
                    holding_days=0,
                    holding_tag="<7d",
                    dividend_method=div_method,
                    notes=note_str,
                    fund_name=fname_it,
                    append_batch=False
                )'''

new_call3 = '''                self.add_or_update_holding(
                    fund_code=code,
                    shares=shares,
                    nav=nav,
                    cost_price=nav,
                    holding_days=0,
                    holding_tag="<7d",
                    dividend_method=div_method,
                    notes=note_str,
                    fund_name=fname_it,
                    append_batch=False,
                    record_snapshot=False
                )'''

assert old_call3 in pm_src, "old_call3 not found"
pm_src = pm_src.replace(old_call3, new_call3, 1)

pm_p.write_text(pm_src, encoding="utf-8")
print("Updated portfolio_manager.py add_or_update_holding snapshot control")
