"""
Agent-1 Milestone 1 (M1) 核心功能综合检验脚本
覆盖:
1. 废除硬编码限额，fetch_realtime_fund_quota 三级缓存、契约规范与状态解析
2. 美股 gb_inx 指数代码前缀与字段映射 (parts[2] 涨跌幅, parts[4] 涨跌额)
3. QDII 与跨市场基金盘中估值纠偏 (gszzl 偏差 > 1.5% 触发 benchmark * 0.95 覆盖并标记 valuation_corrected)
4. 多级瀑布流拆单算法与表格一致性 (action_guide 动态文案)
5. 全赛道备选额度耗尽时的 dca_plan 自动生成
6. generate_rebalance_plan 调仓拆单集成
"""

import sys
from pathlib import Path
from unittest.mock import patch

# 确保 AGY2_FundAdvisory 在 sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "AGY2_FundAdvisory"))
sys.path.insert(0, str(root_dir))

from portfolio_manager import (
    PortfolioManager,
    fetch_realtime_fund_quota,
    fetch_realtime_index_quote,
    fetch_realtime_fund_quote,
    clear_realtime_cache,
    FundQuote
)

def test_m1_all():
    print("=== 1. fetch_realtime_fund_quota 契约与限额测试 ===")
    q_spx = fetch_realtime_fund_quota("050025")
    assert q_spx["fund_code"] == "050025"
    assert q_spx["status"] == "限制大额"
    assert q_spx["daily_limit"] == 500.0
    assert q_spx["is_limited"] is True

    q_morgan = fetch_realtime_fund_quota("001071")
    assert q_morgan["fund_code"] == "001071"
    assert q_morgan["status"] == "开放申购"
    assert q_morgan["daily_limit"] == 1e11
    assert q_morgan["is_limited"] is False

    q_pause = fetch_realtime_fund_quota("018757")
    assert q_pause["fund_code"] == "018757"
    assert q_pause["status"] == "暂停申购"
    assert q_pause["daily_limit"] == 0.0
    assert q_pause["is_limited"] is True
    print("Quota tests passed!")

    print("=== 2. fetch_realtime_index_quote 美股 gb_inx 指数测试 ===")
    clear_realtime_cache()
    fake_sina_us = 'var hq_str_gb_inx="标普500指数,7580.0698,-1.82,2026-10-30 17:00:00,-140.32,7720.39,7560.10,7720.39,7560.10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-10-30 17:00:00,7720.39,0.00,0,0.00,0.00,0.00,0.00";'
    with patch("urllib.request.urlopen") as mock_url:
        mock_url.return_value.__enter__.return_value.read.return_value = fake_sina_us.encode("gbk")
        idx_q = fetch_realtime_index_quote("gb_inx", use_cache=False)
        assert idx_q["name"] == "标普500指数"
        assert abs(idx_q["point"] - 7580.0698) < 1e-4
        assert abs(idx_q["change_pct"] - (-1.82)) < 1e-4
        assert abs(idx_q["change"] - (-140.32)) < 1e-4
    print("US Index quote test passed:", idx_q)

    print("=== 3. fetch_realtime_fund_quote QDII 估值纠偏测试 ===")
    clear_realtime_cache()
    fake_ttjj_distorted = 'jsonpgz({"fundcode":"001071","name":"摩根标普500","jzrq":"2026-10-29","dwjz":"1.5000","gsz":"1.4262","gszzl":"-4.92","gztime":"2026-10-30 15:00"});'
    with patch("urllib.request.urlopen") as mock_url:
        def fake_fetch(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            class MockResp:
                def __init__(self, data):
                    self._data = data
                def read(self):
                    return self._data
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            if "fundgz.1234567.com.cn" in url:
                return MockResp(fake_ttjj_distorted.encode("utf-8"))
            elif "hq.sinajs.cn" in url:
                return MockResp(b'var hq_str_s_sh513500="\xb1\xea\xc6\xd5500,1.850,0.009,0.50,12345,67890";')
            return MockResp(b"")
        mock_url.side_effect = fake_fetch
        q_corrected = fetch_realtime_fund_quote("001071", use_cache=False)
        print("q_corrected:", q_corrected)
        assert q_corrected.valuation_corrected is True
        assert abs(q_corrected.gszzl - 0.47) < 1e-3
        assert abs(q_corrected.gsz - round(1.5000 * (1.0 + 0.47 / 100.0), 4)) < 1e-4
        assert "纠偏" in q_corrected.gztime
    print("QDII valuation correction test passed!")

    print("=== 4. 瀑布流限购拆单与 DCA Plan 测试 ===")
    bp = PortfolioManager.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
    items_050025 = [it for it in bp["items"] if it["fund_code"] == "050025"]
    items_001071 = [it for it in bp["items"] if it["fund_code"] == "001071"]
    assert len(items_050025) == 1
    assert len(items_001071) == 1
    assert items_050025[0]["allocated_amount"] == 500.0
    assert items_050025[0]["action_guide"] == "单日限额¥500·已拆单"
    assert items_001071[0]["allocated_amount"] == 5500.0
    assert items_001071[0]["action_guide"] == "承接超额·不限购正常买"
    print("Blueprint waterfall splitting test passed!")

    with patch("portfolio_manager.fetch_realtime_fund_quota") as mock_q:
        def fake_quota(code, *args, **kwargs):
            if code == "050025":
                return {"fund_code": code, "status": "限制大额", "daily_limit": 500.0, "is_limited": True}
            elif code in ["001071", "006075", "017436"]:
                return {"fund_code": code, "status": "限制大额", "daily_limit": 1000.0, "is_limited": True}
            return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}
        mock_q.side_effect = fake_quota
        bp_dca = PortfolioManager.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
        print("bp_dca dca_plan:", bp_dca.get("dca_plan"))
        assert "dca_plan" in bp_dca
        assert "定投" in bp_dca["dca_plan"]
    print("DCA Plan generation test passed!")

    print("=== 5. generate_rebalance_plan 调仓拆单测试 ===")
    pm = PortfolioManager(":memory:")
    pm.available_cash = 20000.0
    pm.takeover_mode_a(fund_items=[], available_cash=20000.0)
    target_weights = {"050025": 0.25}
    plan = pm.generate_rebalance_plan(target_weights=target_weights, min_buffer_pct=3.0)
    routes = plan["routes"]
    assert len(routes) == 1
    assert routes[0]["buy_amount"] == 500.0
    assert routes[0]["overflow_amount"] == 4500.0
    assert routes[0]["fallback_code"] == "001071"
    assert routes[0]["action_guide"] == "单日限额¥500·已拆单"
    assert routes[0]["overflow_action_guide"] == "承接超额·不限购正常买"
    oids = pm.submit_rebalance_orders(routes)
    assert len(oids) == 2
    assert any(o.fund_code == "050025" and o.amount == 500.0 for o in pm.pending_orders)
    assert any(o.fund_code == "001071" and o.amount == 4500.0 for o in pm.pending_orders)
    print("Rebalance plan quota splitting test passed!")

    print("\n>>> ALL M1 VERIFICATIONS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_m1_all()
