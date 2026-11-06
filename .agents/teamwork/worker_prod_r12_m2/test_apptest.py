import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

WS_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(WS_ROOT) not in sys.path:
    sys.path.insert(0, str(WS_ROOT))
if str(WS_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WS_ROOT / "AGY2_FundAdvisory"))

def test_app():
    print("Testing AppTest on AGY2_FundAdvisory/app_gui.py...")
    at = AppTest.from_file(str(WS_ROOT / "AGY2_FundAdvisory" / "app_gui.py"), default_timeout=30)
    at.run()
    if at.exception:
        print("AppTest exception encountered:")
        for exc in at.exception:
            print(exc.value)
        raise AssertionError(f"AppTest failed with exception: {at.exception[0].value}")
    print("AppTest passed with 0 exceptions!")

if __name__ == "__main__":
    test_app()
