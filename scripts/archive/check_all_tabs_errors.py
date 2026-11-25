from streamlit.testing.v1 import AppTest
from pathlib import Path
import sys

app_path = (Path(__file__).parent.parent / "AGY2_FundAdvisory" / "app_gui.py").resolve()
print(f"Testing AppTest on: {app_path}")
at = AppTest.from_file(str(app_path), default_timeout=35)
at.run()

print(f"Exception count: {len(at.exception)}")
for exc in at.exception:
    print(f"EXCEPTION: {exc.value}")

print(f"Error block count: {len(at.error)}")
for err in at.error:
    print(f"ERROR BOX: {err.value}")

if len(at.exception) > 0:
    sys.exit(1)

# Check if any tab error occurred
tab_errors = [err.value for err in at.error if "渲染" in err.value or "异常" in err.value]
if tab_errors:
    print(f"FAILED: Found tab-level error boxes: {tab_errors}")
    sys.exit(2)

print("SUCCESS: 0 unhandled exceptions, 0 tab error boxes detected.")
