# -*- coding: utf-8 -*-
"""
scripts/test_apptest_sentry_buttons.py
AppTest interaction test to verify sentry buttons are rendered and clickable without exceptions
"""

import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

GUI_FILE = str(WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py")

def test_sentry_buttons_apptest():
    print("Initializing AppTest from app_gui.py...")
    at = AppTest.from_file(GUI_FILE, default_timeout=45)
    at.run()
    assert not at.exception, f"AppTest exception on launch: {at.exception}"

    # Search for buttons rendered by ActiveRiskSentry
    sentry_buttons = [b for b in at.button if "btn_sentry_act_" in str(b.key)]
    print(f"Found {len(sentry_buttons)} sentry action buttons in AppTest:")
    for b in sentry_buttons:
        print(f"  Button key: {b.key}, label: {b.label}")

    assert len(sentry_buttons) > 0, "Expected at least one sentry action button to be rendered in demo portfolio"

    # Click the first sentry button (e.g. lock_shares or countdown_hold)
    first_btn = sentry_buttons[0]
    print(f"\nClicking button: {first_btn.key} ({first_btn.label})...")
    first_btn.click().run()

    assert not at.exception, f"AppTest threw exception after clicking button: {at.exception}"
    assert len(at.error) == 0, f"AppTest errors after button click: {[e.value for e in at.error]}"
    print("Button click executed smoothly with 0 exceptions and 0 errors!")
    print("SESSION STATE VERIFICATION:")
    print(f"  tab2_trigger_diagnose: {at.session_state.get('tab2_trigger_diagnose')}")
    print(f"  tab2_locked_funds: {at.session_state.get('tab2_locked_funds')}")

if __name__ == "__main__":
    test_sentry_buttons_apptest()
    print("\nALL APPTEST SENTRY BUTTON TESTS PASSED!")
