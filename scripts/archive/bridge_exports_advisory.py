from pathlib import Path

TARGET = Path("AGY2_FundAdvisory/advisory_engine.py")
content = TARGET.read_text(encoding="utf-8")

if "find_same_company_conversions" not in content:
    bridge_export = """

# 下沉工具方法便捷导出 (保持向后兼容)
try:
    from AGY2_FundAdvisory.strategy_bridge import find_same_company_conversions, evaluate_macro_dividend_policy
except ImportError:
    try:
        from strategy_bridge import find_same_company_conversions, evaluate_macro_dividend_policy
    except ImportError:
        find_same_company_conversions = None
        evaluate_macro_dividend_policy = None
"""
    content += bridge_export
    TARGET.write_text(content, encoding="utf-8")
    print("✅ Successfully bridged exports in advisory_engine.py!")
else:
    print("Already present.")
