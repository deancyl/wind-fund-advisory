# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

workspace_root = Path(__file__).resolve().parent.parent
target_file = workspace_root / "AGY2_FundAdvisory" / "app_gui.py"
print(f"Initializing AppTest for {target_file}...")
at = AppTest.from_file(str(target_file), default_timeout=40)
at.run()

if at.exception:
    print("AppTest encountered an exception:")
    for exc in at.exception:
        print(exc.value)
    sys.exit(1)
else:
    print("SUCCESS: AppTest completed with 0 exceptions!")
