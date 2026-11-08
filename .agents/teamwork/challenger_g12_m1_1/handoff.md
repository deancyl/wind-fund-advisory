# Milestone 1 Empirical Challenge Report: 4 Circuit-Breaker Bugs & Sentry Penetration

- **Agent**: `teamwork_challenger` (`challenger_g12_m1_1`)
- **Recipient**: `orchestrator_16` (`e873dbb9-9906-41d0-83a7-8e9eb7aaf59a`)
- **Timestamp**: 2026-11-08T15:52:00Z
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g12_m1_1\`
- **Verdict**: **APPROVE**

---

## 1. 观察事实 (Observation)

### 1.1 独立对抗挑战测试套件实装与运行事实
- 针对任务派发要求，在工程标准测试目录编写了独立的对抗测试套件：`tests/test_g12_m1_challenge.py`（共 49 项高强度对抗与参数化模糊测试用例）。
- 在 PowerShell 终端实测运行结果：
  ```powershell
  py -3 -m pytest tests/test_g12_m1_challenge.py -v
  ```
  **运行结果**:
  ```text
  ============================= test session starts =============================
  platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
  rootdir: D:\Google\Workspace\Wind
  collected 49 items

  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.74-False-False-DECOUPLED_NORMAL-green] PASSED [  2%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.75-True-False-MUTATION_ALERT-yellow0] PASSED [  4%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.79-True-False-MUTATION_ALERT-yellow] PASSED [  6%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.8-True-True-MUTATION_ALERT-red0] PASSED [  8%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.85-True-True-MUTATION_ALERT-red] PASSED [ 10%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.7499-False-False-DECOUPLED_NORMAL-green] PASSED [ 12%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.75-True-False-MUTATION_ALERT-yellow1] PASSED [ 14%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.7501-True-False-MUTATION_ALERT-yellow] PASSED [ 16%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.7999-True-False-MUTATION_ALERT-yellow] PASSED [ 18%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.8-True-True-MUTATION_ALERT-red1] PASSED [ 20%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.8001-True-True-MUTATION_ALERT-red] PASSED [ 22%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[-0.5-False-False-DECOUPLED_NORMAL-green] PASSED [ 24%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[0.0-False-False-DECOUPLED_NORMAL-green] PASSED [ 26%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_boundary_values_and_key_alignment[1.0-True-True-MUTATION_ALERT-red] PASSED [ 28%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_property_based_fuzzing_100_points PASSED [ 30%]
  tests/test_g12_m1_challenge.py::TestBug1CorrelationBoundaries::test_html_card_rendering_across_all_boundaries PASSED [ 32%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_conservative_holdings_never_triggers_suitability_alert[C1] PASSED [ 34%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_conservative_holdings_never_triggers_suitability_alert[C2] PASSED [ 36%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_conservative_holdings_never_triggers_suitability_alert[C3] PASSED [ 38%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_conservative_holdings_never_triggers_suitability_alert[C4] PASSED [ 40%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_conservative_holdings_never_triggers_suitability_alert[C5] PASSED [ 42%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_exact_limit_boundary_not_triggered[C1-20] PASSED [ 44%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_exact_limit_boundary_not_triggered[C2-40] PASSED [ 46%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_exact_limit_boundary_not_triggered[C3-78] PASSED [ 48%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_exact_limit_boundary_not_triggered[C4-85] PASSED [ 51%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_exact_limit_boundary_not_triggered[C5-95] PASSED [ 53%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_over_limit_by_one_percent_triggers_alert[C1-20] PASSED [ 55%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_over_limit_by_one_percent_triggers_alert[C2-40] PASSED [ 57%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_over_limit_by_one_percent_triggers_alert[C3-78] PASSED [ 59%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_over_limit_by_one_percent_triggers_alert[C4-85] PASSED [ 61%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_over_limit_by_one_percent_triggers_alert[C5-95] PASSED [ 63%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_aggressive_tech_across_all_tiers PASSED [ 65%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_parameter_passing_routes_and_case_insensitivity[route0] PASSED [ 67%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_parameter_passing_routes_and_case_insensitivity[route1] PASSED [ 69%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_parameter_passing_routes_and_case_insensitivity[route2] PASSED [ 71%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_parameter_passing_routes_and_case_insensitivity[route3] PASSED [ 73%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_parameter_passing_routes_and_case_insensitivity[route4] PASSED [ 75%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension8Suitability::test_missing_tier_graceful_handling PASSED [ 77%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_single_fund_drop_boundary_2_percent PASSED [ 79%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_cushion_depletion_severity_yellow_vs_red PASSED [ 81%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_portfolio_level_shock_without_single_fund_reaching_2_percent PASSED [ 83%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_positive_shock_does_not_trigger_depletion_alert PASSED [ 85%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_quote_data_format_flexibility[quote_format0] PASSED [ 87%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_quote_data_format_flexibility[quote_format1] PASSED [ 89%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_quote_data_format_flexibility[quote_format2] PASSED [ 91%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_quote_data_format_flexibility[quote_format3] PASSED [ 93%]
  tests/test_g12_m1_challenge.py::TestBug2SentryDimension9IntradayShocks::test_quote_data_format_flexibility[quote_format4] PASSED [ 95%]
  tests/test_g12_m1_challenge.py::TestBug3And4Integrity::test_feeder_vs_index_factor_distinction PASSED [ 97%]
  tests/test_g12_m1_challenge.py::TestBug3And4Integrity::test_portfolio_weighted_bias_and_erp_unnormalized_weights PASSED [100%]

  ============================= 49 passed in 32.38s =============================
  ```

### 1.2 Bug 1 (相关性突变门禁与返回字典边界) 实测观察
- **边界点判定值**:
  - `corr = 0.74`: `is_triggered=False`, `is_mutation_alarm=False`, `is_liquidity_shift_triggered=False`, `is_regime_shift_risk=False`, `status="DECOUPLED_NORMAL"`, `alert_level="green"`.
  - `corr = 0.75`: `is_triggered=True`, `is_mutation_alarm=True`, `is_liquidity_shift_triggered=False`, `is_regime_shift_risk=False`, `status="MUTATION_ALERT"`, `alert_level="yellow"`.
  - `corr = 0.79`: `is_triggered=True`, `is_mutation_alarm=True`, `is_liquidity_shift_triggered=False`, `is_regime_shift_risk=False`, `status="MUTATION_ALERT"`, `alert_level="yellow"`.
  - `corr = 0.80`: `is_triggered=True`, `is_mutation_alarm=True`, `is_liquidity_shift_triggered=True`, `is_regime_shift_risk=True`, `status="MUTATION_ALERT"`, `alert_level="red"`.
  - `corr = 0.85`: `is_triggered=True`, `is_mutation_alarm=True`, `is_liquidity_shift_triggered=True`, `is_regime_shift_risk=True`, `status="MUTATION_ALERT"`, `alert_level="red"`.
- **双保险键名一致性不变量**:
  - 在 `[-1.0, 1.0]` 区间内随机生成 100 个点进行属性模糊测试，恒满足：
    - `res["is_triggered"] == res["is_mutation_alarm"]`（100% 恒等）
    - `res["is_liquidity_shift_triggered"] == res["is_regime_shift_risk"]`（100% 恒等）
  - GUI 门禁逻辑 `corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered") or corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk")` 无论按原生键还是别名键求值，布尔结果完全等价。
  - 观察到 `portfolio_manager.py:8551` 中执行了 `round(float(current_corr), 4)`，输入值被标准化为 4 位小数基点精度。

### 1.3 Bug 2 (ActiveRiskSentry 维度 8 与维度 9) 实测观察
- **维度 8 (C1 至 C5 适当性穿透测试)**:
  - 纯债持仓 (0% 权益): C1 至 C5 均不触发适当性警报（通过）。
  - 临界边界值测试: 各档位持仓刚好等于上限 (C1: 20%, C2: 40%, C3: 78%, C4: 85%, C5: 95%) 时均不触发警报；超出 1% (21%, 41%, 79%, 86%, 96%) 时全部确定性触发 `投资者适当性` 警报。
  - 激进科技持仓 (90% 芯片/科创 + 10% 纯债):
    - C1 (上限 20%): 触发 RED 警报（低风险客户持有高波科技标的 + 超标 70% >= 15% 严惩）。
    - C2 (上限 40%): 触发 RED 警报（超标 50% >= 15% 严惩）。
    - C3 (上限 78%): 触发 YELLOW 警报（超标 12% < 15%）。
    - C4 (上限 85%): 触发 YELLOW 警报（超标 5% < 15%）。
    - C5 (上限 95%): 90% <= 95%，完全合规，不触发警报。
  - 传参通道验证: `investor_risk_tier="C1"`、`investor_risk_tier="c1"` (大小写免疫)、kwargs `risk_tier="C1"`、`snapshot["investor_risk_tier"]="C1"`、`snapshot["risk_tier"]="c1"` 5 条通道均能成功传导并触发警报；当未指定等级时静默跳过无报错。
- **维度 9 (盘中实时估值异动与安全垫传导)**:
  - 单基波动未达 2% 且组合波动未达 1% (-1.90% 单基，组合跌 -0.19%): 不触发警报。
  - 单基达到 -2.00% 且消耗安全垫 >= 20%: 确定性触发警报。
  - 安全垫消耗等级区分: 消耗比例 < 50% 为 YELLOW 警报；消耗比例 >= 50% 或初始安全垫为 0 时直接升级为 RED 警报。
  - 组合协同下挫: 多标的各自跌 -1.2% (均未达 2%)，但组合整体跌幅达 -1.2% (<= -1.0%) 时，依然成功触发维度 9 警报。
  - 盘中大涨 (+3.50%): 日内盈亏为正，不误报安全垫消耗警报。
  - 报价结构兼容性: 支持 `FundQuote` 实例、`{"gszzl": ...}`、`{"change_pct": ...}`、`{"chg_pct": ...}` 及裸 float 数值。

### 1.4 回归与裁判基线校验
- `tests/test_infra.py`: 14 passed (100% 绿灯，四大裁判只读文件未被修改，反作弊契约完整)。
- `tests/test_g12_circuit_breakers_and_sentry.py`: 11 passed (Worker M1 单元测试全部通过)。
- `tests/test_g10_correlation_liquidity_and_stress.py`: 6 passed (G10 压力测试回归无影响)。
- `tests/test_adv_final_closure.py`: 14 passed (核心因果律与投顾业务逻辑回归无影响)。

---

## 2. 逻辑推导链 (Logic Chain)

1. **依据 [1.2]**:
   - 之前版本在 `app_gui.py` 与 `portfolio_manager.py` 之间存在键名失配（GUI 端读取 `is_mutation_alarm` / `is_regime_shift_risk`，而底层仅返回 `is_triggered` / `is_liquidity_shift_triggered`）。
   - Worker 采取了“双向互补”修复方案：GUI 端将门禁扩展为 4 键兼容，底层返回字典直接补齐别名映射。
   - 经实证挑战测试，在 0.74、0.75、0.79、0.80、0.85 各阈值及 100 组伪随机相关系数下，双套键值完全严格恒等，彻底根除了前端门禁因键名不匹配导致的“相关性预警卡假死”缺陷。
2. **依据 [1.3]**:
   - 之前版本在 `app_gui.py` 调用 `sentry.inspect_portfolio` 时遗漏了 `investor_risk_tier` 和 `snapshot_dict["fund_quotes"]`，致使维度 8 和维度 9 实际上永远处于静默失效状态。
   - Worker 在首屏双翼看板渲染入口补齐了从 `st.session_state.active_tier_val` 提取投资者风险等级，并遍历持仓获取 `fetch_realtime_fund_quote` 注入 `_augmented_snapshot["fund_quotes"]`。
   - 经实证挑战测试，无论 C1 至 C5 各种组合场景还是盘中估值异动，只要参数注入，维度 8（适当性超额与高波惩罚）和维度 9（单基 2% / 组合 1% 异动与安全垫消耗阶梯分级）均能精准、确定性地触发，无漏报或误报。
3. **依据 [1.1] 与 [1.4]**:
   - 挑战者自行编写的 49 项高压测试及原有系统全量核心单测（累计 94 项）100% 绿灯通过，四大只读裁判文件零改动，代码符合项目规范。

---

## 3. 注意事项与边界说明 (Caveats)

1. **相关系数精度对齐**:
   `portfolio_manager.py:8551` 对传入的 `simulated_corr` 执行了 `round(float(current_corr), 4)`。因此测试用例中若采用大于 4 位的极端浮点数（如 `0.749999`），会被标准四舍五入进位为 `0.7500`。此行为完全符合金融基准万分位（bps）精度规范，并非 Bug。
2. **只读裁判与工作区规范遵守**:
   - 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希未变。
   - 独立测试脚本规范写入工程根目录 `tests/test_g12_m1_challenge.py`，绝无代码或测试外溢至 `.agents/teamwork/`。

---

## 4. 实施结论 (Conclusion)

- **综合风险评级**: **LOW**
- **终审裁决**: **APPROVE** (批准 Milestone 1 验收通过，允许推进后续 Milestone 2)。
- **结论依据**:
  - Bug 1（相关性突变指示卡门禁与返回字典断路）：在各边界点均 100% 对齐，卡片正常激活，双保险机制稳固。
  - Bug 2（ActiveRiskSentry 维度 8 与维度 9 传参穿透）：参数注入后 C1~C5 矩阵分类精确，盘中异动与安全垫消耗分级准确。
  - Bug 3 与 Bug 4（联接基金 0.95 仓位校准与智能定投加权乖离率及 ERP 穿透）：逻辑自洽，纯债隔离有效，加权数学模型严密。
  - 全量 94 项相关单测 100% 绿灯通过。

---

## 5. 独立验证方法 (Verification Method)

在 PowerShell 终端中执行以下命令即可全量独立复现挑战者验证全过程：

```powershell
# 1. 运行挑战者独立编写的 49 项 M1 压力测试套件
py -3 -m pytest tests/test_g12_m1_challenge.py -v

# 2. 运行反作弊裁判与只读基础设施校验
py -3 -m pytest tests/test_infra.py -v

# 3. 运行 Worker M1 专项测试
py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v
```
**失效判据**: 若 `test_g12_m1_challenge.py` 出现任何红灯，或键名对齐出现 `False`，或 C1 激进配置未报警，则立即失效。
