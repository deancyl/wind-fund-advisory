import re
import sys

def audit_sentry():
    with open('AGY2_FundAdvisory/advisory_engine.py', 'r', encoding='utf-8') as f:
        code_text = f.read()

    idx = code_text.find('class ActiveRiskSentry')
    assert idx != -1, "ActiveRiskSentry not found"
    sentry_code = code_text[idx:]

    # Check for hardcoded specific fund code branches
    # like `code == "011612"`, `code in ["011612", ...]`
    pattern = re.compile(r'code\s*(?:==|in|!=)\s*[\'\"\[]', re.IGNORECASE)
    matches = pattern.findall(sentry_code)
    print(f"Pattern matches for code equality/membership: {matches}")

    # Specific check for demo fund codes
    for test_code in ["011612", "011613", "013841", "005561", "100032"]:
        # Find if the code is used in an if/elif condition
        cond_matches = re.findall(rf'(?:if|elif)\s+.*?\b{test_code}\b', sentry_code)
        if cond_matches:
            print(f"VIOLATION: Found test code {test_code} in condition: {cond_matches}")
            return False

    print("PASS: No hardcoded test codes in ActiveRiskSentry conditions.")
    return True

if __name__ == '__main__':
    ok = audit_sentry()
    if not ok:
        sys.exit(1)
