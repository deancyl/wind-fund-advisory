import re

test_files = [
    r"d:\Google\Workspace\Wind\tests\test_gui_multi_ledger_stress.py",
    r"d:\Google\Workspace\Wind\tests\test_infra.py",
    r"d:\Google\Workspace\Wind\tests\test_adv_final_closure.py",
    r"d:\Google\Workspace\Wind\tests\test_g3_evolution_loop.py",
]

for tf in test_files:
    print(f"\n=================== Scanning {tf} ===================")
    try:
        with open(tf, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for idx, line in enumerate(lines):
            l = line.strip()
            # check for tab2, button, key, AppTest, selectbox, radio, data_editor, expander, etc.
            if any(k in l.lower() for k in ["tab2", "ledger", "持仓", "调仓", "apptest", "btn_", "sel_", "pop_"]):
                print(f"{idx+1}: {l[:110]}")
    except Exception as e:
        print(f"Error reading {tf}: {e}")
