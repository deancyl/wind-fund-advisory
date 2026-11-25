import sys
import os

# Add workspace to sys.path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("AGY2_FundAdvisory"))

from AGY2_FundAdvisory.data_loader import DataLoader
from AGY2_FundAdvisory.advisory_engine import compute_ten_dimension_votes, generate_chief_advisor_memo

def test_sync_function():
    print("--- Testing sync_macro_and_fx_parquet_if_stale ---")
    res = DataLoader.sync_macro_and_fx_parquet_if_stale(force=False)
    print("Sync result success:", res.get("success"))
    print("treasury_date:", res.get("treasury_date"))
    print("fx_date:", res.get("fx_date"))
    print("gold_date:", res.get("gold_date"))
    print("details:", res.get("details"))
    assert res.get("success") is True
    assert res.get("treasury_date") == "2026-11-13"
    assert res.get("fx_date") == "2026-11-14"

def test_fetch_realtime_usdcnh_fx():
    print("\n--- Testing fetch_realtime_usdcnh_fx ---")
    fx = DataLoader.fetch_realtime_usdcnh_fx(use_cache=True)
    print("Rate:", fx.get("rate"), "float value:", float(fx))
    print("Date:", fx.get("date"))
    print("Source:", fx.get("source"))
    print("Change pct:", fx.get("change_pct"))
    assert 5.0 <= float(fx) <= 9.0
    assert float(fx) != 7.2385
    assert fx.get("date") in ("2026-11-14", "2026-11-15", "2026-11-16")

def test_fetch_macro_cross_market_indicators():
    print("\n--- Testing fetch_macro_cross_market_indicators ---")
    macro = DataLoader.fetch_macro_cross_market_indicators(use_cache=True)
    print("cgb_10y:", macro.get("cgb_10y"))
    print("us_10y:", macro.get("us_10y"))
    print("cgb_us_spread_bp:", macro.get("cgb_us_spread_bp"))
    print("usdcnh_rate:", macro.get("usdcnh_rate"))
    print("treasury_date:", macro.get("treasury_date"))
    print("usdcnh_date:", macro.get("usdcnh_date"))
    assert macro.get("us_10y") != 4.4200
    assert macro.get("cgb_us_spread_bp") != -278.2
    assert macro.get("usdcnh_rate") != 7.2385
    assert macro.get("treasury_date") == "2026-11-13"

def test_compute_ten_dimension_votes():
    print("\n--- Testing compute_ten_dimension_votes ---")
    macro = DataLoader.fetch_macro_cross_market_indicators(use_cache=True)
    votes = compute_ten_dimension_votes(macro_multi=macro)
    dimensions = votes.get("dimensions", [])
    print("Total dimensions:", len(dimensions))
    print("Total score:", votes.get("summary", {}).get("total_score"))
    print("Verdict:", votes.get("summary", {}).get("verdict"))
    print("Causal formula:", votes.get("causal_formula"))
    d4 = next((d for d in dimensions if d["dimension"] == "国际联动"), None)
    d5 = next((d for d in dimensions if d["dimension"] == "外汇锁汇"), None)
    print("D4 (国际联动):", d4)
    print("D5 (外汇锁汇):", d5)
    assert d4 is not None
    assert "4.4200" not in d4.get("reason", "")
    assert "-278.2" not in d4.get("reason", "")
    assert d5 is not None
    assert "7.2385" not in d5.get("reason", "")

def test_generate_chief_advisor_memo():
    print("\n--- Testing generate_chief_advisor_memo ---")
    memo = generate_chief_advisor_memo()
    insights = memo.get("key_information_insights", [])
    print(f"Number of insights: {len(insights)}")
    assert len(insights) >= 3, "Expected at least 3 insights"
    for i, item in enumerate(insights, 1):
        print(f"\n[Insight {i}]")
        print("  Category:", item.get("category"))
        print("  Badge:", item.get("badge"))
        print("  Key Info:", item.get("key_information"))
        print("  Understanding:", item.get("deep_understanding"))
        print("  Action:", item.get("action_taken"))
        assert "key_information" in item, "Missing key_information"
        assert "deep_understanding" in item, "Missing deep_understanding"
        assert "action_taken" in item, "Missing action_taken"
        assert item["key_information"].strip() != ""
        assert item["deep_understanding"].strip() != ""
        assert item["action_taken"].strip() != ""
        assert "7.2385" not in item["key_information"]
        assert "4.4200" not in item["key_information"]

if __name__ == "__main__":
    test_sync_function()
    test_fetch_realtime_usdcnh_fx()
    test_fetch_macro_cross_market_indicators()
    test_compute_ten_dimension_votes()
    test_generate_chief_advisor_memo()
    print("\nALL VERIFICATIONS PASSED!")
