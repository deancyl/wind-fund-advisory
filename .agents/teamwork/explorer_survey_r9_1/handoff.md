# Handoff Report — Phase 0 Technical Survey (R1 & R2)

## 1. Observation
1. **`portfolio_manager.py` 初始化与持久化实现**：
   - 文件路径：`AGY2_FundAdvisory/portfolio_manager.py`
   - 行号 2387-2406：`PortfolioManager.__init__(self, db_path="portfolio_state.db", ledger_json_path="portfolio_ledger.json", storage_file=None)`。入参为 `ledger_json_path`，当前无 `ledger_file` 别名。
   - 行号 2748-2808：`save_state()` 先执行 SQLite 清空与重写（`DELETE FROM holdings`, `holding_batches`, `pending_orders`），再执行 JSON 镜像写入（`with open(self.ledger_json_path, "w", encoding="utf-8")`）。若 `_is_memory == True`，则跳过 JSON 写入。
   - 行号 2809-2824：`load_state()` 优先检查 `self.ledger_json_path.exists()`，存在则加载 JSON 并从关联 SQLite 回读快照栈。
2. **底层数据湖仓与账本目录现状**：
   - 根目录下存在主实盘账本 `portfolio_ledger.json`（308 行，总资产 191,445.0 元）与 `portfolio_state.db`。
   - `data/ledgers/` 目录与 `data/ledgers_index.json` 目前不存在，需由 `MultiLedgerManager` 自动创建并初始化。
3. **`app_gui.py` 全局实例注入与下游引用**：
   - 文件路径：`AGY2_FundAdvisory/app_gui.py`
   - 行号 1365-1368：`if "pm" not in st.session_state: st.session_state.pm = PortfolioManager(); pm = st.session_state.pm`。
   - 行号 1813-1833（顶部第 4 张卡片）：直接展示 `total_cur_equity`, `pm.available_cash`, `pm.in_transit_cash`, `est_pnl`, `_t2_pnl`。
   - 行号 2011-2018（右翼主动风险哨）：`report = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, ...)`，直接读取 `pm.holdings`。
   - 行号 3325-3375（Tab 2 持仓账本顶部）：现有资产基线横幅与操作按钮，为放置单行多账本管理吧台与沙盒提示的极佳位置。
   - 行号 3201-3213（Tab 1 步骤三）：现有一键写入按钮 `pm.apply_zero_start_blueprint`，为实施「覆盖当前账本 vs 另存为新账本」双轨选项的挂载点。
   - 行号 4806-4826（Tab 3 回测）：直接提取 `pm.holdings` 计算「当前实盘持仓」回测权重。
   - 行号 5190-5194（Tab 4 穿透）：直接提取 `dict(pm.holdings)` 进行行业与前十大重仓穿透体检。

## 2. Logic Chain
1. 基于观测 1：若只修改 `ledger_json_path` 而保留默认 `db_path="portfolio_state.db"`，多账本调用 `save_state()` 时其 SQLite 语句 `DELETE FROM holdings` 会冲刷掉主实盘在数据库中的数据。因此，`MultiLedgerManager` 生成账本实例时必须为非主实盘账本分配独立的 SQLite 数据库文件（如 `data/ledgers/<id>.db`），或在 `PortfolioManager` 中根据 `ledger_json_path` 自动派生 `db_path = ledger_json_path.with_suffix(".db")`。
2. 基于观测 1 & 2：主实盘账本固定为根目录 `portfolio_ledger.json`，在 `data/ledgers_index.json` 中元数据标定为 `id="main_live", name="主实盘账本", type="live", file="portfolio_ledger.json", is_protected=True`。在 `delete_ledger()` 中对 `main_live` 实施硬拦截（抛出异常或拒绝删除），可完全满足测试 C 与系统安全性。
3. 基于观测 3：全站所有 Tab、顶部指标卡与右翼风控哨均基于全局 `st.session_state.pm`。只要在 `app_gui.py` 顶部根据 `active_ledger_id` 将 `st.session_state.pm` 切换为对应账本的 `pm` 实例，并同步 `active_tier_val`、清空 `tab2_diag_cache` 与 `tab2_rebal_cache`，即可在一次 `st.rerun()` 中天然实现全站 100% 动态联动。

## 3. Caveats
1. 本次调研为只读分析（Read-only investigation），未向系统源码提交任何修改。
2. 尚未实地执行 `MultiLedgerManager` 与 `app_gui.py` 联调运行，实际落地时需留意 Streamlit 的 Selectbox `on_change` 与直接 `st.rerun()` 的状态时序，建议在切账本时直接采用标准 Streamlit 回调或条件分支处理。
3. `AGY2_FundAdvisory/strategy_bridge.py` 中存在部分通过 `cls._get_portfolio_manager()` 获取的延迟单例，若下游有无参调用可能默认读取主实盘，建议在 GUI 调用链路中显式传递 `pm`。

## 4. Conclusion
1. **R1 实施蓝图明确**：创建独立模块 `AGY2_FundAdvisory/multi_ledger_manager.py`（并在 `portfolio_manager.py` 导出），实现完整 CRUD、克隆、家庭汇总与物理删除保护；在 `PortfolioManager.__init__` 增加 `ledger_file` 别名与 SQLite 数据库隔离派生。
2. **R2 跨 Tab 贯通无架构阻碍**：在 `app_gui.py` 引入 `st.session_state.active_ledger_id`，在 Tab 2 步骤一顶部挂载单行多账本吧台（选择器、新建、克隆、管理 Popover）及沙盒提示条，在 Tab 1 步骤三提供「覆盖 vs 另存为新账本」双轨选项，切换时同步 `active_tier_val` 并清空 Tab 2 缓存。
3. 详细设计文档已落地于 `.agents/teamwork/explorer_survey_r9_1/report.md`。

## 5. Verification Method
1. **静态代码与文件核验**：
   - 检查 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r9_1\report.md` 的存在性与完整度。
   - 验证 `portfolio_manager.py`（行 2387-2406、2748-2808）与 `app_gui.py`（行 1365-1368、1813-1833、2011-2018、3201-3213、3325-3375、4806-4826、5190-5194）行号与代码片段对齐度。
2. **后续实施检验指令**：
   - 运行独立单元测试：`pytest AGY2_FundAdvisory/tests/test_portfolio_manager.py -q`
   - 专项测试 C 验证：编写并运行测试断言沙盒账本增删、克隆、隔离性及主实盘不可删除性。
   - GUI 运行检验：在 8501 端口启动 Streamlit 并验证多账本切换下无白屏异常。
