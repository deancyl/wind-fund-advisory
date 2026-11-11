import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))
import streamlit as st

start_time = time.time()
timeline = []

def record(tag, duration=None):
    elapsed = time.time() - start_time
    if duration is not None:
        msg = f"[{elapsed:6.2f}s] {tag} (cost: {duration:6.2f}s)"
    else:
        msg = f"[{elapsed:6.2f}s] {tag}"
    timeline.append(msg)
    print(msg, flush=True)

import app_gui

targets = [
    (app_gui, "render_tab3_backtest_content"),
    (app_gui, "render_tab4_toolbox_content"),
    (app_gui, "_cached_look_through_industry"),
    (app_gui, "_cached_stock_overlap"),
    (app_gui, "_cached_penetration_risk"),
    (app_gui, "_cached_stocks_df"),
    (app_gui, "_cached_find_historical_analogs"),
    (app_gui, "simulate_black_swan_stress"),
    (st, "plotly_chart"),
    (st, "dataframe"),
]

for mod, func_name in targets:
    orig = getattr(mod, func_name, None)
    if orig:
        def make_wrapper(fn, name):
            def wrapper(*args, **kwargs):
                t0 = time.time()
                record(f"--> ENTER {name}")
                try:
                    return fn(*args, **kwargs)
                finally:
                    record(f"<-- EXIT  {name}", duration=time.time() - t0)
            return wrapper
        setattr(mod, func_name, make_wrapper(orig, func_name))

from streamlit.testing.v1 import AppTest
record("Starting AppTest...")
app_path = (Path("AGY2_FundAdvisory") / "app_gui.py").resolve()
at = AppTest.from_file(str(app_path), default_timeout=120)
at.run()
record("AppTest completed!")

print("\n=== DETAILED TIMELINE ===")
for line in timeline:
    print(line)
