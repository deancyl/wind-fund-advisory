# Multi-Ledger Idempotent Mount & Holding Days Handoff Report

**Agent**: `explorer_m3_1`  
**Milestone**: Milestone 3 Item 1 (Multi-Ledger Manager Idempotent Mount & Holding Days Reconciliation)  
**Status**: Exploration Complete  

---

## 1. Observation (客观事实与直接观测)

### 1.1 `multi_ledger_manager.py` 现状与测试失败直接报错
- 源码位置：`AGY2_FundAdvisory/multi_ledger_manager.py` 第 170-187 行。
- 观察结果：在 `MultiLedgerManager._ensure_index_initialized` 中，无论传入的 `workspace_root` 是生产目录还是测试用的临时目录 `temp_workspace`，都会无条件调用 `self._init_preset_combat_29_ledger()` 并将 `combat_29_funds` 注入到账本索引中。
- 直接报错 1 (`tests/test_multi_ledger_manager.py:237`):
  ```
  FAILED tests/test_multi_ledger_manager.py::test_get_all_ledgers_summary - AssertionError: assert 427615.1 == 400000.0 ± 0.4
  Obtained: 427615.1
  Expected: 400000.0 ± 0.4
  ```
  原因：单测预期只有 `main_live` (10万) + `稳健养老金` (30万) = 40万总资产、1只持仓、2个账本。由于自动注入了 `combat_29_funds`，导致总资产变为 427,615.10 元、持仓总数变为 30 只、账本数变为 3。
- 直接报错 2 (`tests/test_multi_ledger_manager_stress.py:495`):
  ```
  FAILED tests/test_multi_ledger_manager_stress.py::test_stress_get_all_ledgers_summary_arithmetic_integrity
  AssertionError: assert 8 == 7
  where 8 = len([{'id': 'main_live', ...}, {'id': 'combat_29_funds', ...}, ...])
  ```
  原因：测试用例构建了 1 个主实盘 + 6 个新建账本，预期账本总数为 7，但因为临时目录下被自动注入 `combat_29_funds`，实际变为了 8 个账本。

### 1.2 生产环境与既有实证测试现状
- 在 `WORKSPACE_ROOT`（`D:\Google\Workspace\Wind`）下：
  - `data/ledgers_index.json` 中已注册 `combat_29_funds`；
  - `data/ledgers/combat_29_funds.json` 真实存在，29 只基金市值精确平账至 ¥26,615.10 元；
  - `tests/test_adversarial_m3_combat29_challenger.py`（9 项全过）、`tests/test_g15_phase3_ocr_and_combat29.py` 与 `tests/test_g16_phase1_memo_and_combat29.py`（11 项全过）均依赖 `combat_29_funds` 在生产目录的可用性。

### 1.3 400 天 vs 1040 天持有天数分布观察
1. **400 天**：
   - `data/ledgers/combat_29_funds.json`：所有 29 只基金批次明确写入 `"holding_days": 400` 与 `"notes": "实战存量批次(满400天免赎)"`；
   - `AGY2_FundAdvisory/multi_ledger_manager.py:258`：预置代码中 `holding_days: 400`；
   - `AGY2_FundAdvisory/advisory_engine.py:4384-4386`：降级兜底天数设为 `400`；
   - `AGY2_FundAdvisory/app_gui.py:6134, 6145`：文案表述为“持仓天数均已达 400 天”、“已持有满 400 天”；
   - `tests/test_adversarial_m3_combat29_challenger.py:99`：断言 `assert b["holding_days"] == 400`。
2. **1040+ 天 (实测 1041 天)**：
   - `AGY2_FundAdvisory/portfolio_manager.py:4060-4066`：`_recalculate_totals()` 读取 `b.buy_date="2024-01-05"`，按 `(today_date - b_dt).days` 动态计算自然日天数，在当前时点（2026年11月）重算结果为 1,041 天；
   - `AGY2_FundAdvisory/app_gui.py:5851, 5932`：Tab 2 持仓列表“最短持有天数”列动态显示 1041 天。

---

## 2. Logic Chain (推理链条)

1. **[观察 1.1 -> 单测隔离失效机理]**：
   - pytest 单元测试（如 `test_multi_ledger_manager.py` 与 `test_multi_ledger_manager_stress.py`）通过 `tmp_path` 创建独立的 `temp_workspace` 目录，以测试 MultiLedgerManager 在空状态下的账本生命周期管理。
   - `MultiLedgerManager.__init__` 无条件在任何 `workspace_root` 下执行 `combat_29_funds` 的初始化，破坏了单测工作区的初始纯净假设，注入了预期外的 1 个账本与 29 只持仓，直接导致基于空工作区的账本计数和资产汇总断言失败。
2. **[观察 1.2 -> 生产幂等挂载必要性]**：
   - 用户实际使用 Web UI (`app_gui.py`) 以及端到端实证测试，工作区根目录始终为 `WORKSPACE_ROOT`。
   - 用户指令契约（ORIGINAL_REQUEST.md §一.2）明确要求：由 MultiLedgerManager 自动幂等挂载 29 基实战账本，确保打开网页 100% 可见可用。
   - 因此，**挂载逻辑必须存在，但触发作用域必须严格限制为 `self.root.resolve() == WORKSPACE_ROOT.resolve()`**。
3. **[观察 1.3 -> 400天与1040天的一致性推理]**：
   - 400 天是静态数据档案建档时的基准标记（表示建档于 2025 年初且已满 1 年以上）；
   - 1040+ 天是 PM 运行时基于 `buy_date="2024-01-05"` 动态推进至当前日期（2026年11月）的物理日历天数；
   - 按照证监会与公募基金规则（Rule 7）：C类满 30 天免赎、A类满 365 天免赎、任何份额满 7 天无 1.50% 惩罚费。400 天与 1041 天均远大于 365 天，两者的赎回费率严格为 0.00%，`safety_lock` 均为 False，可免赎份额均为 100%；
   - 因此二者在量化交易与风控模型上完全等价，只需在前端文案上做“基准 400 天 / 现已超 1,040 天”的微调调和，同时保留 JSON 底层 400 天数值以保护既有单测。

---

## 3. Caveats (潜在风险与约束)

1. **JSON 底层 holding_days 严禁修改为 1040**：`tests/test_adversarial_m3_combat29_challenger.py:99` 中有硬断言 `assert b["holding_days"] == 400`。底层 JSON 中的 400 属于既有契约，不可随意改动。
2. **Windows 路径大小写防御**：比较工作区路径时，Windows 环境下驱动器盘符大小写或长短路径可能不同，建议统一转为字符串并小写化比对：`str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower()`。
3. **只读裁判文件红线**：严禁修改 `tests/test_infra.py`、`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`。

---

## 4. Conclusion (探索结论与实施方案)

### 4.1 实施方案 1：`AGY2_FundAdvisory/multi_ledger_manager.py` 隔离保护
在 `_ensure_index_initialized` 中加入根工作区判别：
```python
if str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower():
    combat_item = next((l for l in final_ledgers if l.get("id") == "combat_29_funds"), None)
    combat_json_path = self.ledgers_dir / "combat_29_funds.json"
    if not combat_item or not combat_json_path.exists():
        combat_meta = self._init_preset_combat_29_ledger()
        if not combat_item:
            final_ledgers.append(combat_meta)
        else:
            for idx, l in enumerate(final_ledgers):
                if l.get("id") == "combat_29_funds":
                    final_ledgers[idx] = combat_meta
                    break
```

### 4.2 实施方案 2：`AGY2_FundAdvisory/app_gui.py` 文案调和
将第 6134 行与 6145 行的文案调整为：
- 6134 行：`持仓天数均已达 400~1,040+ 天（基准 400 天 / 现已超 1,040 天，均成立满1年以上），赎回手续费严格为 ¥0.00。`
- 6145 行：`已持有满 400~1,040+ 天（远超 30 天免赎期）但仍按 C 类计提每年 0.40% 销售服务费，长期持有持续钝刀割肉；`

---

## 5. Verification Method (验证方法)

请在 Worker 完成代码修改后执行以下验证命令：

1. **测试隔离环境核验**：
   ```powershell
   py -3 -m pytest tests/test_multi_ledger_manager.py
   ```
   **期望结果**：8 passed，原 `test_get_all_ledgers_summary` 失败彻底消除。

2. **压力测试星系核验**：
   ```powershell
   py -3 -m pytest tests/test_multi_ledger_manager_stress.py
   ```
   **期望结果**：8 passed，原 `test_stress_get_all_ledgers_summary_arithmetic_integrity` 失败彻底消除。

3. **29基实战账本与持仓天数核验**：
   ```powershell
   py -3 -m pytest tests/test_adversarial_m3_combat29_challenger.py
   ```
   **期望结果**：9 passed，分厘平账、400天预置与>=365天动态天数全部绿灯。

4. **全量阶段测试回归**：
   ```powershell
   py -3 -m pytest tests/test_g15_phase3_ocr_and_combat29.py tests/test_g16_phase1_memo_and_combat29.py
   ```
   **期望结果**：11 passed 100% 绿灯。
