# Review & Adversarial Critic Report: Milestone 1 GUI & Integration Review

**Agent**: `reviewer_r9_m1_2` (teamwork_reviewer)  
**Roles**: reviewer, critic  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_r9_m1_2`  
**Parent Conversation ID**: `8849ddae-0421-48b2-aa8f-6d2c7b15dafe`  
**Timestamp**: 2026-11-05T14:55:00Z  
**Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation (观测事实)

1. **测试套件独立核验事实**：
   - 执行命令：`py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_streamlit_apptest_run.py -v`
   - 结果：全量 9 项测试通过（`9 passed in 14.36s`）。
   - 执行底座回归命令：`py -3 -m pytest tests/test_infra.py tests/test_portfolio.py -v`
   - 结果：全量 20 项测试通过（`20 passed in 8.32s`）。
   - 执行防作弊测试 C 命令：`py -3 -m pytest tests/test_anticheat_suite.py::TestMultiLedgerIsolationAndProtection -v`
   - 结果：2 项测试全部通过（`2 passed in 1.18s`）。
   - 校验只读裁判文件：`git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py` 输出完全为空，哈希 100% 完好无损。

2. **代码实现审查事实 (`AGY2_FundAdvisory/app_gui.py`)**：
   - **`st.session_state.active_ledger_id` 初始化与 `pm` 绑定**（第 1374-1388 行）：
     ```python
     if "mlm" not in st.session_state:
         st.session_state.mlm = MultiLedgerManager.get_instance() if MultiLedgerManager else None
     if "active_ledger_id" not in st.session_state:
         st.session_state.active_ledger_id = st.session_state.mlm.get_active_ledger_id() if st.session_state.mlm else "main_live"

     _cur_lid = st.session_state.active_ledger_id
     if "pm" not in st.session_state or getattr(st.session_state.pm, "ledger_id", None) != _cur_lid:
         if st.session_state.mlm:
             st.session_state.pm = st.session_state.mlm.get_pm(_cur_lid)
         else:
             st.session_state.pm = PortfolioManager()

     pm: PortfolioManager = st.session_state.pm
     ```
     初始化绑定严密，`pm` 准确指向当前激活账本。
   - **Tab 2 单行吧台与 3 个 Popover**（第 3425-3520 行）：
     采用 `col_led_sel, col_led_new, col_led_clone, col_led_mgr = st.columns([4.2, 1.8, 1.8, 2.2])` 单行布局，包含【切换账本下拉框】、【➕ 新建账本 Popover】、【📋 克隆当前副本 Popover】、【⚙️ 账本管理 Popover（含重命名、防删除保护与全家庭资产汇总明细表）】。
     当前为沙盒时渲染黄色醒目提示条（`🧪 当前为独立沙盒环境，任何调仓与录基演练均隔离存储，绝不影响主实盘`）。
   - **Tab 1 步骤三双轨保存**（第 3243-3293 行）：
     `col_btn_save_cur, col_btn_save_new, col_btn_to_bt = st.columns([3.6, 3.6, 2.8])`，左侧为「📥 覆盖写入当前激活账本」，中间为「🆕 另存为全新独立账本」Popover（支持新账本名称、类型与风险档位选择），写入后调用 `switch_active_ledger(new_lid)`。

3. **对抗性压力测试中发现的 2 项缺陷**：
   - **观测 3.1（切账本状态回弹）**：
     在 `switch_active_ledger`（第 1390-1412 行）中：
     ```python
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
     ```
     `switch_active_ledger` **没有**同步更新 `st.session_state["sel_tab2_active_ledger"] = target_ledger_id`。
     在 Tab 2 第 3427-3436 行：
     ```python
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
     当在 Tab 1（另存为新账本）或 Tab 2 Popover（新建账本、克隆副本）中调用 `switch_active_ledger(new_id)` 切换激活账本时，因为 `sel_tab2_active_ledger` 小部件未同步，Streamlit 在 rerun 执行到第 3427 行时，自动使用缓存的旧小部件状态（如 `"main_live"`），导致 `selected_lid == "main_live"`，而 `active_lid == new_id`；第 3435 行 `if selected_lid != active_lid:` 条件成立，**立即自动触发二次切换回 `"main_live"`**！导致用户在 Tab 1 或 Tab 2 弹窗中创建/克隆的新账本瞬间被回弹回主实盘。
   - **观测 3.2（风险档位覆盖冲刷）**：
     在 `switch_active_ledger` 中设置了 `st.session_state.active_tier_val = meta.get("default_tier", "C3")`（例如设置为 `C4`）。
     但 `switch_active_ledger` **没有**同步 `st.session_state.target_return_val` 和 `st.session_state.slider_target_return`。
     在页面 rerun 时，执行到 Tab 1 第 2315-2317 行：
     ```python
     target_ret_input = st.slider("期望年化目标收益率 (%)", ..., key="slider_target_return", ...)
     st.session_state.target_return_val = target_ret_input
     active_tier = map_slider_to_tier(target_ret_input)
     st.session_state.active_tier_val = active_tier
     ```
     由于滑块 `slider_target_return` 仍保持着默认的 `15.0%`，而 `map_slider_to_tier(15.0)` 返回 `"C3"`，在每次页面刷新时，第 2317 行都会**无条件将 `st.session_state.active_tier_val` 强行覆盖回 `"C3"`**！导致非 C3 账本的 `default_tier`（如 C1/C2/C4/C5）在渲染到达 Tab 2 前即被冲刷失效。

---

## 2. Logic Chain (推演逻辑链)

1. **基于观测 1 与 2（基础实现与隔离完备性）**：
   - `MultiLedgerManager` 底层 CRUD、独立 SQLite 派生隔离、主实盘物理防删除等能力经过了 `test_multi_ledger_manager.py` 和 `test_anticheat_suite.py` 的充分验证，存储层无任何假代码或投机取巧。
   - 4 大裁判基线哈希无损，基础回归完全通过。
2. **基于观测 3.1（Streamlit 小部件状态机与会话脱节推演）**：
   - Streamlit 的组件如果绑定了 `key`，则其组件内部的值会优先从 `session_state[key]` 中读取，忽略 `index` 参数。
   - 当外部逻辑（如 Tab 1 步骤三另存为新账本、Tab 2 弹窗一键克隆/新建）调用 `switch_active_ledger(new_id)` 时，仅修改了 `st.session_state.active_ledger_id = new_id`，但遗漏了小部件同名键 `st.session_state.sel_tab2_active_ledger`。
   - 页面 `st.rerun()` 重新进入 Tab 2 时，`selectbox` 读取旧值 `"main_live"`，触发 `if selected_lid != active_lid`，导致致命的二次回跳回退（Bounce-Back Bug）。
3. **基于观测 3.2（全局滑块单向冲刷推演）**：
   - Tab 1 在 Python 执行流中排在 Tab 2 之前。
   - Tab 1 中第 2315-2317 行存在硬性单向同步：从 `slider_target_return` -> 计算 `map_slider_to_tier` -> 写入 `active_tier_val`。
   - 若 `switch_active_ledger` 未同时更新 `slider_target_return`，滑块的默认值 15.0% 会无条件逆向覆盖 `active_tier_val`，破坏了 R2 明确要求的“自动将该账本绑定的 default_tier 同步至 active_tier_val”。
4. **结论推导**：
   - 上述两项问题属于典型的前端会话状态不同步导致的交互阻断与功能回归，必须在交付前完成整改。

---

## 3. Caveats (注意事项与假设)

1. 本审查完全基于真实运行时 AppTest 探针与 Streamlit 会话状态机追踪，未使用任何 Mock 糊弄。
2. 基础存储层与数据安全隔离已经具备极高品质，问题仅局限于 `app_gui.py` 内部 `switch_active_ledger` 状态同步闭环。

---

## 4. Conclusion (交付结论与整改指令)

**审定结论**：**`REQUEST_CHANGES`**

### 待整改缺陷清单 (Actionable Findings)：

#### [Major] Finding 1: `switch_active_ledger` 必须同步更新小部件状态 `st.session_state.sel_tab2_active_ledger`
- **文件与行号**：`AGY2_FundAdvisory/app_gui.py:1390-1412`
- **问题说明**：在 `switch_active_ledger` 中缺少对 Tab 2 下拉框 `key="sel_tab2_active_ledger"` 的显式赋值，导致非下拉框直接切换（如 Tab 1 另存为新账本、Popover 新建/克隆）在下一次渲染时被下拉框强制回退回原账本。
- **整改建议**：在 `switch_active_ledger(target_ledger_id: str)` 内部增加：
  ```python
  st.session_state.sel_tab2_active_ledger = target_ledger_id
  ```

#### [Major] Finding 2: `switch_active_ledger` 必须同步更新收益率滑块，防止 Tab 1 将 `default_tier` 覆盖冲刷回 `C3`
- **文件与行号**：`AGY2_FundAdvisory/app_gui.py:1403-1405`
- **问题说明**：切换账本时虽然设置了 `active_tier_val = meta.get("default_tier")`，但由于没有更新 `slider_target_return` 和 `target_return_val`，在 rerun 执行 Tab 1 第 2317 行时，滑块会将 `active_tier_val` 强行重置回 `C3`。
- **整改建议**：在 `switch_active_ledger` 内部增加对期望收益率及滑块的联动更新：
  ```python
  def_tier = meta.get("default_tier", "C3")
  st.session_state.active_tier_val = def_tier
  def_ret = float(RISK_TIERS_CONFIG.get(def_tier, {}).get("default_target", 15.0))
  st.session_state.target_return_val = def_ret
  st.session_state.slider_target_return = def_ret
  ```

---

## 5. Verification Method (独立核验方法)

整改完成后，执行以下 AppTest 自动化交互脚本进行验证：

```powershell
py -3 -c "from streamlit.testing.v1 import AppTest
from pathlib import Path
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager

mlm = MultiLedgerManager.get_instance()
sandbox_id = mlm.create_ledger('验证修复沙盒', base_cash=60000.0, ledger_type='sandbox', default_tier='C4')

app_path = Path('AGY2_FundAdvisory/app_gui.py')
at = AppTest.from_file(str(app_path), default_timeout=30)
at.run()

sb = [s for s in at.selectbox if s.key == 'sel_tab2_active_ledger'][0]
sb.select(sandbox_id).run()

assert not at.exception
assert at.session_state.active_ledger_id == sandbox_id
assert getattr(at.session_state.pm, 'ledger_id', '') == sandbox_id
assert at.session_state.active_tier_val == 'C4'

# 清理
mlm.delete_ledger(sandbox_id)
print('✅ 验证全部通过！')
"
```
验证标准：断言 100% 通过且无任何 `AssertionError`。
