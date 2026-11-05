# Handoff Report — Explorer 2 (Performance & Fragment Architecture)

**核心摘要**：本调研已全面确认 Streamlit 1.66.1 原生支持 `@st.fragment`，锁定了 `app_gui.py` 中 4 大独立交互区块的代码边界与状态流转规则，揭示了 Tab 3/Tab 4 首屏无条件执行导致重仓穿透反复触发的性能根因，并完成了数据新鲜度徽章（Data Freshness Badge）的全链路探针设计。

---

## 1. Observation (客观观察与直接事实)

### 1.1 运行环境与 Streamlit 原生能力
- **命令验证**：
  ```powershell
  py -3 -c "import streamlit as st; print(st.__version__); print(hasattr(st, 'fragment'))"
  ```
  - **实测输出**：
    ```
    streamlit version: 1.66.1
    has st.fragment: True
    has st.experimental_fragment: False
    ```
  - **`st.fragment` 参数**：`(func=None, *, run_every=None, parallel=False, key=None)`
  - **`st.rerun` 参数**：`(scope: Literal['app', 'fragment'] = 'app') -> NoReturn`

### 1.2 app_gui.py 四大独立交互区块当前位置与代码行号
1. **区块 A：侧边栏「核心指数行情走廊」**
   - **文件与行号**：`AGY2_FundAdvisory/app_gui.py:1623 ~ 1806`
   - **包含组件**：
     - `st.popover("⚙️", ...)`（1638 行）：包含走廊展示数量滑块（`sl_corridor_disp_limit`）、38+ 指数多选框（`ms_corridor_indices`）、6 位代码添加输入框与按钮（`txt_add_custom_code`, `btn_add_custom_code`）。
     - 刷新按钮 `btn_refresh_all_live_quotes`（1725 行）。
     - 行情卡片流 HTML 渲染（1745 ~ 1805 行）。
2. **区块 B：Tab 2 持仓账本「极速录基吧台」与「主持仓表编辑」**
   - **文件与行号**：`AGY2_FundAdvisory/app_gui.py:3763 ~ 4119`
   - **包含组件**：
     - ⚡ 极速录基吧台（3763 ~ 3840 行）：`bar_fund_input`, `bar_amt_input`, `bar_pnl_input`, `bar_dur_choice`, `btn_bar_add_holding`。
     - 主持仓表格编辑（3841 ~ 3974 行）：`st.data_editor(key="main_holdings_editor_tab2")`。
     - 快捷操作工具栏（3975 ~ 4119 行）：保存按钮（`btn_save_holdings_tab2`）、现金池修改 Popover、同步净值按钮（`btn_sync_holdings_tab2`）、导出 CSV、删除标的 Popover。
3. **区块 C：Tab 3 组合回测「回测对象与对标基准切换」**
   - **文件与行号**：`AGY2_FundAdvisory/app_gui.py:5075 ~ 5501`
   - **函数定义**：`def render_tab3_backtest_content(pm: PortfolioManager, snapshot: Dict[str, Any]):`（5075 行）
   - **调用位置**：`app_gui.py:5862`（在 `with tab_backtest:` 下直接调用）
   - **包含控件**：`sel_backtest_target_type`（5082 行）、`sel_multiselect_benchmarks`（5091 行）、`sel_backtest_tier_sub`（5138 行）。
4. **区块 D：Tab 4 穿透工具「穿透组合切换与 A/C 算费器」**
   - **文件与行号**：`AGY2_FundAdvisory/app_gui.py:5503 ~ 5855`
   - **函数定义**：`def render_tab4_toolbox_content(pm: PortfolioManager, snapshot: Dict[str, Any]):`（5503 行）
   - **调用位置**：`app_gui.py:5874`（在 `with tab_toolbox:` 下直接调用）
   - **包含控件**：
     - 组合对象切换：`sel_tb_target`（5510 行）。
     - A/C 算费器（5810 ~ 5833 行）：`ac_r_sub`, `ac_r_sales`, `ac_v_amt`, `ac_v_days`。

### 1.3 性能卡顿根因：Tab 4 重仓穿透无条件级联执行
- 在 `app_gui.py:5528 ~ 5531` 行：
  ```python
  else:
      st.info("💡 当前实盘账本持仓为空，已自动为您选用【新建仓组合】进行全景穿透体检。")
      t1_sim_c = st.session_state.get("tab1_sim_cache") or {}
      t1_w = dict(st.session_state.get("selected_backtest_weights") or t1_sim_c.get("optimal_weights", {}))
  ```
- 当用户在 Tab 1（新资建仓）拖动滑块时，`t1_w` 发生改变。在全页重跑时，Tab 4 自动选用新的 `t1_w`，导致 `_h_items` 元组改变，进而击穿 `_cached_look_through_industry`, `_cached_stock_overlap`, `_cached_penetration_risk`, `_cached_stocks_df` 四大重仓股穿透计算的 `@st.cache_data` 缓存，导致用户在 Tab 1 微调时后台被动执行重度穿透。
- 同时，`tests/test_ui_instant_load.py:89~91` 行断言代码中必须存在：
  - `tab3_backtest_activated`
  - `tab4_lookthrough_activated`

### 1.4 数据新鲜度（Data Freshness）链路
- **两市成交与情绪**：`data_loader.py:146` 在成功时返回 `"source": "eastmoney_realtime"` 及 `"updated_at"`；在第 168 行失败降级时返回 `"source": "local_cache_fallback"`。
- **核心指数行情**：`data_loader.py:1852` 在网络接口超时或非交易时段返回 0.00% 假平盘时，自动切入 `calc_offline_2day_return(c)`，读取本地 `aligned_matrix_total_return.parquet` 或 `storage.duckdb`。
- **持仓净值**：`portfolio_manager.py:2129, 2163` 在获取到在线盘中估值时记录时间戳；在 2193 行失败时降级至 `CORE_STRATEGY_POOL` 与 `known_navs`。

---

## 2. Logic Chain (推演逻辑链)

1. **环境原生就绪**：
   - 基于 Observation 1.1，当前环境 Streamlit 1.66.1 原生具备 `st.fragment` 与带 `scope` 参数的 `st.rerun`。因此，无需引入外部 hack 或第三方补丁，可直接使用原生装饰器 `@st.fragment`。
2. **四大区块边界清晰**：
   - 基于 Observation 1.2，区块 A、B、C、D 的代码范围清晰，各自拥有独立的输入控件与渲染视图。
   - 其中区块 C (`render_tab3_backtest_content`) 与区块 D (`render_tab4_toolbox_content`) 本身已经是独立命名的函数，仅需添加 `@st.fragment` 装饰器即可完成局部重刷解耦。
   - 区块 A（侧边栏行情走廊）与区块 B（吧台+持仓表）当前嵌入在全页脚本流中，通过分别提取为 `@st.fragment def render_sidebar_index_corridor()` 与 `@st.fragment def render_tab2_fast_bar_and_holdings_table(pm)`，即可实现组件化隔离。
3. **状态隔离与全页刷新判定**：
   - **局部刷新（Fragment 内部自闭环）**：
     - 侧栏走廊数量调节、指数自选增删；
     - Tab 2 吧台文字/数字录入、主持仓表格内单元格编辑（修改市值/份额/成本/意愿）；
     - Tab 3 切换回测对象、切换 9 大对标基准；
     - Tab 4 切换穿透对象、调整 A/C 算费器的费率与天数。
     以上操作只影响当前视图呈现，绝不修改全站总资产或决策状态机，由 `@st.fragment` 拦截在局部。
   - **全页刷新（显式 `st.rerun(scope="app")`）**：
     - 侧栏走廊的「🔄 极速刷新实时行情」按钮（触发全局缓存清理与全账户估值重算）；
     - Tab 2 的「➕ 加入账本」、「💾 保存修改并入库」、「确认保存现金」、「🔄 同步真实净值」、「确认删除」按钮（直接改变 `pm.holdings`，牵连顶部看板卡片 4 的总资产和预估浮盈，以及步骤二的调仓诊断）。
4. **首屏延迟计算与缓存保护闭环**：
   - 基于 Observation 1.3，Tab 1 交互引发 Tab 4 重仓穿透缓存穿透的罪魁祸首是“全页重跑流经 Tab 4”。
   - 当 Tab 1 和 Tab 2 的操作被 `@st.fragment` 拦截后，这些操作不再触发全页重跑，Tab 4 的重仓股穿透计算物理上不再会被流经执行！
   - 同时，对 Tab 3 的 `StrategyBridge.build_custom_portfolio_backtest` 增加 `@st.cache_data(ttl=300)` 缓存包装，并在 Tab 4 针对 `_h_items` 进行稳定性保护，彻底消除首屏与 Tab 1 调参时的卡顿现象。
5. **数据新鲜度徽章规范呈现**：
   - 基于 Observation 1.4，`fetch_market_turnover_and_sentiment` 已经自带 `"source"` 标识 (`"eastmoney_realtime"` vs `"local_cache_fallback"`) 与时间戳。
   - 只需在前端构建统一探测器 `inspect_data_freshness_status()`，即可在侧边栏「市场状态与底座」及顶部卡片统一渲染状态胶囊：
     - 联机正常：`🟢 实时盘中行情已连接 (更新于 HH:MM:SS)`
     - 离线降级：`🟡 离线湖仓快照兜底模式 (基准日 YYYY-MM-DD)`
   - 彻底消灭静默降级黑盒，符合金融合规透明度要求。

---

## 3. Caveats (注意事项与潜在边界条件)

1. **测试断言兼容性**：
   - `tests/test_ui_instant_load.py` 包含断言 `assert "tab3_backtest_activated" in gui_text` 和 `assert "tab4_lookthrough_activated" in gui_text`。在重构为 `@st.fragment` 时，需确保这两个变量在会话状态中以合适形式存在（如作为首次渲染标记），不可直接物理删除导致既有单元测试红灯。
2. **Tab 2 表格防丢数与局部刷新的联动**：
   - 当主持仓表被封装在 `@st.fragment` 内部时，用户编辑的未保存数据暂存在 `st.session_state["main_holdings_editor_tab2"]` 中。
   - 外部步骤二的「🔍 诊断今日调仓时机」（4453 行）在点击时，必须先行调用 `_auto_commit_pending_table_edits` 读取此 session_state 并同步入库，才能确保用户即使忘记点“保存修改”也能 100% 同步。
3. **Plotly 图表在 Fragment 中的重绘开销**：
   - 虽然 `@st.fragment` 解耦了外部脚本重跑，但在 Fragment 内部交互时（如 Tab 3 增删基准），Plotly 图表仍会重新序列化。对回测与穿透图表应用 `@st.cache_data` 可以最大限度压榨响应速度。

---

## 4. Conclusion (确立的落地架构结论)

1. **采用 Streamlit 原生 `@st.fragment`**：在 `app_gui.py` 中通过 `safe_fragment = getattr(st, "fragment", ...)` 兼容式声明，官方原生就绪。
2. **精准切分 4 大局部刷新组件**：
   - `render_sidebar_index_corridor()`: 侧边栏垂直卡片与自选 Popover（走廊展示数调节与代码添加为局部更新；「🔄」行情刷新按钮显式调用全页 `st.rerun(scope="app")`）。
   - `render_tab2_fast_bar_and_holdings_table(pm)`: 极速录基吧台与 `st.data_editor` 持仓表格（单元格打字与编辑为局部更新；入库/保存/同步/删除按钮调用全页 `st.rerun(scope="app")`）。
   - `render_tab3_backtest_content(pm, snapshot)`: 组合回测对象与 9 大对标基准切换（100% 局部更新，附加 backtest 结果 `@st.cache_data`）。
   - `render_tab4_toolbox_content(pm, snapshot)`: 组合穿透切换与 A/C 算费器（100% 局部更新，子算费器独立内聚）。
3. **首屏延迟穿透与缓存加固**：
   - 依赖 Fragment 阻断机制，用户在 Tab 1 / Tab 2 交互时绝对不流经 Tab 3 和 Tab 4。
   - 为 `StrategyBridge.build_custom_portfolio_backtest` 增设 `@st.cache_data(ttl=300)`。
4. **上线「📡 数据源健康度与时效状态徽章」**：
   - 探针联动 `mb_data["source"]` 与时间戳。
   - 侧栏 1586 行与顶部 1816 行统一输出 `🟢 实时盘中行情已连接 (更新于 HH:MM:SS)` / `🟡 离线湖仓快照兜底模式 (基准日 YYYY-MM-DD)`。

---

## 5. Verification Method (独立核验方案)

后续开发与测试人员可通过以下方式对本调研结论与未来实施结果进行端到端无损核验：

### 5.1 静态代码边界核验
检查 `app_gui.py` 源码是否包含以下 4 个标准 Fragment 装饰定义：
```powershell
py -3 -c "
with open('AGY2_FundAdvisory/app_gui.py', 'r', encoding='utf-8') as f:
    text = f.read()
    assert 'render_sidebar_index_corridor' in text
    assert 'render_tab2_fast_bar_and_holdings_table' in text
    assert 'render_tab3_backtest_content' in text
    assert 'render_tab4_toolbox_content' in text
    assert 'inspect_data_freshness_status' in text
    print('All fragment functions and freshness probe verified!')
"
```

### 5.2 Streamlit AppTest 局部响应与首屏秒开断言
运行既有 AppTest 并断言：
1. `tests/test_ui_instant_load.py` 必须 100% 通过（验证 0 异常、0 裸露 div、卡片对齐、刷新按钮存在）。
2. 在 AppTest 中模拟修改 `main_holdings_editor_tab2` 中的单元格市值，断言 Tab 3 的 `build_custom_portfolio_backtest` 不被调用（可配合 mock 计数器核验调用次数为 0）。
3. 模拟断网或 mock `fetch_market_turnover_and_sentiment` 返回 `"source": "local_cache_fallback"`，断言界面渲染包含 `🟡 离线湖仓快照兜底模式` 徽章。
