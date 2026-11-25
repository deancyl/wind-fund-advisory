import re
from pathlib import Path

# Fix 1 & 2: AGY2_FundAdvisory/app_gui.py
gui_p = Path("AGY2_FundAdvisory/app_gui.py")
gui_src = gui_p.read_text(encoding="utf-8")

# Fix _safe_float
old_safe_float = '''def _safe_float(val, default=0.0) -> float:
    if val is None or pd.isna(val):
        return float(default)
    try:
        f = float(val)
        return float(default) if pd.isna(f) else f
    except (ValueError, TypeError):
        return float(default)'''

new_safe_float = '''def _safe_float(val, default=0.0):
    if val is None or pd.isna(val):
        return None if default is None else float(default)
    try:
        f = float(val)
        return (None if default is None else float(default)) if pd.isna(f) else f
    except (ValueError, TypeError):
        return None if default is None else float(default)'''

assert old_safe_float in gui_src, "old_safe_float not found"
gui_src = gui_src.replace(old_safe_float, new_safe_float, 1)

# Fix format_chinese_amount threshold for 亿元
old_fmt_amount = '''    if abs_v >= 100_000_000:
        yi_v = abs_v / 100_000_000.0
        wan_v = abs_v / 10_000.0
        return f"{standard_str} 折合 {sign}{wan_v:,.2f} 万元 ({sign}{yi_v:,.2f} 亿元)"'''

new_fmt_amount = '''    if abs_v >= 10_000_000:
        yi_v = abs_v / 100_000_000.0
        wan_v = abs_v / 10_000.0
        return f"{standard_str} 折合 {sign}{wan_v:,.2f} 万元 ({sign}{yi_v:.2f} 亿元)"'''

assert old_fmt_amount in gui_src, "old_fmt_amount not found"
gui_src = gui_src.replace(old_fmt_amount, new_fmt_amount, 1)

gui_p.write_text(gui_src, encoding="utf-8")
print("Fixed app_gui.py (_safe_float and format_chinese_amount)")


# Fix 3: AGY2_FundAdvisory/portfolio_manager.py
pm_p = Path("AGY2_FundAdvisory/portfolio_manager.py")
pm_src = pm_p.read_text(encoding="utf-8")

old_pm_bp = '''        allocated_total = 0.0
        items = blueprint.get("items", [])

        for it in items:
            code = str(it.get("fund_code")).strip().zfill(6)
            base_amt = float(it.get("allocated_amount", 0.0))
            if base_amt <= 0:
                continue'''

new_pm_bp = '''        allocated_total = 0.0
        items = blueprint.get("items") or blueprint.get("funds", [])

        for it in items:
            code = str(it.get("fund_code")).strip().zfill(6)
            base_amt = float(it.get("allocated_amount", 0.0) or it.get("amount", 0.0))
            if base_amt <= 0 and "weight_pct" in it and total_cap > 0:
                base_amt = round(total_cap * float(it["weight_pct"]) / 100.0, 2)
            if base_amt <= 0:
                continue
            fname_it = it.get("fund_name")'''

assert old_pm_bp in pm_src, "old_pm_bp not found"
pm_src = pm_src.replace(old_pm_bp, new_pm_bp, 1)

old_add_holding_call = '''                self.add_or_update_holding(
                    fund_code=code,
                    shares=shares,
                    nav=nav,
                    cost_price=nav,
                    holding_days=0,
                    holding_tag="<7d",
                    dividend_method=div_method,
                    notes=note_str,
                    append_batch=False
                )'''

new_add_holding_call = '''                self.add_or_update_holding(
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

assert old_add_holding_call in pm_src, "old_add_holding_call not found"
pm_src = pm_src.replace(old_add_holding_call, new_add_holding_call, 1)

pm_p.write_text(pm_src, encoding="utf-8")
print("Fixed portfolio_manager.py (apply_zero_start_blueprint funds support)")


# Fix 4: AGY2_FundAdvisory/data_loader.py
dl_p = Path("AGY2_FundAdvisory/data_loader.py")
dl_src = dl_p.read_text(encoding="utf-8")

old_dl_res = '''        result = {
            "status": "success",
            "source": source_used,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_sec": now_ts,
            "flash_news": parsed_items,
            "macro_items": macro_items,
            "sector_catalysts": sector_catalysts,
            "summary_bullets": summary_bullets,
            "pulse_summary": f"实时多源资讯感知联动：{source_used} 抓取 {len(parsed_items)} 条快讯，涵盖宏观流动性与重点赛道催化。"
        }'''

new_dl_res = '''        result = {
            "status": "success",
            "source": source_used,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_sec": now_ts,
            "news": parsed_items,
            "flash_news": parsed_items,
            "macro_items": macro_items,
            "sector_catalysts": sector_catalysts,
            "summary_bullets": summary_bullets,
            "pulse_summary": f"实时多源资讯感知联动：{source_used} 抓取 {len(parsed_items)} 条快讯，涵盖宏观流动性与重点赛道催化。"
        }'''

assert old_dl_res in dl_src, "old_dl_res not found"
dl_src = dl_src.replace(old_dl_res, new_dl_res, 1)

# Also ensure cached and fallback return "news"
old_dl_fallback = '''    return {
        "status": "offline_fallback",
        "source": "embedded_baseline",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_sec": now_ts,
        "flash_news": fallback_items,'''

new_dl_fallback = '''    return {
        "status": "offline_fallback",
        "source": "embedded_baseline",
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

dl_p.write_text(dl_src, encoding="utf-8")
print("Fixed data_loader.py (news field in realtime news)")
