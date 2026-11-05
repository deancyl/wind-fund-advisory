import os
import hashlib

files = [
    "AGY2_FundAdvisory/judge_engine.py",
    "AGY2_FundAdvisory/holdout_vault.py",
    "AGY2_FundAdvisory/AGENT_SPEC.md",
    "tests/test_infra.py"
]

for filepath in files:
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        print(f"{filepath}: {digest}")
    else:
        print(f"{filepath}: NOT FOUND")
