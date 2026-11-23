# -*- coding: utf-8 -*-
"""
scripts/remodel_dual_screen_harmony_v2.py
精准修复桌面端与移动端双端排版：
1. 标记容器物理归零：彻底消除 .element-container 带来的 16px 垂直落差
2. 顶栏架构：
   - col_t_b 注入 .topbar-outer-marker
   - col_sel_ld 注入 .topbar-actions-marker
   - 外部主容器 selector: div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker)
   - 内部操作行 selector: div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"]:has(.topbar-actions-marker)
   - 桌面端：外层两端对齐，左侧品牌+时钟，右侧 460px 包含宽裕账本选择器 + 3 个 32px 紧凑图标
   - 移动端：外层垂直分两行，上行品牌+状态，下行账本选择器(260px) + 3 图标(34px)，上下间距留足 8px，完全杜绝裁切与折行
3. 移动端顶部指数行情条：
   - 移动端隐藏 .index-pill-val-badge（PE/分位），使 3 只核心指数横向直接排开
   - 右侧 ⚙️ 与 🔄 保持 32px 方形紧凑并排
4. 6 键操作工具栏：
   - 桌面端 6 列横排
   - 移动端 2×3 紧凑网格基线严格水平对齐
5. 处方重塑单行条：
   - 桌面端单行，移动端精致紧凑
"""

import ast
import shutil
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
APP_GUI = WORKSPACE_ROOT / "app_gui.py"
APP_GUI_MIRROR = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"


def remodel_v2():
    print(f"Reading {APP_GUI}...")
    with open(APP_GUI, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. 替换 CSS 规则块 (注意 f-string 需要双大括号 {{ 和 }})
    old_css_start = "    /* =========================================================================\n       方案 A 高定无侧栏双端响应式规约 (Dual-Screen Harmony Invariants v2.0)"
    old_css_end = "    /* 顶部紧凑单行指数走廊横条 (Top Compact Index Ticker Strip) */"

    new_css_block = """    /* =========================================================================
       方案 A 高定无侧栏双端响应式规约 (Dual-Screen Harmony Invariants v2.0)
       ========================================================================= */
    /* 0. 专用标记容器物理归零（彻底消除空容器造成的垂直偏移） */
    div.element-container:has(.topbar-outer-marker),
    div.element-container:has(.topbar-actions-marker),
    div.element-container:has(.ticker-strip-marker),
    div.element-container:has(.prescription-action-marker),
    div.element-container:has(.toolbar-6col-marker) {{
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    /* 1. 顶栏外层主容器：桌面端水平两极布局，移动端优雅垂直分层 */
    div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        width: 100% !important;
        margin-bottom: 2px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="column"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="stColumn"]:first-child {{
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="column"]:last-child,
    div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="stColumn"]:last-child {{
        flex: 0 0 460px !important;
        min-width: 380px !important;
        max-width: 500px !important;
        width: 460px !important;
    }}
    @media (max-width: 768px) {{
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) {{
            flex-direction: column !important;
            align-items: stretch !important;
            gap: 8px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="column"]:first-child,
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="stColumn"]:first-child {{
            flex: 1 1 auto !important;
            min-width: 100% !important;
            max-width: 100% !important;
            width: 100% !important;
            height: auto !important;
            min-height: auto !important;
            overflow: visible !important;
            margin-bottom: 4px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="column"]:last-child,
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="stColumn"]:last-child {{
            flex: 1 1 auto !important;
            min-width: 100% !important;
            max-width: 100% !important;
            width: 100% !important;
            height: auto !important;
            min-height: auto !important;
            overflow: visible !important;
        }}
    }}

    /* 2. 顶栏右侧内层操作行（账本选择器 + 🎨 + i + ↩️）：通过祖先选择器严格锁定内层，绝不误伤外层容器 */
    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"]:has(.topbar-actions-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
        width: 100% !important;
    }}
    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"]:has(.topbar-actions-marker) > div[data-testid="column"]:first-child,
    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"]:has(.topbar-actions-marker) > div[data-testid="stColumn"]:first-child {{
        flex: 1 1 auto !important;
        min-width: 180px !important;
        max-width: none !important;
        width: auto !important;
    }}
    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"]:has(.topbar-actions-marker) > div[data-testid="column"]:not(:first-child),
    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"]:has(.topbar-actions-marker) > div[data-testid="stColumn"]:not(:first-child) {{
        flex: 0 0 34px !important;
        min-width: 34px !important;
        max-width: 34px !important;
        width: 34px !important;
    }}
    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"]:has(.topbar-actions-marker) button {{
        width: 32px !important;
        min-width: 32px !important;
        max-width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 6px !important;
    }}

    /* 3. 顶部单行指数行情横条专用布局（桌面与移动端统一不换行，左滑右固） */
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
        width: 100% !important;
        margin-top: 2px !important;
        margin-bottom: 6px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="column"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="stColumn"]:first-child {{
        flex: 1 1 auto !important;
        min-width: 0 !important;
        max-width: none !important;
        width: auto !important;
        overflow-x: auto !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="column"]:not(:first-child),
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="stColumn"]:not(:first-child) {{
        flex: 0 0 34px !important;
        min-width: 34px !important;
        max-width: 34px !important;
        width: 34px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) button {{
        width: 32px !important;
        min-width: 32px !important;
        max-width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 13px !important;
        border-radius: 6px !important;
    }}
    @media (max-width: 768px) {{
        .top-index-pill .index-pill-val-badge {{
            display: none !important;
        }}
        .top-index-pill {{
            padding: 3px 6px !important;
            font-size: 11px !important;
            gap: 4px !important;
        }}
    }}

    /* 4. 处方重塑单行条防膨胀规约 */
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 6px !important;
        margin-bottom: 6px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="column"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="stColumn"]:first-child {{
        flex: 0 0 auto !important;
        min-width: 100px !important;
        width: auto !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="column"]:nth-child(2),
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="stColumn"]:nth-child(2) {{
        flex: 0 0 34px !important;
        min-width: 34px !important;
        max-width: 34px !important;
        width: 34px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="column"]:last-child,
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="stColumn"]:last-child {{
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) button[data-testid="stPopoverButton"] {{
        width: 32px !important;
        min-width: 32px !important;
        max-width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    /* 5. 6 键操作工具栏：桌面端 6 列横排，移动端 2 行 3 列平铺 */
    div[data-testid="stHorizontalBlock"]:has(.toolbar-6col-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        width: 100% !important;
        margin-bottom: 4px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.toolbar-6col-marker) > div[data-testid="column"],
    div[data-testid="stHorizontalBlock"]:has(.toolbar-6col-marker) > div[data-testid="stColumn"] {{
        flex: 1 1 16.666% !important;
        min-width: 0 !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.toolbar-6col-marker) button {{
        height: 34px !important;
        min-height: 34px !important;
        font-size: 12px !important;
        padding: 0 4px !important;
    }}
    @media (max-width: 768px) {{
        div[data-testid="stHorizontalBlock"]:has(.toolbar-6col-marker) {{
            flex-wrap: wrap !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.toolbar-6col-marker) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has(.toolbar-6col-marker) > div[data-testid="stColumn"] {{
            flex: 1 1 calc(33.333% - 4px) !important;
            min-width: calc(33.333% - 4px) !important;
            max-width: calc(33.333% - 4px) !important;
        }}
    }}
"""

    if old_css_start in code and old_css_end in code:
        idx1 = code.find(old_css_start)
        idx2 = code.find(old_css_end)
        code = code[:idx1] + new_css_block + "\n" + code[idx2:]
        print("  [OK] Successfully replaced CSS rules block with 8px margin spacing")
    else:
        print("  [ERROR] Old CSS markers not matched!")
        return False

    # AST 语法检验
    print("Verifying AST...")
    ast.parse(code)
    print("AST verification passed!")

    # 写回并镜像同步
    with open(APP_GUI, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully written to {APP_GUI}")

    with open(APP_GUI_MIRROR, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully mirrored to {APP_GUI_MIRROR}")
    return True


if __name__ == "__main__":
    remodel_v2()
