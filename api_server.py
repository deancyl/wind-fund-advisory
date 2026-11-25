# -*- coding: utf-8 -*-
import importlib.util
import runpy
import sys
from pathlib import Path

_CORE_DIR = (Path(__file__).resolve().parent / "AGY2_FundAdvisory").resolve()
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))
_TARGET = _CORE_DIR / Path(__file__).name
if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
else:
    _spec = importlib.util.spec_from_file_location(__name__, _TARGET)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[__name__] = _mod
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
