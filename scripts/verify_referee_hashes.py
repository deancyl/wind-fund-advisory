# -*- coding: utf-8 -*-
import hashlib
import sys

EXPECTED = {
    "AGY2_FundAdvisory/judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
    "AGY2_FundAdvisory/holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
    "AGY2_FundAdvisory/AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
    "tests/test_infra.py": "48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100"
}

all_match = True
for fpath, exp_hash in EXPECTED.items():
    with open(fpath, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest().upper()
    if actual_hash == exp_hash:
        print(f"PASS: {fpath} matches expected hash.")
    else:
        print(f"FAIL: {fpath} hash mismatch!\nExpected: {exp_hash}\nActual:   {actual_hash}")
        all_match = False

if not all_match:
    sys.exit(1)
print("ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.")
