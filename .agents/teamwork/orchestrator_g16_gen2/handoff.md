# Orchestrator Soft Handoff (Generation 2 -> Generation 3)

## 1. Observation (Completed Work & Evidence Chain)
- **Phase 0 (Survey)**:
  - 3 名探索智能体（explorer_survey_1, 2, 3）完成了对系统架构、`advisory_engine.py`、`app_gui.py`、`portfolio_manager.py`、`multi_ledger_manager.py`、`strategy_bridge.py` 以及测试套件/只读裁判文件的实地勘察，确立了 `SCOPE.md`。
- **Milestone 1 (DONE & VERIFIED)**:
  - `advisory_engine.py`: `generate_chief_advisor_memo` 彻底修复读取不存在 `cost_value` 的 Bug，支持多字段兼容降级链 (`cost_basis` -> `shares * cost_price` -> `cost_value`) 与 `floating_pnl_pct` / `pnl_pct`；实测 29 基账本准确检出深套标的 18 只 (`deep_loss_count >= 3`)，点名 `011613` (-17.1%)、`100032` (-12.0%)、`161725` (-25.1%)；Tab 1 目标权重字典自适应防护，彻底消除“6只碎片尾仓合计 ¥1.00”的不良展示；碎片尾仓判定与 ActiveRiskSentry 维度 13 对齐，准确剔除 #10 `005827 易方达蓝筹` (¥124.14)，锁定 19 只免赎碎片合计平账为 ¥442.70。
  - `app_gui.py`: `render_chief_advisor_memo_card` 移出收起的折叠框，在顶部 4 张全局指标卡正下方直显；CSS 重构为 1 行 5 列横向等高矩阵网格 (`repeat(5, minmax(0, 1fr))`, 子卡高 ~115px)，带 `@media (max-width: 768px)` 移动端自适应折行；统一经由 `_clean_html()` 与 `safe_markdown_html()`，完全杜绝 CommonMark 4 空格缩进代码块泄露风险（规则 27 达标）。
  - M1 门禁全票通过：2 Reviewers APPROVE, 2 Challengers APPROVE, Forensic Auditor CLEAN。
- **Milestone 2 (IMPLEMENTED & REMEDIATED)**:
  - `app_gui.py`: 在第 2850 行左右实装全局紧凑顶栏控制条（品牌与行情角标 + 「📂 当前激活账本」选择器 + 「🖥️ 桌面专业 / 📱 手机盯盘」切换胶囊），桌面与手机模式 100% 共享。
  - `app_gui.py`: 手机极简盯盘视图完整构建 5 张卡片流：Card 1 资产大卡、Card 2 五维备忘录摘要、Card 3 碎片尾仓清扫卡、Card 4 14:30 复制小抄、Card 5 手机长截图真 OCR 切片识别（调用 RapidOCR 离线模型，渲染 `st.data_editor` 预览编辑表与「一键覆盖 / 追加合并」写入落盘闭环）。
  - `portfolio_manager.py`: `parse_smart_text_holdings` 前置正则剥离昨日收益标签与数值，直通 `fuzzy_match_fund_by_name`，封堵纯数字词条调用全库搜索，挂载 `parse_long_screenshot_holdings` 兼容别名。
  - M2 门禁复核与缺陷修复：在 M2 初审中，`reviewer_m2_1` 提出唯一修改请求（手机端 Card 3/4 尾仓清扫逻辑粗暴导致腰部仓 `005827` 被误卷入，与 Card 2 的 19 只 / ¥442.70 冲突）。已由 `worker_m2_fix` 完成对齐修复，手机端全屏统一锁定为 19 只免赎碎片与 ¥442.70。新增测试 `tests/test_m2_features.py`（6 项全过）与 `tests/test_infra.py`（14 项全过）。

## 2. Milestone State (当前里程碑状态)
| 里程碑 | 内容 | 状态 | 后续操作 |
|---|---|---|---|
| M1 | 备忘录 Bug 修复与 1行5列横向情报矩阵 | **DONE** | 已归档通过 |
| M2 | 全局顶栏控制条、手机真 OCR 闭环与模糊匹配打通 | **REMEDIATED** | 需继任者组织最终门禁验收并标记 DONE |
| M3 | 29基真实账本实战演练、Tab 2 手术面板与 Tab 3 回测对比 | **PLANNED** | 继任者派工执行 |
| M4 | 物理红线法证审计、全量单测、服务重启多模态验收与 G17 归档 | **PLANNED** | 继任者派工执行 |

## 3. Active Subagents (当前子代理状态)
- 累计派工数：16 / 16（已达上限）。
- 所有 16 个子代理均已成功交付 handoff 报告并处于 idle/completed 状态，无悬挂挂起任务。

## 4. Pending Decisions & Key Constraints (关键决策与约束)
- **物理安全红线**：严禁修改四个只读裁判文件 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`；严禁修改 `DataLoader.simulate_execution` 默认签名与计费逻辑。
- **M2 收口决策**：`worker_m2_fix` 已将 Card 3/4 尾仓清扫规则与 `advisory_engine.py` 严格对齐，清除了同屏数字冲突。继任者可直接组织 M2 门禁收口，或派 reviewer 快速核准后进入 M3。
- **M3 重点工作**：
  1. `multi_ledger_manager.py`：保持 `combat_29_funds` 幂等挂载，但须保护 `tests/test_multi_ledger_manager.py::test_get_all_ledgers_summary` 单测隔离（`if self.root == WORKSPACE_ROOT:`），统一持有天数文案（400天 vs 1040天）；
  2. Tab 2：联动 `strategy_bridge.estimate_rebalance_impact` 呈现 29->6 只、盘活资金 ¥442.70~¥962.57、票息垫提升与回本天数缩短；
  3. Tab 3：实装「实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）」，支持真实申赎费率与 T+1，在时光机动态再平衡消除 2024.09 踏空。
- **G17 终审指令门禁**：在最终报告输出 G17 指令时，严禁使用带冒号的 `slashCommand:` 格式，必须按纯文本 `/goal`, `/boost`, `/teamwork`, `/browser` 输出。

## 5. Remaining Work (继任者具体下一步)
1. 继承并激活新状态目录 `.agents/teamwork/orchestrator_g16_gen3`；
2. 启动继任者心跳守护任务；
3. 将 M2 门禁标记为 PASS 并更新 `GATE_STATUS.md` 与 `SCOPE.md`；
4. 派发 Worker 进入 Milestone 3 代码实现（`multi_ledger_manager.py`, `strategy_bridge.py`, `app_gui.py`）；
5. 推进 M3 门禁质检与 M4 全量测试、/browser 验收与 Git 归档。

## 6. Key Artifacts
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (原始用户需求)
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen2\SCOPE.md` (里程碑与功能契约)
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen2\GATE_STATUS.md` (门禁状态账本)
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen2\BRIEFING.md` (先任记忆快照)
