# Handoff Report: Milestone 1 (M1) 故障综合整改方案交付报告

**Agent**: `explorer_remediation_r9_m1` (teamwork_explorer)  
**Roles**: investigation, synthesis  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_remediation_r9_m1`  
**Parent Conversation ID**: `8849ddae-0421-48b2-aa8f-6d2c7b15dafe`  
**Timestamp**: 2026-11-05T15:03:30Z  
**Verdict**: **COMPLETE** (Surgical Remediation Plan Delivered)

---

## 1. Observation (观测事实与物证链)

### 1.1 `multi_ledger_manager.py` 存储与安全缺陷观测
1. **大小写与空格规避主实盘保护漏洞**：
   - 文件与行号：`AGY2_FundAdvisory/multi_ledger_manager.py:324-326`
     ```python
     if ledger_id == "main_live":
         raise PermissionError("主实盘账本受物理保护，禁止删除！")
     ```
   - 报错实证：运行 `py -3 -m pytest tests/test_multi_ledger_manager_stress.py -k "test_protection_attack_case_and_whitespace_variants"`
     `Failed: DID NOT RAISE PermissionError`。当传入 `"MAIN_LIVE"`、`"Main_Live"`、`"main_live "` 时，全等比对失效，返回 `False` 而未抛出 `PermissionError`。
2. **路径遍历与别名误删主实盘物理漏洞**：
   - 文件与行号：`AGY2_FundAdvisory/multi_ledger_manager.py:337-350`
     ```python
     f_path = self.root / target.get("file", "")
     db_path = self.root / target.get("db_file", "")
     if f_path.exists() and f_path != self.main_file:
         f_path.unlink()
     ```
   - 报错实证：运行 `py -3 -m pytest tests/test_multi_ledger_manager_stress.py -k "test_protection_attack_path_traversal_and_file_alias"`
     `AssertionError: CRITICAL BUG: 主实盘 portfolio_ledger.json 被路径遍历漏洞误删！ assert False where False = exists()`。
     当索引包含 `file: "data/../portfolio_ledger.json"` 时，`Path` 对象未调用 `.resolve()`，`f_path != self.main_file` 判定为 `True`，直接触发 `unlink()` 误删了生产环境主实盘。
3. **`get_pm` 静默回退主实盘引发污染隐患**：
   - 文件与行号：`AGY2_FundAdvisory/multi_ledger_manager.py:371-376`
     ```python
     meta = self.get_ledger_meta(ledger_id)
     if not meta:
         ledger_id = "main_live"
         meta = self._get_default_main_meta()
     ```
   - 事实：当传入不存在或已删除账本 ID 时，函数静默返回生产环境 `main_live` 的 `PortfolioManager`，若调用方随后执行清空或加仓，将直接污染主实盘。

### 1.2 `app_gui.py` GUI 状态机与控件脱节缺陷观测
1. **切账本小部件键脱节与逆反回弹缺陷**：
   - 文件与行号：`AGY2_FundAdvisory/app_gui.py:1390-1412` 与 `3427-3436`
     ```python
     # switch_active_ledger
     st.session_state.active_ledger_id = target_ledger_id
     # 遗漏了 st.session_state.sel_tab2_active_ledger = target_ledger_id
     ...
     # Tab 2 selectbox
     selected_lid = st.selectbox(..., key="sel_tab2_active_ledger", index=active_idx)
     if selected_lid != active_lid:
         switch_active_ledger(selected_lid)
     ```
   - 事实实证：`tests/test_gui_multi_ledger_stress.py:511-521` 证实，在 Tab 1 另存为新账本或 Tab 2 Popover 中调用 `switch_active_ledger(new_id)` 后，Streamlit 在 rerun 时优先读取小部件绑定的旧值 `"main_live"`，立即触发 `if selected_lid != active_lid` 强行逆向切回 `"main_live"`。
2. **Tab 1 滑块单向冲刷洗白账本专属风险档位缺陷**：
   - 文件与行号：`AGY2_FundAdvisory/app_gui.py:1403-1405` 与 `2315-2317`
     ```python
     # switch_active_ledger 仅设置了：
     st.session_state.active_tier_val = meta.get("default_tier", "C3")
     # 遗漏了 slider_target_return 和 target_return_val
     ...
     # Tab 1 步骤一渲染：
     target_ret_input = st.slider(..., key="slider_target_return") # 仍为默认 15.0%
     st.session_state.target_return_val = target_ret_input
     active_tier = map_slider_to_tier(target_ret_input) # map_slider_to_tier(15.0) -> "C3"
     st.session_state.active_tier_val = active_tier      # 强行将 C1/C2/C4/C5 冲刷回 C3
     ```
   - 事实实证：`tests/test_gui_multi_ledger_stress.py:527-538` 证实即使人工绕过回弹，C5 账本在渲染 Tab 1 后也会被无条件洗成 C3。
   - 且实机验证测算：`strategy_bridge.map_target_return_to_tier(10.0)` 返回 `"C3"` 而非 `"C2"`。若直接读取 `RISK_TIERS_CONFIG["C2"]["default_target"]`（10.0），会导致 C2 账本在滑块处依然被洗成 C3；必须采用专用的 `TIER_TARGET_RETURN_MAP = {"C1": 6.5, "C2": 9.0, "C3": 15.0, "C4": 22.0, "C5": 50.0}`。
3. **Tab 2 下拉框非法控件键导致全站白屏崩溃缺陷**：
   - 文件与行号：`AGY2_FundAdvisory/app_gui.py:3427-3435`
   - 报错实证：`tests/test_gui_multi_ledger_stress.py:569-590` 证实，当 `st.session_state["sel_tab2_active_ledger"]` 残存已被删除或损坏的非法账本 ID 时，Streamlit 渲染 `selectbox` 因该值不在 options 中抛出未捕获的 `ValueError: '... is not in list'`，直接导致界面白屏崩溃。

---

## 2. Logic Chain (推演逻辑链)

1. **针对 Observation 1.1 (存储与删除安全)**：
   - **推导 1 (P1)**：字符串比较大小写敏感。为守死“主实盘物理禁止删除”的铁律，在 `delete_ledger` 入口必须统一做 `str(ledger_id).strip().lower() == "main_live"` 归一化校验，一旦匹配立即抛出 `PermissionError`，物理阻断一切变体绕过。
   - **推导 2 (P2)**：操作系统的相对路径可能包含 `..` 等别名。`Path("a/b/../c") == Path("a/c")` 结果为 `False`。只有通过 `.resolve()` 解析出文件在操作系统的真实物理绝对路径后比对（`f_path.resolve() != self.main_file.resolve()`），才能从数学机制上杜绝别名绕过，守死主实盘物理文件。
   - **推导 3 (P3)**：`get_pm` 作为工厂方法，若对不存在的账本 ID 静默返回主实盘，破坏了“沙盒隔离”语义。应遵循“失败显式暴露”原则，对非 `main_live` 且不存在的 ID 抛出 `KeyError(f"账本未找到: {ledger_id}")`。

2. **针对 Observation 1.2 (GUI 状态机与控件联动)**：
   - **推导 4 (P4)**：Streamlit 内部采用键控状态机管理组件值。凡具有 `key` 的组件，`session_state[key]` 的优先级高于代码中的 `index` 参数。因此外部调用 `switch_active_ledger(target_id)` 必须同步强写 `st.session_state.sel_tab2_active_ledger = target_id`，杜绝组件读取旧值导致的二次回弹。
   - **推导 5 (P5)**：Tab 1 在 Streamlit 执行流中先于 Tab 2 渲染，其收益率滑块单向绑定了 `active_tier_val = map_slider_to_tier(target_ret_input)`。若只更新 `active_tier_val` 而不更新滑块，滑块内部的默认值会逆向冲刷覆盖目标档位。通过定义自洽映射表 `TIER_TARGET_RETURN_MAP`（特别是为 C2 配置 9.0% 收益率，严格避开 10.0% 的 C3 分界点），在切换账本时联动写入 `slider_target_return` 与 `target_return_val`，实现双向映射 100% 闭环。
   - **推导 6 (P6)**：由于用户可在管理弹窗中随时删除沙盒账本，已删除的 ID 可能仍驻留在 `st.session_state.sel_tab2_active_ledger` 中。在调用 `st.selectbox` 前增加防御性清洗：若该键不在可用账本列表 `avail_lids` 中，立即重置为 `"main_live"`，同时在主入口 `get_pm(_cur_lid)` 处捕获 `KeyError` 自动回退至 `"main_live"`，实现“全站零白屏崩溃”的高可用承诺。

---

## 3. Caveats (注意事项与假设)

1. **测试用例对齐假设**：
   - 现有的 `tests/test_multi_ledger_manager_stress.py` 与 `tests/test_gui_multi_ledger_stress.py` 中有部分用例（如用 `raises(ValueError)` 或断言 `reverted = True`）是为了在 Iteration 1 实证暴露缺陷而编写的。
   - Worker 在应用加固补丁后，应将这些测试更新为对加固后期望行为的断言（例如断言 `active_ledger_id == sb_id`、断言 `sel_tab2_active_ledger == "main_live"`），详见 `remediation_plan.md` 第 4 节。
2. **只读裁判文件红线绝对不变**：
   - 4 大裁判基线文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）以及 `DataLoader.simulate_execution` 绝不在本次整改范围内，必须保持 100% 只读。

---

## 4. Conclusion (交付结论)

已成功编制并输出完整、精准、行级对齐的整改方案文档：
- **方案路径**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_remediation_r9_m1\remediation_plan.md`
- **核心整改点交付清单**:
  1. `multi_ledger_manager.py:324`: `str(ledger_id).strip().lower() == "main_live"` 统一抛出 `PermissionError`。
  2. `multi_ledger_manager.py:337-350`: 使用 `.resolve()` 强比对物理路径，根除路径遍历误删实盘漏洞。
  3. `multi_ledger_manager.py:371-376`: `get_pm` 对不存在账本显式抛出 `KeyError(f"账本未找到: {ledger_id}")`。
  4. `app_gui.py:1390-1412`: `switch_active_ledger` 显式同步 `sel_tab2_active_ledger`，消灭逆反回弹 Bug。
  5. `app_gui.py:1403-1405`: 联动同步 `slider_target_return` 与 `target_return_val`（采用严格自洽的 `TIER_TARGET_RETURN_MAP`，C2 锁死 9.0%），消灭 Tab 1 档位冲刷 Bug。
  6. `app_gui.py:3410-3435`: Tab 2 selectbox 渲染前对 `sel_tab2_active_ledger` 进行防御性校验与自愈重置，消灭 `ValueError` 白屏崩溃。

---

## 5. Verification Method (独立核验方法)

下游 Remediation Worker 实施代码修改后，依次运行以下独立测试进行全量闭环验证：

```powershell
# 1. 验证 MultiLedgerManager 对抗压力测试（预期 8 passed in ~15s）
py -3 -m pytest tests/test_multi_ledger_manager_stress.py -v

# 2. 验证 GUI 对抗压力测试（预期 8 passed in ~25s）
py -3 -m pytest tests/test_gui_multi_ledger_stress.py -v

# 3. 运行基础多账本功能测试
py -3 -m pytest tests/test_multi_ledger_manager.py -v

# 4. 运行全量核心回归与防作弊测试套件（预期 31 passed in ~25s）
py -3 -m pytest tests/test_infra.py tests/test_portfolio.py tests/test_multi_ledger_manager.py tests/test_streamlit_apptest_run.py tests/test_anticheat_suite.py::TestMultiLedgerIsolationAndProtection -v

# 5. 校验 4 大裁判文件哈希 100% 完好无损
py -3 -c "import hashlib; [print(p, hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]) for p in ['AGY2_FundAdvisory/judge_engine.py', 'AGY2_FundAdvisory/holdout_vault.py', 'AGY2_FundAdvisory/AGENT_SPEC.md', 'tests/test_infra.py']]"
```
