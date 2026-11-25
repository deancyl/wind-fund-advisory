from pathlib import Path

dl_p = Path("AGY2_FundAdvisory/data_loader.py")
dl_src = dl_p.read_text(encoding="utf-8")

old_block = '''        result = {
            "status": "success",
            "source": source_used,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_sec": now_ts,
            "flash_news": parsed_items,'''

new_block = '''        result = {
            "status": "success",
            "source": source_used,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_sec": now_ts,
            "news": parsed_items,
            "flash_news": parsed_items,'''

assert old_block in dl_src, "old_block not found"
dl_src = dl_src.replace(old_block, new_block, 1)

dl_p.write_text(dl_src, encoding="utf-8")
print("Successfully added news key to result dict in data_loader.py")

# Remove any old cache file on disk
cache_f = Path("data/cache/realtime_news_cache.json")
if cache_f.exists():
    cache_f.unlink()
    print("Deleted old realtime_news_cache.json")
