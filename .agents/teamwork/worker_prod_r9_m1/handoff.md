# Handoff Report: Milestone 1 (R1 & R2) 多账本体系存储管理与全站热装配交付

**Agent**: `worker_prod_r9_m1` (teamwork_worker)  
**Roles**: implementer, qa, specialist  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r9_m1`  
**Parent Conversation ID**: `8849ddae-0421-48b2-aa8f-6d2c7b15dafe`  
**Timestamp**: 2026-11-05T14:41:30Z  

---

## 1. Observation (观测事实)

1. **底层存储与防冲刷暗礁**：
   - 原 `PortfolioManager.save_state()` 采用 SQLite 与 JSON 镜像双轨保存机制。当调用 `save_state()` 时，会执行 `DELETE FROM holdings`, `holding_batches`, `pending_orders`, `portfolio_meta` 并重写 SQLite 表。
   - 若多个账本仅区分 JSON 文件路径而共享默认的 `portfolio_state.db`，在保存任何沙盒账本时会清空并冲刷主实盘在 SQLite 中的记录。
   - 主实盘账本依赖根目录下 `portfolio_ledger.json` 与 `portfolio_state.db`，现有所有单元测试（如 `test_portfolio.py`, `test_infra.py`）无参调用 `PortfolioManager()` 必须保持对这两个默认文件的 100% 行为兼容。

2. **UI 状态绑定与跨 Tab 联动机制**：
   - `AGY2_FundAdvisory/app_gui.py` 在首屏第 1365 行初始化绑定 `st.session_state.pm`，后续的顶部大卡片 4（总资产与今日预估）、右翼主动风险哨 `ActiveRiskSentry`、Tab 2 持仓账本与调仓、Tab 3 组合回测（当前实盘持仓）、Tab 4 穿透工具（当前实盘持仓）均直接读取 `pm` 或 `pm.holdings`。
   - 原 Tab 2 缺少账本选择与管理入口，无法在沙盒与主实盘之间平滑切换；Tab 1 步骤三仅有一个单一按钮「🚀 设为初始持仓」，缺少另存为新账本的保护选项。

3. **执行结果检验**：
   - 执行 `py -3 -m pytest tests/test_infra.py tests/test_portfolio.py tests/test_multi_ledger_manager.py tests/test_streamlit_apptest_run.py`：全量 29 项测试 100% 通过（29 passed in 38.97s）。
   - 4 大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未做任何修改，SHA256 完好无损。

---

## 2. Logic Chain (推演逻辑链)

1. **基于观察 1（SQLite 双轨存储防冲刷）**：
   - 新建专职模块 `AGY2_FundAdvisory/multi_ledger_manager.py`，实现 `MultiLedgerManager`。
   - 在 `MultiLedgerManager` 中严格约定：主实盘账本固定映射 `id="main_live"`、`file="portfolio_ledger.json"`、`db_file="portfolio_state.db"`、`is_protected=True`。在 `delete_ledger("main_live")` 时显式抛出 `PermissionError("主实盘账本受物理保护，禁止删除！")`，物理层拦截任何删除行为。
   - 在 `portfolio_manager.py` 的 `PortfolioManager.__init__` 中新增 `ledger_file` 别名与 `ledger_id` 支持。当检测到 `ledger_json_path != "portfolio_ledger.json"` 且 `db_path` 为缺省值时，自动派生 `db_path = ledger_json_path.with_suffix(".db")`。此举确保每个新建或克隆的账本均拥有独立的 `data/ledgers/<id>.json` 与 `data/ledgers/<id>.db`，沙盒执行 `save_state()` 时仅写入自身数据库，主实盘 SQLite 零污染。
   - 在 `portfolio_manager.py` 底部完成 `from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager` 的 re-export，满足外部模块双向导入需求。

2. **基于观察 2（UI 全局状态机热装配与全站贯通）**：
   - 在 `app_gui.py` 首屏引入 `st.session_state.active_ledger_id` 与 `st.session_state.mlm`，动态绑定 `st.session_state.pm = mlm.get_pm(active_ledger_id)`。
   - 封装 `switch_active_ledger(target_ledger_id)` 函数：切换时自动调用当前 `pm.save_state()` 存盘、更新 `active_ledger_id`、装配目标 `pm`、同步 `active_tier_val` 为目标账本的 `default_tier`、清空 `tab2_diag_cache` 与 `tab2_rebal_cache`，并触发 `st.rerun()`。
   - 在 Tab 2「步骤一：持仓账本」标题正下方挂载单行多账本管理吧台：包含【当前账本选择器】、【➕ 新建账本 Popover】、【📋 克隆当前副本 Popover】、【⚙️ 账本管理 Popover（含重命名、防删除保护与全家庭资产汇总明细表）】。
   - 当检测到当前账本类型为 `sandbox` 时，醒目呈现黄色安全提示条：「🧪 当前为独立沙盒环境，任何调仓与录基演练均隔离存储，绝不影响主实盘」。
   - 在 Tab 1 步骤三升级为双轨保存方案：左侧为「📥 覆盖写入当前激活账本」，右侧为「🆕 另存为全新独立账本」Popover（支持设置新账本名称、初始资金、账本类型与风险档位），一键创建并写入持仓后平滑切换至新账本。

3. **基于观察 3（端到端测试与真实性保障）**：
   - 编写 `tests/test_multi_ledger_manager.py`，包含 8 项深度测试用例：覆盖 re-export、主实盘物理防删除、新建账本独立文件落盘、深拷贝克隆、修改沙盒持仓前后主实盘文件哈希完全一致性（隔离性检验）、删除账本物理清理与激活回退、全账本家庭资产汇总计算、以及 Streamlit AppTest 全站会话状态机热装配无白屏验证。

---

## 3. Caveats (注意事项与假设)

1. **网络超时防护**：测试与运行时部分基金行情查询会访问外部网络接口，若遇断网或未安装证书，底层内置了静态行情与全收益矩阵回退，测试始终稳定通过。
2. **多进程并发与锁**：当前多账本管理采用本地单用户单实例架构，`ledgers_index.json` 由单进程读写，未引入复杂的分布式文件锁，完全满足个人本地投顾工作台定位。

---

## 4. Conclusion (交付结论)

Milestone 1（R1 与 R2）全部需求已高质量、完整实现：
1. `AGY2_FundAdvisory/multi_ledger_manager.py` 已就绪，提供完整的多账本增、删、改、查、克隆与家庭资产聚合汇总能力，主实盘受物理删除保护；
2. `AGY2_FundAdvisory/portfolio_manager.py` 成功支持 `ledger_file` / `ledger_id` 别名与独立 SQLite 数据库派生隔离，并完成 `MultiLedgerManager` re-export；
3. `AGY2_FundAdvisory/app_gui.py` 实现了基于 `active_ledger_id` 的全站级动态热装配，Tab 2 单行吧台、3 大 Popover、沙盒环境警示横幅与 Tab 1 双轨保存功能均已上线且通过 AppTest 无报错验证；
4. 全量自动化测试套件（29 项测试）100% 通过，裁判基线完好无损，无任何回归。

---

## 5. Verification Method (独立核验方法)

下游审计员或主编排代理可执行以下命令进行独立核验：

```powershell
# 1. 运行多账本管理专属自动化测试集（含 AppTest 会话热装配验证）
py -3 -m pytest tests/test_multi_ledger_manager.py -v

# 2. 运行整体回归测试（基建底座 + 投资组合分析 + 多账本 + Streamlit AppTest）
py -3 -m pytest tests/test_infra.py tests/test_portfolio.py tests/test_multi_ledger_manager.py tests/test_streamlit_apptest_run.py

# 3. 校验裁判文件哈希是否完好
git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
# 期望输出：空（无任何修改）
```
