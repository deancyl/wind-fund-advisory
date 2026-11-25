import sys
import cProfile
import pstats
import io
import threading
from pathlib import Path

sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))

orig_thread_run = threading.Thread.run
def hooked_thread_run(self):
    if "ScriptRunner" in type(self).__name__ or "ScriptRunner" in self.name or "Script" in self.name:
        pr = cProfile.Profile()
        pr.enable()
        try:
            return orig_thread_run(self)
        finally:
            pr.disable()
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
            ps.print_stats(35)
            print(f"\n==========================================")
            print(f"=== PROFILE FOR THREAD {self.name} ===")
            print(f"==========================================")
            print(s.getvalue())
    else:
        return orig_thread_run(self)

threading.Thread.run = hooked_thread_run

from streamlit.testing.v1 import AppTest

app_path = (Path("AGY2_FundAdvisory") / "app_gui.py").resolve()
at = AppTest.from_file(str(app_path), default_timeout=120)

print("Starting AppTest with Thread Hook...", flush=True)
try:
    at.run()
    print("AppTest completed!", flush=True)
except Exception as e:
    print(f"AppTest run error: {e}", flush=True)
