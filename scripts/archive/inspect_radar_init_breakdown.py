# -*- coding: utf-8 -*-
import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, OnlineHeuristicFactorEvolver

engine = OpportunityRadarEngine.__new__(OpportunityRadarEngine)

t0 = time.perf_counter()
engine.cache_dir = engine._resolve_cache_dir()
t1 = time.perf_counter()
print(f"_resolve_cache_dir: {(t1 - t0)*1000:.2f} ms")

engine.valuation_cache = engine._load_valuation_cache()
t2 = time.perf_counter()
print(f"_load_valuation_cache: {(t2 - t1)*1000:.2f} ms")

engine.realtime_quotes = engine._load_realtime_quotes()
t3 = time.perf_counter()
print(f"_load_realtime_quotes: {(t3 - t2)*1000:.2f} ms")

engine.dynamic_metrics = engine._calc_dynamic_sector_metrics()
t4 = time.perf_counter()
print(f"_calc_dynamic_sector_metrics: {(t4 - t3)*1000:.2f} ms")

engine.evolver = OnlineHeuristicFactorEvolver()
t5 = time.perf_counter()
print(f"OnlineHeuristicFactorEvolver(): {(t5 - t4)*1000:.2f} ms")

cached_disk = engine.evolver._read_disk_cache(max_age_seconds=43200.0)
t6 = time.perf_counter()
print(f"_read_disk_cache: {(t6 - t5)*1000:.2f} ms")

print(f"Total: {(t6 - t0)*1000:.2f} ms")
