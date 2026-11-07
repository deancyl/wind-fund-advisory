import hashlib

files = [
    "AGY2_FundAdvisory/judge_engine.py",
    "AGY2_FundAdvisory/holdout_vault.py",
    "AGY2_FundAdvisory/AGENT_SPEC.md",
    "tests/test_infra.py"
]

for f in files:
    with open(f, "rb") as fp:
        h = hashlib.sha256(fp.read()).hexdigest()
    print(f"{f}: {h}")
