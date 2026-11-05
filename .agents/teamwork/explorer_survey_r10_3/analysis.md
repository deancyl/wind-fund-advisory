# 技术深度调研报告：UI/UX 体验治理、实盘净值记账闭环与交付验证基线 (Explorer 3)

## 一、 首屏视觉提权：双翼智能投顾看板精简摘要条与折叠交互设计

### 1. 现有代码结构与视觉痛点诊断
- **文件位置**：`AGY2_FundAdvisory/app_gui.py` 第 1971 ~ 2248 行 (`def render_dual_wing_advisory_dashboard(pm_instance, snapshot_dict)`)。
- **痛点分析**：
  1. 当前看板使用 `with st.expander("🔭 全市场机会雷达 ｜ 🚨 主动风险预警哨 (双翼智能投顾看板)", expanded=True):`。
  2. 默认 `expanded=True` 强制完全展开，内部包含左翼（今日脉搏卡片 + Top 3 机会赛道卡 + 14 赛道温度计总表折叠框）与右翼（主动风险哨 300px 高度容器 + 各种处置按钮）。
  3. 整体占据垂直高度超过 450px~550px，导致下方核心四大主工作区（【🌱 新资建仓 / 💼 持仓调仓 / 📈 组合回测 / 🔍 穿透工具】）在 1080p 标准分辨率下被压到屏幕下半屏甚至首屏之外，用户每次进入系统必须大幅向下滚动页面。
  4. 如果直接关闭 `expanded=False`，用户在折叠态下无法感知今日市场脉搏、机会赛道与风险巡检状态，变成了完全的“信息盲盒”。

### 2. 精简单行高密度摘要条架构方案
在双翼看板顶部（或作为折叠组件的常驻信息条）设计单行高密度信息胶囊栏：
```html
「📢 今日脉搏晨报 + 🎯 Top 3 机会赛道胶囊 + 🚨 风险预警汇总徽章 + 展开/收起详情切换」
```

#### 数据准备与串联：
1. **今日脉搏晨报**：
   - 提取成交额与放量状态：`turnover_str`, `vol_text`。
   - 提取 ERP 状态区间：`erp_zone`。
   - 生成 $\le 40$ 字核心脉搏短语。
2. **Top 3 机会赛道胶囊**：
   - 从 `OpportunityRadarEngine().scan_all_sectors()` 过滤出 Top 3 赛道。
   - 渲染 3 枚紧凑状态胶囊，如：`[🔥 红利低波 88.5分]`, `[🎯 中证红利 85.0分]`, `[📈 恒生科技 82.0分]`。
   - 严格遵循 GEMINI.md 规则 15：`flex: 0 0 auto !important; white-space: nowrap !important;` 物理防挤压。
3. **主动风险预警哨徽章**：
   - 执行 `ActiveRiskSentry().inspect_portfolio(...)`。
   - 若 `report.get("all_passed")`: 渲染 `🟢 风控全通` 绿灯徽章。
   - 若存在风险: 统计未满 7 天锁定期、超买拥挤等警报数量，渲染 `🚨 发现 X 项待处置风险` 醒目徽章。
4. **一键折叠/展开联动**：
   - 利用 `st.session_state.get("dual_wing_expanded", not report.get("all_passed"))` 智能初始化：当所有风控通过时默认折叠收起；当发现紧急风险时智能默认展开。
   - 提供紧凑切换控制，将双翼看板主体置于自适应容器中，一键释放 450px+ 首屏净空间。

---

## 二、 Tab 2 主持仓表 (st.data_editor) 未保存修改防丢失自动同步机制

### 1. 现有持仓编辑与保存流程梳理
- **表格渲染位置**：`AGY2_FundAdvisory/app_gui.py` 第 3878 ~ 3973 行。
  ```python
  edited_table = st.data_editor(
      df_table,
      column_config={...},
      use_container_width=True,
      num_rows="dynamic",
      key="main_holdings_editor_tab2"
  )
  ```
- **现有保存逻辑**：
  - 第 3978 行：`if st.button("💾 保存修改并入库", key="btn_save_holdings_tab2"):` 仅在用户显式点击该按钮时，才遍历 `edited_table` 反算份额/成本并写入 `pm.holdings`。
  - 第 4453 行：`if st.button("🔍 诊断今日调仓时机", key="btn_tab2_diagnose"):`
  - 第 4476 行：`if st.button("🚀 一键执行全案", key="btn_tab2_all"):`
- **丢数根因**：
  Streamlit 的 `st.data_editor` 在单元格编辑完成后，修改数据保存在前端组件的返回值 `edited_table` (DataFrame) 中。若用户未点“保存修改并入库”而直接点击下方的“诊断”或“执行全案”，页面触发 `st.rerun()`，而 `pm.holdings` 尚未更新，下一轮渲染重新由 `pm.export_snapshot_df()` 驱动，导致前端 `st.data_editor` 刚刚输入的数值被彻底覆盖冲刷，用户编辑 100% 丢失！

### 2. `_auto_commit_pending_table_edits(edited_table, pm)` 算法与架构设计
为彻底根治此痛点，必须实现双重防御：

#### A. 差异检测逻辑 (`_detect_table_diffs(edited_table, pm) -> Tuple[bool, List[str]]`)
比较 `edited_table` 与当前 `pm.holdings`：
1. **代码集合差异**：
   - 提取 `edited_table` 中有效 6 位代码集合 `set_table`；
   - 提取 `pm.holdings.keys()` 集合 `set_pm`；
   - 若 `set_table != set_pm`，判定存在增删标的差异。
2. **标的属性数值差异**（对公同标的）：
   - 市值变化：`abs(row['当前市值(元)'] - h.market_value) > 1.0`
   - 份额变化：`abs(row['持仓份额'] - h.shares) > 0.01`
   - 成本变化：`abs(row['持仓成本价'] - h.cost_price) > 0.001` 或累计盈亏改动
   - 调仓意愿：`row['调仓意愿']` 与 `h.rebalance_intent` 不一致
   - 最短持有天数与分红方式差异。
3. **差异提示呈现**：
   - 若检测到差异：在 `st.data_editor` 紧邻上方渲染醒目温和提示：
     `st.info("💡 检测到表格内有未保存的修改，您可直接点击「保存」、「诊断」或「执行全案」，系统将自动先行为您保存入库，绝不丢数！")`。

#### B. 统一入库核心函数 (`_commit_holdings_from_table(edited_table, pm) -> bool`)
将当前第 3982 ~ 4065 行的入库逻辑抽取为纯函数：
- 遍历 `edited_table` 行，校验 6 位代码；
- 联网补齐净值、基金名称与盘中估值；
- 执行四向反算（改盈亏反算成本价、改市值反算份额）；
- 调用 `pm.add_or_update_holding(...)`；
- 删除已被用户在表格中移除的代码；
- 清空诊断与调仓下游缓存 (`tab2_diag_cache = None`, `tab2_rebal_cache = None`)；
- 持久化写入 `pm.save_state(record_snapshot=True)`。

#### C. 三大触发入口无感自动织入 (Zero-Loss Interceptor)
在以下 3 个关键按钮点击时，统一前置拦截并提交：
1. **「💾 保存修改并入库」**：直接调用 `_commit_holdings_from_table(edited_table, pm)` 并 toast 提示。
2. **「🔍 诊断今日调仓时机」**：
   ```python
   if st.button("🔍 诊断今日调仓时机", ...):
       has_diff, _ = _detect_table_diffs(edited_table, pm)
       if has_diff:
           _commit_holdings_from_table(edited_table, pm)
           st.toast("💾 已自动保存表格修改至账本，正在为您全面诊断...")
       st.session_state.tab2_diagnosed = True
       st.session_state.tab2_trigger_diagnose = True
       st.rerun()
   ```
3. **「🚀 一键执行全案」**：
   ```python
   if st.button("🚀 一键执行全案", ...):
       has_diff, _ = _detect_table_diffs(edited_table, pm)
       if has_diff:
           _commit_holdings_from_table(edited_table, pm)
           st.toast("💾 已自动保存表格修改至账本，正在推进全案...")
       st.session_state.tab2_diagnosed = True
       st.session_state.tab2_rebalanced = True
       st.session_state.tab2_trigger_diagnose = True
       st.session_state.tab2_trigger_rebalance = True
       st.rerun()
   ```

---

## 三、 实盘账本历史净值记账曲线 (NAV Curve) 与一键跟单打卡

### 1. `portfolio_manager.py` 底层净值记账与持久化设计
- **现有状态**：
  `PortfolioManager` 目前记录了 `baseline_date`, `baseline_equity`, `peak_equity`, `max_drawdown_pct`, `alpha_return_pct`，但尚未维护历史时间序列 `nav_history`。
- **数据结构规范**：
  在 `PortfolioManager.__init__` 中初始化：
  ```python
  self.nav_history: List[Dict[str, Any]] = []
  ```
  单个记账点字典模式：
  ```python
  {
      "date": "2026-11-05",                    # 记账日期 (YYYY-MM-DD)
      "timestamp": "2026-11-05 14:35:00",      # 记账时间戳
      "total_assets": 180945.0,                # 账户总资产 (元)
      "unit_nav": 1.0520,                      # 累计份额净值 (total_assets / baseline_equity)
      "benchmark_code": "000300.SH",           # 对标基准
      "benchmark_nav": 1.0315,                 # 同期基准归一化净值
      "portfolio_return_pct": 5.20,            # 组合累计收益率 (%)
      "benchmark_return_pct": 3.15,            # 基准累计收益率 (%)
      "alpha_return_pct": 2.05                 # 累计超额 Alpha (%)
  }
  ```
- **记账触发时机**：
  1. `save_state(record_snapshot=True)` 被调用时（如调仓确认、导入持仓、手工改现金）；
  2. `sync_holdings_live_nav()` 联网同步真实净值完成时；
  3. **去重与平滑机制**：若当日已有记录，更新当日最新点位；若跨日则追加新节点，避免日内重复刷出上百条冗余记录。
- **持久化对齐**：
  - `_export_state_dict()`：导出 `"nav_history": copy.deepcopy(self.nav_history)`；
  - `_import_state_dict()`：安全载入 `self.nav_history = copy.deepcopy(state.get("nav_history", []))`；
  - 落盘至 `portfolio_ledger.json` 与独立账本 JSON 文件。

### 2. Tab 2「🗄️ 账本环境与实盘档案」走势图绘制
- **位置**：`AGY2_FundAdvisory/app_gui.py` 第 4261 行 (`dock_tab3`)。
- **实现方案**：
  - 提取 `pm.nav_history`；若为空，自动以 `(pm.baseline_date, pm.baseline_equity, 1.0, 1.0)` 生成首个基准锚点。
  - 构建 Plotly `go.Figure()`：
    * 曲线 1：实盘账户累计净值（宽度 2.5，配色绑定 `active_co['color_up']` 或 `active_th['accent_primary']`）；
    * 曲线 2：沪深300基准走势（虚线，配色 `#94a3b8`）；
  - 调用 `apply_theme_to_plotly_figure(fig)` 保证 5 套主题与夜间模式完美自适应；
  - 展示核心表现指标胶囊：当前累计净值、年化收益率、跑赢沪深300超额收益、期间最大回撤。

### 3. Tab 2 步骤三底部「一键跟单打卡」投后闭环
- **位置**：`AGY2_FundAdvisory/app_gui.py` 步骤三执行单下方（第 5018 ~ 5065 行附近）。
- **业务场景**：
  买方投顾用户在看完全案建议（包含温和免伤调仓、未满7天锁定期拦截、C转A零费率置换等）后，在天天基金/蚂蚁/招行 App 上手动完成了调仓买卖。用户需要一键将当前账本持仓同步对齐到调仓目标，完成投后记账闭环。
- **按钮与执行机制**：
  - 增加操作按钮：`「✅ 我已在手机端按此方案下单 -> 一键将调仓单同步至当前账本持仓」`。
  - **同步算法**：
    1. 遍历当前建议执行单 `items`；
    2. 计算每只标的的调后目标市值与预估份额：
       `target_mv = max(0.0, current_mv + diff_amt)`
       若 `target_mv <= 10.0`：全额清仓，调用 `pm.delete_holding(code)`；
       若 `target_mv > 10.0`：调用 `pm.add_or_update_holding(code, shares=round(target_mv / nav, 2), ...)`；
    3. 扣减/增加账户现金：`pm.available_cash = max(0.0, pm.available_cash - net_buy_amount)`；
    4. 自动写入一条实盘净值记账快照 `pm.save_state(record_snapshot=True)`；
    5. 清空旧步骤缓存，弹出气球与 toast 祝贺：「🎉 实盘调仓已全额同步入库！净值记账曲线已更新」。

---

## 四、 自动化测试基线与交付验证方案 (Section 4)

### 1. 物理安全只读红线坚守
- **绝对只读文件清单**：
  * `AGY2_FundAdvisory/judge_engine.py`
  * `AGY2_FundAdvisory/holdout_vault.py`
  * `AGY2_FundAdvisory/AGENT_SPEC.md`
  * `tests/test_infra.py` 与 `AGY2_FundAdvisory/tests/test_infra.py`
  * `DataLoader.simulate_execution` 默认函数签名与扣费逻辑
- **本探查员郑重承诺**：保持纯只读探查，严禁修改任何测试与业务源码，严禁自行执行 build/test。

### 2. 四大增量断言测试用例设计

#### 测试 1：红利低波指数代码对齐 (H30269 绝非 000978)
- **目标**：断言 `RADAR_SECTOR_CATALOG["dividend_low_vol"]` 的基准指数彻底修正。
- **断言逻辑**：
  ```python
  from advisory_engine import RADAR_SECTOR_CATALOG

  def test_dividend_low_vol_benchmark_is_h30269():
      sec = RADAR_SECTOR_CATALOG.get("dividend_low_vol")
      assert sec is not None
      assert sec["benchmark_index"] == "H30269", f"期望 H30269，实际为 {sec.get('benchmark_index')}"
      assert sec["benchmark_index"] != "000978", "严厉违规：红利低波绝不可映射为中证医药100指数(000978)！"
      assert sec["index_code"] == "H30269" or sec["index_code"] != "000978"
  ```

#### 测试 2：合规词汇全站审计（“保本率”零容忍）
- **目标**：静态扫描全站 UI 源码与文本配置，断言违规词汇彻底消除。
- **断言逻辑**：
  ```python
  from pathlib import Path

  def test_zero_illegal_capital_guarantee_terms():
      workspace = Path(__file__).resolve().parent.parent
      ui_file = workspace / "AGY2_FundAdvisory" / "app_gui.py"
      content = ui_file.read_text(encoding="utf-8")
      assert "保本率" not in content, "合规红线违规：app_gui.py 中依然存在'保本率'字样，必须替换为'正收益概率 (≥0%)'或'本金安全率'！"
      assert "保本" not in content or "【绝对保本率】" not in content
  ```

#### 测试 3：QDII 跨时区清算规则与同公司转换排除
- **目标**：验证 QDII 基金（050025 等）识别、T+2 确认/T+6+ 到账、以及严禁进入同公司 T+1 转换候选列表。
- **断言逻辑**：
  ```python
  from portfolio_manager import PortfolioManager, CORE_STRATEGY_POOL
  from trading_clock_fee import TradingClock

  def test_qdii_fund_settlement_and_switch_exclusion():
      clock = TradingClock()
      pm = PortfolioManager(ledger_json_path=":memory:", db_path=":memory:")
      # 1. 验证 050025 元数据或交割推算
      meta_050025 = pm.resolve_fund_meta("050025")
      assert meta_050025.get("confirm_cycle") in ["T+2", "T+3"]
      assert int(meta_050025.get("arrive_cycle", "T+6").replace("T+", "")) >= 6
      # 2. 验证同公司基金转换 (PRIORITY_1_SWITCH) 绝不包含 050025
      pm.add_or_update_holding("050025", amount=20000.0) # 博时标普500
      routes = pm.generate_rebalance_routes_scenario(...)
      for r in routes:
          if r.get("route_priority") == "PRIORITY_1_SWITCH":
              assert r.get("from_code") != "050025" and r.get("to_code") != "050025", "QDII 基金严禁列入同公司 T+1 转换！"
  ```

#### 测试 4：Streamlit AppTest 4 个 Tab 全量端到端 0 异常渲染
- **目标**：使用 `streamlit.testing.v1.AppTest` 完整遍历四大主工作区 Tab，断言 `len(at.exception) == 0`。
- **断言逻辑**：
  ```python
  from streamlit.testing.v1 import AppTest
  from pathlib import Path

  def test_apptest_all_four_tabs_zero_exception():
      app_path = Path(__file__).resolve().parent.parent / "AGY2_FundAdvisory" / "app_gui.py"
      at = AppTest.from_file(str(app_path), default_timeout=60)
      at.run()
      assert len(at.exception) == 0, f"AppTest 首屏渲染异常: {[e.value for e in at.exception]}"
      # 依次断言 4 个 Tab 均正常存在
      tab_labels = [t.label for t in at.tabs]
      for expected in ["新资建仓", "持仓调仓", "组合回测", "穿透工具"]:
          assert any(expected in lbl for lbl in tab_labels), f"缺少主工作区 Tab: {expected}"
  ```
