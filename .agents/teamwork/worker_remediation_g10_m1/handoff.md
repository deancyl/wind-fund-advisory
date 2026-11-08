# G10 M1 压力测试缺陷整改交付报告 (handoff.md)

**执行智能体**: `worker_remediation_g10_m1` (teamwork_worker / implementer & qa)  
**被修复目标**: `AGY2_FundAdvisory/portfolio_manager.py`  
**上级调度方 (Caller)**: `22f2ddb7-c220-44ca-b889-a5c0901cc3b3` (orchestrator_11)  
**时间戳**: 2026-11-08T04:25:30Z  
**交付裁决 (Verdict)**: **RESOLVED (全部缺陷修复完毕，100% 验收通过)**

---

## 1. 事实观察 (Observation)

### 1.1 缺陷复现观察 (Pre-fix Reproduction)
在整改前执行 Challenger 2 的实证压测脚本：
```powershell
py -3 scripts/verify_cvar_stress_testing.py
```
终端输出 verbatim：
```
[CHECK 5] ADVERSARIAL TEST: FIFO 7-Day Lock Penalty Defense...
  Dict input (holding_days=2): liquidation_days=2.8
  Dict input (holding_days=30): liquidation_days=2.8
  Dict difference: 0.0 days (expected 5.0 days penalty)
  -> FAIL: CRITICAL BUG: simulate_portfolio_cvar_bootstrap fails to account for FIFO locks when holdings are passed as dicts! Got diff=0.0 days instead of 5.0 days.
  PM instance (holding_days=2 in batch): liquidation_days=2.8
  PM instance (holding_days=30 in batch): liquidation_days=2.8
  PM instance difference: 0.0 days (expected 5.0 days penalty)
  -> FAIL: CRITICAL BUG: simulate_portfolio_cvar_bootstrap_instance fails to account for FIFO locks in real FundHolding batches! Got diff=0.0 days instead of 5.0 days.

[CHECK 6] ADVERSARIAL TEST: simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm)...
  -> FAIL: CRITICAL BUG: simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm) crashes with: AttributeError: 'FundHolding' object has no attribute 'holding_days'.

VERDICT: REJECT (3 critical defect(s) discovered empirically)
```

### 1.2 代码缺陷根因定位 (Root Cause Analysis)
1. **字典入参短路缺陷**:
   原 `portfolio_manager.py` 第 8677 行与 8687 行采用 `hd = int(getattr(v, "holding_days", 30) or ...)`。对字典对象 `v`，`getattr(v, "holding_days", 30)` 查找属性失败返回默认值 `30`，导致 `30 or ...` 触发真值短路，完全忽略了 `v.get("holding_days")`。
2. **FundHolding 批次穿透缺失缺陷**:
   `FundHolding`（原 261-294 行）本身不包含 `holding_days` 标量字段，其实际持有天数存放在批次 `batches[i].holding_days` 中。当 `v` 为 `FundHolding` 实例时，`getattr(v, "holding_days", 30)` 同样返回 30，无法穿透至真实批次持有天数。
3. **pm_instance 调用路径 AttributeError 崩溃**:
   原第 8697 行：
   `items_detail.append({"code": str(c), "name": h.fund_name, "market_value": h.market_value, "holding_days": h.holding_days, "weight": w})`
   由于 `h` 是 `FundHolding` 类型，直接点号访问不存在的属性 `h.holding_days` 抛出 `AttributeError` 崩溃。

### 1.3 修复实施观察 (Applied Remediation)
在 `AGY2_FundAdvisory/portfolio_manager.py` 中实施双重防御：
1. **数据模型层 (FundHolding)**:
   为 `FundHolding` 数据类（第 295-300 行）添加 `@property def holding_days(self) -> int` 属性：
   ```python
   @property
   def holding_days(self) -> int:
       """悲观最短持有天数 (FIFO 惩罚锁防线)"""
       if getattr(self, "batches", None):
           return min((b.holding_days for b in self.batches), default=30)
       return 30
   ```
2. **算法入参解析层 (simulate_portfolio_cvar_bootstrap)**:
   在字典循环与列表/元组循环中，采用显式三级提取逻辑：
   ```python
   if isinstance(v, dict):
       hd = int(v.get("holding_days", 30))
   elif getattr(v, "batches", None):
       hd = int(min((b.holding_days for b in v.batches), default=30))
   else:
       hd = int(getattr(v, "holding_days", 30))
   ```
   在 `pm_instance` 分支中安全提取：
   ```python
   h_days = min((b.holding_days for b in h.batches), default=30) if getattr(h, "batches", None) else getattr(h, "holding_days", 30)
   items_detail.append({"code": str(c), "name": h.fund_name, "market_value": h.market_value, "holding_days": int(h_days), "weight": w})
   ```

### 1.4 修复后验证观察 (Post-fix Verification)
1. 运行 `py -3 scripts/verify_cvar_stress_testing.py`：
   ```
   [CHECK 1] Testing Mathematical Risk Axioms across portfolios and risk tiers...
     -> PASS: All 90 scenario risk axiom checks verified (CVaR_99 >= VaR_99 >= VaR_95).
   [CHECK 2] Testing Scenario Realism and Differentiation...
     -> PASS: Scenario differentiation verified: 2008 has deepest equity drawdown, 2015 has highest liquidation days.
   [CHECK 3] Testing Determinism and Top 5 ADV Capacity Scaling...
     -> PASS: Deterministic repeatability verified.
     -> PASS: Top 5 ADV capacity scaling verified: 10k capital=5.0d, 50B capital=28.0d.
   [CHECK 4] Testing Investor Risk Tolerance Gating (C1 vs C5)...
     -> PASS: C1 conservative triggers exceeds_risk_tolerance=True, while C5 aggressive remains within limits.
   [CHECK 5] ADVERSARIAL TEST: FIFO 7-Day Lock Penalty Defense...
     Dict input (holding_days=2): liquidation_days=7.8
     Dict input (holding_days=30): liquidation_days=2.8
     Dict difference: 5.0 days (expected 5.0 days penalty)
     -> PASS: Dict FIFO lock verified.
     PM instance (holding_days=2 in batch): liquidation_days=7.8
     PM instance (holding_days=30 in batch): liquidation_days=2.8
     PM instance difference: 5.0 days (expected 5.0 days penalty)
     -> PASS: PM FundHolding FIFO lock verified.
   [CHECK 6] ADVERSARIAL TEST: simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm)...
     -> PASS: pm_instance call succeeded.
   VERDICT: APPROVE (All empirical adversarial checks passed)
   ```
2. 运行全量 65 项自动化测试套件：
   ```powershell
   py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py
   ```
   结果：
   ```
   ================= 65 passed, 121 warnings in 76.44s (0:01:16) =================
   ```
   65 项测试 100% 绿灯通过，退出码为 0。

3. 裁判只读文件完整性核验：
   `git status AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py` 输出工作区干净，四大只读裁判文件零改动。

---

## 2. 逻辑论证链 (Logic Chain)

1. **前提 1 (调度与契约要求)**:
   - 调度指令与 GEMINI.md 第 7 条明确要求：“持仓批次天数与先进先出安全赎回铁律：必须使用悲观保守的 `min((b.holding_days for b in batches), default=30)`；未满 7 天份额触发惩罚锁定”。
   - Challenger 2 对抗测试发现，由于短路和对象属性缺失，输入未满 7 天份额计算出的变现天数与持有 30 天无异（差值为 0.0 天，缺少 5.0 天惩罚锁定），且 `holdings=None, pm_instance=pm` 抛出 `AttributeError`。
2. **逻辑推理与因果对应**:
   - 依据 Observation 1.2，修复将布尔短路替换为显式 `isinstance(v, dict)` 与 `v.get(...)` 分支，使得字典传入 `holding_days: 2` 时准确解析为 `2`；
   - 对 `FundHolding` 实例，通过 `getattr(v, "batches", None)` 与属性 `@property def holding_days` 提取悲观最短批次天数 `min(b.holding_days for b in v.batches)`，使得持有 2 天的新增批次准确解析为 `2`；
   - 在第 8825 行：`t_lock = max(0, 7 - hd) if hd < 7 else 0`，当 `hd = 2` 时 `t_lock = 5.0`，因此变现天数由 2.8 天精确增至 7.8 天，差值恰好为 5.0 天；
   - 在第 8697 行，将 `h.holding_days` 替换为安全提取表达式，彻底根除了 `AttributeError` 崩溃。
3. **结论**:
   上述修复直接消除了 Challenger 2 报告中列出的 3 项阻断缺陷，且未引入任何副作用与未来函数。

---

## 3. 注意事项与边界说明 (Caveats)

1. **只读裁判文件零触碰**:
   四大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希未变。
2. **最小修改原则**:
   除 `FundHolding` 数据类与 `simulate_portfolio_cvar_bootstrap` 函数中的持仓持有天数解析逻辑外，未改动任何其他业务逻辑与默认参数。
3. **No other caveats**。

---

## 4. 交付结论 (Conclusion)

- **综合裁决**: **RESOLVED / APPROVE (缺陷全部修复并通过独立对抗脚本与全量回归套件)**
- **代码状态**:
  - `AGY2_FundAdvisory/portfolio_manager.py` 已完全支持字典、列表、`FundHolding` 批次与 `pm_instance` 多态持有天数提取；
  - 悲观 7 天 FIFO 惩罚锁已在压力测试与流动性变现天数算法中生效（变现天数准确增加 $7 - \min(batches)$ 天）；
  - 全量 65 项自动化测试 100% 通过。

---

## 5. 独立复现与验证方法 (Verification Method)

### 5.1 对抗压测脚本验证
在 Windows PowerShell 终端中执行：
```powershell
py -3 scripts/verify_cvar_stress_testing.py
```
**期望结果**: 终端输出 `VERDICT: APPROVE (All empirical adversarial checks passed)` 且退出码为 0。

### 5.2 全量自动化回归套件验证
在 Windows PowerShell 终端中执行：
```powershell
py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py
```
**期望结果**: 65 passed in ~76s, 退出码为 0。
