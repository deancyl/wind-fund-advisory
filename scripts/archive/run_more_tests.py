import sys
import os
from pathlib import Path
import pytest

workspace = Path(__file__).resolve().parent.parent
agy2_dir = workspace / "AGY2_FundAdvisory"

sys.path.insert(0, str(agy2_dir))
sys.path.insert(0, str(workspace))
os.environ["PYTHONPATH"] = f"{agy2_dir};{workspace}"

test_files = [
    "tests/test_advisory_core_capabilities.py",
    "tests/test_m2_features.py",
    "tests/test_anticheat_full_closure.py",
    "tests/test_challenger_tab2_rebalance_adversarial.py",
    "tests/test_adversarial_m3_combat29_challenger.py",
    "tests/test_g8_ux_and_realtime_fusion.py",
    "tests/test_g7_architecture_and_decoupling.py"
]

existing_test_files = [f for f in test_files if (workspace / f).exists()]
print(f"Testing files: {existing_test_files}")

ret = pytest.main(["-v", *existing_test_files])
print(f"Pytest return code: {ret}")
sys.exit(ret)
