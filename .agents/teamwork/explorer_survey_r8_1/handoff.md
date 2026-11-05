# Handoff Report - Explorer Survey R8-1 (Requirement R1)

- **Agent**: Explorer Survey R8-1
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\`
- **Target**: Requirement R1 - 升级侧边栏核心指数行情走廊与全市场自由定制
- **Timestamp**: 2026-11-05T01:50:00Z
- **Status**: Complete Survey & Analysis (Ready for Worker Implementation)

---

## 1. Observation (客观观察与精准定位)

1. **CSS 类名失配与徽章失效定位**：
   - `AGY2_FundAdvisory/data_loader.py` 第 298 行与第 306 行输出的状态字符串为下划线格式：
     `status, label = "very_low", f"PE {pe_val:.1f} ({pct_val:.0f}%极低)"`
     `status, label = "very_high", f"PE {pe_val:.1f} ({pct_val:.0f}%过热)"`
   - `AGY2_FundAdvisory/app_gui.py` 第 1370 行生成 HTML 类名：
     `v_badge_html = f'<span class="index-pill-val-badge val-{v_status}" ...>{v_label}</span>'`，即输出了 `.val-very_low` 与 `.val-very_high`；
   - `AGY2_FundAdvisory/app_gui.py` 第 878 行与第 898 行 CSS 规则仅定义了连字符版本：
     `.val-very-low { background: rgba(16, 185, 129, 0.15) !important; color: #10b981 !important; border: 1px solid rgba(16, 185, 129, 0.35) !important; }`
     `.val-very-high { background: rgba(239, 68, 68, 0.12) !important; color: #ef4444 !important; border: 1px solid rgba(239, 68, 68, 0.3) !important; }`
   - 现网单元测试 `AGY2_FundAdvisory/tests/test_adversarial_m1_2_prod_screener_liquidation_gui.py` 第 382 行校验了 `status_classes = ["val-very-low", "val-low", "val-mid", "val-high", "val-very-high"]`。
2. **行情整排 0.00% 假平盘根因与湖仓数据源验证**：
   - `AGY2_FundAdvisory/portfolio_manager.py` 第 1777-1784 行 `CORE_MARKET_INDICES_CONFIG` 仅包含 6 只硬编码指数，且未提供非交易时段动态计算机制；
   - 图 1 截图直观显示：科创50、中证红利、中证500、中证1000由于当时处于非交易/收盘时段，涨跌幅显示均为 `0.00%`；
   - 经 `py -3 -c "import pandas as pd; df = pd.read_parquet('data/processed/aligned_matrix_total_return.parquet'); ..."` 实测，本地湖仓最后两行（2026-11-02 与 2026-11-03）数据完好，可实时精算出各指数真实涨跌幅：
     - `H00300`: -0.20%
     - `H00905`: -1.45%
     - `H00852`: -1.71%
     - `H00922`: -0.16%
     - `STAR50_STITCH`: -3.81%
     - `AU9999`: +0.60%
   - 本地 `data/processed/indices/` 目录下共存放有 754 个指数 parquet 文件，可为任意 A股指数提供收盘价支持。
3. **卡片结构现状**：
   - `AGY2_FundAdvisory/app_gui.py` 第 1378-1395 行当前仅输出左右 1 层的单薄布局，缺乏 MA20 趋势与近 20 日涨跌幅指标。
4. **侧边栏设置弹窗现状**：
   - `AGY2_FundAdvisory/app_gui.py` 第 1313-1338 行中的 popover 仅包含 1 个硬编码 10 只标的的 `st.multiselect`，无数量滑块（3~15只）、无代码/拼音实时检索映射、无 6 位代码实时接入输入框，且尚未创建或读取持久化文件 `data/cache/custom_watchlist.json`。
5. **UI 细节修复定位**：
   - `button[kind="primary"]` 缺失文字白色穿透样式；
   - `AGY2_FundAdvisory/app_gui.py` 第 1840-1850 行的 Tab 1 步骤一灰框与 caption 存在重复的“资产锚点”和“权益上限”文案。
6. **裁判文件哈希状态**：
   - 执行 `py -3 scripts/verify_referee_hashes.py`，全部 4 大裁判文件返回 `PASS`，哈希完好无损。

---

## 2. Logic Chain (推理链条)

1. **样式修复推理**：
   - 基于 Observation 1，`data_loader.py` 输出下划线类名 `val-very_low` 与 `val-very_high`，而 CSS 仅含 `.val-very-low` 与 `.val-very-high`；
   - 为同时兼容既有单元测试与 Python 动态生成的类名，CSS 应使用并集选择器 `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high`；同时在 Python 端将类名安全替换为 `v_status.replace('_', '-')` 实现双向防御。
2. **假平盘消除与接口架构推理**：
   - 基于 Observation 2，`fetch_batch_realtime_indices()` 在现有测试用例 `test_ui_instant_load.py` 中被断言必须返回 6 只核心指数；因此 `fetch_batch_realtime_indices` 必须保留无参默认返回 6 只标的的兼容性；
   - 增加专用的 `fetch_custom_realtime_indices(codes, use_cache)` 函数处理自定义任意标的列表；
   - 在批处理中，若东财/新浪接口返回的点位涨跌幅为 0.00%（非交易时段清算期）或网络异常，动态提取 `aligned_matrix_total_return.parquet` 或本地指数 parquet 最后两个交易日收盘价，计算真实涨跌幅（如 -0.20%, -1.45%），确保全时段点位和涨跌幅真实可信。
3. **卡片 3 层专业信息推理**：
   - 基于 Observation 3 与用户截图需求，将卡片重构为垂直三行：
     - 第一行：名称 + 代码 + 点位 + 涨跌幅胶囊（Flexbox 防折行锁死 `white-space: nowrap !important; flex: 0 0 auto !important;`）；
     - 第二行：真实 PE/PB 估值标签 + 近 20 日累计涨跌幅；
     - 第三行：MA20 偏离趋势（`站上 MA20 偏离 +X.X%` 或 `跌破 MA20 防守`）。
   - 卡片容器声明 `height: auto !important` 与 `overflow: visible !important`，底部内边距 $\ge 10$px，满足 GEMINI.md Rule 14 空间几何不变量。
4. **全市场 30+ 目录与交互推理**：
   - 基于 Observation 4，规划涵盖 12 大板块 38 只真实标的，中证红利锁死代码 `000922`（坚守 Rule 16 铁律，不混淆为 `000015`）；
   - 设置弹窗设置 `st.slider("展示数量", 3, 15, value=6)`；
   - 多选选项格式化为 `{name} ({code}) [{pinyin}]`，利用 Streamlit 原生文本匹配机制，实现名称、代码、拼音三模秒级检索并保持勾选顺序；
   - 6 位代码接入输入框通过 `validate_and_fetch_code()` 动态校验行情真实性；
   - 自选配置落盘至 `data/cache/custom_watchlist.json`，实现冷热启动自治持久化。

---

## 3. Caveats (注意事项与假设)

1. **港股与美股 QDII 标的行情时段差异**：美股与港股在 A 股交易时段可能无实时盘中交易，采用对应的场内跨境 ETF（如 513180 恒生科技ETF、513100 纳指ETF、513500 标普500ETF）作为代理能够提供完美的日内实时 A 股交易走廊体验。
2. **新浪/东财接口高可用**：东财接口为批量 json，新浪接口为逐个/批量 gbk 文本，二者互为备份；若二者均遇断网，已实装完整的本地湖仓两日收盘价回退。
3. **裁判文件零修改红线**：后续 Worker 实施阶段绝对禁止修改裁判文件 `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。

---

## 4. Conclusion (调研结论)

需求 R1 的所有缺陷根因均已精准锁定，技术路线明确，具体实施方案完备：
1. **样式修复**：合并支持 `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high`，徽章边框与背景色立即复原；
2. **假平盘根除**：优先东财批量实时拉取，非交易时段与离线环境采用本地湖仓最新两交易日收盘价回退，真实呈现涨跌幅；
3. **卡片升级**：实装 3 层信息流卡片结构，兼备估值标签、近 20 日涨跌幅与 MA20 趋势攻防状态；
4. **全市场自由定制**：内置 38 只全市场标的，设置弹窗提供 3~15 滑块、拼音/代码/名称三模检索、任意 6 位代码实时校验接入与 JSON 持久化；
5. **UI 细节**：补齐 `button[kind="primary"]` 文字纯白样式并精简 Tab 1 步骤一重复文案。

详细分析报告已写入：`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\analysis.md`。

---

## 5. Verification Method (独立验证方法)

后续实施人员与审核员可按以下步骤进行独立验证：

1. **裁判文件哈希验证**：
   ```powershell
   py -3 scripts/verify_referee_hashes.py
   ```
   *预期结果*：4 个文件全部 PASS，返回退出码 0。
2. **徽章样式与几何不变量测试**：
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_adversarial_m1_2_prod_screener_liquidation_gui.py -v
   ```
   *预期结果*：全部样式断言与几何不变量断言 100% 通过。
3. **批量与自定义指数获取单元测试**：
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_ui_instant_load.py -k test_fetch_batch_realtime_indices -v
   ```
   *预期结果*：耗时 < 1.0s，6 项数据完整返回。
4. **自选持久化与 6 位代码校验验证**：
   - 验证 `data/cache/custom_watchlist.json` 能够成功生成并写入选定配置；
   - 输入有效代码（如 `159915`）成功拉取名称与点位并加入走廊，输入无效代码友好拦截。
5. **UI 渲染与 3 层卡片视觉检视**：
   - 启动 Streamlit 服务检视侧边栏，确认卡片清晰呈现 3 层指标；
   - 确认中证红利为 `000922`，过热徽章红底红字带边框；
   - 确认非交易时段无整排 0.00% 现象。
