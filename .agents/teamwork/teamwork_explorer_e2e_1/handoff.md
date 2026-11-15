# Handoff Report — E2E Testing Explorer: Test Suite Investigation

- **Author**: `teamwork_explorer_e2e_1`
- **Recipient**: Orchestrator (`f19968e9-b489-4e77-a974-7e98bb7b9acd`) / Implementers
- **Date**: 2026-11-15
- **Working Directory**: `d:\Google\Workspace\Wind`
- **Analysis Document**: `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_e2e_1\analysis.md`

---

## 1. Observation

1. **全局测试套件扫描结果**:
   - 执行命令: `py -3 -m pytest -q`
   - 结果: `50 failed, 855 passed, 111 warnings in 494.35s (0:08:14)`。
2. **物理安全基线测试 (`tests/test_infra.py`)**:
   - 执行命令: `py -3 -m pytest tests/test_infra.py -v`
   - 结果: `14 passed in 8.30s` (100% 绿灯全通)。
   - 覆盖范围: `data_loader.py` 全收益矩阵对齐与模拟算子摩擦费、`judge_engine.py` 因果探针与 Gate B 七大约束（纯债套利、Rf 扣除、切片防逃避、外援上限、A股底线、CAGR 11.5% 底线、牛市防踏空）、四岛策略接口合规与空数据鲁棒性、`holdout_vault.py` 额度防护。
3. **已知异常 (a) `tests/test_g16_phase1_memo_and_combat29.py` 调查**:
   - 执行命令: `py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py -v`
   - 结果: 5 passed, 1 failed (耗时 11.07s)。
   - 报错位置: Line 219: `assert "建仓标的" in call_arg`。
   - 实际渲染值: `call_arg` 中的第四胶囊副标题为 `0深套 ｜ 结构优良`（`app_gui.py:312`），未渲染包含 `"建仓标的"` 的文本。
4. **已知异常 (b) `tests/test_g15_phase2_memo_and_timemachine.py` 调查**:
   - 执行命令: `py -3 -m pytest tests/test_g15_phase2_memo_and_timemachine.py -v`
   - 结果: 7 passed, 1 failed (耗时 14.67s)。
   - 报错位置: Line 250: `with pytest.raises(ValueError, match="缺乏前推回测样本"): StrategyBridge.run_historical_time_machine_backtest(target_date="2026-11-09")`。
   - 实际现象: `Failed: DID NOT RAISE ValueError`。
   - 湖仓数据核验: `DataLoader.load_total_return_matrix()` 数据截止日期已自动同步至 `2026-11-13`，在 `2026-11-09` 之后存在 5 个交易日（`len(fwd_slice) == 5 >= 2`），故未触发 `len(fwd_slice) < 2` 抛出异常。
5. **十维投票与兜底常数代码现场观察**:
   - `AGY2_FundAdvisory/advisory_engine.py:4295-4299`: `n_radar = len(radar_top3) if radar_top3 else 3`，`d6_score = 80.0 if n_radar >= 2 else 55.0` 恒真为 BULL。
   - `AGY2_FundAdvisory/advisory_engine.py:4204`: `crowd_score = float(snap.get("crowding_score", 85.0))`，恒取默认值 85.0 投赞成票。
   - `AGY2_FundAdvisory/advisory_engine.py:4354-4364`: 仅检查 alerts 动态相关性，完全无视 `option_iv_pct` 与 `ic_annualized_basis_rate`。
   - `AGY2_FundAdvisory/data_loader.py:3033, 3180`: 硬编码 `us_10y = 5.0000` 与 `usdcnh_rate = float(usdcnh_info.get("rate", 6.6676))`。
   - `AGY2_FundAdvisory/data_loader.py:3235`: `macro_summary` 输出了 `"10Y中债"` 导致 `test_g12_stop_profit_and_sensors.py:293` 断言 `"10Y国债"` 失败。
   - `AGY2_FundAdvisory/app_gui.py:288`: `ts = memo_data.get("timestamp", "")`，当 timestamp 显式为 None 时触发 `TypeError` 导致 `test_challenger_m1_adv_memo.py` 失败。
   - `AGY2_FundAdvisory/strategy_bridge.py:5926-5930, 5975-5979`: 硬编码 `cagr_val = 14.28/16.85`、`mdd_all = -17.24/-16.76` 等假常数。
   - `AGY2_FundAdvisory/portfolio_manager.py:1906`: `if len(clean_res) >= 1: return clean_res` 提前返回丢弃空间块聚类。

---

## 2. Logic Chain

1. **关于物理安全底线**:
   - 引用 Observation 2，`test_infra.py` 全量通过证明现有底层数据矩阵和防作弊机制完全正常。根据系统指令，四大裁判文件与 `simulate_execution` 默认逻辑必须保持零修改。
2. **关于 `test_g16` 行 219 失败原因与修复方案**:
   - 引用 Observation 3，`app_gui.py` 渲染胶囊四副标题时，仅根据 `deep_loss_count` 与 `frag_count` 赋值为 `"0深套 ｜ 结构优良"`，未在紧凑副标题中使用 `"建仓标的"`。由于 `PROJECT.md` 明确规定修复 g16 建仓断言，单测断言应调整为兼容实际紧凑文本 `assert ("建仓标的" in call_arg or "0深套 ｜ 结构优良" in call_arg)`，或者在 `app_gui.py` 的胶囊副标题中注入拟建仓标的数（如 `f"{n_funds}只建仓标的 ｜ 结构优良"`）。
3. **关于 `test_g15` 行 250 失败原因与修复方案**:
   - 引用 Observation 4，`StrategyBridge.run_historical_time_machine_backtest` 仅当 `len(fwd_slice) < 2` 时抛出异常。由于湖仓最新交易日已达到 `2026-11-13`，`target_date="2026-11-09"` 已非最新切片。按 `PROJECT.md` 要求将测试用例中的目标日期修改为湖仓最大日期之后的未来日期（如 `2026-11-14` 或 `2028-01-01`）即可保证异常正确抛出。
4. **关于 G19 M1 目标实现与测试**:
   - 引用 Observation 5，`compute_ten_dimension_votes` 中第六维、第七维、第十维确实存在恒真/默认值假逻辑，`data_loader.py` 与 `app_gui.py` 确实残留 6.6676 与 5.0000。按需求改写真实 14 赛道估值、拥挤度、期权隐波与黑天鹅熔断后，编写新建针对性测试 `tests/test_g19_m1_ten_dimension_and_memo.py` 即可形成严密验证。
5. **关于 G19 M2 目标实现与测试**:
   - 引用 Observation 5，`strategy_bridge.py` 摩擦账单存在静态假常数，`portfolio_manager.py` OCR 存在提前 return 丢弃分支。M2 需重构这些逻辑并为 29 基首次加载跳转 Tab 2、滚动发车回测表建立 `tests/test_g19_m2_routing_and_rolling_dca.py`。

---

## 3. Caveats

1. **全量回归效率与剪枝原则**:
   - 全量 pytest 跑完耗时约 8 分 14 秒（494s）。按照用户规则与 Wind 工作区准则，M1 与 M2 交付阶段必须执行“三阶轻量核验”（针对性增量单测 Delta Test、AST/Regex 红线扫描、运行时探针），严禁外层交付反复跑全量 905 项用例。
2. **测试文件分类保护**:
   - `tests/test_infra.py` 绝对禁止修改（只读门禁）；
   - 业务单测文件（如 `test_g16_phase1_memo_and_combat29.py`、`test_g15_phase2_memo_and_timemachine.py`）按 `PROJECT.md` 授权进行契约对齐与维护。

---

## 4. Conclusion

1. **底层安全基线坚固**: `test_infra.py` 14 项全绿，数据湖与因果防作弊完全合规。
2. **两处已知单测故障完全定位**:
   - `test_g16` 第 219 行因胶囊四副标题渲染文本差异断言失败；
   - `test_g15` 第 250 行因湖仓数据前推至 `2026-11-13` 使 `2026-11-09` 具备 5 天样本而不再报错；
   - 两处均有明确的一行式修复方案。
3. **G19 M1/M2 需求法证完全证实**: 现存源码中 100% 确认存在假投票逻辑、兜底常数 6.6676/5.0000、OCR 提前 return、摩擦账单静态假常数。
4. **测试套件设计方案齐备**: 规划了 `tests/test_g19_m1_ten_dimension_and_memo.py` 与 `tests/test_g19_m2_routing_and_rolling_dca.py` 两大针对性门禁。

---

## 5. Verification Method

1. **验证只读基线**:
   ```powershell
   py -3 -m pytest tests/test_infra.py -v
   ```
   预期结果: 14 passed in < 10s。
2. **验证已知单测修复**:
   ```powershell
   py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py tests/test_g15_phase2_memo_and_timemachine.py -v
   ```
   预期结果: 修复后两文件共 14 项用例 100% 通过。
3. **验证宏观指标总结断言**:
   ```powershell
   py -3 -m pytest tests/test_g12_stop_profit_and_sensors.py -k "test_fetch_macro_cross_market_indicators" -v
   ```
   预期结果: 1 passed。
4. **验证 G19 M1 针对性测试**:
   ```powershell
   py -3 -m pytest tests/test_g19_m1_ten_dimension_and_memo.py -v
   ```
   预期结果: 全量通过。
