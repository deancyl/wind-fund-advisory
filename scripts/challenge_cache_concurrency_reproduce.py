"""
Empirical verification of disk cache write race condition and non-atomic file truncation.
"""
import concurrent.futures
import json
import time
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from advisory_engine import OnlineHeuristicFactorEvolver

evolver = OnlineHeuristicFactorEvolver()
cache_path = evolver._resolve_cache_path()

# Verify cache has full data
with open(cache_path, "r", encoding="utf-8") as f:
    initial_data = json.load(f)

print("[Initial Cache Keys]:", list(initial_data.keys()))
assert "weights" in initial_data
assert "nav_trajectory" in initial_data

# Now simulate concurrent read and incremental write
errors = []
stop = False

def reader():
    while not stop:
        data = evolver._read_disk_cache(max_age_seconds=43200.0)
        if data is None:
            errors.append("CACHE_MISS_DURING_CONCURRENT_WRITE")
        elif "weights" not in data:
            errors.append(f"DATA_CORRUPTION_MISSING_WEIGHTS: keys={list(data.keys())}")
        time.sleep(0.002)

def writer():
    for i in range(10):
        evolver._write_disk_cache({"ping": i})
        time.sleep(0.005)

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    r_futs = [ex.submit(reader) for _ in range(4)]
    w_futs = [ex.submit(writer) for _ in range(2)]
    concurrent.futures.wait(w_futs)
    stop = True
    concurrent.futures.wait(r_futs)

print(f"[Results] Total errors observed: {len(errors)}")
if errors:
    print(f"[Sample Error 1]: {errors[0]}")
    print(f"[Sample Error -1]: {errors[-1]}")

# Check disk cache after concurrency:
with open(cache_path, "r", encoding="utf-8") as f:
    final_data = json.load(f)

print("[Final Cache Keys on Disk]:", list(final_data.keys()))
is_corrupted = "weights" not in final_data
print(f"[Is Cache Corrupted on Disk?]: {is_corrupted}")

# Restore
with open(cache_path, "w", encoding="utf-8") as f:
    json.dump(initial_data, f, ensure_ascii=False, indent=2)
print("[Restored Initial Cache]")
