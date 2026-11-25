# -*- coding: utf-8 -*-
"""
scripts/verify_m1_reviewer_comprehensive.py
Reviewer R13-M1-1 综合独立核验与对抗压力测试脚本
"""
import sys
import os
import json
import time
import inspect
from pathlib import Path
import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import (
    OnlineHeuristicFactorEvolver,
    OpportunityRadarEngine,
    FlexTuple,
)
from AGY2_FundAdvisory.strategy_bridge import (
    StrategyBridge,
    BENCHMARK_INDICES_MAP,
    UNIVERSE_18_CHAMPION_POOL,
)


def verify_pain_point_1():
    print("=== [1/4] 核验痛点 1：因子进化 12h 磁盘持久化缓存与主线程零阻塞 ===")
    
    # 1.1 磁盘缓存文件验证
    cache_path = WORKSPACE_ROOT / "data" / "cache" / "factor_evolution_cache.json"
    assert cache_path.exists(), f"缓存文件不存在: {cache_path}"
    print(f"[*] 缓存文件存在: {cache_path} (大小: {cache_path.stat().st_size} bytes)")
    
    with open(cache_path, "r", encoding="utf-8") as f:
        cache_data = json.load(f)
    
    required_keys = ["timestamp", "weights", "generation_scores", "best_fitness", "evolved_result", "nav_trajectory"]
    for k in required_keys:
        assert k in cache_data, f"缓存缺少关键键: {k}"
    print(f"[*] 缓存关键键完整: {required_keys}")
    
    # 1.2 缓存命中性能 (< 5ms)
    evolver = OnlineHeuristicFactorEvolver()
    
    # 测试 evolve_factor_weights(force=False)
    t0 = time.perf_counter()
    res_evolve = evolver.evolve_factor_weights(force=False)
    t_evolve_ms = (time.perf_counter() - t0) * 1000.0
    print(f"[*] evolve_factor_weights 缓存命中耗时: {t_evolve_ms:.3f} ms")
    assert t_evolve_ms < 5.0, f"evolve_factor_weights 耗时超出 5ms: {t_evolve_ms} ms"
    assert res_evolve is not None
    assert "weights" in res_evolve
    
    # 测试 get_60d_rolling_nav_and_trajectory(force=False)
    # 重置内存缓存以强制走磁盘缓存读取
    evolver._cached_60d_data = None
    t0 = time.perf_counter()
    res_traj = evolver.get_60d_rolling_nav_and_trajectory(force=False)
    t_traj_ms = (time.perf_counter() - t0) * 1000.0
    print(f"[*] get_60d_rolling_nav_and_trajectory 磁盘缓存命中耗时: {t_traj_ms:.3f} ms")
    assert t_traj_ms < 5.0, f"get_60d_rolling_nav_and_trajectory 耗时超出 5ms: {t_traj_ms} ms"
    assert len(res_traj["dates"]) == 60
    assert len(res_traj["nav_dynamic"]) == 60
    assert len(res_traj["trajectory"]) == 60
    
    # 1.3 12h TTL 机制与过期逻辑核验
    print("[*] 测试 12h TTL 判定机制...")
    now_ts = time.time()
    fake_fresh = {"timestamp": now_ts - 3600, "evolved_result": {"test": "ok"}}
    assert (now_ts - fake_fresh["timestamp"]) < 43200.0
    
    # 模拟过期 (例如 13 小时前)
    expired_ts = now_ts - (13 * 3600)
    original_content = cache_path.read_text(encoding="utf-8")
    try:
        # 写入过期时间戳测试
        expired_data = dict(cache_data)
        expired_data["timestamp"] = expired_ts
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(expired_data, f)
        
        expired_read = evolver._read_disk_cache(max_age_seconds=43200.0)
        assert expired_read is None, f"过期缓存应该返回 None，实际返回了: {expired_read}"
        print("[*] 12h TTL 过期逻辑核验通过 (超过 43200s 正确返回 None)")
        
        # 损坏的 JSON 格式
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write("{corrupted json string")
        corrupted_read = evolver._read_disk_cache(max_age_seconds=43200.0)
        assert corrupted_read is None, "损坏 JSON 应静默降级为 None"
        print("[*] 损坏 JSON 容错降级核验通过")
    finally:
        # 恢复原有效缓存
        cache_path.write_text(original_content, encoding="utf-8")
    
    # 1.4 OpportunityRadarEngine 实例化零 GA 计算验证
    print("[*] 验证 OpportunityRadarEngine.__init__ 杜绝主线程同步 GA 计算...")
    from unittest.mock import patch
    with patch.object(OnlineHeuristicFactorEvolver, "evolve_factor_weights") as mock_ga:
        radar = OpportunityRadarEngine()
        assert mock_ga.call_count == 0, f"OpportunityRadarEngine.__init__ 仍然同步调用了 evolve_factor_weights! 调用次数: {mock_ga.call_count}"
        assert hasattr(radar, "factor_weights") and len(radar.factor_weights) == 4
        assert hasattr(radar, "evolved_result") and radar.evolved_result is not None
        print("[*] 有缓存时 OpportunityRadarEngine.__init__ 未触发任何 GA 计算 (call_count == 0)")
    
    # 进一步验证：无缓存时 OpportunityRadarEngine 也不阻塞跑 GA
    try:
        temp_backup = cache_path.with_suffix(".tmp_bak")
        cache_path.rename(temp_backup)
        with patch.object(OnlineHeuristicFactorEvolver, "evolve_factor_weights") as mock_ga:
            radar_no_cache = OpportunityRadarEngine()
            assert mock_ga.call_count == 0, f"无缓存时 OpportunityRadarEngine.__init__ 触发了 GA 计算! 调用次数: {mock_ga.call_count}"
            assert radar_no_cache.evolved_result.get("status") == "cached_default"
            print("[*] 无磁盘缓存时 OpportunityRadarEngine.__init__ 自动降级为 default，未触发任何 GA 计算 (call_count == 0)")
    finally:
        if temp_backup.exists():
            temp_backup.rename(cache_path)
    
    print("[PASS] 痛点 1 全部核验项 100% 通过！\n")


def verify_pain_point_4():
    print("=== [2/4] 核验痛点 4：Tab 3 回测去假 Alpha 与真实基准日度全收益 ===")
    
    # 2.1 检查源代码，确保 alpha_ann / 250 已彻底删除
    src = inspect.getsource(StrategyBridge.build_custom_portfolio_backtest)
    assert "alpha_ann / 250" not in src, "致命漏洞：仍然存在 alpha_ann / 250 人为硬加代码！"
    assert "alpha_ann/250" not in src, "致命漏洞：仍然存在 alpha_ann/250 人为硬加代码！"
    print("[*] StrategyBridge.build_custom_portfolio_backtest 源码审查: alpha_ann / 250 彻底被删除")
    
    # 2.2 检查基准字典映射与纯债基准
    assert BENCHMARK_INDICES_MAP["纯债指数"]["col"] == "H11009", (
        f"纯债指数映射错误，预期 H11009，实际: {BENCHMARK_INDICES_MAP['纯债指数']['col']}"
    )
    print("[*] BENCHMARK_INDICES_MAP['纯债指数'] 映射为: H11009")
    
    # 检查金牌底池纯债标的归一映射
    for item in UNIVERSE_18_CHAMPION_POOL:
        if item.get("bucket") == "纯债固收":
            assert item["index_col"] == "H11009", f"金牌底池纯债 {item['code']} 未映射至 H11009"
    print("[*] UNIVERSE_18_CHAMPION_POOL 纯债标的 100% 归一映射至 H11009")
    
    # 2.3 检查底层行情矩阵中 H11009 的真实性与非线性
    df_mat = StrategyBridge.load_matrix()
    assert "H11009" in df_mat.columns, "对齐行情矩阵中缺少 H11009"
    h11009_series = df_mat["H11009"].dropna().astype(float).values
    assert len(h11009_series) > 1000, f"H11009 历史长度不足: {len(h11009_series)}"
    
    # 验证不是假直线：每日收益率方差大于 0，且二阶差分不恒为 0
    h11009_rets = np.diff(h11009_series) / h11009_series[:-1]
    assert np.std(h11009_rets) > 0.0001, "H11009 每日收益率无波动，疑似假直线！"
    
    # 验证不是两点线性插值 (linspace)
    diffs = np.diff(h11009_series)
    assert np.std(diffs) > 1e-4, "H11009 一阶差分为常数，存在线性插值造假！"
    
    # 测算纯债全收益真实 CAGR
    n_days = len(h11009_series)
    cagr_h11009 = ( (h11009_series[-1] / h11009_series[0]) ** (252.0 / n_days) - 1.0 ) * 100.0
    print(f"[*] H11009 中证综合债全收益全历史真实 CAGR: {cagr_h11009:.2f}%")
    assert 4.0 <= cagr_h11009 <= 5.5, f"H11009 CAGR 异常: {cagr_h11009:.2f}%"
    
    # 2.4 实盘静态账本回测测试
    df_backtest = StrategyBridge.build_custom_portfolio_backtest(
        {"002351": 0.5, "000216": 0.5},
        is_real_ledger=True,
        target_name="主实盘账本"
    )
    assert isinstance(df_backtest, pd.DataFrame)
    
    # 验证后视镜效应免责声明
    disclaimer_attr = df_backtest.attrs.get("disclaimer", "")
    disclaimer_prop = getattr(df_backtest, "disclaimer", "")
    assert "当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）" in disclaimer_attr
    assert "当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）" in disclaimer_prop
    print(f"[*] 实盘账本后视镜效应 disclaimer 验证通过: '{disclaimer_attr}'")
    
    # 验证非实盘时 disclaimer 为空
    df_non_real = StrategyBridge.build_custom_portfolio_backtest(
        {"002351": 1.0},
        is_real_ledger=False,
        target_name="方案A"
    )
    assert getattr(df_non_real, "disclaimer", "") == "", "非实盘账本不应带有实盘免责声明"
    
    # 验证 C3 动态策略对照曲线数据
    assert "c3_dynamic_nav" in df_backtest.columns, "回测结果缺少 c3_dynamic_nav 对照序列"
    assert "c3_dynamic_drawdown" in df_backtest.columns, "回测结果缺少 c3_dynamic_drawdown 对照序列"
    c3_nav = df_backtest["c3_dynamic_nav"].values
    assert len(c3_nav) == len(df_backtest)
    assert not np.isnan(c3_nav).any(), "c3_dynamic_nav 包含 NaN 值"
    assert c3_nav[-1] > 1.0, f"C3 最终净值异常: {c3_nav[-1]}"
    print(f"[*] C3 动态对照序列已成功挂载 (最终净值: {c3_nav[-1]:.4f})")
    
    # 验证回测中纯债基准 bm_nav_纯债指数
    assert "bm_nav_纯债指数" in df_backtest.columns, "回测结果缺少 bm_nav_纯债指数"
    bm_pure_bond = df_backtest["bm_nav_纯债指数"].values
    assert bm_pure_bond[0] == 1.0, "基准净值必须归一化从 1.0 开始"
    assert bm_pure_bond[-1] > 1.2, f"纯债全收益基准终端净值过低: {bm_pure_bond[-1]}"
    print(f"[*] 回测纯债基准序列归一化验证通过 (起始: {bm_pure_bond[0]}, 终点: {bm_pure_bond[-1]:.4f})")
    
    print("[PASS] 痛点 4 全部核验项 100% 通过！\n")


def verify_readonly_files_and_safety():
    print("=== [3/4] 核验 4 个只读裁判文件与物理安全红线 ===")
    import subprocess
    cmd = ["git", "status", "--porcelain", "judge_engine.py", "AGY2_FundAdvisory/judge_engine.py",
           "holdout_vault.py", "AGY2_FundAdvisory/holdout_vault.py", "AGENT_SPEC.md", "tests/test_infra.py"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
    assert res.returncode == 0
    assert res.stdout.strip() == "", f"只读文件发生修改！\n{res.stdout}"
    print("[*] 4 个只读裁判文件 (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) 0 修改！")
    
    # 验证 DataLoader.simulate_execution 默认签名与扣费逻辑未修改
    from AGY2_FundAdvisory.data_loader import DataLoader
    sig = inspect.signature(DataLoader.simulate_execution)
    params = list(sig.parameters.keys())
    print(f"[*] DataLoader.simulate_execution 签名参数: {params}")
    assert "self" in params or "cls" in params or len(params) >= 3
    src_dl = inspect.getsource(DataLoader.simulate_execution)
    assert "0.0015" in src_dl or "0.001" in src_dl or "fee" in src_dl
    print("[*] DataLoader.simulate_execution 签名与扣费逻辑完好")
    print("[PASS] 物理安全红线全部守住！\n")


def verify_adversarial_stress_and_edge_cases():
    print("=== [4/4] 对抗压力测试与极端边缘场景 ===")
    
    # 4.1 FlexTuple 解包测试
    print("[*] 测试 FlexTuple 在 2 变量与 3 变量解包下的自适应兼容性...")
    ft = FlexTuple(["item1", "item2", "item3"])
    
    # 3 变量解包
    a, b, c = ft
    assert a == "item1" and b == "item2" and c == "item3"
    
    # 2 变量解包
    x, y = ft
    assert x == "item1" and y == "item2"
    
    # 单变量/索引访问
    assert ft[0] == "item1"
    assert len(ft) == 3
    print("[*] FlexTuple 2 变量与 3 变量解包测试全部通过！")
    
    # 4.2 资产池中存在空权重或单一标的的回测压力测试
    print("[*] 测试极端持仓组合回测...")
    df_single = StrategyBridge.build_custom_portfolio_backtest({"002351": 1.0})
    assert len(df_single) > 0
    assert not df_single["strategy_nav"].isna().any()
    
    # 包含高波动/海外/黄金的跨市场极端组合
    df_multi = StrategyBridge.build_custom_portfolio_backtest({
        "000216": 0.3,  # 黄金
        "017436": 0.3,  # 美股标普/纳指
        "002351": 0.4,  # 纯债
    }, is_real_ledger=True, target_name="全球宏观配置实盘")
    assert getattr(df_multi, "disclaimer", "") != ""
    assert not df_multi["strategy_nav"].isna().any()
    assert df_multi["strategy_nav"].iloc[-1] > 0
    print("[*] 跨市场复杂资产回测压力测试通过")
    
    # 4.3 缓存读写并发与异常抗压
    print("[*] 测试缓存读写原子性与增量合并...")
    evolver = OnlineHeuristicFactorEvolver()
    evolver._write_disk_cache({"test_key_adversarial": 12345})
    read_back = evolver._read_disk_cache()
    assert read_back is not None
    assert read_back.get("test_key_adversarial") == 12345
    assert "weights" in read_back
    assert "nav_trajectory" in read_back
    
    # 清理测试键
    cache_path = WORKSPACE_ROOT / "data" / "cache" / "factor_evolution_cache.json"
    data = json.load(open(cache_path, "r", encoding="utf-8"))
    data.pop("test_key_adversarial", None)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("[*] 缓存增量写入与清理测试通过")
    
    print("[PASS] 对抗压力测试全部通过！\n")


if __name__ == "__main__":
    try:
        verify_pain_point_1()
        verify_pain_point_4()
        verify_readonly_files_and_safety()
        verify_adversarial_stress_and_edge_cases()
        print("==================================================")
        print(">>> REVIEWER R13-M1-1 ALL CHECKS PASSED: 100% <<<")
        print("==================================================")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
