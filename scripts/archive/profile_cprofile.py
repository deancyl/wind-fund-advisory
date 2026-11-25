import sys
import cProfile
import pstats
import io
from pathlib import Path

sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))
from streamlit.testing.v1 import AppTest

app_path = (Path("AGY2_FundAdvisory") / "app_gui.py").resolve()
at = AppTest.from_file(str(app_path), default_timeout=120)

pr = cProfile.Profile()
pr.enable()

try:
    at.run()
except Exception as e:
    print(f"AppTest run error: {e}")

pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
ps.print_stats(40)

print(s.getvalue())
