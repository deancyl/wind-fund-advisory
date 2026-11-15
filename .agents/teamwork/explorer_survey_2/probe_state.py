import sys
import json
from pathlib import Path

p = Path("AGY2_FundAdvisory/data/multi_ledger_state.json")
if p.exists():
    print(p.read_text(encoding="utf-8"))
else:
    print("multi_ledger_state.json does not exist, checking other json files:")
    for f in Path("AGY2_FundAdvisory").glob("*.json"):
        print(f)
    for f in Path("AGY2_FundAdvisory/data").glob("*.json"):
        print(f)
