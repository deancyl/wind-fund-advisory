import ast
import os
import re
import sys

def check_c3_bypass():
    print("=== Checking C3 Bypass in strategy_bridge.py ===")
    with open("AGY2_FundAdvisory/strategy_bridge.py", "r", encoding="utf-8") as f:
        sb_text = f.read()

    # Search for any return statement returning hardcoded 0.38
    if "0.38" in sb_text:
        print("[CHECK] Searching where 0.38 appears:")
        for i, line in enumerate(sb_text.splitlines(), 1):
            if "0.38" in line:
                print(f"  Line {i}: {line.strip()}")

    # Search for C3 special cases
    for m in re.finditer(r'tier\s*==\s*[\'"]C3[\'"]', sb_text):
        idx = m.start()
        print(f"  Match near {idx}:")
        print(sb_text[max(0, idx-60):min(len(sb_text), idx+150)])

def check_time_sleep_and_cheats():
    print("\n=== Checking time.sleep and calendar cheats ===")
    for root, dirs, files in os.walk("AGY2_FundAdvisory"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "time.sleep" in content and "tests" not in path:
                    print(f"  [ALERT] time.sleep in {path}")
                # Check for year/calendar tampering
                if "2026" in content and "tests" not in path and "AGENT_SPEC" not in path:
                    # Check if it's year tampering
                    pass

def check_frontend_monkey_patch():
    print("\n=== Checking frontend monkey patches in app_gui.py ===")
    with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
        gui_text = f.read()
    
    # Check for setattr, monkeypatch, or overriding core functions
    suspicious = ["setattr(", "monkeypatch", "unittest.mock", "patch(", "__dict__"]
    for s in suspicious:
        if s in gui_text:
            print(f"  [ALERT] Found {s} in app_gui.py")
    print("Frontend app_gui.py check complete.")

def check_c3_dynamic_execution():
    print("\n=== Checking dynamic calculation of C1-C5 weights ===")
    sys.path.insert(0, "AGY2_FundAdvisory")
    from strategy_bridge import StrategyBridge, TIER_TARGET_WEIGHTS
    
    for t in ["C1", "C2", "C3", "C4", "C5"]:
        w = StrategyBridge.compute_dynamic_tier_weights(tier=t)
        w_dict = TIER_TARGET_WEIGHTS[t]
        print(f"  Tier {t}: sum={sum(w.values()):.4f}, keys={list(w.keys())}")
        assert abs(sum(w.values()) - 1.0) < 1e-4, f"Sum of weights for {t} is not 1.0"
        assert w == w_dict, f"TIER_TARGET_WEIGHTS[{t}] does not match compute_dynamic_tier_weights"

if __name__ == "__main__":
    check_c3_bypass()
    check_time_sleep_and_cheats()
    check_frontend_monkey_patch()
    check_c3_dynamic_execution()
    print("\nAll initial script checks finished.")
