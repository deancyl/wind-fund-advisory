import os
import sys
import unittest.mock as mock
import pandas as pd
import tempfile
import urllib.error

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("AGY2_FundAdvisory"))

from AGY2_FundAdvisory.data_loader import (
    sync_macro_and_fx_parquet_if_stale,
    fetch_realtime_usdcnh_fx,
    fetch_macro_cross_market_indicators,
    DataLoader
)
from AGY2_FundAdvisory.advisory_engine import (
    compute_ten_dimension_votes,
    generate_chief_advisor_memo
)

def test_sync_network_timeout_and_graceful_fallback():
    """Adversarial Test 1: Simulating total network timeout on both akshare and sina."""
    print("Running test_sync_network_timeout_and_graceful_fallback...")
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
        with mock.patch("akshare.bond_zh_us_rate", side_effect=TimeoutError("Akshare timed out")):
            # Force sync with timeout
            res = sync_macro_and_fx_parquet_if_stale(force=True, timeout=0.1)
            assert res["success"] is True
            assert "fallback" in res["details"]["bond"] or "error" in res["details"]["bond"]
            assert "fallback" in res["details"]["fx"] or "error" in res["details"]["fx"]
            # Verify it preserved real dates from local parquet
            assert res["treasury_date"] == "2026-11-13"
            assert res["fx_date"] == "2026-11-14"
    print("  -> Passed!")

def test_fetch_realtime_usdcnh_garbage_defense():
    """Adversarial Test 2: Simulating Sina returning crazy out-of-bound exchange rates."""
    print("Running test_fetch_realtime_usdcnh_garbage_defense...")
    fake_sina_response = b'var hq_str_fx_susdcnh="08:00:00,99.9999,6.6700,6.6700,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-11-15,";'
    with mock.patch("urllib.request.urlopen") as mock_url:
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = fake_sina_response
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        # Should reject 99.9999 and fall back to valid parquet rate without raising or crashing
        res = fetch_realtime_usdcnh_fx(use_cache=False)
        assert 5.0 <= float(res) <= 9.0
        assert float(res) != 99.9999
        assert float(res) != 7.2385
    print("  -> Passed!")

def test_fetch_macro_cross_market_indicators_no_fake_constants():
    """Adversarial Test 3: Output indicators contain zero fake constants."""
    print("Running test_fetch_macro_cross_market_indicators_no_fake_constants...")
    ind = fetch_macro_cross_market_indicators(use_cache=True)
    assert ind["us_10y"] != 4.4200
    assert ind["cgb_us_spread_bp"] != -278.2
    assert ind["usdcnh_rate"] != 7.2385
    assert ind["treasury_date"] == "2026-11-13"
    assert ind["usdcnh_date"] in ("2026-11-14", "2026-11-15", "2026-11-16")
    print("  -> Passed!")

def test_chief_advisor_memo_key_information_insights():
    """Adversarial Test 4: Key information insights structure and semantic integrity."""
    print("Running test_chief_advisor_memo_key_information_insights...")
    memo = generate_chief_advisor_memo()
    assert "key_information_insights" in memo
    insights = memo["key_information_insights"]
    assert len(insights) >= 5

    categories = [i["category"] for i in insights]
    assert "宏观政策与利率" in categories
    assert "国际汇率与利差" in categories
    assert "产业估值与赛道" in categories
    assert "存量病灶与风控" in categories
    assert "实时要闻与尾盘异动" in categories

    for item in insights:
        for field in ["category", "badge", "key_information", "deep_understanding", "action_taken"]:
            assert field in item, f"Missing field {field} in insight: {item}"
            assert isinstance(item[field], str) and len(item[field].strip()) > 0
        # No fake constants
        assert "7.2385" not in item["key_information"]
        assert "4.4200" not in item["key_information"]
        assert "-278.2" not in item["key_information"]
    print("  -> Passed!")

def test_ten_dimension_votes_no_hardcoded_overrides():
    """Adversarial Test 5: Verify ten dimension model does not override with fake constants."""
    print("Running test_ten_dimension_votes_no_hardcoded_overrides...")
    res = compute_ten_dimension_votes()
    dims = res["dimensions"]
    assert len(dims) == 10
    intl = next((d for d in dims if d["dimension"] == "国际联动"), None)
    fx = next((d for d in dims if d["dimension"] == "外汇锁汇"), None)
    assert intl is not None
    assert fx is not None
    assert "4.4200" not in intl["reason"]
    assert "-278.2" not in intl["reason"]
    assert "7.2385" not in fx["reason"]
    print("  -> Passed!")

if __name__ == "__main__":
    test_sync_network_timeout_and_graceful_fallback()
    test_fetch_realtime_usdcnh_garbage_defense()
    test_fetch_macro_cross_market_indicators_no_fake_constants()
    test_chief_advisor_memo_key_information_insights()
    test_ten_dimension_votes_no_hardcoded_overrides()
    print("\nALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
