# -*- coding: utf-8 -*-
"""Verify api_server.py endpoints using FastAPI TestClient."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient
import api_server

client = TestClient(api_server.app)

# 1. /api/health
r_health = client.get("/api/health")
print("Health:", r_health.status_code, r_health.json())
assert r_health.status_code == 200
assert r_health.json().get("status") == "ok"

# 2. /api/overview (Normal & 404)
r_ov = client.get("/api/overview")
print("Overview:", r_ov.status_code, r_ov.json().get("ledger_id"), "total_equity:", r_ov.json().get("total_equity"))
assert r_ov.status_code == 200
assert "total_equity" in r_ov.json()
r_ov_404 = client.get("/api/overview?ledger_id=nonexistent_test_123")
assert r_ov_404.status_code == 404, f"Expected 404 for invalid ledger, got {r_ov_404.status_code}"

# 3. /api/holdings (Normal & 404)
r_h = client.get("/api/holdings")
print("Holdings count:", r_h.json().get("count"))
assert r_h.status_code == 200
assert r_h.json().get("count", 0) > 0
r_h_404 = client.get("/api/holdings?ledger_id=nonexistent_test_123")
assert r_h_404.status_code == 404, f"Expected 404 for invalid ledger, got {r_h_404.status_code}"

# 4. /api/rebalance (Normal & 404)
r_reb = client.get("/api/rebalance")
print("Rebalance is_empty:", r_reb.json().get("is_empty"), "tail_sweep:", r_reb.json().get("tail_sweep", {}).get("title"))
assert r_reb.status_code == 200
assert "items" in r_reb.json().get("buffer_hold", {})
r_reb_404 = client.get("/api/rebalance?ledger_id=nonexistent_test_123")
assert r_reb_404.status_code == 404, f"Expected 404 for invalid ledger, got {r_reb_404.status_code}"

# 5. /api/cashflow/plan (Normal, 404 & edge cases)
r_cf = client.post("/api/cashflow/plan", json={"monthly_new_cash": 3000.0, "plan_months": 3})
print("Cashflow plan investable_cash:", r_cf.json().get("investable_cash"))
assert r_cf.status_code == 200
r_cf_404 = client.post("/api/cashflow/plan", json={"ledger_id": "nonexistent_test_123"})
assert r_cf_404.status_code == 404, f"Expected 404 for invalid ledger, got {r_cf_404.status_code}"
r_cf_neg = client.post("/api/cashflow/plan", json={"monthly_new_cash": -100.0, "plan_months": -2, "rigid_reserve": -50.0})
assert r_cf_neg.status_code == 200
r_cf_big = client.post("/api/cashflow/plan", json={"monthly_new_cash": 1000000000.0, "plan_months": 12, "rigid_reserve": 500000.0})
assert r_cf_big.status_code == 200

# 6. /api/backups
r_bk = client.get("/api/backups")
print("Backups count:", len(r_bk.json().get("snapshots", [])))
assert r_bk.status_code == 200

# 7. /api/backups/restore (Error handling)
r_res_bad = client.post("/api/backups/restore", json={"snapshot_id": "invalid_snapshot_id_999"})
assert r_res_bad.status_code == 400, f"Expected 400 for bad snapshot, got {r_res_bad.status_code}"

# 8. /api/forward-audit
r_fa = client.get("/api/forward-audit")
print("Forward audit count:", r_fa.json().get("count"))
assert r_fa.status_code == 200

print("[PASS] All 8 api_server endpoints and edge cases verified successfully!")
