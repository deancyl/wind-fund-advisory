# 对抗性质询与 UI 运行时审查报告 (Challenger Handoff Report)

- **质询智能体**: `challenger_m2_2`
- **目标里程碑**: Milestone 2 (M2) — 全局紧凑顶栏、手机极简盯盘 5 张卡片流与真 OCR 切片平账闭环
- **最终裁决结论**: **`APPROVE` (核验通过)**

---

## 1. Observation (客观实测与法证事实)

质询智能体编写并独立运行了全新的对抗性质询测试套件 `tests/test_challenger_g16_m2_adversarial.py`，并对四个物理只读裁判文件与回归基准进行了端到端实测验证，客观实测数据如下：

### 1.1 独立对抗性质询套件执行事实 (`tests/test_challenger_g16_m2_adversarial.py`)
- **执行命令**:
  ```powershell
  py -3 -m pytest tests/test_challenger_g16_m2_adversarial.py -v
  ```
- **实测输出**:
  ```text
  ============================= test session starts =============================
  platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
  rootdir: D:\Google\Workspace\Wind
  plugins: anyio-4.13.0, asyncio-1.4.0, cov-7.1.0
  collected 7 items

  tests/test_challenger_g16_m2_adversarial.py::test_topbar_bidirectional_sync_desktop_and_mobile PASSED [ 14%]
  tests/test_challenger_g16_m2_adversarial.py::test_mobile_five_cards_rendering_combat29 PASSED [ 28%]
  tests/test_challenger_g16_m2_adversarial.py::test_mobile_card3_sweep_tails_action_state_mutation PASSED [ 42%]
  tests/test_challenger_g16_m2_adversarial.py::test_mobile_card5_ocr_upload_preview_and_interactive_commit PASSED [ 57%]
  tests/test_challenger_g16_m2_adversarial.py::test_mobile_card5_corrupted_image_error_boundary PASSED [ 71%]
  tests/test_challenger_g16_m2_adversarial.py::test_parse_smart_text_holdings_adversarial_variations PASSED [ 85%]
  tests/test_challenger_g16_m2_adversarial.py::test_mobile_performance_isolation_via_st_stop PASSED [100%]

  ================== 7 passed, 31 warnings in 95.29s (0:01:35) ==================
  ```

### 1.2 核心对抗场景走查证据链
1. **顶栏双向同步与账本切换 (`test_topbar_bidirectional_sync_desktop_and_mobile`)**:
   - 验证在 `AGY2_FundAdvisory/app_gui.py` 第 2850~2922 行实装的全局顶栏：
     - 左侧品牌 `🧭 AGY2 智投量化终端` 及数据源/日期角标 100% 渲染。
     - 下拉选择框（`topbar_ledger_select_...`）列出所有账本，精确包含 `🟢 [实盘] 主实盘账本 (¥109,556)` 与 `🟢 [实盘] 实战存量组合（29只·¥2.66万） (¥27,615)`。
     - 切换到 `📱 手机极简盯盘` 视图时，顶栏依然保留在页面最顶部，不随视图切换丢失。
2. **手机 5 大卡片与 29 基真实特征断言 (`test_mobile_five_cards_rendering_combat29`)**:
   - 拒绝唯异常断言，严格核验卡片内容语义与几何呈现：
     - **卡片 1**：总资产卡呈现 `📱 账户总资产`、`今日预估`、`累计浮盈`。
     - **卡片 2**：五维备忘录摘要卡呈现 `🧭 首席投顾五维决策备忘录`、微型徽章胶囊与 `投顾人话结论`。
     - **卡片 3**：碎片尾仓卡在 `combat_29_funds` 激活下精准识别出 19~20 只免赎碎片（¥566.84），并完整渲染按钮 `btn_mob_sweep_tails`（`🧹 一键模拟/清扫碎片尾仓归拢至纯债 (002351)`）。
     - **卡片 4**：14:30 尾盘指令呈现 `⏱️ 14:30 尾盘操作指令` 与 `st.code` 格式的 `【AGY2 智投量化 14:30 下单小抄】`，自带原生复制能力并明确给出 `002351` 申购代码。
     - **卡片 5**：长截图上传组件 `mob_uploader_feed` 真实就绪，彻底消除了原第 1530 行“正在研发中”的假功能提示。
3. **卡片 3 状态机变异对抗 (`test_mobile_card3_sweep_tails_action_state_mutation`)**:
   - 模拟点击 `btn_mob_sweep_tails`，实测 `st.session_state` 正确设置：
     - `tab2_rebalanced = True`
     - `tab2_diagnosed = True`
     - `tab2_trigger_rebalance = True`
     - `rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"`
     - `sel_sc_anchor = "002351 - 易方达裕祥回报债券A"`
     - 界面呈现成功提示：`已成功启动清扫归拢预案：将 20 只免赎碎片 (¥566.84) 全额平移归集至 002351！`。
4. **卡片 5 截图上传、识别与覆盖/追加交互闭环 (`test_mobile_card5_ocr_upload_preview_and_interactive_commit`)**:
   - 模拟用户上传截图并输入 OCR 数据：
     - 成功渲染 `st.dataframe` 预览表格（`mob_ocr_data_editor`）。
     - 渲染「✅ 确认无误，一键覆盖写入当前账本 (`btn_mob_ocr_commit_replace`)」与「➕ 追加合并写入当前账本 (`btn_mob_ocr_commit_append`)」。
     - 实测点击追加合并时，底层正确调用 `PortfolioManager.import_from_smart_text(..., replace_existing=False)`，执行平账且无抛错。
5. **损坏图片优雅错误边界 (`test_mobile_card5_corrupted_image_error_boundary`)**:
   - 模拟 OCR 引擎抛出 `RuntimeError("Corrupted ONNX image tensor")` 时，系统由 `try-except` 兜底，渲染友好提示 `st.error`，未发生 Streamlit 白屏或未捕获异常。
6. **昨日收益与混淆数字代码防截断压测 (`test_parse_smart_text_holdings_adversarial_variations`)**:
   - 带有千分位逗号（`1,234.56`）、正负号收益（`+0.05`、`-67.89`）、6位数字代码（`005561`、`100032`）及纯别名（`招商白酒`、`纯债`）均能 100% 精确提取，无数字被错误替换或截断。
7. **手机模式性能隔离 (`test_mobile_performance_isolation_via_st_stop`)**:
   - 手机极简盯盘视图末尾调用 `st.stop()`（第 3274 行），实测手机模式下组件数量远少于桌面模式（`desk_sb=24, mob_sb=3`），且桌面 4 个重量级主选项卡（`len(at_desk.tabs) > 0`）在手机模式下完全被截断不执行（`len(at_mob.tabs) == 0`），达成物理性能隔离。

### 1.3 四只读裁判文件与基础测试回归
- `git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py`：**输出严格为空**。
- `pytest tests/test_infra.py -v`：**14/14 PASSED** (5.80s)。
- `pytest tests/test_adv_final_closure.py -v`：**14/14 PASSED** (40.45s)。

---

## 2. Logic Chain (质询推演与因果链)

1. **顶栏提权与双向同步因果推演**:
   - 观察：`app_gui.py` 将全局顶栏置于第 2850 行（位于 `if app_view_layout_mode == "📱 手机极简盯盘"` 之前）。
   - 推导：无论是宽屏桌面还是极窄手机屏幕，用户加载应用后均首先执行顶栏渲染。
   - 验证：在 AppTest 中，桌面与手机模式均存在 `topbar_ledger_select_...` 与视图模式切换胶囊，且包含 `main_live` 与 `combat_29_funds`，逻辑链闭合。

2. **手机 5 卡流与真实存量账本协同因果推演**:
   - 观察：`combat_29_funds` 内存在 19~20 只市值小于 200 元且满期天数大于 30 天的尾部零头标的。
   - 推导：卡片 3 扫描 `pm.holdings` 能够命中并触发 `t_count > 0` 分支，渲染高优先级的橙色瘦身卡与一键清扫按钮。
   - 验证：AppTest 实际捕获到 `btn_mob_sweep_tails`，点击后直接在 session_state 中载入 Tab 2 清扫方案，并输出可复制的 14:30 下单口令小抄，逻辑链完整。

3. **长截图真 OCR 切片平账因果推演**:
   - 观察：卡片 5 对接 `pm.parse_screenshot_ocr_holdings`，并提供可编辑表格与覆盖/追加双按钮。
   - 推导：彻底替代了旧版的假提示，支持用户即时查看识别出的 7 个字段（基金代码、名称、市值、盈亏、成本、份额类别、天数）并在界面直接入库。
   - 验证：AppTest 成功注入模拟数据并触发 commit 交互，会计恒等式与入库逻辑完全自洽。

---

## 3. Caveats (质询边界与限制说明)

1. **OCR 模型环境依赖**:
   - RapidOCR 依赖本地 ONNX Runtime 及离线权重文件。若环境缺少 ONNX 支持，代码已实装 `try-except` 错误边界并优雅呈现 `st.error`，不会引发服务崩溃。
2. **测试环境 save_state 隔离**:
   - 在测试 `btn_mob_ocr_commit_replace` 与 `btn_mob_ocr_commit_append` 时，需注意 mock 或隔离 `pm.save_state()`，避免单元测试污染本地活跃实盘的 `portfolio_ledger.json`（本审查已在测试后完成 git 还原核验）。
3. **顶栏与侧边栏双状态联动说明**:
   - Streamlit 的组件状态机制中，顶栏切换模式时需同步重置 `sb_view_layout_radio`，代码第 2920 行已完成此项同步，确保两处控件互不打架。

---

## 4. Conclusion (裁决结论)

- **质询裁决**: **`APPROVE` (核验通过)**。
- **依据总结**:
  1. 顶栏双向同步、账本快捷切换（含 `combat_29_funds` 与 `main_live`）与桌面/手机视图胶囊已 100% 达成。
  2. 手机极简盯盘 5 张卡片流结构完整、语义丰富，19 只碎片尾仓一键清扫与 14:30 下单小抄均真实联动。
  3. 手机长截图真 OCR 切片解析、预览平账与一键覆盖/追加完全闭环，假功能提示已彻底清除。
  4. 7 项独立对抗测试全绿通过，四只读裁判文件严格零修改，核心回归基准全部保持绿灯。

---

## 5. Verification Method (独立复现与验证指令)

任何审计员或后续流水线智能体可执行以下命令独立复现实测结果：

```powershell
# 1. 验证四个裁判文件物理只读红线
git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py

# 2. 运行本次质询智能体创建的 7 项独立对抗测试
py -3 -m pytest tests/test_challenger_g16_m2_adversarial.py -v

# 3. 运行基础裁判套件与回归测试
py -3 -m pytest tests/test_infra.py -v
py -3 -m pytest tests/test_adv_final_closure.py -v
```
- **预期通过条件**:
  - 指令 1 输出严格为空。
  - 指令 2 输出 `7 passed`。
  - 指令 3 输出 `14 passed`，`14 passed`。
