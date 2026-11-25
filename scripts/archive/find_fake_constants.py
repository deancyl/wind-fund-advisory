import os
import re

PATTERNS = {
    "7.2385": re.compile(r"7\.2385"),
    "4.4200": re.compile(r"4\.4200"),
}

TARGET_FILES = [
    "AGY2_FundAdvisory/data_loader.py",
    "AGY2_FundAdvisory/advisory_engine.py",
    "AGY2_FundAdvisory/strategy_bridge.py",
    "AGY2_FundAdvisory/portfolio_manager.py",
    "AGY2_FundAdvisory/app_gui.py",
]

found = []
for path in TARGET_FILES:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as fp:
            for idx, line in enumerate(fp, 1):
                for name, p in PATTERNS.items():
                    if p.search(line):
                        found.append((path, idx, name, line.strip()))

print(f"Total occurrences of 7.2385 and 4.4200 in modified files: {len(found)}")
for path, idx, name, line in found:
    print(f"  {path}:{idx} [{name}]: {line}")

if len(found) == 0:
    print("SUCCESS: ZERO occurrences of fake constants in all modified files!")
else:
    print("FAILURE: Fake constants detected!")
