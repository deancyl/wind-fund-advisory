from pathlib import Path

GUI_FILE = Path("AGY2_FundAdvisory/app_gui.py")

def main():
    content = GUI_FILE.read_text(encoding="utf-8")
    content_norm = content.replace("\r\n", "\n")

    target = """        # 步骤三：【⚖️ 调仓方案与执行单】（四大后果 + 建议执行单）
        # ---------------------------------------------------------
        if st.session_state.get("tab2_rebalanced", False):"""

    replacement = """        # 步骤三：【⚖️ 调仓方案与执行单】（四大后果 + 建议执行单）
        # ---------------------------------------------------------
        if is_t2_main_mode and st.session_state.get("tab2_rebalanced", False):"""

    assert target in content_norm, "target not found"
    content_norm = content_norm.replace(target, replacement, 1)
    GUI_FILE.write_text(content_norm, encoding="utf-8")
    print("✅ 成功为步骤三加入 is_t2_main_mode 保护分支！")

if __name__ == "__main__":
    main()
