import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import unittest
from unittest.mock import MagicMock, patch

from AGY2_FundAdvisory.app_gui import (
    render_chief_advisor_memo_card,
    safe_markdown_html,
    _clean_html,
)
from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo

def test_ui_adversarial():
    print("=== 1. Testing _clean_html against CommonMark 4-space code block leakage ===")
    test_cases = [
        # 4 spaces at line start
        ("<div>\n    <p>Indented line with 4 spaces</p>\n</div>", "Indented line with 4 spaces"),
        # 8 spaces at line start
        ("<div>\n        <p>Indented line with 8 spaces</p>\n</div>", "Indented line with 8 spaces"),
        # Tab indentation
        ("<div>\n\t<p>Tab indented</p>\n</div>", "Tab indented"),
        # Multiple blank lines
        ("<div>\n\n\n    <p>Multiple blank lines</p>\n\n\n</div>", "Multiple blank lines"),
        # Trailing spaces
        ("<div>   \n    <p>Trailing and leading</p>   \n</div>  ", "Trailing and leading"),
    ]
    for raw_html, target_sub in test_cases:
        cleaned = _clean_html(raw_html)
        # Check that no line in cleaned starts with 4 or more spaces
        for line in cleaned.splitlines():
            assert not line.startswith("    "), f"CommonMark leak risk! Line starts with 4 spaces: '{line}'"
            assert not line.startswith("\t"), f"CommonMark leak risk! Line starts with tab: '{line}'"
            assert len(line.strip()) == len(line), f"Line has unstripped whitespace: '{line}'"
        assert target_sub in cleaned
    print("✓ _clean_html successfully strips all leading 4-space, 8-space, tab, and blank lines.")

    print("\n=== 2. Testing render_chief_advisor_memo_card with normal memo ===")
    normal_memo = generate_chief_advisor_memo()
    with patch("streamlit.markdown") as mock_st_markdown:
        render_chief_advisor_memo_card(normal_memo)
        assert mock_st_markdown.called, "st.markdown was not called for normal memo"
        rendered_arg = mock_st_markdown.call_args[0][0]
        # Verify rendered HTML does not contain 4-space indentation anywhere
        for idx, line in enumerate(rendered_arg.splitlines()):
            assert not line.startswith("    "), f"Line {idx} in rendered HTML starts with 4 spaces: '{line}'"
    print("✓ Normal memo renders cleanly via safe_markdown_html without 4-space leaks.")

    print("\n=== 3. Testing render_chief_advisor_memo_card with HTML injection strings ===")
    injection_memo = generate_chief_advisor_memo()
    injection_memo["macro_policy"]["content"] = "<script>alert('xss')</script>\n    <b>Bold Attack</b>"
    injection_memo["action_directive"]["content"] = "</div><div style='background:red'>Broken Tag Attack</div>"
    with patch("streamlit.markdown") as mock_st_markdown:
        render_chief_advisor_memo_card(injection_memo, title="<img src=x onerror=alert(1)> Title")
        assert mock_st_markdown.called
        rendered_arg = mock_st_markdown.call_args[0][0]
        for line in rendered_arg.splitlines():
            assert not line.startswith("    "), f"Line starts with 4 spaces in injection test: '{line}'"
    print("✓ Injection memo handled cleanly without code block leakage.")

    print("\n=== 4. Testing render_chief_advisor_memo_card with Empty/Partial/Malformed inputs ===")
    # 4.1 None and {}
    with patch("streamlit.markdown") as mock_st_markdown:
        render_chief_advisor_memo_card(None)
        assert not mock_st_markdown.called
        render_chief_advisor_memo_card({})
        assert not mock_st_markdown.called
    print("✓ None and {} are handled gracefully without rendering.")

    # 4.2 Partial dictionary (only some keys present)
    partial_memo = {
        "timestamp": "2026-11-09",
        "macro_policy": {"badge": "🟢 测试", "content": "测试内容"},
        # other keys missing
    }
    with patch("streamlit.markdown") as mock_st_markdown:
        render_chief_advisor_memo_card(partial_memo)
        assert mock_st_markdown.called
        print("✓ Partial dictionary with missing sub-keys handled without raising exception.")

    # 4.3 Malformed inputs: non-dict values for sub-keys
    malformed_cases = [
        ("None sub-key", {"macro_policy": None}),
        ("String sub-key", {"macro_policy": "string_value"}),
        ("List sub-key", {"portfolio_pathology": [1, 2, 3]}),
        ("Integer sub-key", {"action_directive": 999}),
        ("Non-dict memo_data string", "not_a_dict_at_all"),
        ("Non-dict memo_data list", [1, 2, 3]),
    ]
    crashes = []
    for desc, malformed_val in malformed_cases:
        try:
            render_chief_advisor_memo_card(malformed_val)
        except Exception as e:
            crashes.append((desc, type(e).__name__, str(e)))

    print(f"Malformed inputs crash count: {len(crashes)} / {len(malformed_cases)}")
    for desc, exc_name, exc_msg in crashes:
        print(f"  [CRASH DETECTED] {desc} -> {exc_name}: {exc_msg}")

    return crashes

if __name__ == "__main__":
    test_ui_adversarial()
