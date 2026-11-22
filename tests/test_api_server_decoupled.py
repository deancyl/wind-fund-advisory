# -*- coding: utf-8 -*-
"""
验证 api_server 完全脱离 Streamlit 依赖，并提供全套跨端 /api/v1/* 接口。
"""
import sys
import pytest


def test_api_server_no_streamlit():
    # 确保在导入 api_server 前若无 streamlit，导入后也不应引入 streamlit
    # 如果当前测试环境中已加载过 streamlit，检查 api_server 自身模块与 rebalance_grouping 模块均未导入 streamlit
    import api_server
    import rebalance_grouping
    # 静态断言其源码不含 streamlit import
    from pathlib import Path
    srv_txt = Path(api_server.__file__).read_text(encoding="utf-8")
    grp_txt = Path(rebalance_grouping.__file__).read_text(encoding="utf-8")
    assert "import streamlit" not in srv_txt
    assert "import streamlit" not in grp_txt
    assert "from ui_daily_brief" not in srv_txt


def test_api_server_v1_new_endpoints():
    from fastapi.testclient import TestClient
    import api_server
    client = TestClient(api_server.app)

    # 1. movers
    r_mov = client.get("/api/v1/holdings/movers")
    assert r_mov.status_code == 200
    j_mov = r_mov.json()
    assert "top_gainers" in j_mov and "top_losers" in j_mov

    # 2. checkin GET & POST
    r_ck = client.post("/api/v1/rebalance/checkin", json={"fund_code": "005561", "action": "BUY", "amount": 500.0, "checked": True})
    assert r_ck.status_code == 200
    assert "005561" in r_ck.json().get("checked_codes", {})

    r_get_ck = client.get("/api/v1/rebalance/checkin")
    assert r_get_ck.status_code == 200
    assert "005561" in r_get_ck.json().get("checked_codes", {})

    # 取消打卡
    client.post("/api/v1/rebalance/checkin", json={"fund_code": "005561", "action": "BUY", "amount": 500.0, "checked": False})

    # 3. alerts push
    r_alert = client.get("/api/v1/alerts/push")
    assert r_alert.status_code == 200
    j_al = r_alert.json()
    assert "alerts" in j_al and isinstance(j_al["alerts"], list)

    # 4. review subviews
    for sv in ["timemachine", "rolling_winrate", "forward_audit", "shadow_race"]:
        r_rev = client.get(f"/api/v1/review/{sv}")
        assert r_rev.status_code == 200, f"review/{sv} failed: {r_rev.text}"
        assert "<div" not in r_rev.text and "<span" not in r_rev.text

    # 5. diagnose subviews
    for sv in ["risk_check", "exposure", "overlap", "stress_test", "ten_dim_votes"]:
        r_diag = client.get(f"/api/v1/diagnose/{sv}")
        assert r_diag.status_code == 200, f"diagnose/{sv} failed: {r_diag.text}"
        assert "<div" not in r_diag.text and "<span" not in r_diag.text

    # 6. backtest summary
    r_bt = client.get("/api/v1/backtest/summary")
    assert r_bt.status_code == 200
