# Handoff Report: Milestone 1 (M1) MultiLedgerManager 对抗压力测试与漏洞审计报告

**Agent**: `challenger_r9_m1_1` (teamwork_challenger)  
**Roles**: critic, specialist (empirical_challenger)  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_r9_m1_1`  
**Parent Conversation ID**: `8849ddae-0421-48b2-aa8f-6d2c7b15dafe`  
**Timestamp**: 2026-11-05T14:53:00Z  
**Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation (观测事实)

挑战者编写并运行了独立的对抗压力测试套件 `tests/test_multi_ledger_manager_stress.py`（包含 8 项端到端压力与攻击测试）。在 Python 3.11 环境下执行：

```powershell
py -3 -m pytest tests/test_multi_ledger_manager_stress.py -v
```

执行产出如下测试结果：
- **PASSED** (6项):
  1. `test_stress_rapid_lifecycle_cycles`: 40 个账本高频创建、10 个克隆、10 个重命名、20 个删除，无 UUID 碰撞，`active_ledger_id` 回退与索引结构完好无损。
  2. `test_stress_isolation_extreme_batches_transactions_snapshots`: 沙盒注入 40 只基金、120 个批次、15 个在途挂单、25 次 `save_state` 快照，主实盘 `portfolio_ledger.json` 与 `portfolio_state.db` 的 SHA256 哈希值 **逐字节 100% 完全未变（0 字节篡改）**，SQLite 内部行数完好无损。
  3. `test_protection_attack_direct_call`: 直接调用 `mlm.delete_ledger("main_live")` 成功抛出 `PermissionError` 并拒绝删除。
  4. `test_protection_attack_protected_flag`: 针对标记为 `is_protected=True` 的自定义账本，调用 `delete_ledger()` 成功抛出 `PermissionError`。
  5. `test_get_pm_nonexistent_ledger_safety`: 记录并验证了不存在账本 ID 时的静默回退行为。
  6. `test_stress_get_all_ledgers_summary_arithmetic_integrity`: 覆盖纯现金、大幅浮盈、大幅浮亏、在途交收、内存运行态未落盘、高精度微小金额等 7 种账本星系，总资产、总浮盈、总市值、持仓只数完全符合严格算术恒等式与自洽公式（`total_equity == market_value + available_cash + in_transit_cash`）。
- **FAILED** (2项，暴露 2 处严重物理漏洞):
  1. `test_protection_attack_case_and_whitespace_variants`:
     - 报错信息: `Failed: DID NOT RAISE PermissionError`
     - 对应代码: `AGY2_FundAdvisory/multi_ledger_manager.py` 第 324 行
       ```python
       if ledger_id == "main_live":
           raise PermissionError("主实盘账本受物理保护，禁止删除！")
       ```
     - 事实: 当传入大小写变体（`"MAIN_LIVE"`、`"Main_Live"`）或首尾空格变体（`"main_live "`）时，`ledger_id == "main_live"` 判定为 `False`。随后在未命中索引列表时直接返回 `False`，**未能按设计红线无条件抛出 `PermissionError` 物理拦截**。
  2. `test_protection_attack_path_traversal_and_file_alias`:
     - 报错信息: `AssertionError: CRITICAL BUG: 主实盘 portfolio_ledger.json 被路径遍历漏洞误删！ assert False where False = exists()`
     - 对应代码: `AGY2_FundAdvisory/multi_ledger_manager.py` 第 337-350 行
       ```python
       f_path = self.root / target.get("file", "")
       db_path = self.root / target.get("db_file", "")

       if f_path.exists() and f_path != self.main_file:
           try:
               f_path.unlink()
           except Exception:
               pass
       ```
     - 事实: `self.main_file` 为 `self.root / "portfolio_ledger.json"`。当索引条目中包含未归一化的相对路径（如 `"data/../portfolio_ledger.json"`）时，`Path` 对象直接比对 `f_path != self.main_file` 判定为 `True`（两者字符串未 normalize），导致 `f_path.unlink()` 被触发，**生产级主实盘 `portfolio_ledger.json` 被直接物理删除**！同样漏洞在 `db_path != self.main_db` 中对称存在，会导致 `portfolio_state.db` 被误删。

---

## 2. Logic Chain (推演逻辑链)

1. **隔离性与算术完整性推演**：
   - 在高频 40 个账本生命周期中，UUID 后缀与毫秒时间戳有效防止了碰撞；
   - 在极端压力测试中，沙盒通过派生独立的 `data/ledgers/<id>.json` 与 `data/ledgers/<id>.db`，完全切断了与根目录 SQLite 的关联，25 次连续存盘未对主实盘文件造成任何字节级改动（SHA256 完全恒定）；
   - `get_all_ledgers_summary()` 在多账本存在不同盈亏极值、现金结构与内存态的情况下，算术聚合严格自洽，表明聚合数学模型与状态机抓取准确无误。

2. **安全防护绕过漏洞推演 (基于 Observation 2)**：
   - **漏洞 A (CRITICAL 物理误删漏洞)**: `Path` 在比较 `f_path != self.main_file` 时，如果一个包含冗余的点段（如 `data/..`），`Path('a/b/../c') == Path('a/c')` 为 `False`。由于未调用 `.resolve()`，当索引文件被篡改、迁移或录入带点路径时，删除该条目会导致 `f_path.unlink()` 击穿物理防御，抹除主实盘数据文件！必须使用 `f_path.resolve() != self.main_file.resolve()` 实施绝对路径防线。
   - **漏洞 B (HIGH 保护规避漏洞)**: 主实盘保护要求对任何指向主实盘的删除指令均予以拒绝并报警（抛出 `PermissionError`）。当前代码仅匹配小写 `"main_live"`，对变体判定为普通不存在账本而静默返回 `False`，违背了“无条件抛出 PermissionError 坚决拒绝”的约束。应通过 `str(ledger_id).strip().lower() == "main_live"` 进行归一化校验。
   - **架构隐患 C (MEDIUM 静默回退污染风险)**: `get_pm(ledger_id)` 在 `not meta` 时静默回退至 `main_live`。若调用方拼错 ID 或操作已删除沙盒，将误拿到实盘 PM 并执行写入，应抛出 `KeyError`。

---

## 3. Caveats (注意事项与假设)

1. 挑战者遵循严格的“仅审查/测试、严禁擅自修改产品代码”原则，故未在 `AGY2_FundAdvisory/multi_ledger_manager.py` 中自行打补丁，而是保留失败用例与经验事实交由 Implementer (Worker) 统一修正。
2. 基础功能的 8 项单元测试（`tests/test_multi_ledger_manager.py`）依然 100% 通过，本报告指出的两项漏洞属于对抗性安全红线与极端路径穿透场景。

---

## 4. Conclusion (交付结论)

**明确裁定：`REQUEST_CHANGES` (要求打回整改)**

`MultiLedgerManager` 的基本生命周期、独立 SQLite 派生隔离（SHA256 绝对一致）以及家庭资产算术汇总功能已高度完善并承受住了高频极端压力考验。然而，其在安全删除防护机制上存在两处确凿漏洞，必须由 Worker 进行生产级加固：

1. **【必须修复 - CRITICAL】** 在 `delete_ledger` 的文件物理清理判断中，强制使用 `.resolve()` 进行绝对路径归一化比对：
   ```python
   f_path = (self.root / target.get("file", "")).resolve()
   db_path = (self.root / target.get("db_file", "")).resolve()
   main_file_res = self.main_file.resolve()
   main_db_res = self.main_db.resolve()

   if f_path.exists() and f_path != main_file_res:
       try:
           f_path.unlink()
       except Exception:
           pass

   if db_path.exists() and db_path != main_db_res:
       try:
           db_path.unlink()
       except Exception:
           pass
   ```
2. **【必须修复 - HIGH】** 在 `delete_ledger` 入口处对 `ledger_id` 进行大小写与空白字符归一化：
   ```python
   if str(ledger_id).strip().lower() == "main_live":
       raise PermissionError("主实盘账本受物理保护，禁止删除！")
   ```
3. **【建议修复 - MEDIUM】** `get_pm(ledger_id)` 对非 `main_live` 且在索引中不存在的账本 ID 抛出 `KeyError(f"账本未找到: {ledger_id}")`，防止调用方发生无意识静默踩踏。

---

## 5. Verification Method (独立核验方法)

下游 Worker 修复上述代码后，执行以下命令验证整改效果：

```powershell
# 1. 运行挑战者全量对抗压力测试套件（修复后预期 8 passed in ~20s）
py -3 -m pytest tests/test_multi_ledger_manager_stress.py -v

# 2. 运行基础多账本功能测试
py -3 -m pytest tests/test_multi_ledger_manager.py -v

# 3. 运行整体回归测试套件
py -3 -m pytest tests/test_infra.py tests/test_portfolio.py tests/test_multi_ledger_manager.py tests/test_multi_ledger_manager_stress.py
```
