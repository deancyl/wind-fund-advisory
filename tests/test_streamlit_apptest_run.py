from streamlit.testing.v1 import AppTest
from pathlib import Path
import pytest

def test_streamlit_app_full_render():
    app_path = (Path(__file__).parent.parent / "AGY2_FundAdvisory" / "app_gui.py").resolve()
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.run()
    assert not at.exception, f"AppTest raised an exception: {at.exception}"
    print("Streamlit AppTest passed with 0 exceptions!")
