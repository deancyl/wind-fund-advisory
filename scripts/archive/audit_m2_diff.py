import subprocess
import re
import sys

files = [
    'AGY2_FundAdvisory/portfolio_manager.py',
    'AGY2_FundAdvisory/app_gui.py',
    'tests/test_m2_features.py'
]

print("=== FORENSIC ANTI-CHEAT SCAN ===")
for fname in files:
    try:
        if fname.startswith('tests/'):
            with open(fname, 'r', encoding='utf-8') as f:
                content = f.read()
            added_lines = content.splitlines()
        else:
            diff = subprocess.check_output(['git', 'diff', 'HEAD', '--', fname], encoding='utf-8')
            added_lines = [l[1:] for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++')]
    except Exception as e:
        print(f"Error checking {fname}: {e}")
        continue

    print(f"\n--- Checking {fname} ({len(added_lines)} lines) ---")
    suspicious = []
    for i, line in enumerate(added_lines, 1):
        # Look for hardcoded test conditions
        if re.search(r'\b(if\s+["\'].*test|if\s+test_|__file__|pytest|mock|bypass|cheat)\b', line, re.IGNORECASE):
            suspicious.append((i, "Test-specific condition / mock keyword", line.strip()))
        # Look for hardcoded constants matching tests
        if re.search(r'return\s+\[\s*\{\s*["\']fund_code["\']\s*:\s*["\'](000217|012832|002351)["\']\s*\}\s*\]', line):
            suspicious.append((i, "Hardcoded test return constant", line.strip()))
        # Look for facade implementations (e.g. dummy return)
        if re.search(r'def\s+\w+\(.*?\):\s*(?:pass|return\s+(?:None|True|False|0|\[\]|\{\}))\s*$', line.strip()):
            suspicious.append((i, "Facade/dummy function", line.strip()))

    if not suspicious:
        print(f"CLEAN: No suspicious patterns found in {fname}.")
    else:
        for idx, tag, l in suspicious:
            print(f"  [Line {idx}] {tag}: {l}")

print("\n=== SCAN COMPLETE ===")
