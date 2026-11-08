# Milestone 1 审查与对抗性质询报告 (Reviewer & Adversarial Critic Report)

- **审查人 (Reviewer & Critic)**: `teamwork_reviewer` (`reviewer_g12_m1_1`)
- **审查目标**: G12 Generation Milestone 1 (四大代码断路修复与风控穿透)
- **审查基准**:
  - `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
  - `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_16\PROJECT.md`
  - `d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m1\handoff.md`
- **审查裁决 (Verdict)**: **APPROVE (批准通过)**

---

## 1. 观察事实 (Observation)

### 1.1 裁判文件与只读不变量验证
- 执行命令: `git diff --exit-code HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py`
- 结果: 退出码为 `0`，标准输出与标准错误均为空，差异为 0 行 (0 git diff)。四个只读裁判文件未受任何修改。
- 全局规则文件 `c:\Users\deanc\.gemini\GEMINI.md` 未被触碰。

### 1.2 Bug 1: 相关性突变预警指示卡门禁与双保险别名
- 文件位置: `AGY2_FundAdvisory/app_gui.py` 第 3005 行与 `AGY2_FundAdvisory/portfolio_manager.py` 第 8689-8693 行。
- 代码核验:
  - `portfolio_manager.py` 在返回字典中同时返回原生键与别名键：
    ```python
    "is_triggered": is_triggered,
    "is_liquidity_shift_triggered": is_liquidity_shift_triggered,
    "is_mutation_alarm": is_triggered,
    "is_regime_shift_risk": is_liquidity_shift_triggered,
    ```
  - `app_gui.py` 门禁升级为四键兼容：
    ```python
    if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered") or corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
        safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
    ```
  - 核查 `render_correlation_mutation_card_html` (第 1853-1854 行) 原生依赖 `is_triggered` 与 `is_liquidity_shift_triggered`，键名已完全对齐。

### 1.3 Bug 2: `sentry.inspect_portfolio` 投资者适当性与持仓实时报价穿透
- 文件位置: `AGY2_FundAdvisory/app_gui.py` 第 2719-2743 行。
- 代码核验:
  - 显式从 `st.session_state` 获取 `_cur_tier = str(st.session_state.get("active_tier_val", "C3")).upper()`。
  - 遍历持仓提取实时报价 `_f_quotes[_c] = fetch_realtime_fund_quote(_c, use_cache=True)`。
  - 注入 `_augmented_snapshot["fund_quotes"] = _f_quotes` 与 `_augmented_snapshot["investor_risk_tier"] = _cur_tier`。
  - 显式向 `sentry.inspect_portfolio` 传递 `investor_risk_tier=_cur_tier` 与增强后的快照字典。
  - 验证激活了 `ActiveRiskSentry` 维度 8 (适当性与权益超限巡检) 与维度 9 (盘中实时异动及安全垫消耗传导)。

### 1.4 Bug 3: 指数与 ETF 联接基金盘中估值校准精度
- 文件位置: `AGY2_FundAdvisory/portfolio_manager.py` 第 2174-2302 行及 2341, 2375, 2400, 2437 行。
- 代码核验:
  - 扩展 `INDEX_AND_FEEDER_BENCHMARK_MAP`（涵盖标普500、纳指、黄金、科创50、芯片半导体、红利低波、中证红利、沪深300、中证500、中证1000、白酒等），并保留 `QDII_BENCHMARK_MAP` 别名。
  - 实装 `_apply_fund_valuation_calibration`：联接基金按 `0.95` 仓位系数折算，纯指数基金按 `1.0` 折算。
  - 对 QDII/黄金严格保持既有偏差 `> 1.5%` 纠偏契约；对 A 股指数与联接基金在偏差 `> 0.1%` 或天天基金盘中滞后为 `0.0%` 时结合基准实时涨跌幅执行动态覆盖校准。
  - 纯债标的（如 `002351`）不匹配基准，绝不误触发纠偏。
  - 导出兼容别名 `_apply_qdii_valuation_correction = _apply_fund_valuation_calibration`，向下兼容既有单测与调用点。

### 1.5 Bug 4: Tab 1 智能定投加权乖离率与 ERP 穿透
- 文件位置: `AGY2_FundAdvisory/advisory_engine.py` 第 2430-2475 行与 `AGY2_FundAdvisory/app_gui.py` 第 3905-3921 行。
- 代码核验:
  - 实装 `SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(allocations, snapshot)`：
    - 精算建仓组合标的加权 `bias_20`。
    - 纯债/黄金/固收防守标的对齐宏观中性 ERP，权益/行业资产结合自身乖离率上浮或下调 ERP，加权输出 `(weighted_erp_pct, weighted_bias_20)`。
  - 在 `app_gui.py` 智能定投流程中，计算得到的 `erp_pct, bias_20` 同时注入 `SmartExecutionDCAEngine.plan_smart_dca` 与 `StrategyBridge.get_historical_inflection_ruler`，彻底消除了单一大盘指数（沪深300）对异质化组合的代表性失真。

### 1.6 自动化测试套件独立复验执行结果
独立执行全部关键测试套件，均 100% 绿灯通过：
1. `py -3 -m pytest tests/test_infra.py -v`: **14 passed** in 5.64s
2. `py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v`: **11 passed** in 20.07s
3. `py -3 -m pytest tests/test_adv_final_closure.py -v`: **14 passed** in 39.24s
4. `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py -v`: **6 passed**
5. `py -3 -m pytest AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py -v`: **12 passed**
累计 **57 项自动化测试全部通过**。

### 1.7 诚信与作弊模式排查 (Integrity Audit)
- 检查是否存在写死测试期望值或特定返回分支：无。各函数均根据传入参数或实时行情计算，不存在 `if test: return ...` 或死常数欺骗。
- 检查是否存在空壳/假实现 (Facade)：无。四个功能模块均包含完整的数学计算、数据穿透与双向容错逻辑。
- 检查是否存在绕过核心任务或自封报告：无。测试全部由真实 pytest 进程在 Windows Python 3.11 运行并通过。

---

## 2. 逻辑推导链 (Logic Chain)

1. **Bug 1 闭环有效性**:
   - 基于 [1.2]，旧代码中 `app_gui.py` 监听不存在的 `is_mutation_alarm` / `is_regime_shift_risk`，而 `portfolio_manager.py` 只输出 `is_triggered` / `is_liquidity_shift_triggered`。
   - Worker 采取了双保险策略：在底层补齐别名键，并在前端对四键进行 `or` 组合判断。即使上游或下游任一处未来出现键名变动，指示卡都能正确响应，断路缺陷彻底消除。
2. **Bug 2 闭环有效性**:
   - 基于 [1.3]，`ActiveRiskSentry` 内部原已实装维度 8 (适当性) 与维度 9 (盘中异动消耗传导)，但因外层未传入 `investor_risk_tier` 且快照缺少 `fund_quotes` 导致两大风控维度长期处于冷冻休眠状态。
   - Worker 从 `st.session_state` 动态提取风险等级并实时拉取单基报价注入快照后，直接击穿了参数隔离层，使得首屏双翼看板能够对 C1 客户超配 80% 权益标的精准告警，对单基盘中暴跌超 2% 传导安全垫消耗即时提醒。
3. **Bug 3 闭环有效性**:
   - 基于 [1.4]，中国公募基金中场外 ETF 联接基金投资于目标 ETF 的资产比例不低于基金资产净值的 90%（通常维持在 95%）。天天基金在盘中由于重仓股季报滞后，其盘中估值通常不准或显示为 0.0%。
   - Worker 实装的 `_apply_fund_valuation_calibration` 锚定场内标的变动并乘以 0.95 仓位系数（纯指数按 1.0），同时严格保持 QDII 1.5% 阈值契约并物理豁免纯债基金，既解决了估值失真，又未破坏任何既有资产的边界契约。
4. **Bug 4 闭环有效性**:
   - 基于 [1.5]，用户建仓通常为混合组合，单一大盘沪深 300 无法代表科技成长或纯债标的的估值分位。
   - Worker 实装的 `compute_portfolio_weighted_bias_and_erp` 对资产类别进行分类处理（防守资产对齐宏观中性 ERP，弹性资产基于乖离率调整），并加权输出，使 Tab 1 智能定投乘数与牛熊对照尺真实锚定持仓篮子自身的真实周期位置。
5. **裁判与合规底线**:
   - 基于 [1.1] 和 [1.7]，四大裁判文件 0 diff，无诚信违规，测试全绿，代码稳健。

---

## 3. 注意事项与对抗性挑战发现 (Caveats & Adversarial Findings)

1. **对抗性极端输入发现 (Adversarial Robustness - Minor)**:
   - 在对抗性测试脚本 `test_adversarial_m1.py` 中发现：若向 `compute_portfolio_weighted_bias_and_erp` 传入包含 `"weight": None` 的畸形字典项时，`a.get("weight", 0.0)` 因键存在且值为 `None` 会返回 `None`，导致 `float(None)` 抛出 `TypeError`。
   - **风险评估**: **极低 (Low Risk)**。在生产 GUI 中，`allocations` 均由系统模型或表格行安全解析生成，权重均为浮点数，不会出现 `None`。
   - **优化建议**: 后续可微调为 `float(a.get("weight") or 0.0)` 以获得极致防御。
2. **总权重为 0 的边界处理**:
   - 若传入的 `allocations` 列表中所有标的权重均为 0，当前逻辑会计算出 `(0.0, 0.0)`。建议在 `total_w <= 0.0` 时直接回退返回 `(round(macro_erp, 2), round(c300_bias, 2))`。
3. **未探索范围**:
   - 本里程碑仅覆盖 Bug 1-4（M1 范围）。M2（移动止盈与日线自愈）、M3（7D GP 规则树）及 M4（服务重启与浏览器视觉走查）属于后续里程碑，将在后续阶段逐一闭环。

---

## 4. 实施结论 (Conclusion)

- **综合评价**: Milestone 1 交付质量优良。4 处断路缺陷被精准修复，代码改动紧凑且具备双保险与向下兼容设计；57 项自动化测试 100% 绿灯；裁判文件哈希零变动；无作弊或假实现。
- **裁决结论**: **APPROVE (批准通过，无阻塞性缺陷，可立即推进至 Milestone 2)**。

---

## 5. 独立验证方法 (Verification Method)

在项目根目录下通过 PowerShell 运行以下命令即可独立验证本结论：

```powershell
# 1. 验证四大裁判文件严格只读 (应输出 0 差异且退出码为 0)
git diff --exit-code HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py

# 2. 运行基础设施裁判测试套件 (14 passed)
py -3 -m pytest tests/test_infra.py -v

# 3. 运行 M1 专项测试套件 (11 passed)
py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v

# 4. 运行全量业务核心与因子演化测试套件 (14 passed)
py -3 -m pytest tests/test_adv_final_closure.py -v
```
