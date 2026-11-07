"""
Script: fix_html_leak_bug.py
Purpose: 精准修复 app_gui.py 中由于原生 st.markdown 与多层前导空格引起的 HTML 裸代码块泄露 Bug。
遵循 Windows 命令行复杂替换与批量操作脚本化防御准则 (Rule 14)。
"""

from pathlib import Path

APP_GUI_PATH = Path("AGY2_FundAdvisory/app_gui.py")

def main():
    content = APP_GUI_PATH.read_text(encoding="utf-8")
    original_len = len(content)

    # 1. 修复 render_historical_inflection_ruler_html 的返回值，确保紧凑且包裹 _clean_html
    target_inflection_cards = '''        card = f"""
        <div class="inflection-node-card {'inflection-today-card' if is_today else ''}" style="border: 1.5px solid {border}; background: {bg}; border-radius: 6px; padding: 6px 10px; min-width: 135px; flex: 1 1 0; box-sizing: border-box;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                <span style="font-size: 11px; font-weight: 700; color: {tag_color}; white-space: nowrap;">{badge_title}</span>
                <span style="font-size: 10px; color: var(--text-muted); font-family: monospace;">{d_str}</span>
            </div>
            <div style="display: flex; align-items: baseline; justify-content: space-between; gap: 4px;">
                <span style="font-size: 15px; font-weight: 800; font-family: monospace; color: {tag_color};">{mult:.2f}x</span>
                <span style="font-size: 10px; color: var(--text-secondary); white-space: nowrap;">{sub_lbl}</span>
            </div>
        </div>
        """
        cards_html.append(card)

    return f"""
    <div class="inflection-ruler-container" style="margin: 4px 0 6px 0; padding: 6px 8px; border-radius: 8px; background: var(--bg-canvas); border: 1px dashed var(--border-subtle);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-size: 11px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 4px;">
                <span>📏 历史三大牛熊拐点实盘对照尺</span>
                <span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(2021顶 0.50x ｜ 2022底 1.93x ｜ 2024底 1.94x ｜ 今日水位)</span>
            </span>
            <span style="font-size: 10px; color: var(--accent-primary); font-weight: 600;">定投扣款乘数对照</span>
        </div>
        <div class="inflection-ruler-scroll-row">
            {''.join(cards_html)}
        </div>
    </div>
    """'''

    replacement_inflection_cards = '''        card = (
            f'<div class="inflection-node-card {"inflection-today-card" if is_today else ""}" '
            f'style="border: 1.5px solid {border}; background: {bg}; border-radius: 6px; padding: 6px 10px; min-width: 135px; flex: 1 1 0; box-sizing: border-box;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">'
            f'<span style="font-size: 11px; font-weight: 700; color: {tag_color}; white-space: nowrap;">{badge_title}</span>'
            f'<span style="font-size: 10px; color: var(--text-muted); font-family: monospace;">{d_str}</span>'
            f'</div>'
            f'<div style="display: flex; align-items: baseline; justify-content: space-between; gap: 4px;">'
            f'<span style="font-size: 15px; font-weight: 800; font-family: monospace; color: {tag_color};">{mult:.2f}x</span>'
            f'<span style="font-size: 10px; color: var(--text-secondary); white-space: nowrap;">{sub_lbl}</span>'
            f'</div>'
            f'</div>'
        )
        cards_html.append(card)

    container_html = (
        f'<div class="inflection-ruler-container" style="margin: 4px 0 6px 0; padding: 6px 8px; border-radius: 8px; background: var(--bg-canvas); border: 1px dashed var(--border-subtle);">'
        f'<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">'
        f'<span style="font-size: 11px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 4px;">'
        f'<span>📏 历史三大牛熊拐点实盘对照尺</span>'
        f'<span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(2021顶 0.50x ｜ 2022底 1.93x ｜ 2024底 1.94x ｜ 今日水位)</span>'
        f'</span>'
        f'<span style="font-size: 10px; color: var(--accent-primary); font-weight: 600;">定投扣款乘数对照</span>'
        f'</div>'
        f'<div class="inflection-ruler-scroll-row">'
        f'{"".join(cards_html)}'
        f'</div>'
        f'</div>'
    )
    return _clean_html(container_html)'''

    # 处理换行符兼容性
    target_norm = target_inflection_cards.replace("\r\n", "\n")
    content_norm = content.replace("\r\n", "\n")
    if target_norm in content_norm:
        content_norm = content_norm.replace(target_norm, replacement_inflection_cards)
        print("✅ 成功替换 render_historical_inflection_ruler_html 内部构建逻辑")
    else:
        print("⚠️ 未直接匹配 target_inflection_cards，尝试正则或局部匹配")

    # 2. 修复 render_portfolio_cushion_and_stress_card_html 的返回值，确保包裹 _clean_html
    target_cushion_ret = """        <div class="cushion-scenarios-row">
            {''.join(scenario_cards)}
        </div>
    </div>
    \"\"\""""
    replacement_cushion_ret = """        <div class="cushion-scenarios-row">
            {''.join(scenario_cards)}
        </div>
    </div>
    \"\"\"
    return _clean_html(card_html)"""

    # 检查是否定义了 card_html 变量
    if "return f\"\"\"\n    <div class=\"decision-card cushion-stress-container\"" in content_norm:
        content_norm = content_norm.replace(
            "return f\"\"\"\n    <div class=\"decision-card cushion-stress-container\"",
            "card_html = f\"\"\"\n    <div class=\"decision-card cushion-stress-container\""
        )
        content_norm = content_norm.replace(
            target_cushion_ret,
            replacement_cushion_ret
        )
        print("✅ 成功包裹 render_portfolio_cushion_and_stress_card_html 返回值 _clean_html")

    # 3. 修复首屏晨报处的裸 HTML 泄露 (原先使用 st.markdown 拼接多行导致代码块逃逸)
    target_pulse_st = """                st.markdown(f\"\"\"
                <div class="decision-card" style="padding: 8px 12px; margin-bottom: 10px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
                        <span style="font-size: 11px; font-weight: 700; color: var(--accent-primary);">📢 今日市场脉搏晨报</span>
                        <span style="font-size: 10px; color: var(--text-secondary);">全景量化串联 ｜ 历史拐点并列对照</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-primary); line-height: 1.4; margin-bottom: 4px;">
                        {pulse_brief}
                    </div>
                    {ruler_bar_html}
                </div>
                \"\"\", unsafe_allow_html=True)"""

    replacement_pulse_st = """                pulse_card_html = f\"\"\"
                <div class="decision-card" style="padding: 8px 12px; margin-bottom: 10px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
                        <span style="font-size: 11px; font-weight: 700; color: var(--accent-primary);">📢 今日市场脉搏晨报</span>
                        <span style="font-size: 10px; color: var(--text-secondary);">全景量化串联 ｜ 历史拐点并列对照</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-primary); line-height: 1.4; margin-bottom: 4px;">
                        {pulse_brief}
                    </div>
                    {ruler_bar_html}
                </div>
                \"\"\"
                safe_markdown_html(pulse_card_html)"""

    if target_pulse_st in content_norm:
        content_norm = content_norm.replace(target_pulse_st, replacement_pulse_st)
        print("✅ 成功将首屏晨报 st.markdown 转换为 safe_markdown_html")
    else:
        print("⚠️ 未直接匹配 target_pulse_st")

    # 4. 修复 cols_top3 的卡片，确保也是 safe_markdown_html
    target_top3 = """                        st.markdown(f\"\"\"
                        <div class="decision-card" style="padding: 10px 12px; height: 100%; border-top: 2px solid {tag_color};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>
                                <span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec['tag']}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                                综合得分: <b style="color: var(--text-primary);">{sec['total_score']}</b> ｜ 估值分位: {sec['val_percentile']:.0f}%
                            </div>
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                                优选: {sec_fund.get('name', '')}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                代码: <code>{sec_fund.get('code', '')}</code>
                            </div>
                        </div>
                        \"\"\", unsafe_allow_html=True)"""

    replacement_top3 = """                        safe_markdown_html(f\"\"\"
                        <div class="decision-card" style="padding: 10px 12px; height: 100%; border-top: 2px solid {tag_color};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>
                                <span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec['tag']}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                                综合得分: <b style="color: var(--text-primary);">{sec['total_score']}</b> ｜ 估值分位: {sec['val_percentile']:.0f}%
                            </div>
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                                优选: {sec_fund.get('name', '')}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                代码: <code>{sec_fund.get('code', '')}</code>
                            </div>
                        </div>
                        \"\"\")"""

    if target_top3 in content_norm:
        content_norm = content_norm.replace(target_top3, replacement_top3)
        print("✅ 成功将 top3 赛道卡片 st.markdown 转换为 safe_markdown_html")
    else:
        print("⚠️ 未直接匹配 target_top3")

    # 写回文件（保留原生换行）
    APP_GUI_PATH.write_text(content_norm, encoding="utf-8")
    print("✨ 文件已成功写入，准备执行语法与渲染校验！")

if __name__ == "__main__":
    main()
