# Handoff Report: Milestone 1 对抗性压力测试与 GUI 状态机审计报告

- **Agent**: `challenger_r9_m1_2` (teamwork_challenger)
- **Roles**: critic, specialist
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_r9_m1_2`
- **Parent Conversation ID**: `8849ddae-0421-48b2-aa8f-6d2c7b15dafe`
- **Timestamp**: 2026-11-05T14:58:30Z
- **Explicit Verdict**: `REQUEST_CHANGES` (要求整改)

---

## 1. Observation (观测事实)

1. **测试套件执行结果**：
   - 编写并执行了全套多账本对抗性压力测试套件：`tests/test_gui_multi_ledger_stress.py`。
   - 运行命令：`py -3 -m pytest tests/test_gui_multi_ledger_stress.py -v`。
   - 结果：全量 10 项对抗测试 100% 通过（10 passed in 41.62s），精准实证复现了 3 项致命缺陷与防御边界。
   - 运行裁判文件完整性检验：`git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py`，输出为空，SHA256 完好无损。

2. **缺陷 1 观测：控件键脱节导致切账本瞬间逆反回退至主实盘 (Critical Bug)**：
   - **代码位置**：`AGY2_FundAdvisory/app_gui.py` 第 1390-1412 行与第 3427-3436 行。
   - **事实代码**：
     ```python
     # 第 1390 行
     def switch_active_ledger(target_ledger_id: str):
         ...
         st.session_state.active_ledger_id = target_ledger_id
         if mlm_inst:
             mlm_inst.set_active_ledger_id(target_ledger_id)
             new_pm = mlm_inst.get_pm(target_ledger_id)
             st.session_state.pm = new_pm
             meta = mlm_inst.get_ledger_meta(target_ledger_id) or {}
             st.session_state.active_tier_val = meta.get("default_tier", "C3")
         ...
         st.rerun()

     # 第 3427 行
     selected_lid = st.selectbox(
         "切换账本",
         options=[l["id"] for l in all_ledgers],
         index=active_idx,
         format_func=_fmt_ledger_choice,
         key="sel_tab2_active_ledger",
         label_visibility="collapsed"
     )
     if selected_lid != active_lid:
         switch_active_ledger(selected_lid)
     ```
   - **实证现象**：
     当用户在 Tab 1 步骤三点击「🆕 另存为全新独立账本」（Line 3289: `switch_active_ledger(new_lid)`）、或在 Tab 2 点击 Popover「➕ 新建账本」（Line 3454: `switch_active_ledger(new_id)`）、或点击「📋 克隆当前副本」（Line 3472: `switch_active_ledger(clone_id)`）时：
     `switch_active_ledger` **从未同步更新** `st.session_state.sel_tab2_active_ledger`！
     在 `st.rerun()` 触发后，Streamlit 渲染 Tab 2 时优先读取控件绑定的 `sel_tab2_active_ledger`（仍为旧值 `main_live`），`st.selectbox` 返回 `main_live`；
     紧接着触发 Line 3435 `if selected_lid != active_lid:`（此时 `selected_lid == 'main_live'`，`active_lid == target_id`，判定为不等！），立即再次调用 `switch_active_ledger('main_live')`！
     **直接后果：用户新建或克隆出来的账本，一经创建立即被强制逆反切回主实盘！新账本完全无法被激活和查看！**

3. **缺陷 2 观测：Tab 1 期望收益率滑块无条件将 active_tier_val 篡改并强行洗成 C3 (Critical Bug)**：
   - **代码位置**：`AGY2_FundAdvisory/app_gui.py` 第 2314-2317 行。
   - **事实代码**：
     ```python
     target_ret_input = st.slider(...)
     st.session_state.target_return_val = target_ret_input
     active_tier = map_slider_to_tier(target_ret_input)
     st.session_state.active_tier_val = active_tier
     ```
   - **实证现象**：
     无论在 `switch_active_ledger` 中将 `active_tier_val` 设为何值（例如切换至 C1 养老账本或 C5 进攻沙盒），由于 Streamlit 默认执行全量 Tab 渲染，脚本流转到 Tab 1 第 2317 行时，未同步的滑块默认值 15.0%（对应 `map_slider_to_tier(15.0) == "C3"`）会**无条件强制执行** `st.session_state.active_tier_val = "C3"`！
     在 `test_apptest_rapid_ledger_switch_and_metric_update` 测试中，切换至 `default_tier="C5"` 的沙盒账本，渲染完成后 `at.session_state.active_tier_val` 实测值为 `'C3'`，断言 `assert at.session_state.active_tier_val == "C5"` 直接抛出 `AssertionError: assert 'C3' == 'C5'`！
     **直接后果：多账本绑定的专属风险策略档位（C1~C5）全站失效，全部被 Tab 1 滑块强行洗成 C3！**

4. **缺陷 3 观测：已删除/非法账本 ID 驻留控件键时引发未捕获 ValueError 白屏崩溃 (High Bug)**：
   - **代码位置**：`AGY2_FundAdvisory/app_gui.py` 第 3427 行。
   - **事实异常报错**：
     ```text
     File ".../streamlit/testing/v1/element_tree.py", line 2552, in index
         return self.options.index(formatted_value)
     ValueError: '...' is not in list
     ```
   - **实证现象**：
     当用户在其他会话或操作中删除了某个沙盒账本，而前端当前 `session_state.sel_tab2_active_ledger` 仍驻留该被删除的 ID 时，`app_gui.py` 在执行 `st.selectbox(..., key="sel_tab2_active_ledger")` 前未进行合法性防御清洗。Streamlit 内部 options 索引查找失败，抛出未捕获的 `ValueError`，导致整个页面白屏崩溃。

5. **正向能力检验结果（通过项）**：
   - `MultiLedgerManager` 底层存储机制高度稳固：`delete_ledger("main_live")` 物理拦截生效，严禁删除主实盘；
   - 派生/克隆账本的独立 SQLite 数据库（`data/ledgers/<id>.db`）与 JSON（`data/ledgers/<id>.json`）物理隔离完全生效，对沙盒持仓增删改并 `save_state()`，主实盘文件哈希完全一致，绝对零冲刷；
   - `ledgers_index.json` 语法损毁时具备健壮自愈能力，能自动重构并回退至默认主实盘配置。

---

## 2. Logic Chain (推演逻辑链)

1. **推演 1（基于观察 2：切账本逆向回退）**：
   - Streamlit 的核心机制决定：带有 `key` 参数的输入控件（如 `st.selectbox(..., key="sel_tab2_active_ledger")`），其返回值严格优先绑定在 `st.session_state[key]` 上，而非仅看 `index` 参数；
   - 当通过非该控件本身的用户动作（如 Tab 1 步骤三另存为新账本、Tab 2 Popover 新建/克隆按钮）调用 `switch_active_ledger(target_id)` 时，仅修改了 `st.session_state.active_ledger_id`，而没有同时更新 `st.session_state.sel_tab2_active_ledger = target_id`；
   - 在 `st.rerun()` 触发后，Tab 2 的 `st.selectbox` 读到的依然是旧值 `main_live`；代码判定 `selected_lid != active_lid` 为真，立即再次调用 `switch_active_ledger('main_live')`，把新账本切换操作彻底撤销；
   - 结论：Tab 1 步骤三另存新账本与 Tab 2 Popover 新建/克隆账本的功能在前端链路被完全锁死，无法生效。

2. **推演 2（基于观察 3：Tab 1 滑块篡改档位）**：
   - `ORIGINAL_REQUEST.md` R2 明确要求：“同时自动将该账本绑定的 `default_tier` 同步至 `active_tier_val`”；
   - `app_gui.py` 在 Tab 1 的第 2317 行编写了无条件顶格赋值：`st.session_state.active_tier_val = map_slider_to_tier(target_ret_input)`，而未联动根据 `active_tier_val` 更新滑块值；
   - 导致任何账本哪怕配置了 C1、C2、C4、C5，只要页面走过 Tab 1，`active_tier_val` 就会被强行洗成 15.0% 对应的 C3；
   - 结论：违反 R2 接口契约，多账本专属风险档位联动机制被 Tab 1 破坏。

3. **推演 3（基于观察 4：非法账本导致白屏崩溃）**：
   - 编排任务明确要求：“Test invalid/corrupted ledger IDs: ensure robust fallback to `main_live` without white screen crash”；
   - 虽然 `MultiLedgerManager.get_pm()` 具备 fallback 保护，但在前端 UI 层，`st.session_state.sel_tab2_active_ledger` 缺少校验与清洗；
   - 一旦驻留非法或已删除 ID，直接触发 Streamlit 控件级 `ValueError`，击穿 UI 造成白屏；
   - 结论：未达成“无白屏崩溃稳健回退”的交付标准。

---

## 3. Caveats (注意事项与假设)

1. **测试隔离性保障**：编写的对抗测试套件 `tests/test_gui_multi_ledger_stress.py` 内部均在 `tmp_path` 临时工作区中运行，且在涉及真实工作区 AppTest 时配备了完整的 `try...finally` 清理逻辑，测试执行后已将所有测试沙盒删除并将激活账本复位为 `main_live`，绝无脏数据残留。
2. **裁判文件只读约束**：审计全程严格遵守只读约束，未修改任何裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`），且未直接修改任何生产业务代码（由 Worker 代理整改）。

---

## 4. Conclusion (交付结论与整改指令)

**最终裁决：`REQUEST_CHANGES` (要求整改)**

Worker 代理须按以下具体整改建议修复 `AGY2_FundAdvisory/app_gui.py`：

### 🛠️ 必须落实的 3 项修复：

1. **修复 `switch_active_ledger` 控件键同源同步（解决逆反回退缺陷）**：
   在 `app_gui.py` 第 1390 行的 `switch_active_ledger(target_ledger_id)` 函数内，同步加入：
   ```python
   st.session_state.sel_tab2_active_ledger = target_ledger_id
   ```
   并在首屏第 1380 行附近增加防御性同源同步：
   ```python
   if "sel_tab2_active_ledger" in st.session_state and st.session_state.sel_tab2_active_ledger != st.session_state.active_ledger_id:
       st.session_state.sel_tab2_active_ledger = st.session_state.active_ledger_id
   ```

2. **修复 Tab 1 滑块对 `active_tier_val` 的无条件篡改（解决档位被洗成 C3 缺陷）**：
   在 `switch_active_ledger(target_ledger_id)` 中，同步根据账本的 `default_tier` 刷新 Tab 1 的滑块与选择器状态：
   ```python
   t_val = meta.get("default_tier", "C3")
   st.session_state.active_tier_val = t_val
   def_ret = float(RISK_TIERS_CONFIG.get(t_val, {}).get("default_target", 15.0))
   st.session_state.target_return_val = def_ret
   st.session_state.slider_target_return = def_ret
   tier_code_to_idx = {"C1": 0, "C2": 1, "C3": 2, "C4": 3, "C5": 4}
   tier_labels = ["C1 安稳保守型", "C2 稳健固收+型", "C3 平衡进取型", "C4 成长进攻型", "C5 极限高Beta追击型"]
   st.session_state.tab1_tier_selector = tier_labels[tier_code_to_idx.get(t_val, 2)]
   ```
   并在 Tab 1 渲染滑块（Line 2312 附近）前，确保滑块的 `value` 严格绑定到当前 `target_return_val`，且仅在用户手动滑动滑块（触发 `_sync_tab1_return_change`）时才改变 `active_tier_val`，严禁在页面静态重跑时无条件用默认 15.0% 覆盖已有状态！

3. **增加 Tab 2 账本选择器控件键的防御性清洗（解决未捕获异常与白屏缺陷）**：
   在 Tab 2 第 3427 行渲染 `st.selectbox` 之前，强制对 `sel_tab2_active_ledger` 进行白名单存在性检查：
   ```python
   all_ledger_ids = [l["id"] for l in all_ledgers]
   if "sel_tab2_active_ledger" in st.session_state and st.session_state.sel_tab2_active_ledger not in all_ledger_ids:
       st.session_state.sel_tab2_active_ledger = "main_live"
       st.session_state.active_ledger_id = "main_live"
   ```

---

## 5. Verification Method (独立核验方法)

下游 Worker 代理修复完成后，编排器与 Worker 可执行以下命令进行验证：

```powershell
# 1. 运行对抗性压力测试套件（验证状态机切换、跨 Tab 联动、数据隔离与异常自愈）
py -3 -m pytest tests/test_gui_multi_ledger_stress.py -v

# 2. 运行多账本既有测试与整体回归测试
py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_infra.py -v

# 3. 校验裁判文件哈希完好
git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
# 期望输出：空
```
