# BRIEFING — 2026-11-11T02:21:00Z

## Mission
Milestone 2 门禁缺陷修复 (Remediation) —— 修复 `app_gui.py` 手机极简模式 Card 3/Card 4 尾仓清扫判定规则，与 `advisory_engine.py` 完全对齐，消除对腰部持仓 `005827 易方达蓝筹` (¥124.14) 的误卷入，使手机模式全屏统一锁定 19 只免赎碎片与 ¥442.70 平账，并通过全部测试用例。

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_fix
- Original parent: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Milestone: Milestone 2 Remediation

## 🔒 Key Constraints
- 独占所有权文件：`AGY2_FundAdvisory/app_gui.py` 与 `tests/test_m2_features.py`
- 四个裁判文件必须保持绝对 0 修改：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- 手机极简模式 Card 3/Card 4 必须与 `advisory_engine.py` 严格对齐，提取 19 只免赎碎片，总金额 ¥442.70，排除 005827
- 严禁作弊，所有测试断言真实执行，通过 `pytest tests/test_m2_features.py` 和 `pytest tests/test_infra.py`

## Current Parent
- Conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Updated: 2026-11-11T02:21:00Z

## Task Summary
- **What to build**: 修复 `app_gui.py` 手机模式 Card 3 扫描 `tail_items` 判定逻辑，将 `005827 易方达蓝筹` 排除出碎片清扫，使 Card 3/4 呈现 19 只、¥442.70，与 Card 2 达到 100% 同屏一致。更新 `tests/test_m2_features.py` 补充真实断言。
- **Success criteria**:
  - `combat_29_funds` 账本下扫出的免赎尾仓数量严格为 19
  - 总金额严格为 442.70
  - `005827` 绝不在清扫列表中
  - `pytest tests/test_m2_features.py` 6 passed (100%)
  - `pytest tests/test_infra.py` 14 passed (100%)
  - 四个裁判文件 0 修改
- **Interface contracts**: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

## Key Decisions Made
- 在 `app_gui.py` 第 3003~3015 行将粗暴的 `0 < mv_h < 200.0 and min_d >= 30` 替换为与 `advisory_engine.py` 及 `ActiveRiskSentry` 维度 13 严格对齐的判定规则：
  `is_tail = (0 < mv_h < 100.0) or (100.0 <= mv_h < 200.0 and (s_cls == "C" or any(k in fname for k in ["联接", "ETF", "指数", "红包", "体验", "尾仓", "碎片"])))`
  `is_fee_free = (s_cls == "C" and min_d >= 30) or (s_cls != "C" and min_d >= 365)`
- 在 `tests/test_m2_features.py` 新增 `test_mobile_tail_sweep_rule_and_combat29_alignment`，对 `combat_29_funds` 下的真实数量（19）、金额（442.70）、排除 005827 建立严格断言。

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/app_gui.py`: 修正手机模式 Card 3/Card 4 尾仓清扫判定规则，与 `advisory_engine.py` 严格对齐
  - `tests/test_m2_features.py`: 增加 AST 规则完整性断言与 `test_mobile_tail_sweep_rule_and_combat29_alignment` 真实数值断言
- **Build status**: PASS (pytest test_m2_features.py: 6 passed, pytest test_infra.py: 14 passed)
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (6 passed in test_m2_features.py, 14 passed in test_infra.py)
- **Lint status**: Clean (py_compile 0 errors)
- **Tests added/modified**: `test_mobile_tail_sweep_rule_and_combat29_alignment`, `test_app_gui_source_code_integrity`

## Loaded Skills
- None required

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_fix\DISPATCH.md` — 任务调度单
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_fix\handoff.md` — 交付报告
