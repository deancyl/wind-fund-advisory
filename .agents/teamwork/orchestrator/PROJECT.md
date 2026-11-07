# Project: G8 世代深度 UI 与 UX 金融防错整改、Tab 2 物理视图真隔离、跨 Tab 真实路由跳转与实时多源感知进化

## Architecture
- **Web UI & Interaction Layer**: `AGY2_FundAdvisory/app_gui.py`
  - Tab 2 双视图真正物理分支隔离：主流程模式（`is_t2_main_mode=True`）仅渲染安全垫抗震看板、4张资产概览卡、极速录基吧台、持仓明细大表、步骤二时机裁决、步骤三调仓执行单，严禁渲染底部的账本工具坞 Expander；宽屏工具坞模式（`is_t2_main_mode=False`）隐藏持仓大表与步骤二三，直接在首屏平铺展示 6 大工具子 Tab。
  - Tab 2 持仓表未保存修改拦截与周边操作前置自动提交（`_commit_edited_holdings_table`），杜绝因点击周边按钮导致用户输入被静默清空。
  - 清理单页三度克隆的重复滑块（保留步骤三单控制点，设置 `# tab2_rebal_buf_slider_bot` 兼容注释），删除 `dock_tab3` 重复按钮，清理预警哨开发口号并将容器高度优化为 380px。
  - 大额本金输入框千分位与中文数量级防错提示（`format_chinese_amount`）。
  - Tab 1 覆盖写入当前激活账本升级为 `st.popover` + `st.checkbox` 确认门禁，覆写前强制压栈 Undo 快照，覆写后提供 `↩️ 撤销本次覆盖` 快捷按钮。
  - 首屏双翼看板跨 Tab 联动通过 `components.html` 注入同源 DOM 脚本触发真实 Tab 切换与平滑滚动，补齐 6 类预警处置参数传递，渲染高可见度跨区指令生效承接横幅。
  - 首屏晨报展示秒级时间戳与最新快讯摘要；Top 3 赛道卡片展示盘中实时涨跌幅胶囊、四维子项得分明细与核心入选依据。
- **Data & Ingestion Layer**: `AGY2_FundAdvisory/data_loader.py`
  - 挂载 `fetch_realtime_market_news_and_catalysts` 至 `DataLoader` 类，支持 2 秒超时约束、内存高速缓存 (TTL 60s) 与本地 `data/cache/realtime_news.json` 磁盘快照兜底。
  - 保持 `fetch_custom_realtime_indices` 批量实时行情与离线双日收盘价真实涨跌幅计算。
- **Quant & Advisory Engine Layer**: `AGY2_FundAdvisory/advisory_engine.py`, `portfolio_manager.py`
  - `OpportunityRadarEngine` 注入盘中实时指数涨跌幅与最新点位，动态响应乖离率与动量。
  - `evaluate_sector` 返回值透传 `core_logic`、`realtime_chg_pct`、`realtime_point` 及四维子项得分（`s_val`, `s_mom`, `s_er`, `s_crowd`）。
  - `PortfolioManager` 实装 `_push_undo_snapshot(self)` 并在 `apply_zero_start_blueprint` 清空持仓前调用，保障一键可逆回滚。
- **Physical Safety Redline Layer**:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（物理只读红线，零字符修改）。
  - `DataLoader.simulate_execution` 默认签名与 7 天 1.50% 扣费逻辑原封不动。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Tab 2 双视图物理分支隔离 | 主流程严格隐藏底部账本工具坞；工具坞模式隐藏持仓大表与步骤二三并全宽平铺 6 大子 Tab | M1 | P0 Item 1 |
| 2 | 持仓表未保存修改保护 | 检测 uncommitted changes 渲染动态警告条；周边按钮前置触发自动入库 | M1 | P1 Item 4 |
| 3 | 清理重复滑块与口号残留 | 清理 Tab 2 顶部与底部冗余缓冲带滑块，清理 dock_tab3 重复按钮，清理预警哨口号并设容器高 380px | M1 | P1 Item 5 |
| 4 | 大额本金中文数量级防错提示 | Tab 1、Tab 2 现金池、新增补仓/提现金额下方动态提示千分位与中文万元折算 | M1 | P2 Item 7 |
| 5 | 高危覆写防误触与一键回滚 | Tab 1 步骤三覆盖写入增加 popover 确认门禁，覆写前自动存 Undo 快照，成功后提供一键回滚按钮 | M2 | P0 Item 2 |
| 6 | 首屏双翼跨 Tab 真路由与承接横幅 | components.html 注入 DOM 脚本触发真实 Tab 点击与滚动，补齐 6 类预警处置参数传递，渲染承接横幅 | M2 | P0 Item 3 |
| 7 | 机会雷达实时行情融合与四维证据链 | 注入实时指数行情，绑定实时资讯爬虫与本地缓存，晨报展示秒级时间戳与快讯，Top 3 卡片展示涨跌幅与四维得分 | M3 | P1 Item 6 |
| 8 | G8 专属测试套件与全量回归 | 编写 tests/test_g8_ux_and_realtime_fusion.py，回归全量 5 套测试并通过 4 大只读文件审计 | M4 | 验证要求 |
| 9 | 服务平滑重启与 /browser 视觉核验 | 终止旧进程，重启 8501 端口服务，调用 /browser 针对四大工作区进行端到端多模态走查 | M5 | 走查要求 |
| 10 | Git 归档打标 v3.8-G8 与 G9 指令生成 | git add -A, commit, tag v3.8-G8, push origin HEAD & tags (禁止 Release)，生成 G9 指令 | M5 | 归档要求 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Tab 2 物理视图真隔离、持仓表未保存保护、重复滑块清理与大额本金防错 | Features 1, 2, 3, 4 (`app_gui.py`) | none | IN_PROGRESS |
| M2 | 高危覆写防误触与一键回滚、首屏双翼跨 Tab 真路由与承接横幅 | Features 5, 6 (`app_gui.py`, `portfolio_manager.py`) | M1 | PLANNED |
| M3 | 机会雷达盘中实时行情融合、秒级快讯感知与四维评分证据链 | Feature 7 (`data_loader.py`, `advisory_engine.py`, `app_gui.py`) | M1, M2 | PLANNED |
| M4 | G8 专属针对性测试套件与全量自动化回归验证 | Feature 8 (`tests/test_g8_ux_and_realtime_fusion.py` + 全量测试) | M1, M2, M3 | PLANNED |
| M5 | 8501 服务平滑重启、/browser 视觉交互走查、Git 归档打标 v3.8-G8 与 G9 自举指令 | Features 9, 10 (全流程交付闭环) | M4 | PLANNED |

## Interface Contracts
### M1 ↔ M2: Tab 2 State Machine & Navigation Contract
- **File**: `AGY2_FundAdvisory/app_gui.py`
- **Contract**:
  - `is_t2_main_mode = tab2_view_mode.startswith("🎯")` controls main flow vs maintenance flow.
  - `# tab2_rebal_buf_slider_bot` comment is preserved for static test backward-compatibility.
  - `<b>{len(pm.holdings)} 只</b>` static string contract in dock_tab3 is preserved.
  - `format_chinese_amount(val: float) -> str` returns e.g. `"¥100,000.00 折合 10.00 万元"`.

### M2 ↔ M3: Cross-Tab Jump & Undo Snapshot Contract
- **File**: `AGY2_FundAdvisory/portfolio_manager.py` & `app_gui.py`
- **Contract**:
  - `pm._push_undo_snapshot()` captures current holdings, cash, and pending orders into `self.snapshot_stack` and SQLite `portfolio_snapshots`.
  - `pm.undo()` restores previous state without data loss.
  - `st.session_state["pending_cross_tab_jump"] = {"tab_index": int, "tab_name": str, "action_type": str, "target_code": str}` consumed by `components.html` and cleared on arrival.

### M3 ↔ M4: Real-Time Radar & 4D Evidence Contract
- **File**: `AGY2_FundAdvisory/advisory_engine.py` & `data_loader.py`
- **Contract**:
  - `DataLoader.fetch_realtime_market_news_and_catalysts(limit=20, timeout=2.0, cache_ttl_sec=60.0)` returns `List[Dict]` with keys: `title`, `time`, `url`, `source`, `sentiment`.
  - `OpportunityRadarEngine.scan_all_sectors()` / `evaluate_sector()` returns dict containing `core_logic`, `realtime_chg_pct`, `realtime_point`, and `sub_scores`: `{"valuation": float, "momentum": float, "kaufman_snr": float, "anti_crowding": float}`.

## Code Layout
- `AGY2_FundAdvisory/app_gui.py`: Tab 2 双视图物理分支、持仓表未保存保护、金额防错格式化、覆写 popover 门禁与撤销回滚按钮、跨 Tab DOM 脚本注入、晨报时间戳与 Top 3 四维卡片
- `AGY2_FundAdvisory/portfolio_manager.py`: `_push_undo_snapshot` 封装与 `apply_zero_start_blueprint` 前置快照压栈
- `AGY2_FundAdvisory/data_loader.py`: `DataLoader` 类挂载实时资讯爬虫与本地缓存兜底
- `AGY2_FundAdvisory/advisory_engine.py`: `OpportunityRadarEngine` 实时指数行情注入与四维子项得分透传
- `tests/`:
  - `test_infra.py`: 只读裁判测试基线（严禁修改）
  - `test_g8_ux_and_realtime_fusion.py`: G8 增量针对性测试套件
