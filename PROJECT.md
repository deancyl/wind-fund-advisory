# Project: Wind G22 世代外科手术式精准修复与 AST 静态调用图门禁闭环

## Architecture
- **展示与交互层 (`app_gui.py`)**:
  - Tab 2 六大快捷操作功能完整真实后端接线（截图导入 OCR、极速录基、批量导入、撤销修改、同步估值、账本管理）。
  - Tab 2 五处断链与属性幻觉精准修复（深套判定 `floating_pnl_pct`、备忘录方法 `generate_chief_advisor_memo`、动态目标权重 `compute_dynamic_tier_weights`、场景模式 `rad_tab2_scenario_mode`、微观滑点 `calculate_vwap_execution_slippage` 与 8 维锁仓判断）。
  - 十五段文字墙收拢折叠抽屉 `st.expander(..., expanded=False)` 与胶囊副标题自然折行样式。
  - 修复第 6470 行隐蔽属性幻觉：`pm.evaluate_rebalance_audit()`。
- **数据与决策层 (`data_loader.py`, `advisory_engine.py`, `strategy_bridge.py`, `portfolio_manager.py`)**:
  - USD/CNH 汇率合理区间 `[6.85, 7.60]` 与校准基线 `7.2385`。
  - 10 年期美债收益率合理区间 `[3.0, 6.0]` 与校准基线 `4.4200`（中美利差 `-278.2 bp`）。
  - 宏观、国际、病灶三段式因果链根据 ERP 分位、利差倒挂深度、风险档位 tier 与持仓病灶数动态分支生成。
- **测试与门禁层 (`tests/`, `scripts/verify_g22_ast_gate.py`)**:
  - 14 个核心 Python 文件 `ast.parse` 静态编译零语法错误。
  - AST 静态调用图与属性反射契约门禁：`pm` 与 `mlm_inst` 零属性幻觉，6 大禁用词彻底清除，7 大必选调用全部实装。
  - 修复 `tests/test_g19_m1_ten_dimension_and_memo.py` 中过期断言为区间断言。
  - 桌面与手机端双视口浏览器实盘验收。
  - Git 打标 `v5.2-G22` 推送与严格无冒号、无嵌套代码块 G23 交付指令。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Tab 2 截图导入弹窗真实接线 | 支持 png/jpg/jpeg/webp，调用 pm.parse_screenshot_ocr_holdings 切片 OCR，展示可编辑预览表，提供覆盖与追加按钮 | M1 | ORIGINAL_REQUEST §二.1 |
| 2 | Tab 2 极速录基弹窗真实接线 | 模糊匹配与目录检索，fetch_realtime_fund_quote 拉取净值反算份额成本，五档持有期映射，调用 pm.add_or_update_holding | M1 | ORIGINAL_REQUEST §二.2 |
| 3 | Tab 2 批量导入弹窗真实接线 | 调用 pm.parse_smart_text_holdings 智能解析，调用 pm.import_from_smart_text 与 save_state | M1 | ORIGINAL_REQUEST §二.3 |
| 4 | Tab 2 撤销修改按钮真实接线 | 调用 pm.undo() 与 pm.save_state() 回退至上一快照状态 | M1 | ORIGINAL_REQUEST §二.4 |
| 5 | Tab 2 同步估值按钮真实接线 | 调用 pm.sync_holdings_live_nav(use_intraday_gsz=True) 同步全部持仓最新估值 | M1 | ORIGINAL_REQUEST §二.5 |
| 6 | Tab 2 账本管理新建参数修复 | 使用 mlm_inst.create_ledger 真实参数 default_tier 与 base_cash | M1 | ORIGINAL_REQUEST §二.6 |
| 7 | Tab 2 顶栏深套出血点属性修复 | 使用 floating_pnl_pct 判定 < -10.0，使 29 真实持仓准确显示 18 只深套 | M1 | ORIGINAL_REQUEST §三.1 |
| 8 | 首席投顾备忘录兜底函数修复 | 修正为 advisory_engine.generate_chief_advisor_memo | M1 | ORIGINAL_REQUEST §三.2 |
| 9 | 动态大类目标权重非空修复 | 调用 StrategyBridge.compute_dynamic_tier_weights 获取真实目标权重 | M1 | ORIGINAL_REQUEST §三.3 |
| 10 | 一键清扫尾仓 session_state 键名一致 | 统一读取 rad_tab2_scenario_mode | M1 | ORIGINAL_REQUEST §三.4 |
| 11 | 微观滑点精算与锁仓分支恢复 | 彻底删除 1.2 bps，调用 calculate_vwap_execution_slippage 精算，实装 8 维锁仓分支 | M1 | ORIGINAL_REQUEST §三.5 |
| 12 | 第 6470 行隐蔽属性幻觉修复 | 修正 pm.audit_rebalance_vs_shadow_baseline 为 pm.evaluate_rebalance_audit | M1 | Survey 1 & 3 发现 |
| 13 | 十五段文字墙收拢折叠抽屉 | render_causal_intelligence_card 使用 st.expander 默认收起 (expanded=False) | M1 | ORIGINAL_REQUEST §四.1 |
| 14 | 胶囊副标题样式优化 | .chief-memo-capsule-sub 允许最多两行自然折行展示 | M1 | ORIGINAL_REQUEST §四.2 |
| 15 | 汇率与美债校准值恢复 | data_loader, advisory_engine, strategy_bridge, portfolio_manager 恢复 7.2385 与 4.4200，动态因果链 | M1 | ORIGINAL_REQUEST §五.1 |
| 16 | tests 目录下过期断言更新 | 更新 test_g19_m1_ten_dimension_and_memo.py 为区间断言 [6.85, 7.60] 与 [3.0, 6.0] | M1 | ORIGINAL_REQUEST §五.2 |
| 17 | AST 静态调用图与契约门禁验证 | 编写并运行 scripts/verify_g22_ast_gate.py，14 文件语法、属性、禁用词、必选调用 100% 通过 | M2 | ORIGINAL_REQUEST §六.1 |
| 18 | 8501 重启与双视口实盘验收 | 重启服务，/browser 桌面与手机端截图核验四大核心事实 | M2 | ORIGINAL_REQUEST §六.2 |
| 19 | 文档沉淀、Git 打标推送与 G23 输出 | 更新 GEMINI.md, PROGRESS_LOG.md，git tag -a v5.2-G22 并 push，无冒号无嵌套严格输出 G23 指令 | M2 | ORIGINAL_REQUEST §六.3, 六.4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 前端接线、数据断链修复与汇率校准 | Features 1-16 (app_gui.py, data_loader.py, advisory_engine.py, strategy_bridge.py, portfolio_manager.py, tests/) | none | DONE |
| M2 | AST 门禁核验、双视口实盘验收与 G22 发布交付 | Features 17-19 (verify_g22_ast_gate.py, app restart, browser tests, docs, git tag, G23 output) | M1 | IN_PROGRESS |

## Interface Contracts
### app_gui.py ↔ portfolio_manager.py
- `pm.parse_screenshot_ocr_holdings(image_bytes: bytes) -> List[Dict[str, Any]]`: OCR 解析返回持仓字典列表。
- `pm.import_from_smart_text(text: list, replace_existing: bool) -> Dict[str, Any]`: 批量/OCR 持仓入库，支持覆盖与追加。
- `pm.add_or_update_holding(fund_code: str, shares: float, nav: float, cost_price: float, holding_days: int, notes: str)`: 极速录基录入。
- `pm.parse_smart_text_holdings(text: str) -> List[Dict[str, Any]]`: 智能解析文本持仓。
- `pm.undo() -> bool`: 回退至上一持仓快照。
- `pm.sync_holdings_live_nav(use_intraday_gsz: bool = True) -> Dict[str, Any]`: 同步全量基金最新净值与估值。
- `pm.evaluate_rebalance_audit() -> Dict[str, Any]`: 调仓 Brinson 归因审计。

### app_gui.py ↔ multi_ledger_manager.py
- `mlm_inst.create_ledger(name: str, base_cash: float, ledger_type: str, default_tier: str) -> str`: 创建新账本。

### app_gui.py ↔ advisory_engine.py & strategy_bridge.py
- `advisory_engine.generate_chief_advisor_memo(...) -> dict`: 首席投顾备忘录。
- `StrategyBridge.compute_dynamic_tier_weights(tier: str, market_snapshot: dict) -> dict`: 动态大类目标权重字典。
- `SmartExecutionDCAEngine.calculate_vwap_execution_slippage(...) -> dict`: 动态微观滑点精算。

## Code Layout
- `AGY2_FundAdvisory/`
  - `app_gui.py`: Streamlit 交互大屏、Tab 2 操作栏与调仓建议单、折叠抽屉与全局样式
  - `data_loader.py`: 数据加载器、离岸汇率与美债基线校准
  - `advisory_engine.py`: 投顾决策、动态因果链、SmartExecutionDCAEngine
  - `strategy_bridge.py`: 策略桥接、动态大类权重测算
  - `portfolio_manager.py`: 账本管理器、持仓数据结构与快照
- `tests/`
  - `test_infra.py` [只读神圣]
  - `test_g19_m1_ten_dimension_and_memo.py` [更新区间断言]
- `scripts/`
  - `verify_g22_ast_gate.py` [AST 静态调用图与反射契约终极门禁脚本]
