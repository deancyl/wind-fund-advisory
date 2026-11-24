import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OLD_PART1 = """    /* G40 私人银行曜石蓝深色侧边栏 + 桌面端绝对零滚动死锁 */
    @media (min-width: 769px) {{
        [data-testid="stSidebar"] {{
            background-color: #0F1C2E !important;
            width: 248px !important;
            min-width: 248px !important;
            max-width: 248px !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            height: 100vh !important;
            max-height: 100vh !important;
            overflow-y: hidden !important;
            padding: 14px 14px 12px 14px !important;
            display: flex !important;
            flex-direction: column !important;
            box-sizing: border-box !important;
        }}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 0.45rem !important;
        }}
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {{
            color: #E2E8F0 !important;
        }}
        [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {{
            color: #94A3B8 !important;
        }}
    }}"""

NEW_PART1 = """    /* G40 私人银行曜石蓝深色侧边栏 + 桌面端绝对零滚动死锁 */
    @media (min-width: 769px) {{
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebarContent"],
        [data-testid="stSidebarUserContent"] {{
            background-color: #0F1C2E !important;
            background: #0F1C2E !important;
        }}
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"] {{
            width: 256px !important;
            min-width: 256px !important;
            max-width: 256px !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            height: 100vh !important;
            max-height: 100vh !important;
            overflow-y: hidden !important;
            padding: 14px 14px 12px 14px !important;
            display: flex !important;
            flex-direction: column !important;
            box-sizing: border-box !important;
        }}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 0.45rem !important;
        }}
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {{
            color: #E2E8F0 !important;
        }}
        [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {{
            color: #94A3B8 !important;
        }}
        [data-testid="stSidebar"] button:not([kind="primary"]) {{
            background: rgba(255, 255, 255, 0.06) !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            color: #E2E8F0 !important;
        }}
        [data-testid="stSidebar"] button:not([kind="primary"]):hover {{
            background: rgba(255, 255, 255, 0.12) !important;
            border-color: rgba(255, 255, 255, 0.25) !important;
        }}
        [data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
            background: rgba(255, 255, 255, 0.06) !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            color: #E2E8F0 !important;
        }}
    }}"""

OLD_PART2 = """    /* 桌面端专业侧边栏 (方案 B：Windows .exe 桌面客户端质感) */
    [data-testid="stSidebar"] {{
        display: block !important;
        visibility: visible !important;
        min-width: 270px !important;
        max-width: 300px !important;
        background: var(--bg-surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }}"""

NEW_PART2 = """    /* 桌面端专业侧边栏 (方案 B：Windows .exe 桌面客户端质感) */
    [data-testid="stSidebar"] {{
        display: block !important;
        visibility: visible !important;
    }}"""

targets = [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]

for target in targets:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")
    assert OLD_PART1 in content, f"OLD_PART1 not found in {target}"
    assert OLD_PART2 in content, f"OLD_PART2 not found in {target}"
    content = content.replace(OLD_PART1, NEW_PART1)
    content = content.replace(OLD_PART2, NEW_PART2)
    ast.parse(content, filename=str(target))
    target.write_text(content, encoding="utf-8")
    print(f"Successfully patched {target}")
