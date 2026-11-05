# Handoff Report — Explorer 3 (UI/UX, NAV Tracking & Verification)

## 1. Observation (客观观察事实)

### 观察事实 1.1：首屏双翼智能投顾看板高度占用与折叠缺失
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **代码位置**：第 1978 ~ 2248 行
- **直接引用**：
  ```python
  1978: with st.expander("🔭 全市场机会雷达 ｜ 🚨 主动风险预警哨 (双翼智能投顾看板)", expanded=True):
  1979:     col_radar, col_sentry = st.columns([6.2, 3.8])
  ...
  2099:     with st.container(height=300):
  ...
  2247: render_dual_wing_advisory_dashboard(pm, snapshot)
  2248: 
  2249: # -------------------------------------------------------------
  2250: # 核心四大工作区 (精简 ≤ 5 字符，彻底砍掉独立 Tab 5)
  2251: # -------------------------------------------------------------
  2252: tab_zero_start, tab_holdings_and_rebalance, tab_backtest, tab_toolbox = st.tabs([
  ```
- **现象**：`expanded=True` 写死，内含高度 300px 的哨兵滚动容器 + Top 3 机会赛道卡 + 脉搏卡 + 14 赛道总表折叠框，整体占据首屏垂直高度超过 450px；四大主工作区 Tab 被压迫至屏幕下半屏；折叠时外部没有常驻关键信息，变为黑盒。

### 观察事实 1.2：Tab 2 st.data_editor 修改与诊断/调仓脱钩导致的丢数缺陷
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **代码位置**：第 3878 ~ 4071 行，第 4453 行，第 4476 行
- **直接引用**：
  ```python
  3878: edited_table = st.data_editor(
  ...
  3978:     if st.button("💾 保存修改并入库", type="primary", use_container_width=True, key="btn_save_holdings_tab2"):
  ... # 入库并调用 pm.add_or_update_holding, st.rerun()
  4453:     if st.button("🔍 诊断今日调仓时机", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
  4454:         st.session_state.tab2_diagnosed = True
  4455:         st.session_state.tab2_trigger_diagnose = True
  4456:         st.rerun()
  ...
  4476:     if st.button("🚀 一键执行全案", type="secondary", use_container_width=True, key="btn_tab2_all"):
  4477:         st.session_state.tab2_diagnosed = True
  4478:         st.session_state.tab2_rebalanced = True
  4479:         st.session_state.tab2_trigger_diagnose = True
  4480:         st.session_state.tab2_trigger_rebalance = True
  4481:         st.rerun()
  ```
- **现象**：用户在 `st.data_editor` 编辑数值后，若直接点击“诊断今日调仓时机”或“一键执行全案”，未执行 `_commit_holdings` 就直接 `st.rerun()`，导致前端已编辑的 DataFrame 被 `pm.export_snapshot_df()` 重新生成的内容无情冲刷覆盖，用户修改丢失率 100%。

### 观察事实 1.3：账本历史净值记账时间序列缺失与调仓跟单断环
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 及 `app_gui.py`
- **代码位置**：
  * `portfolio_manager.py` 第 2433 ~ 2452 行 (`PortfolioManager.__init__`)
  * `portfolio_manager.py` 第 2739 ~ 2830 行 (`save_state`)
  * `portfolio_manager.py` 第 2956 ~ 3020 行 (`_export_state_dict` / `_import_state_dict`)
  * `app_gui.py` 第 4310 ~ 4320 行 (`dock_tab3` 账本环境与实盘档案)
  * `app_gui.py` 第 5018 ~ 5067 行 (步骤三调仓执行单底部)
- **直接引用**：
  ```python
  2968: return {
  2969:     "version": "AGY2_PORTFOLIO_V2",
  2970:     "takeover_mode": self.takeover_mode,
  2971:     "baseline_date": self.baseline_date,
  ...
  2988:     "staged_batch_plans": copy.deepcopy(self.staged_batch_plans),
  2989:     "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  2990: }
  ```
- **现象**：
  1. `PortfolioManager` 没有维护 `nav_history` 列表，`portfolio_ledger.json` 中不存在历史净值时间序列。
  2. `dock_tab3` 仅展示静态文本统计，缺乏走势图。
  3. 步骤三底部仅有“保存明日预案”、“立即执行调仓（在途单）”、“送入回测对比”，缺乏买方投顾用户在手机端下单后的“一键将调仓单同步至当前账本持仓”直达按钮。

### 观察事实 1.4：金融事实错误与违规术语残留
- **文件路径**：
  * `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` 第 29 ~ 31 行：
    ```python
    26: "dividend_low_vol": {
    27:     "sector_id": "dividend_low_vol",
    28:     "name": "红利低波",
    29:     "benchmark_index": "000978",
    30:     "symbol": "H30269",
    31:     "index_code": "000978",
    ```
    （`000978` 实为中证医药100指数，严重张冠李戴）。
  * `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 2728, 2736 行：
    ```python
    2728: 保本率 <b>{_no_loss:.0f}%</b> ｜ 跑赢货基 <b>{_beat_cash:.0f}%</b>
    2736: - **保本率 (收益 $\ge 0\%$)**：持有期满本金不亏损的概率。
    ```
    （含有证监会合规明令禁止的“保本”词汇）。
  * `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 528 ~ 538 行：
    `050025`（博时标普500ETF联接A）标为 `"confirm_cycle": "T+1", "arrive_cycle": "T+4"`，且未在同公司转换中被排除。

---

## 2. Logic Chain (推理链条)

1. **首屏视觉提权推理**：
   - 依赖观察 1.1：`render_dual_wing_advisory_dashboard` 占据 450px+ 且无常驻紧凑摘要。
   - 推导：若将今日脉搏短语（$\le 40$ 字）、Top 3 机会赛道胶囊与风险哨巡检徽章提取为一个常驻单行高密度条，并在风控全通时默认折叠详情，则首屏四大主工作区 Tab 将即刻上提 450px，完全进入首屏最佳黄金视区，同时用户不会丢失核心市场脉搏与风控感知。

2. **表格防丢数自动保存推理**：
   - 依赖观察 1.2：`st.data_editor` 的返回值只保存在瞬态变量 `edited_table` 中，而下游按钮未前置入库即重刷页面。
   - 推导：通过将入库代码抽象为 `_commit_holdings_from_table(edited_table, pm)`，并在检测到表格与 `pm.holdings` 存在 diff 时自动在前台显示温馨提示，同时在“保存”、“诊断”、“执行全案”三个按钮触发时无感先执行 commit，可实现 100% 物理防丢数。

3. **实盘净值记账与跟单闭环推理**：
   - 依赖观察 1.3：实盘账本仅有单点截面，缺乏曲线闭环与手机端下单后的确认链路。
   - 推导：在 `PortfolioManager` 中注入 `nav_history` 记录，由 `save_state(record_snapshot=True)` 与 `sync_holdings_live_nav` 自动推进日度点位；并在 `dock_tab3` 绘制 Plotly 净值 vs 沪深300走势图；在步骤三底部加入「✅ 我已在手机端按此方案下单 -> 一键将调仓单同步至当前账本持仓」，即可实现从“看建议”到“记实盘账本”的完整投后闭环。

4. **合规与交付验证基线推理**：
   - 依赖观察 1.4：代码中存在红利低波误标医药 000978、违规使用“保本率”、以及 QDII 规则不精确问题。
   - 推导：必须建立 4 组严格的 pytest 自动化断言（红利低波 H30269、全站零“保本率”、QDII 规则精准、AppTest 4 Tab 渲染 0 异常），作为交付铁门禁。

---

## 3. Caveats (局限与前提假设)

1. **只读约束**：本探查员遵循只读铁律，未对任何源码或裁判文件（`tests/test_infra.py` 等）执行写操作，也未自行运行测试。
2. **时钟边界**：在 15:00 盘后时段或周末非交易日测试时，AppTest 与交割日期推算依赖 `trading_clock_fee.py` 的节假日日历。
3. **Plotly 主题联动**：绘制实盘净值曲线时，需调用现有的 `apply_theme_to_plotly_figure`，以适配用户可能切换的浅色/深色主题。

---

## 4. Conclusion (结论与建议行动方案)

1. **首屏视觉提权**：在 `app_gui.py` 的 `render_dual_wing_advisory_dashboard` 前置渲染紧凑单行导航条（脉搏 + Top 3 赛道胶囊 + 风控徽章），并将展开卡片容器改为默认受控折叠（风控全通默认折叠，有警报默认展开，支持用户自由一键折叠/展开）。
2. **Tab 2 表格防丢数**：编写 `_detect_table_diffs` 与 `_commit_holdings_from_table`，在表格上方显示未保存修改提示，并在“保存”、“诊断”、“一键执行全案” 3 处统一自动前置调用。
3. **实盘净值记账**：在 `portfolio_manager.py` 的 `PortfolioManager` 中增补 `nav_history`，落盘于 JSON 与状态字典；在 `dock_tab3` 绘制累计净值 vs 沪深300走势图；在步骤三底部提供「我已在手机端按此方案下单 -> 一键将调仓单同步至当前账本持仓」按钮。
4. **合规修正与测试**：红利低波指数代码修正为 `H30269`；全站“保本率”替换为“正收益概率 (≥0%)”或“本金安全率”；QDII 基金交割标识为 T+2 确认/T+6+ 到账且排除同公司 T+1 转换；新增针对性测试并确保 AppTest 4 Tab 0 异常。

---

## 5. Verification Method (独立核验方法)

1. **红利低波指数验证**：
   - 检查 `AGY2_FundAdvisory/advisory_engine.py` 第 29 行，核验 `RADAR_SECTOR_CATALOG["dividend_low_vol"]["benchmark_index"] == "H30269"` 且不为 `000978`。
2. **合规词汇静态核验**：
   - 检查 `AGY2_FundAdvisory/app_gui.py` 第 2728, 2736 行，确认“保本率”已被替换为“正收益概率 (≥0%)”或“本金安全率”。
3. **QDII 规则核验**：
   - 检查 `AGY2_FundAdvisory/portfolio_manager.py` 中 `050025` 元数据 `confirm_cycle == "T+2"`, `arrive_cycle == "T+6"`，并在同公司转换候选列表筛选中确认排除 QDII 基金。
4. **自动化测试执行指令**（供后续交付角色运行）：
   - `py -3 -m pytest tests/test_infra.py -v`（裁判基建回归测试，必须 100% 通过且不得修改）
   - `py -3 -m pytest tests/test_streamlit_apptest_run.py -v`（Streamlit AppTest 全量渲染测试）
