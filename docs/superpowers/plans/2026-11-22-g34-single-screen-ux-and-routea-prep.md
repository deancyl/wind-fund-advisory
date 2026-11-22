# AGY2 G34 单屏聚焦瘦身（路线 B）与双端原生架构预备（路线 A）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 彻底消灭 8 屏长瀑布流报表墙，将四大主标签（持仓/调仓/复盘/工具）改造为 1~1.5 屏单屏分段聚焦体验并加入打卡闭环；同时斩断 `api_server.py` 对 Streamlit 的依赖并补齐跨端 `/api/v1/*` 接口契约，为未来 Windows `.exe` 与 Android `.apk` 扫清全部障碍。

**Architecture:** 
1. 解耦抽取纯 Python 模块 `rebalance_grouping.py`（无 Streamlit 依赖），统一管理意图分组与 `daily_execution_checklist.json` 每日打卡。
2. 改造 `app_gui.py`：移除首屏常驻黄色降级大横幅；主标签 1「持仓」加顶部分段单选（持仓明细/估值对账/在途限购）与今日红黑榜；主标签 2「调仓」加顶部分段单选（今日调仓/新钱定投/存量重塑）与打卡进度条；主标签 3「复盘」加顶部分段单选（历史时光机/滚动胜率/样本外前瞻/影子账本）；主标签 4「工具/诊断」加顶部分段单选（风险体检/资产敞口/重仓重叠/极端承压/投顾底稿），全部采用严格 `if / elif` 按需渲染，未选中不计算不绘图。
3. 改造 `api_server.py`：完全斩断对 Streamlit 的直接与间接引用，增加 `/api/v1/holdings/movers`、`/api/v1/rebalance/checkin`、`/api/v1/alerts/push`、`/api/v1/review/{subview}`、`/api/v1/diagnose/{subview}`，并导出 `docs/openapi_v1.json`、`docs/client_ia_contract.json`、`API_CONTRACT.md`。

**Tech Stack:** Python 3.11, Streamlit, FastAPI, Pydantic, Playwright, Plotly, Pandas

**Spec:** `c:\Users\deanc\Downloads\agy2_g33_b_a.md`, `c:\Users\deanc\Downloads\agy2_g34_singlescreen_ux_and_routea_prep_instruction.md`

## Global Constraints
- 绝对禁止修改四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 绝对禁止篡改用户真实持仓账本 `combat_29_funds`。
- 绝对禁止外溢写入全局 `c:\Users\deanc\.gemini\GEMINI.md`。
- 所有按钮文字严格控制在 2~4 个字（严禁括号说明），解释性文案统一收进 `i` 气泡。
- 必须保持 `verify_g25` ~ `verify_g33` 历史门禁 100% 通过。

## Review Focus
1. `import api_server` 触发 `sys.modules["streamlit"]` 污染 -> 必须彻底解耦，由独立单测强制断言。
2. `app_gui.py` 内部 `tab_holdings_and_rebalance`、`tab_backtest`、`tab_toolbox` 若全量平铺会导致 DOM 超高 -> 必须使用水平单选控制器严格 `if / elif` 分支渲染。
3. 调仓打卡 `daily_execution_checklist.json` 写入失败或并发读写异常 -> 用标准 JSON 容错与默认结构兜底。
4. 移动端 390px 下水平分段单选是否溢出 -> 控制选项文字在 4 字以内。
5. 历史门禁依赖的 `rebal_cols_10`、`估值 vs 官方逐基对账单`、`_render_chart_reading_guide` 等静态特征必须保留。

---

### Task 1: 独立解耦模块 `rebalance_grouping.py` 与打卡持久化
**Files:**
- Create: `AGY2_FundAdvisory/rebalance_grouping.py`
- Create: `rebalance_grouping.py` (根目录镜像)
- Modify: `AGY2_FundAdvisory/ui_daily_brief.py`
- Modify: `ui_daily_brief.py` (根目录镜像)
- Test: `tests/test_rebalance_grouping.py`

- [ ] **Step 1: 编写测试 `tests/test_rebalance_grouping.py`**
  验证 `rebalance_grouping.py` 不导入 streamlit，`IntentGroup`、`group_rebalance_orders_by_intent`、`load_daily_checkin`、`save_daily_checkin` 正常工作。
- [ ] **Step 2: 运行测试验证失败**
- [ ] **Step 3: 实现 `rebalance_grouping.py` 并让 `ui_daily_brief.py` 改为导入它**
- [ ] **Step 4: 运行测试验证通过**
- [ ] **Step 5: 验证 `ui_daily_brief.py` 行数仍在 400 行以内**

### Task 2: 升级 `api_server.py` 跨端接口与斩断 Streamlit 依赖
**Files:**
- Modify: `AGY2_FundAdvisory/api_server.py`
- Modify: `api_server.py` (根目录镜像)
- Test: `tests/test_api_server_decoupled.py`

- [ ] **Step 1: 编写测试验证 `import api_server` 后 `"streamlit" not in sys.modules`**
- [ ] **Step 2: 运行测试**
- [ ] **Step 3: 在 `api_server.py` 补齐 5 组跨端新接口**
  - `GET /api/v1/holdings/movers`
  - `GET /api/v1/rebalance/checkin` 与 `POST /api/v1/rebalance/checkin`
  - `GET /api/v1/alerts/push`
  - `GET /api/v1/review/{subview}`
  - `GET /api/v1/diagnose/{subview}`
  - `GET /api/v1/backtest/summary`
  - CLI 独立启动入口
- [ ] **Step 4: 运行测试并验证全部 200 OK 且纯净 JSON（无 HTML、无 Emoji）**

### Task 3: 导出 OpenAPI 契约与跨端架构规范
**Files:**
- Create: `docs/openapi_v1.json`
- Create: `docs/client_ia_contract.json`
- Create: `AGY2_FundAdvisory/API_CONTRACT.md`
- Create: `API_CONTRACT.md` (根目录镜像)

- [ ] **Step 1: 编写导出脚本导出 `docs/openapi_v1.json`**
- [ ] **Step 2: 编写 `docs/client_ia_contract.json` 映射 4 主标签 + 子分段**
- [ ] **Step 3: 编写 `API_CONTRACT.md` 跨端冻结接口契约**

### Task 4: 路线 B 改造 `app_gui.py` 消除 8 屏瀑布流，实现单屏分段聚焦
**Files:**
- Modify: `AGY2_FundAdvisory/app_gui.py`
- Modify: `AGY2_FundAdvisory/ui_daily_brief.py`
- Modify: `ui_daily_brief.py`

- [ ] **Step 1: 移除 L4342 的常驻黄色降级横幅**，改为仅在全断线时提示，局部降级收进顶栏小圆点与 i 弹窗。
- [ ] **Step 2: 改造 Tab 1「持仓」**：
  - 顶部增加 `_render_daily_movers_strip` 今日红黑榜（Top 3 贡献 / Top 3 拖累）。
  - 水平分段单选 `rad_holdings_subview`: `["持仓明细", "估值对账", "在途限购"]`，严格 `if / elif` 按需渲染，移除原冗余堆叠。
- [ ] **Step 3: 改造 Tab 2「调仓」**：
  - 水平分段单选 `rad_rebalance_subview`: `["今日调仓", "新钱定投", "存量重塑"]`。
  - 在「今日调仓」中集成执行进度条与可勾选打卡复选框，接入 `save_daily_checkin`。
- [ ] **Step 4: 改造 Tab 3「复盘」**：
  - 水平分段单选 `rad_backtest_single_view`: `["历史时光机", "近三年胜率", "样本外前瞻", "影子账本"]`，严格 `if / elif` 按需渲染，彻底终结 7 屏长瀑布流！
- [ ] **Step 5: 改造 Tab 4「工具/诊断」**：
  - 水平分段单选 `rad_toolbox_single_view`: `["风险体检", "资产敞口", "重仓重叠", "极端承压", "投顾底稿"]`，严格 `if / elif` 按需渲染，未选中项不提前绘图计算！

### Task 5: 编写 G34 终极双轨门禁脚本并执行完整验收
**Files:**
- Create: `scripts/verify_g34_single_screen_and_routeA_prep_gate.py`
- Create: `scripts/verify_g33_route_b_and_route_a_prep_gate.py`

- [ ] **Step 1: 编写门禁脚本，包含 5 项硬性断言**
- [ ] **Step 2: 运行门禁脚本，进行 Playwright 双端浏览器无头实测**
- [ ] **Step 3: 运行历史核心门禁（G25 ~ G33 + pytest）验证 100% 绿灯回归**
- [ ] **Step 4: 清理测试产生的临时数据，提交并推送 Git**
- [ ] **Step 5: 重启本地 8501 服务并验证健康探针**
