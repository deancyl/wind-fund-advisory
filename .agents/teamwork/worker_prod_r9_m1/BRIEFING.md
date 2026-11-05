# BRIEFING — 2026-11-05T14:41:00Z

## Mission
完成 Milestone 1 (R1 & R2)：实现 MultiLedgerManager 多账本体系存储与管理、PortfolioManager 独立数据库隔离派生、以及 app_gui.py 全站级动态热装配与跨 Tab 贯通。

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r9_m1
- Original parent: 8849ddae-0421-48b2-aa8f-6d2c7b15dafe
- Milestone: M1 (Features 1-4, R1 & R2)

## 🔒 Key Constraints
- 物理安全红线：严禁修改只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 严禁假代码：严禁硬编码测试结果，严禁 dummy/facade，真实逻辑与状态。
- 文件所有权：`AGY2_FundAdvisory/multi_ledger_manager.py`, `data/ledgers_index.json`, `data/ledgers/`, M1 additions in `portfolio_manager.py` and `app_gui.py`。
- 主实盘账本 `portfolio_ledger.json` (`id="main_live"`, `name="主实盘账本"`, `type="live"`) 受物理保护禁止删除，无参 `PortfolioManager()` 保持 100% 行为兼容。
- 派生/沙盒账本在 `data/ledgers/<id>.json`，配对隔离 SQLite `data/ledgers/<id>.db`，防止冲刷主实盘 `portfolio_state.db`。

## Current Parent
- Conversation ID: 8849ddae-0421-48b2-aa8f-6d2c7b15dafe
- Updated: 2026-11-05T14:41:00Z

## Task Summary
- **What to build**:
  1. `AGY2_FundAdvisory/multi_ledger_manager.py`: `MultiLedgerManager` 单例与生命周期管理，支持 `list_ledgers`, `create_ledger`, `clone_ledger`, `rename_ledger`, `delete_ledger`, `get_all_ledgers_summary`, `get_pm(ledger_id)`.
  2. `portfolio_manager.py`: 支持 `ledger_file` 兼容别名与 `ledger_id`，非主实盘账本默认隔离 `data/ledgers/<id>.db`，re-export `MultiLedgerManager`.
  3. `app_gui.py`: 全站绑定 `active_ledger_id` 与 `MultiLedgerManager.get_instance().get_pm(...)`，账本切换联动所有卡片/看板/Tab，Tab 2 顶部多账本单行吧台与 Popover、沙盒环境黄色警告条，Tab 1 步骤三双轨保存（覆盖当前 vs 另存为新账本）。
- **Success criteria**:
  - `MultiLedgerManager` 完整实现并通过单元测试；
  - 切换账本全站联动且互不污染；
  - 主实盘防删除保护生效；
  - 现有测试 100% 通过无回归。
- **Interface contracts**: `PROJECT.md` § Interface Contracts (M1)
- **Code layout**: `PROJECT.md` § Code Layout

## Key Decisions Made
- `MultiLedgerManager` 单例管理 `data/ledgers_index.json`，确保 `main_live` 永远置顶并强制 `is_protected=True`；
- 所有非主实盘账本在 `data/ledgers/<id>.json` 与 `data/ledgers/<id>.db` 严格成对，彻底物理杜绝 `save_state()` 清空主实盘 SQLite 记录；
- `PortfolioManager.__init__` 支持 `ledger_file` 别名与 `ledger_id`，当非主实盘账本传入时自动派生 `db_path = ledger_json_path.with_suffix(".db")`；
- `app_gui.py` 引入 `switch_active_ledger` 统一状态机，切换账本时联动清空 Tab 2 诊断与调仓缓存并同步 `active_tier_val`；
- Tab 2 顶部单行集成账本选择器与 3 大 Popover（新建、克隆、管理/全家庭汇总），沙盒账本实时挂载黄色隔离提示条；
- Tab 1 步骤三升级为双轨方案（覆盖写入当前账本 vs 另存为全新独立账本）。

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/multi_ledger_manager.py`: 新建，实现多账本生命周期与全账本资产聚合
  - `AGY2_FundAdvisory/portfolio_manager.py`: 支持 ledger_file / ledger_id / 独立 DB 派生，re-export MultiLedgerManager
  - `AGY2_FundAdvisory/app_gui.py`: active_ledger_id 绑定，switch_active_ledger 全局联动，Tab 2 单行吧台与 Popover，Tab 1 双轨保存
  - `tests/test_multi_ledger_manager.py`: 新建 8 项全覆盖自动化测试（含 AppTest 会话集成）
  - `data/ledgers_index.json`: 账本元数据中央索引
- **Build status**: pytest passed 29/29 (test_infra, test_portfolio, test_multi_ledger_manager, test_streamlit_apptest_run)
- **Pending issues**: None

## Quality Status
- **Build/test result**: All 29 passed
- **Lint status**: Clean
- **Tests added/modified**: 8 new tests in `tests/test_multi_ledger_manager.py`

## Loaded Skills
- None
