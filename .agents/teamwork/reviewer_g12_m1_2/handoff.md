# Milestone 1 Independent Review & Adversarial Audit Report

- **Reviewer**: `teamwork_reviewer` (`reviewer_g12_m1_2`)
- **Recipient**: `orchestrator_16` (`e873dbb9-9906-41d0-83a7-8e9eb7aaf59a`)
- **Timestamp**: 2026-11-08T15:51:00Z
- **Target Milestone**: Milestone 1 (4 Circuit-Breaker Bugs & Sentry Parameter Penetration)
- **Definitive Verdict**: **APPROVE**

---

## 1. 观察事实 (Observation)

### 1.1 裁判文件与全局配置完整性核验
- **全局 `GEMINI.md` 零触碰**:
  - 执行 `Get-Item "C:\Users\deanc\.gemini\GEMINI.md" | Select-Object LastWriteTime`
  - 观察结果: 最后修改时间为 `2026/11/3 18:44:33`，本轮执行期间无任何修改，严格遵循《工作区硬隔离铁律》。
- **四大只读裁判文件零改动**:
  - 执行 `git diff --exit-code AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/tests/test_infra.py`
  - 观察结果: 退出码为 `0`，无任何 diff 输出，哈希值与内容 100% 只读未变。

### 1.2 四大 Bug 代码修复查验
- **Bug 1 (相关性卡片键名对齐)**:
  - `AGY2_FundAdvisory/app_gui.py:3005` 门禁修正为：
    ```python
    if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered") or corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
        safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
    ```
  - `AGY2_FundAdvisory/portfolio_manager.py:8692-8693` 底层补齐别名键：
    ```python
    "is_mutation_alarm": is_triggered,
    "is_regime_shift_risk": is_liquidity_shift_triggered,
    ```
  - 前后端实现双向兼容双保险。
- **Bug 2 (Sentry 适当性与盘中估值异动参数穿透)**:
  - `AGY2_FundAdvisory/app_gui.py:2719-2743`：
    - 显式从 `st.session_state` 提取 `_cur_tier = str(st.session_state.get("active_tier_val", "C3")).upper()`。
    - 遍历持仓拉取实时报价存入 `_f_quotes`，构造 `_augmented_snapshot`。
    - 调用 `sentry.inspect_portfolio` 时显式传入 `investor_risk_tier=_cur_tier` 及 `_augmented_snapshot`。
  - `data/portfolio_watchdog.json` 真实盯盘快照直接记录了新激活的预警：
    - `dimension: "组合级止盈", action_type: "take_profit"`
    - `dimension: "盘中异动安全垫传导", action_type: "defense_mode"`
- **Bug 3 (指数与 ETF 联接基金盘中估值精度校准)**:
  - `AGY2_FundAdvisory/portfolio_manager.py:2177-2295`：
    - 新增 `INDEX_AND_FEEDER_BENCHMARK_MAP`，扩充科创50、芯片半导体、红利低波、中证红利、沪深300、中证500、中证1000、白酒等基准映射，并保留 `QDII_BENCHMARK_MAP` 别名。
    - 实现 `_apply_fund_valuation_calibration`，针对联接基金严格按 `0.95` 仓位折算，纯指数按 `1.0` 折算。
    - 对 QDII/黄金继续维持既有 `> 1.5%` 阈值纠偏契约；对 A 股指数/联接基金当绝对偏差 `> 0.1%` 或为 `0.0%` 时结合基准涨跌幅校准。
    - 纯债标的（如 002351）经由 `is_index_or_feeder_name` 前置白名单过滤，绝不发生误校准。
- **Bug 4 (Tab 1 智能定投加权乖离率与 ERP 穿透)**:
  - `AGY2_FundAdvisory/advisory_engine.py:2430-2474` 实装 `SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp`。
  - 根据输入 allocations 的权重，精算各标的 20 日乖离率与属性自适应的 ERP 分位。
  - `AGY2_FundAdvisory/app_gui.py:3905-3908` 在智能定投模式中接入加权计算结果。

### 1.3 测试套件执行结果 (独立复测)
1. `py -3 -m pytest tests/test_infra.py -v`:
   - 结果: **14 passed** (5.92s)
2. `py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v`:
   - 结果: **11 passed** (18.88s)
3. `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py -v`:
   - 结果: **6 passed** (22.04s)
4. `$env:PYTHONPATH = "AGY2_FundAdvisory"; py -3 -m pytest AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py -v`:
   - 结果: **12 passed** (7.74s)
5. `py -3 -m pytest tests/test_adv_final_closure.py -v`:
   - 结果: **14 passed** (35.95s)
6. `py -3 -m pytest tests/test_g3_evolution_loop.py -v`:
   - 结果: **12 passed** (22.39s)
- **累计通过用例**: 69 项自动化测试 100% 绿灯。

---

## 2. 逻辑推导链 (Logic Chain)

1. **反作弊与完整性推导 [基于 1.1]**:
   四大裁判文件与全局 GEMINI.md 哈希值/时间戳未发生任何变动，说明工作区绝对隔离和裁判契约得到了严格遵循。
2. **断路修复与鲁棒性推导 [基于 1.2]**:
   - Bug 1: 原本卡片不显示是由于前端查找别名键而后端只返回原生键；现在前端后端均包含两套键，无论是旧调用方还是新调用方均能正确获取触发状态。
   - Bug 2: 维度 8 与维度 9 在 `ActiveRiskSentry` 内部原本已有完备的算法实现，但因首屏未传递适当性档位与持仓行情字典导致短路。修复后，数据字典完整下传，本地实盘 watchdog 快照立即产生有效预警，逻辑闭环。
   - Bug 3: 联接基金遵循证监会规定的 90%~95% 投资于目标 ETF 的法规，取 0.95 仓位折算符合公募投资实盘规则。同时白名单机制与 QDII 1.5% 阈值的保留，杜绝了纯债标的误伤和历史边界测试回归。
   - Bug 4: 穿透持仓篮子计算加权指标消除了以往拿单一沪深 300 粗暴代表所有组合（尤其是行业主题或债基）的宏观失真，在数学上符合加权期望公式。
3. **回归与稳定性推导 [基于 1.3]**:
   所有相关基础设施、因果律探针、历史演化、蒙特卡洛及 GUI 界面测试全量通过，无任何破坏性副作用。

---

## 3. 注意事项与边界说明 (Caveats)

1. **测试执行环境路径约定**:
   `AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py` 内部直接使用了 `from data_loader import DataLoader`（历史旧有代码导入风格），在工作区根目录执行时必须确保 `AGY2_FundAdvisory` 在 `PYTHONPATH` 中（如在 PowerShell 中执行 `$env:PYTHONPATH = "AGY2_FundAdvisory"`，或通过 pytest 选项 `-o pythonpath="AGY2_FundAdvisory ."` 执行）。根目录下的新测试套件（如 `tests/test_g12_circuit_breakers_and_sentry.py`）已在文件头部自适应将 `AGY2_FundAdvisory` 加入 `sys.path`，因此可直接运行。
2. **网络缓存隔离**:
   `fetch_realtime_index_quote` 存在 15 秒内存缓存，单测中已使用 `clear_realtime_cache()` 与 Mock 进行妥善隔离。

---

## 4. 实施结论 (Conclusion)

- **完整性审计**: 未发现任何硬编码测试结果、虚假实现、绕道作弊或伪造结果行为（Zero Integrity Violations）。
- **质量与对抗审查**: 4 项 Bug 修复方案严谨、接口契约兼容、边界条件完备，经受住了对抗性场景（空持仓、零权重、纯债隔离、API 异常等）检验。
- **最终裁决**: **APPROVE** (批准 Milestone 1 交付，允许流水线推进至 Milestone 2)。

---

## 5. 独立验证方法 (Verification Method)

在 PowerShell 环境中逐项执行以下命令进行独立复核：

```powershell
# 1. 验证四大裁判文件零修改 (输出必须为空，退出码为 0)
git diff --exit-code AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/tests/test_infra.py

# 2. 运行基础设施与反作弊裁判测试 (14 passed)
py -3 -m pytest tests/test_infra.py -v

# 3. 运行 M1 专项修复测试套件 (11 passed)
py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v

# 4. 运行 G10 相关性突变与压力测试套件 (6 passed)
py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py -v

# 5. 运行实盘调仓与盘中估值升级测试套件 (12 passed)
$env:PYTHONPATH = "AGY2_FundAdvisory"; py -3 -m pytest AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py -v
```
