# Changes Summary — worker_g16_m3_fix

## 1. AGY2_FundAdvisory/strategy_bridge.py
- **Method**: `StrategyBridge.get_combat_29_rebalance_prescription()`
- **Fix**: Corrected schema of `step3_core_reconstruction["funds"]` items 1 to 5 (`110020`, `017436`, `002351`, `011612`, `000216`). Replaced keys-as-fund-codes with uniform `{"code": "...", "name": "...", "weight_pct": ...}` format.

## 2. tests/test_m3_item2_rebalance_impact.py
- **Test**: `test_combat_29_rebalance_prescription_structure()`
- **Enhancement**: Added strong schema assertions on `step3["funds"]`:
  - `all("code" in f and "name" in f and "weight_pct" in f for f in step3["funds"])`
  - Validated that `f["code"]` is a 6-character string, `f["name"]` is non-empty, and `f["weight_pct"]` is a positive numeric value.

## 3. AGY2_FundAdvisory/app_gui.py
- **Tab 2 Dynamic Prescription & 4-Dimension Metric Wiring**:
  - Dynamically invoked `StrategyBridge.get_combat_29_rebalance_prescription()` and `StrategyBridge.estimate_rebalance_impact(pm.holdings, rx_preset["reconstructed_6_weights"], pm.total_equity, [])`.
  - Replaced hardcoded "7 只全天候压舱石" / "7 大核心底仓" with "6 只全天候核心压舱石" / "6 只核心底仓".
  - Rendered real dynamic 4-dimension metric comparison:
    - 持仓标的数量: 29 只 ➔ 6 只核心底仓 (-79%)
    - 盘活零费率资金: ¥442.70 ~ ¥962.57 (零手续费)
    - 调仓交易手续费: ¥0.00 / 预计回本天数: 0 天 (即时零损耗)
    - 年化内生票息垫: +1.32% 票息厚度提升
  - Replaced dead state assignment `st.session_state.tab2_sweep_tail = True` in `btn_apply_combat29_rx` with real operational state machine wiring:
    - `st.session_state.rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"`
    - `st.session_state.sel_sc_anchor = "002351 - 易方达裕祥回报债券A"`
    - `st.session_state.tab2_c_replace = "011613"`
    - `st.session_state.tab2_diagnosed = True`
    - `st.session_state.tab2_rebalanced = True`
    - `st.session_state.tab2_trigger_rebalance = True`
    - `st.session_state.tab2_rebal_cache = None`
    - `st.rerun()`
- **Tab 3 Backtest Curve Legends & Time Machine Toggle**:
  - In Time Machine: added `tgl_dynamic = st.toggle("⚡ 启用时光机动态再平衡（按信号敏捷轮动）", value=True, key="tm_dynamic_rebalance_toggle", help="开启后在历史盲测中实施 Point-in-Time 动态调仓，消除 2024.09 政策底踏空")` and passed `dynamic_rebalance=tgl_dynamic` into `StrategyBridge.run_historical_time_machine_backtest(...)`.
  - In `preset_combat_29_vs_6` backtest plotting:
    - Primary curve: "投顾重构 6 基核心组合 (理论 +...%)"
    - Secondary curve: "原始 29 基存量组合 (理论 +...%)"
    - Primary drawdown: "投顾重构 6 基水下回撤"
    - Secondary drawdown: "原始 29 基水下回撤"
    - Completely eliminated mislabeling raw 29 funds as "调仓后组合".
