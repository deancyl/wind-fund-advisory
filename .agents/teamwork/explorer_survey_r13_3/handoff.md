# Handoff Report — Explorer 3 (GUI Architecture & Test Suites)

## 1. Observation
- **代码文件与行号定位**:
  - `AGY2_FundAdvisory/app_gui.py`:
    - 晨报渲染位置: 第 2411~2456 行，包含 `t_data = data_loader.fetch_market_turnover_and_sentiment()`、`StrategyBridge.get_historical_inflection_ruler` 及 `render_historical_inflection_ruler_html`。
    - Top 3 赛道卡片: 第 2457~2498 行，使用 `cols_top3 = st.columns(3)` 循环渲染各赛道名称、得分、优选基金与入池按钮。
    - 右翼主动风险预警哨标题: 第 2521 行字面存在灰色开发口号尾缀：
      `<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检 <span style='font-size: 11px; font-weight: 400; color: var(--text-secondary);'>[主动风险预警哨 · 四维巡检升级版]</span></div>`。
    - 预警卡片容器: 第 2531 行 `with st.container(height=300):`，因第 574~585 行全局 `.decision-card` 具有 `min-height: 108px;`，导致多张卡片或卡片加按钮时总高度溢出产生滚动条，上边沿易被截断。
    - Tab 1 归因与推演区: 第 3428~3442 行。
    - Tab 2 调仓后果与净效用门禁区: 第 5372~5460 行。
  - `AGY2_FundAdvisory/advisory_engine.py`:
    - 静态权重常数: 第 575~578 行字面定义了：
      `total_score = round(0.30 * s_val + 0.30 * s_mom + 0.25 * s_er + 0.15 * s_crowd, 1)`。
    - 四维因子得分: 第 600~617 行中 `_score_sector` 已经原生返回了 `s_val`、`s_mom`、`s_er` 与 `s_crowd`。
  - 只读裁判硬红线校验:
    - 运行 `git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py`，输出为空（0 变更，100% 干净）。
  - 基准测试套件执行:
    - 运行 `& "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py -q`
    - 结果：`50 passed, 121 warnings in 93.17s`。

## 2. Logic Chain
1. **晨报与 Top 3 赛道升级路径**:
   - 依据 Observation 1，第 2411~2456 行处于 `with col_radar:` 下，`fetch_market_turnover_and_sentiment` 已具备成交额与涨跌家数接口。
   - 接入新实装的 `data_loader.fetch_realtime_market_news_and_catalysts()`，可无缝注入实时抓取秒级时间戳、两市成交额与主力情绪、最新 2~3 条快讯与操作定调；
   - 保持 `ruler_bar_html` 在同一卡片内渲染，可守住三大牛熊拐点对照尺不丢失；
   - 依据 Observation 2，`_score_sector` 字典已包含四维因子分，直接在第 2463~2478 行 Top 3 卡片中提取展示，并加上实时涨跌幅胶囊与定性定量入选依据。
2. **预警哨标题清理与防截断**:
   - 依据 Observation 1 中的第 2521 行，字面删除 `<span ...>[主动风险预警哨 · 四维巡检升级版]</span>` 即可消除视觉瑕疵；
   - 依据 Observation 1 中的第 2531 行与第 574 行，将容器由 `height=300` 调整为 `height=360`，并在预警卡片内联样式中显式覆盖 `min-height: auto !important;`，可消除滚动条与卡片上边缘截断。
3. **在线基因进化徽章挂载**:
   - 依据 Observation 2 中的静态加权代码，在线进化引擎 `OnlineHeuristicFactorEvolver` 产出动态权重后，在机会雷达顶部（第 2406 行下方）渲染紧凑白盒徽章，直观展示 60 日真实日线演化状态、动态权重与 OOS 超额适应度。
4. **Tab 1 与 Tab 2 风控卡片扩展**:
   - 依据 Observation 1 中的第 3428 行与第 5420 行，分别在 Tab 1 推演归因区与 Tab 2 调仓净效用门禁区，接入目标波动率超标预警卡片与红利再投资转现金分红再配置卡片，提供精准压降比例与免赎回费/免在途计算。
5. **测试套件保障与增量规划**:
   - 依据 Observation 3 与 4，四大测试套件当前 50 个用例 100% 通过且只读文件完全未受破坏。在 `tests/test_g3_evolution_loop.py` 中增加 `test_g6_1`、`test_g6_2`、`test_g6_3` 三大测试用例即可形成 G6 世代闭环。

## 3. Caveats
- 外部行情与资讯接口（东财/新浪）在网络异常时可能超时，代码中已包含本地持久化 JSON 缓存兜底机制，离线环境下可平滑使用最新缓存；
- Streamlit AppTest 测试运行耗时较长（约 30 秒），本地完整回归测试耗时约 90 秒，符合预期。

## 4. Conclusion
- GUI 架构与测试套件的技术现状、代码行号与修改方案已 100% 厘清，调研报告已落盘至 `report.md`。
- 修改方案完全遵循 GEMINI.md 的公募基金真实交易制度、界面复杂度守恒及四大只读裁判文件硬红线。
- 下游实施阶段可直接依照本方案执行代码注入与视觉走查。

## 5. Verification Method
- **测试运行命令**:
  ```powershell
  & "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py -q
  ```
  预期通过率：50 项全部通过（100% Passed）。
- **只读文件检查命令**:
  ```powershell
  git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
  ```
  预期结果：输出为空（无修改）。
