# Explorer G8-3 Handoff Report (交接报告)

**Agent**: Explorer G8-3 (Real-Time Radar & Test Explorer)  
**Parent Orchestrator ID**: `9e61e1d7-9eb6-4227-b899-75a22db1e25b`  
**Handoff Type**: Hard (Task Complete)  
**Date**: 2026-11-07  

---

## 1. Observation (客观观察)

直接代码审查与文件核验的具体事实与行号如下：

1. **只读裁判文件与核心签名保留**:
   - `AGY2_FundAdvisory/judge_engine.py`: 844 行，文件完好，包含 AST 静态扫描 `compute_ast_hash` (第 34 行) 与 `scan_ast_for_calendar_cheating` (第 58 行)。
   - `AGY2_FundAdvisory/holdout_vault.py`: 162 行，文件完好，包含 `HoldoutVaultExhaustedError` (第 22 行) 与 3 次熔断计数锁。
   - `AGY2_FundAdvisory/AGENT_SPEC.md`: 110 行，定义 50/50 基准、6 大风格切片与 4 大门禁标准。
   - `tests/test_infra.py`: 251 行，包含 11 个关键单元测试，验证对齐矩阵、T+1、7 天锁定期扣费等。
   - `AGY2_FundAdvisory/data_loader.py` 第 1354 至 1362 行：
     ```python
     @staticmethod
     def simulate_execution(
         weights_df: pd.DataFrame,
         prices_df: pd.DataFrame,
         is_otc: bool = True,
         penalty_days: int = 7,
         penalty_rate: float = 0.015,
         etf_impact: float = 0.001
     ) -> pd.DataFrame:
     ```
     默认参数与阶梯赎回扣费逻辑完全满足规范，持有天数 $< 7$ 天严格扣除 1.50% 惩罚费。

2. **实时资讯与宏观脉搏感知引擎 (`data_loader.py`)**:
   - 第 205 至 224 行：已定义 14 大赛道分类映射 `SECTOR_KEYWORD_RULES`、宏观关键词 `MACRO_KEYWORDS`、大盘关键词 `MARKET_KEYWORDS`。
   - 第 247 至 432 行：实装了 `fetch_realtime_market_news_and_catalysts(limit=20, timeout=2.0, force_refresh=False, cache_ttl_sec=60.0)`，具备东财 7x24 全球快讯与新浪财经双轨接口、2 秒超时约束、内存高速缓存 (TTL 60s)、磁盘持久化快照 (`data/cache/realtime_news.json`) 及冷启动离线保底。
   - 第 1961 至 2178 行：实装了 `fetch_custom_realtime_indices` 与 `fetch_batch_realtime_indices`，基于东财 push2 批量接口、新浪备用接口与本地 parquet 双日收盘真实涨跌幅计算 `calc_offline_2day_return`，彻底杜绝 0.00% 假平盘。
   - 第 865 至 868 行：`DataLoader` 类目前仅将 `denoise_covariance_matrix`、`fetch_market_turnover_and_sentiment`、`fetch_or_calc_index_valuations` 绑定为 staticmethod，未显式绑定 `fetch_realtime_market_news_and_catalysts` 与 `fetch_custom_realtime_indices`。

3. **机会雷达与 14 大赛道量化指标 (`advisory_engine.py`)**:
   - 第 26 至 225 行：`RADAR_SECTOR_CATALOG` 完整定义了 14 大核心赛道元数据，每个赛道均已包含精炼的入选依据文本 `core_logic`（例如：红利低波为 `"精选高股息低波动标的，防御属性与股息分红双重安全边际"`）。
   - 第 637 至 787 行：`OpportunityRadarEngine._calc_dynamic_sector_metrics()` 从本地 Parquet/DuckDB 日线提取序列 $s$，计算 `er_20`, `bias_20`, `slope_20`, `crowding_score`。当前逻辑未显式接入当日盘中实时行情点位 $P_{\text{rt}}$，导致盘中急涨急跌时乖离率与动量未能实时自适应响应。
   - 第 927 至 1003 行：`evaluate_sector()` 计算四维得分（`s_val`, `s_mom`, `s_er`, `s_crowd`）与总分，但返回值未携带 `core_logic`，也未携带当日盘中实时涨跌幅 `realtime_chg_pct` 与点位 `realtime_point`。

4. **首屏晨报与 Top 3 赛道卡片前端渲染 (`app_gui.py`)**:
   - 第 2468 至 2478 行：`pulse_card_html` 仅展示静态标签 `"全景量化串联 ｜ 历史拐点并列对照"` 与文字 `pulse_brief`，缺失秒级数据感知时间戳（如 `数据感知时间: 2026-11-07 15:30:00`）与最新快讯摘要条。
   - 第 2486 至 2502 行：Top 3 赛道卡片目前仅渲染赛道名称、标签、综合得分、估值分位与优选基金代码名称，缺失当日实时涨跌幅胶囊（如 `盘中 +1.80%`）、四维子项得分明细（估/动/噪/拥）及入选核心逻辑依据。

5. **Tab 2 视图模式隔离与未保存修改保护现状 (`app_gui.py`)**:
   - 第 4204 至 4213 行：`rad_tab2_view_mode` 切换主流程与工具坞；
   - 第 4649 行：`with st.expander("🛠️ 账本工具坞...", expanded=(not is_t2_main_mode or not has_holdings)):` 在主流程下仍然渲染了该折叠框，且当空仓时强制展开，与主流程模式冲突；
   - 第 5053、5079 行：`btn_tab2_diagnose` 与 `btn_tab2_all` 在工具坞模式下依然暴露，但下游步骤二三被 `is_t2_main_mode` 截断，造成点击无反应；
   - 第 4581 行保存按钮下方，第 4612 行 `"🔄 同步真实净值"` 与第 4603 行修改现金池未检测 `edited_table` 未提交修改，点击直接 `st.rerun()` 冲刷丢数；
   - 第 3837 行：覆盖写入当前激活账本按钮直接调用 `pm.apply_zero_start_blueprint()`，无二次确认弹窗门禁，且清空前未强制保存 Undo 快照，一旦误触无法回滚。

6. **现有测试资产覆盖**:
   - `tests/test_infra.py` (251 行)
   - `tests/test_adv_final_closure.py` (466 行)
   - `tests/test_g3_evolution_loop.py` (638 行)
   - `tests/test_gui_multi_ledger_stress.py` (573 行)
   - `tests/test_g7_architecture_and_decoupling.py` (121 行)

---

## 2. Logic Chain (推理链条)

1. **由 Observation 2 与 3 推导实时行情与快讯证据链打通机制**:
   - `data_loader.py` 已具备健壮的 `fetch_realtime_market_news_and_catalysts` 与 `fetch_custom_realtime_indices`，底层数据源与缓存完备；
   - `OpportunityRadarEngine` 需要在 `scan_all_sectors` 或 `_calc_dynamic_sector_metrics` 中调用这些接口，将盘中实时点位注入价格序列末端，动态计算盘中实时乖离率与动量反超买惩罚；
   - 将 `RADAR_SECTOR_CATALOG` 中的 `core_logic` 与实时行情字段透传至 `evaluate_sector` 的返回值字典中，为前端呈现提供 100% 完备的数据支撑。

2. **由 Observation 4 推导前端 UI/UX 呈现升级**:
   - 首屏晨报在右上角展示 `⏱️ 数据感知时间: {news_ts}`，并在正文下方追加 `⚡ 实时快讯: {news_title} [{news_time}]`，满足秒级时效感知需求；
   - Top 3 赛道卡片在赛道名称右侧展示带红涨绿跌色彩的 `盘中 {realtime_chg_pct:+.2f}%` 胶囊，在中间紧凑呈现四维得分微徽章（估值/动量/信噪比/反拥挤），在底部以浅色注释展示 `💡 入选逻辑: {core_logic}`，彻底打通买方投顾证据链。

3. **由 Observation 5 推导 Tab 2 视图物理隔离与金融级防错护栏**:
   - 当 `is_t2_main_mode` 为 True 时，通过条件分支彻底移除底部的 6-dock Expander；
   - 当 `is_t2_main_mode` 为 False 时，直接平铺展示 6 大运维 Tabs，并隐藏持仓大表与调仓步骤二三；
   - 在 `btn_tab2_diagnose` 与 `btn_tab2_all` 回调中将 `tab2_view_mode` 自愈切回主流程；
   - 在表格上方展示未保存提醒，并在同步净值与修改现金前自动前置执行 `_commit_edited_holdings_table(edited_table, pm)`；
   - 将覆盖写入当前激活账本升级为 `st.popover` 二次确认弹窗，并在覆盖前调用 `pm.save_state(record_snapshot=True)` 留存 Undo 历史快照，并在覆写成功横幅旁提供一键回滚按钮。

4. **由 Observation 1 与 6 推导测试架构设计**:
   - 现有的 `test_infra.py` 等测试套件已建立严格的基建门禁，但缺少对 G8 世代新增特性的针对性断言；
   - 必须设计专属测试套件 `tests/test_g8_ux_and_realtime_fusion.py`，覆盖 Tab 2 物理分支隔离、未保存修改自动提交、盘中实时雷达行情融合与四维证据链、大额本金中文数量级防错、覆盖写入 Undo 回滚及只读契约，形成自动化质量闭环。

---

## 3. Caveats (注意事项与局限说明)

1. **网络超时降级策略**: 东方财富与新浪快讯及行情接口受公网网络状况影响。测试中如遇离线无网环境，代码必须无缝降级至本地 `data/cache/realtime_news.json` 磁盘快照或冷启动保底，测试断言应同时兼容真实网络返回与离线保底数据结构。
2. **只读约束绝对遵守**: 本次调研严格遵循只读原则，未对任何源码进行修改，未执行任何构建与测试命令。实现阶段必须严禁修改四个只读裁判文件与 `DataLoader.simulate_execution` 扣费签名。
3. **Streamlit 运行态上下文**: 部分 UI 控件逻辑（如 `st.popover`, `st.radio`）依赖 Streamlit 会话上下文，测试设计应兼顾纯后端逻辑单元测试（函数级/方法级）与静态源码 AST/正则契约断言，确保在 CI/命令行纯 Python 环境下亦能稳定 100% 绿灯运行。

---

## 4. Conclusion (调查结论与建议行动)

1. **Item 6 (P1) 方案完备可立即实施**:
   - `data_loader.py`: 将现有 `fetch_realtime_market_news_and_catalysts` 挂载至 `DataLoader` 类；
   - `advisory_engine.py`: 在 `OpportunityRadarEngine` 中注入实时指数行情，完善 `evaluate_sector` 输出字段（`realtime_chg_pct`, `realtime_point`, `core_logic`, `sub_scores`）；
   - `app_gui.py`: 在首屏晨报与 Top 3 卡片渲染中融入秒级时间戳、快讯摘要、实时涨跌幅、四维得分拆解与推荐逻辑。
2. **Tab 2 双视图模式与交易防错护栏路径清晰**:
   - 调整 `app_gui.py` 分支缩进，严格实现 `is_t2_main_mode` 的平铺与隐藏隔离；
   - 增加未提交修改比对与动作前置 Commit；
   - 增加覆盖写入二次确认、Undo 快照保存与回滚按钮；
   - 增加 `format_chinese_amount_hint` 大额本金中文数量级防错提示。
3. **G8 测试架构已设计就绪**:
   - 编制专属测试文件 `tests/test_g8_ux_and_realtime_fusion.py`，涵盖 6 大测试用例，提供全生命周期的自动化护栏。

---

## 5. Verification Method (独立核验方法)

后续实施 Agent 或测试 Agent 可通过以下具体步骤独立核验：

1. **静态代码与契约检查**:
   ```powershell
   # 检查只读裁判文件未被篡改
   git diff AGY2_FundAdvisory/judge_engine.py
   git diff AGY2_FundAdvisory/holdout_vault.py
   git diff AGY2_FundAdvisory/AGENT_SPEC.md
   git diff tests/test_infra.py
   ```
2. **基建单元测试全量回归**:
   ```powershell
   pytest tests/test_infra.py
   pytest tests/test_adv_final_closure.py
   pytest tests/test_g3_evolution_loop.py
   pytest tests/test_gui_multi_ledger_stress.py
   pytest tests/test_g7_architecture_and_decoupling.py
   ```
3. **G8 专项测试套件执行**:
   ```powershell
   pytest tests/test_g8_ux_and_realtime_fusion.py -v
   ```
4. **失效条件 (Invalidation Conditions)**:
   - 若 `simulate_execution` 扣费逻辑发生变动或 `test_infra.py` 报错，则当前整改无效；
   - 若 `OpportunityRadarEngine.scan_all_sectors()` 未输出 `realtime_chg_pct` 或 `core_logic`，则 Item 6 未闭环；
   - 若在 `is_t2_main_mode == True` 时页面依然渲染底部 6-dock 工具坞，则 Tab 2 视图物理隔离未达成；
   - 若在持仓表格修改份额后点击“同步真实净值”导致修改丢失，则防错拦截失效。

---
*交接报告编写完毕，详细技术调研文档已同步归档至 `.agents/teamwork/explorer_g8_3/analysis.md`。*
