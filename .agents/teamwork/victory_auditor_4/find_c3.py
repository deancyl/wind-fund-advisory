with open("AGY2_FundAdvisory/strategy_bridge.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if 'tier == "C3"' in line or "tier == 'C3'" in line:
            print(f"{i}: {line.strip()}")
