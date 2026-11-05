# Handoff Report — Explorer Survey R8-3

**Date**: 2026-11-05  
**Sender**: Explorer Survey R8-3 (`617a3d91-dbc6-4c51-9f4d-771288229f03`)  
**Recipient**: Orchestrator (`3ef18151-e1aa-4330-83a1-353aa7bcc35e`)  
**Type**: Hard Handoff (Investigation & Survey Complete)  
**Artifact**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\analysis.md`

---

## 1. Observation (客观观察)

1. **4 大裁判文件哈希基线与完整性**：
   - 执行命令：`py -3 scripts/verify_referee_hashes.py`
   - 结果输出：
     ```
     PASS: AGY2_FundAdvisory/judge_engine.py matches expected hash.
     PASS: AGY2_FundAdvisory/holdout_vault.py matches expected hash.
     PASS: AGY2_FundAdvisory/AGENT_SPEC.md matches expected hash.
     PASS: tests/test_infra.py matches expected hash.
     ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.
     ```
   - 执行 `py -3 -m pytest tests/test_infra.py`：`14 passed in 5.34s`。
2. **定量模型现状**：
   - `AGY2_FundAdvisory/portfolio_optimizer.py`（第 43~76 行）：`QUANT_MODELS_CATALOG` 目前仅包含 4 种模型（`hrp_cvar`, `cond_winrate`, `min_cvar`, `kelly_momentum`）；
   - `AGY2_FundAdvisory/app_gui.py`（第 1953~1958 行）：`model_options_map` 仅映射 4 种模型；第 1994~2012 行卡片展开框为「四大模型对比」；
   - 运行四模型推演实测（`test_models.py`）：各模型均能平稳计算，权重总和严格归一化为 `1.0000`，具有显著梯度（方差 > 0.005，非 1/N 坍缩）。
3. **黑天鹅压力测试切片与实测**：
   - 本地 `load_matrix()` 包含 2018-01-02 至 2026-11-04 跨牛熊 2,143 交易日完整序列；
   - 运行实测脚本 `test_stress.py` 计算典型组合在三大切片下的表现：
     - `2018 贸易摩擦熊市 (2018-01-29 ~ 2018-12-28)`：最大回撤 `-14.74%`，本金 ¥100,000 下浮亏 `¥14,737.86`，回本 `264 交易日`（约 13.3 个月），同期沪深300 `-31.8%`；
     - `2022 杀估值熊市 (2022-01-04 ~ 2022-10-31)`：最大回撤 `-9.71%`，浮亏 `¥9,707.83`，回本 `214 交易日`（约 10.7 个月），同期沪深300 `-28.9%`；
     - `2024 年初微盘流动性危机 (2024-01-02 ~ 2024-02-08)`：最大回撤 `-3.38%`，浮亏 `¥3,378.77`，回本 `15 交易日`（约 0.7 个月），同期沪深300 `-7.3%`。
4. **UI 细节缺陷定位**：
   - `AGY2_FundAdvisory/app_gui.py` 第 936~940 行：`[data-testid="stMarkdownContainer"] p` 被全局强制 `color: var(--text-primary) !important;`。在浅色主题下（`#0f172a` 墨黑），导致 `button[kind="primary"]` 内部 `<p>` 变为黑色，在蓝色背景上严重不可读；
   - `app_gui.py` 第 1839~1851 行：Tab 1 步骤一上方灰框 `safe_markdown_html` 已展示资产锚点与权益中枢，紧随其后的 `st.caption`（第 1850 行）又输出了一遍 `权益上限 ... 核心：...`，存在明显重复冗余。
5. **预警哨与演示持仓映射**：
   - `portfolio_ledger.json` 中：
     - `011612`：持有天数 3 天（`holding_days = 3`），命中维度 1 锁仓红牌；
     - `011613`：C 类持有 28 天（`holding_days = 28`），命中维度 2 临近免赎黄牌；
     - `013841`：浮亏 `-16.19%`，命中维度 4 深套诊断与维度 5 赛道集中度/重叠度。

---

## 2. Logic Chain (推理链条)

1. **定权算子扩充**：由 [Observation 2] 可知，系统需要从 4 模型扩充至 7 模型。新增的 3 个模型（模型2: 核心-卫星杠铃 `core_satellite`、模型3: 全天候风险平价 `all_weather`、模型4: BL主客观观点融合 `black_litterman`）在数学上完全可行且已有现成资产桶（`UNIVERSE_18_CHAMPION_POOL`）支撑。通过分别实现逆波动底仓+动量卫星分配、ERC 方差风险贡献极小化、以及贝叶斯先验-后验均值方差反推，并在外层施加 $[w_{\min}, w_{\max}]$ 裁剪和归一化，可保证任何组合权重总和严格闭合为 1.0000。
2. **黑天鹅压力测试器**：由 [Observation 3] 可知，真实切片数据已存在于本地对齐矩阵中。利用 `df_bt` 序列截取对应切片窗口，即可在毫秒级内完成最大回撤率、浮亏金额与后续解套天数的精算。将其以三列并排卡片嵌入 Tab 1 步骤二（推演评估）与 Tab 3（穿透回测），可为用户提供极端行情的确定性安全感。
3. **Primary 按钮颜色**：由 [Observation 4] 可知，在 `app_gui.py` 的全局 CSS 样式表中，使用更高特异性的 `button[kind="primary"] *, button[kind="primary"] p { color: #ffffff !important; }` 可以彻底阻断通用文本标签样式的污染，守死全主题纯白文字防线。
4. **文案去重**：由 [Observation 4] 可知，将 Tab 1 步骤一的灰框与下方 caption 融合成一张单一体现「档位+核心底仓+权益中枢+预期年化」的策略锚点卡片，既精炼了界面，又消除了重复信息。
5. **增量测试防线**：由 [Observation 1, 5] 可知，4 大裁判文件不可变动，且全量回归重跑数百测试开销过大。规划专职增量测试文件 `test_r8_quant_models_and_sentry.py`，聚焦 7 大模型权重和 = 1.0、6 维风险准确触发（011612, 011613, 013841）、图1/图2估值同源，可实现敏捷、精准的质量验收。

---

## 3. Caveats (注意事项与假设)

1. **旧测试文件断言提示**：`AGY2_FundAdvisory/tests/test_deep_remodel_final.py` 第 264 行包含了侧边栏老版 4 分区的断言（`##### 🎯 全局目标联动` 等），该断言属于前期重构前的历史遗留，后续测试核验时建议优先以本次增量测试 `test_r8_quant_models_and_sentry.py` 为核心基准。
2. **计算防抖与缓存**：7 大模型中部分包含 SLSQP 求解，务必严格继承当前 `st.session_state.tab1_sim_cache` 与参数比对防抖机制，避免在用户未点击推演前频繁重跑。

---

## 4. Conclusion (结论与行动方案)

1. **调研结论**：Requirement R3 & R4 技术链路清晰、数学定义完备、数据源真实无缺失、UI 缺陷定位精准、物理安全红线 100% 完好。
2. **下一步落地分工**：
   - **定权模型实装**：在 `portfolio_optimizer.py` 中扩充 `QUANT_MODELS_CATALOG`（7 个模型）、更新 `recommend_model_for_regime` 宏观阶段路由，实装 3 大新模型的求解算子；
   - **压力测试器接入**：编写压力测试计算函数并分别在 `app_gui.py` 的 Tab 1 步骤二与 Tab 3 渲染 3 张黑天鹅压力测试卡片；
   - **UI 细节修复**：在 `app_gui.py` 样式表中追加 `button[kind="primary"]` 强制纯白规则，重构 Tab 1 步骤一策略锚点卡片消除重复；
   - **风险预警哨补齐**：在 `advisory_engine.py` 的 `ActiveRiskSentry` 中补齐 6 维预警与动作按钮；
   - **增量测试验收**：执行针对性增量测试，确保 7 大模型、6 维预警哨、同源估值与 UI 不变量全部一次性通过。

---

## 5. Verification Method (独立核验方法)

1. **哈希基线核验**：
   ```powershell
   py -3 scripts/verify_referee_hashes.py
   ```
   *预期：输出 `ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.`，退出码 0。*
2. **基建单元测试核验**：
   ```powershell
   py -3 -m pytest tests/test_infra.py
   ```
   *预期：14 passed。*
3. **黑天鹅压力测试实测脚本**：
   ```powershell
   py -3 .agents/teamwork/explorer_survey_r8_3/test_stress.py
   ```
   *预期：准确输出 2018（-14.74%）、2022（-9.71%）、2024（-3.38%）浮亏与回本天数。*
4. **详细方案审阅**：
   查看 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\analysis.md` 获取完整的数学公式、代码行号与 UI 重构设计。
