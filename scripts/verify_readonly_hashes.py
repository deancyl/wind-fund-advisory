import hashlib
from pathlib import Path

EXPECTED_HASHES = {
    "AGY2_FundAdvisory/judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
    "AGY2_FundAdvisory/holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
    "AGY2_FundAdvisory/AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
    "tests/test_infra.py": "48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100",
}

root = Path(__file__).resolve().parent.parent

all_matched = True
for rel_path, expected_hash in EXPECTED_HASHES.items():
    file_path = root / rel_path
    if not file_path.exists():
        print(f"FAIL: {rel_path} does not exist!")
        all_matched = False
        continue
    content = file_path.read_bytes()
    calc_hash = hashlib.sha256(content).hexdigest().upper()
    if calc_hash == expected_hash:
        print(f"PASS: {rel_path} -> {calc_hash}")
    else:
        print(f"MISMATCH: {rel_path}\n  Expected: {expected_hash}\n  Actual:   {calc_hash}")
        all_matched = False

if all_matched:
    print("ALL 4 READ-ONLY FILES SHA256 VERIFIED 100% IDENTICAL.")
else:
    print("HASH VERIFICATION FAILED!")
    exit(1)
