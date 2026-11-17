import sys
import os
from pathlib import Path
import pytest

workspace = Path(__file__).resolve().parent.parent
agy2_dir = workspace / "AGY2_FundAdvisory"

sys.path.insert(0, str(agy2_dir))
sys.path.insert(0, str(workspace))
os.environ["PYTHONPATH"] = f"{agy2_dir};{workspace}"

print(f"Running pytest from {workspace}...")
# Run core test files
test_files = [
    "tests/test_infra.py",
    "tests/test_g12_circuit_breakers_and_sentry.py",
    "tests/test_acceptance_r1_r7.py",
    "tests/test_g22_acceptance.py",
]
existing_test_files = [f for f in test_files if (workspace / f).exists()]
print(f"Testing files: {existing_test_files}")

ret = pytest.main(["-v", *existing_test_files])
print(f"Pytest return code: {ret}")
sys.exit(ret)
