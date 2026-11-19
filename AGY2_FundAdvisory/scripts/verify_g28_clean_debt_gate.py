import os
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from portfolio_manager import get_calibrated_feeder_beta


def verify_g28_clean_debt():
    print("=== [GATE 1] 核心代码硬编码常数物理清零扫描 ===")
    targets = ["7.2385", "4.4200", "11569.50"]
    core_files = [
        AGY2_DIR / "data_loader.py",
        AGY2_DIR / "advisory_engine.py",
        AGY2_DIR / "strategy_bridge.py",
        AGY2_DIR / "portfolio_manager.py",
        AGY2_DIR / "app_gui.py",
    ]
    active_hits = []
    for f in core_files:
        if not f.exists():
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, l in enumerate(lines):
            s_l = l.strip()
            if s_l.startswith("#") or s_l.startswith("//") or s_l.startswith('"""') or s_l.startswith("'''"):
                continue
            for t in targets:
                if t in l:
                    active_hits.append((str(f.name), i + 1, t, s_l))

    if active_hits:
        for h in active_hits:
            print(f"❌ 残留硬编码: {h[0]}:{h[1]} -> {h[2]}: {h[3]}")
    assert len(active_hits) == 0, f"发现 {len(active_hits)} 处未清零硬编码活代码！"
    print("✅ 核心生产代码 7.2385 / 4.4200 / 11569.50 活代码命中次数严格等于 0！")

    print("\n=== [GATE 2] 动态 Beta 反向边界与联接基金裁剪断言 ===")
    # 1. 测试未命中标的不会跨赛道误用 H00300
    beta_unmapped = get_calibrated_feeder_beta("016441", "sz159758", default_beta=0.95, fund_name="华夏中证红利质量ETF联接C")
    assert 0.90 <= beta_unmapped <= 0.97, f"联接基金 Beta 未落在 [0.90, 0.97] 区间: {beta_unmapped}"

    # 2. 测试普通指数基金落在 [0.88, 1.00]
    beta_normal = get_calibrated_feeder_beta("161725", "sz399997", default_beta=0.95, fund_name="招商中证白酒指数(LOF)A")
    assert 0.88 <= beta_normal <= 1.00, f"普通指数基金 Beta 未落在 [0.88, 1.00] 区间: {beta_normal}"
    print(f"✅ Beta 断言通过: 016441(联接)={beta_unmapped:.4f}, 161725(行业)={beta_normal:.4f}")

    print("\nALL G28 CLEAN DEBT GATES PASSED 100%")


if __name__ == "__main__":
    verify_g28_clean_debt()
