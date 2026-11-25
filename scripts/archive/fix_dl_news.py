from pathlib import Path

# Fix data_loader.py
dl_p = Path("AGY2_FundAdvisory/data_loader.py")
dl_src = dl_p.read_text(encoding="utf-8")

old_dl_fallback = '''    offline_res = {
        "status": "cold_start_fallback",
        "source": "cold_start_fallback",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_sec": now_ts,
        "flash_news": fallback_items,'''

new_dl_fallback = '''    offline_res = {
        "status": "cold_start_fallback",
        "source": "cold_start_fallback",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_sec": now_ts,
        "news": fallback_items,
        "flash_news": fallback_items,'''

assert old_dl_fallback in dl_src, "old_dl_fallback not found"
dl_src = dl_src.replace(old_dl_fallback, new_dl_fallback, 1)

# And in cache return:
old_cache_ret = '''            cached_dt = datetime.fromisoformat(cached.get("updated_at", "2000-01-01"))
            if (datetime.now() - cached_dt).total_seconds() < cache_ttl_sec:
                _REALTIME_NEWS_MEM_CACHE["ts"] = now_ts
                _REALTIME_NEWS_MEM_CACHE["data"] = cached
                return cached'''

new_cache_ret = '''            cached_dt = datetime.fromisoformat(cached.get("updated_at", "2000-01-01"))
            if (datetime.now() - cached_dt).total_seconds() < cache_ttl_sec:
                cached["news"] = cached.get("news") or cached.get("flash_news", [])
                _REALTIME_NEWS_MEM_CACHE["ts"] = now_ts
                _REALTIME_NEWS_MEM_CACHE["data"] = cached
                return cached'''

assert old_cache_ret in dl_src, "old_cache_ret not found"
dl_src = dl_src.replace(old_cache_ret, new_cache_ret, 1)

# Also in step 6 fallback from disk
old_step6 = '''    if REALTIME_NEWS_CACHE_FILE.exists():
        try:
            with open(REALTIME_NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached["source"] = "cached_fallback"
            cached["status"] = "cached_fallback"
            _REALTIME_NEWS_MEM_CACHE["ts"] = now_ts
            _REALTIME_NEWS_MEM_CACHE["data"] = cached
            return cached'''

new_step6 = '''    if REALTIME_NEWS_CACHE_FILE.exists():
        try:
            with open(REALTIME_NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached["source"] = "cached_fallback"
            cached["status"] = "cached_fallback"
            cached["news"] = cached.get("news") or cached.get("flash_news", [])
            _REALTIME_NEWS_MEM_CACHE["ts"] = now_ts
            _REALTIME_NEWS_MEM_CACHE["data"] = cached
            return cached'''

assert old_step6 in dl_src, "old_step6 not found"
dl_src = dl_src.replace(old_step6, new_step6, 1)

dl_p.write_text(dl_src, encoding="utf-8")
print("Fixed data_loader.py (news field in realtime news)")
