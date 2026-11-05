# Handoff Report — Explorer 1 (R1 & R2 勘测报告)

## 1. Observation (客观观察)

- **攻防红线双源漂移**:
  - `AGY2_FundAdvisory/app_gui.py` 第 677-679 行主看板 Card 2 读取点位：
    ```python
    trigger_lines = snapshot.get("trigger_lines") or {}
    surge_line = float(trigger_lines.get("surge_line", snapshot.get("surge_line", c300_disp * 1.012)))
    breakdown_line = float(trigger_lines.get("breakdown_line", snapshot.get("breakdown_line", c300_disp * 0.985)))
    ```
    第 751-752 行展示：`<span>📈破 {surge_line:,.0f} 进攻</span> <span>🛡️跌 {breakdown_line:,.0f} 防守</span>`
  - 而 `AGY2_FundAdvisory/app_gui.py` 第 625-627 行侧边栏直接硬编码：
    ```python
    _c300 = snapshot.get('c300_price', 4053.0)
    st.write(f"**攻防红线**：破 `{_c300*1.012:,.0f}` 进攻 ｜ 跌 `{_c300*0.985:,.0f}` 防守")
    ```
  - `AGY2_FundAdvisory/strategy_bridge.py` 第 2710 行：
    `trigger_lines = SchmidtHysteresisBuffer.get_hysteresis_trigger_lines(m20_price, c300_price)`
    计算逻辑在第 1346 行：`surge_line = round(max(m20_up, c300_price * 1.012), 1)`，当 c300=4053, m20=4140 时，`surge_line = 4189.7`（Card 2 显示 4,190），但侧边栏硬编码为 `4053 * 1.012 = 4101.6`（显示 4,102），产生 **88 点**的直接数值冲突。

- **核心指数实时行情条 CSS 规则**:
  - `AGY2_FundAdvisory/app_gui.py` 第 339-381 行：
    `.index-pill-point` 的字号为 `13px`；`.index-pill-name` 的字号为 `12px`；`.index-pill-chg-up` 与 `.index-pill-chg-down` 字号为 `11px`；`.index-ticker-pill` 内边距为 `3px 8px`、`gap: 6px`。
  - 行情条在 `app_gui.py:805-833` 由 `fetch_batch_realtime_indices(use_cache=True)` 驱动，并在容器 `.index-pills-scroll-wrap` 中横向排列。

- **侧边栏状态与功能布局**:
  - `AGY2_FundAdvisory/app_gui.py` 第 613-658 行：侧边栏 `with st.sidebar:` 目前仅以静态文本展示 `_act_t`、`_act_r`、`pm.holdings`，缺少交互控制器。
  - `active_tier_val` 与 `target_return_val` 直到第 910-913 行才在 Tab 1 前夕执行默认初始化，时序滞后于侧边栏执行点（第 613 行）。
  - 单日限购：`portfolio_manager.py:1624` 的 `fetch_realtime_fund_quota` 返回标的限额（如 `050025` 限额 100 元，`018757` 限额 0.01 元，`001071` 开放不限额）。`portfolio_manager.py:2275` 的 `_get_sector_alternatives` 维护了同赛道备选池。
  - 调仓缓冲阈值：`trading_clock_fee.py:589` 的 `is_rebalance_actionable`、`strategy_bridge.py:5888` 的 `evaluate_today_rebalance_suitability`、`strategy_bridge.py:6028` 的 `simulate_rebalance_modes_and_consequences` 以及 `app_gui.py:2340` 均存在硬编码 `3%` / `0.03`。
  - 演示组合与快照撤销：`app_gui.py:1778-1800` 目前占据 Tab 2 步骤一顶部整行（`t2_ctrl_c1, t2_ctrl_c2`）。

- **既有测试基线验证**:
  - 运行命令：`py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v`
  - 结果：全部 7 项测试通过（`7 passed, 21 warnings in 71.72s`），基线运行态完好。

## 2. Logic Chain (逻辑推演链)

1. **R1 攻防红线一致性**：因为 `strategy_bridge.py` 内部已经通过 `SchmidtHysteresisBuffer` 提供了权威的施密特双向迟滞触发线并存入 `snapshot["trigger_lines"]`（同时映射在 `snapshot["surge_line"]` 与 `snapshot["breakdown_line"]`），侧边栏却在没有读取字典的情况下直接通过 `_c300 * 1.012` 自行粗暴推算，因此只要将侧边栏（`app_gui.py:626`）替换为读取 `snapshot["surge_line"]` 和 `snapshot["breakdown_line"]`，即可实现 100% 同源对齐。
2. **R1 行情条视觉层级**：因为点位数字是行情带首要信息资产，提升至 `15px` 加粗等宽（`font-feature-settings: 'tnum'`）、名称与徽章提升至 `13px`、内边距扩大至 `4px 10px`、相邻间距锁死 `8px`，既大幅提升专业金融质感，又严格遵守了 `GEMINI.md` Rule 14（组件间距 $\ge 8$px）与 Rule 15（Flexbox 防压扁与横向滚动容器标配）。
3. **R2 侧边栏全局控盘**：
   - 将 `active_tier_val` 与 `target_return_val` 提权初始化后，在侧边栏挂载档位切换与收益率调节，并同步修改 Tab 1 的 `slider_target_return` 键值并清空 Tab 2 诊断缓存，可实现跨 Tab 零冲突双向响应。
   - 单日限购选择器（不限 / <1000 / <5000）联动 `fetch_realtime_fund_quota` 与 `_get_sector_alternatives`，在 Tab 1 选基与建仓单中将受限标的替换为备选标的（如 050025 -> 001071），能彻底免去拆单操作，实现大额一键买入。
   - 调仓缓冲带滑块（1.0%~5.0%）打通到 `evaluate_today_rebalance_suitability`、`simulate_rebalance_modes_and_consequences` 和 `pm.generate_rebalance_plan`，可动态调节调仓敏感度。
   - 将 `🚀 加载演示组合` 与 `↩️ 一键撤销快照` 收拢进侧边栏，Tab 2 顶部可完全移除原有的 4 个冗余大按钮，为 R3 的人体工学 4 卡片一屏尽览彻底扫清障碍。

## 3. Caveats (注意事项与假设)

- **无头测试耗时**：`test_deep_remodel_final.py` 包含多模型全周期回测与 AppTest 无头渲染，全量执行需约 70 秒。在敏捷交付阶段应遵照 GEMINI.md Rule 6 与 13，优先执行 Delta 增量测试。
- **只读文件保护**：勘测确认 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 与 `tests/test_infra.py` 均为只读裁判文件，实施阶段严禁进行任何修改。
- **只读勘测声明**：本 Explorer 严格遵循只读原则，未对任何源码执行写入，所有成果已固化在 `survey_report.md` 中。

## 4. Conclusion (调查结论与交付成果)

R1 与 R2 的技术瓶颈、代码行号、数据流向与修改方案已 100% 探明并闭环：
- 完整勘测报告已生成在：`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_1\survey_report.md`
- 报告内包含代码级 Before/After 对照方案、精确 CSS 配置规则、侧边栏全模块重塑伪代码与 6 项增量测试套件（Delta Test）设计，可直接交付给后续实施代理进行无风险精准施工。

## 5. Verification Method (独立核验方法)

1. **勘测报告核验**：
   查看 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_1\survey_report.md` 确认各模块论证与代码方案。
2. **既有基线测试复验**：
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v
   ```
3. **数据一致性验证断言**：
   检查 `app_gui.py` 中侧边栏渲染文本与 Card 2 文本是否均读取自 `snapshot["trigger_lines"]`。
