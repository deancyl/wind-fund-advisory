import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for target in [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")
    
    # 增加 CSS 类
    if ".sec-chg-up" not in content:
        css_anchor = "/* 侧边栏折叠箭头 << 强制亮白可见 */"
        css_add = """        /* 自选板块涨跌红绿语义色高亮 (G41) */
        .sec-chg-up, [data-testid="stSidebar"] .sec-chg-up {
            color: #F87171 !important;
        }
        .sec-chg-down, [data-testid="stSidebar"] .sec-chg-down {
            color: #4ADE80 !important;
        }
        .sec-chg-flat, [data-testid="stSidebar"] .sec-chg-flat {
            color: #94A3B8 !important;
        }
        
        """
        assert css_anchor in content, f"css_anchor not found in {target}"
        content = content.replace(css_anchor, css_add + css_anchor)

    # 替换自选板块渲染
    old_loop = """    _watchlist_items = load_sector_watchlist()[:5]
    for _sec in _watchlist_items:
        _spct = fetch_sector_change_pct(_sec)
        _scol = "#F87171" if _spct > 0 else ("#4ADE80" if _spct < 0 else "#94A3B8")
        _ssign = "+" if _spct > 0 else ""
        st.markdown(f'''<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 8px;margin-bottom:2px;background:rgba(255,255,255,0.05);border-radius:5px;font-size:11.5px;line-height:20px;">
            <span style="font-weight:500;color:#E2E8F0 !important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:105px;">{_sec.get('name', '')}</span>
            <span style="font-variant-numeric:tabular-nums;color:#94A3B8 !important;font-size:10.5px;">{_sec.get('code', '')}</span>
            <span style="font-weight:700;color:{_scol} !important;font-variant-numeric:tabular-nums;min-width:52px;text-align:right;">{_ssign}{_spct:.2f}%</span>
        </div>''', unsafe_allow_html=True)"""

    new_loop = """    _watchlist_items = load_sector_watchlist()[:5]
    for _sec in _watchlist_items:
        _spct = fetch_sector_change_pct(_sec)
        _scol = "#F87171" if _spct > 0 else ("#4ADE80" if _spct < 0 else "#94A3B8")
        _scls = "sec-chg-up" if _spct > 0 else ("sec-chg-down" if _spct < 0 else "sec-chg-flat")
        _ssign = "+" if _spct > 0 else ""
        st.markdown(f'''<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 8px;margin-bottom:2px;background:rgba(255,255,255,0.05);border-radius:5px;font-size:11.5px;line-height:20px;">
            <span style="font-weight:500;color:#E2E8F0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:105px;">{_sec.get('name', '')}</span>
            <span style="font-variant-numeric:tabular-nums;color:#94A3B8;font-size:10.5px;">{_sec.get('code', '')}</span>
            <span class="{_scls}" style="font-weight:700;color:{_scol};font-variant-numeric:tabular-nums;min-width:52px;text-align:right;">{_ssign}{_spct:.2f}%</span>
        </div>''', unsafe_allow_html=True)"""

    assert old_loop in content, f"old_loop not found in {target}"
    content = content.replace(old_loop, new_loop)
    ast.parse(content, filename=str(target))
    target.write_text(content, encoding="utf-8")
    print(f"[OK] Enhanced watchlist colors in {target}")
