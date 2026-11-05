import sys
import os
sys.path.insert(0, os.path.abspath("AGY2_FundAdvisory"))

from streamlit.testing.v1 import AppTest

gui_path = os.path.abspath("AGY2_FundAdvisory/app_gui.py")
print(f"=== Running AppTest from_file: {gui_path} ===")
at = AppTest.from_file(gui_path, default_timeout=30)
at.run()

if at.exception:
    print(f"EXCEPTION ENCOUNTERED: {len(at.exception)}")
    for exc in at.exception:
        print(f"  {exc.value}")
        print(f"  {exc.stack_trace}")
else:
    print("SUCCESS: No exceptions!")
    # Check model selector
    for sb in at.selectbox:
        if "定权模型" in (sb.label or ""):
            print(f"Model selectbox label: {sb.label}, options: {sb.options}, value: {sb.value}")
    
    # Check buttons in sentry
    sentry_buttons = [b.label for b in at.button if any(k in (b.label or "") for k in ["锁定", "倒计时", "置换", "止盈", "反弹"])]
    print(f"Sentry action buttons found: {sentry_buttons}")

    # Check expanders
    expanders = [e.label for e in at.expander]
    print(f"Expanders found: {expanders[:5]}")
