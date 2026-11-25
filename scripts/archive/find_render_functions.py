import re

with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    gui_text = f.read()

print("Rendering functions in app_gui.py:")
for m in re.finditer(r"^def (render_\w+)\((.*?)\):", gui_text, re.MULTILINE):
    print(f"  {m.group(1)}")

with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py", "r", encoding="utf-8") as f:
    bridge_text = f.read()

print("\nRendering functions in strategy_bridge.py:")
for m in re.finditer(r"^def (render_\w+)\((.*?)\):", bridge_text, re.MULTILINE):
    print(f"  {m.group(1)}")
