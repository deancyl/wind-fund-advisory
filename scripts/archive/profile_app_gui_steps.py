import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))
from streamlit.testing.v1 import AppTest

t_start = time.time()
print(f"[{time.strftime('%H:%M:%S')}] Starting AppTest to profile page execution...")
app_path = (Path("AGY2_FundAdvisory") / "app_gui.py").resolve()
at = AppTest.from_file(str(app_path), default_timeout=60)
at.run()
t_end = time.time()
print(f"[{time.strftime('%H:%M:%S')}] AppTest completed in {t_end - t_start:.2f}s!")
print(f"Total elements: {len(at.elements)}")
