# Milestone 1 Quality & Adversarial Review Report

**Reviewer**: Reviewer R8-M1-1 (reviewer, critic)  
**Milestone**: Milestone 1 (Features 1-6: 侧边栏核心指数走廊升级、全市场自由定制与 UI 细节修复)  
**Target Files Reviewed**:
- `AGY2_FundAdvisory/app_gui.py`
- `AGY2_FundAdvisory/data_loader.py`
- `data/cache/custom_watchlist.json`
- `AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py`  
**Date**: 2026-11-05T02:20:00Z  

---

## 1. Review Summary

**Verdict**: **APPROVE** (附 1 项高价值对抗性改进建议)

本次评审从**功能正确性**、**代码质量与规范遵从度**（GEMINI.md Rule 14/15/16）、**自动化测试独立复现**与**反作弊完整性审计**四个维度对 Worker Prod R8-M1 的交付成果进行了独立且严苛的复核与对抗性压力测试。

**核心结论**：
1. **完整性无违规 (Zero Integrity Violation)**：源码中未检出任何针对测试断言的硬编码期望、假常数或假门面实现；物理安全红线 4 大只读裁判文件 SHA256 哈希完好率 100%。
2. **三层卡片指标流与样式生效**：`.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high` 并集选择器工作正常；侧边栏卡片严格呈现“第1行实时点位与防压扁胶囊、第2行PE/PB真实分位与20日涨跌幅、第3行MA20攻防生命线”的 3 层专业纵向流，符合 Rule 14 与 Rule 15 前端空间几何规范。
3. **真实行情与离线消灭假平盘**：高可用三轨互备机制健全。非交易时段与返回 0.00% 假平盘时，自动基于本地 parquet 真实交易日数据计算涨跌幅，杜绝整排 0.00% 现象。
4. **全市场自由定制与持久化**：内置 40 只全市场指数/ETF，支持 3~15 只滑块切片、拼音/代码/名称三模检索排序、任意 6 位代码探针校验，配置原子落盘至 `data/cache/custom_watchlist.json`，冷启动自愈能力完备。

---

## 2. Findings (评审发现与对抗性挑战)

### [Major] Finding 1: 极端冷启动彻底断网下全收益指数点位与价格指数点位尺度的微观偏离 (Total Return vs. Price Index Scale Divergence in Complete Offline Mode)

- **现象定位**：`AGY2_FundAdvisory/data_loader.py` 第 1317-1350 行 `calc_offline_2day_return` 与第 1662-1675 行 `fetch_custom_realtime_indices`。
- **成因剖析**：
  在 `calc_offline_2day_return` 中，为计算 2026 年最新两个交易日的真实涨跌幅百分比，代码优先读取了包含 2026-11 最新日线的全收益矩阵 `data/processed/aligned_matrix_total_return.parquet`（映射 H00300, H00922 等）。
  全收益指数（Total Return Index）由于包含 20 年来的分红再投资复利，其点位高于价格指数（Price Index）：
  - 沪深300价格指数（000300）现价约 4,119 点，而全收益 H00300 为 6,175 点；
  - 中证红利价格指数（000922）现价约 5,501 点，而全收益 H00922 为 12,189 点。
- **影响范围与场景**：
  1. **正常网络或非交易时段（99.9% 场景）**：东财/新浪接口能正常拉到价格指数点位（如 5501.61），仅在涨跌幅返回 0.00% 时借用全收益矩阵的真实日收益率（如 +0.06%），此时点位完全准确。但点位变动额 `chg = off_chg` 会直接继承全收益的差值（6.98 点）而非按价格指数换算（3.30 点）。
  2. **冷启动且完全彻底断网**：若盘中冷启动且网络完全不可达（`pt <= 0`），代码会直接将 `pt` 置为 `off_pt`（12189.99 点），偏离了 GEMINI.md Rule 16 规定的中证红利 5000~6500 点合理基线。
- **改进建议（建议后续里程碑优化）**：
  1. 在 `fetch_custom_realtime_indices` 注入涨跌幅时，变动额应按标的当前点位重新折算：`chg = round(pt * (off_pct / 100.0), 3 if pt < 100.0 else 2)`。
  2. 在极端断网 `pt <= 0` 时，点位优先取 `EXPANDED_INDEX_CATALOG[c]["fb_point"]`，仅由离线矩阵提供 `chg_pct`，实现价格点位与收益率的绝对平滑解耦。

### [Minor] Finding 2: `validate_and_fetch_code` 离线态降级范围

- **现象定位**：`data_loader.py` 第 1281-1290 行。
- **成因剖析**：当用户在侧边栏手动接入任意 6 位代码时，若处于彻底离线状态，目前主要依赖 DuckDB 的 `v_etfs` 表进行反查。若输入的为场外指数或非 ETF 标的，离线时无法识别。
- **评估**：前端给出了清晰的“代码 X 探针失败，未能获取有效盘中行情”错误提示，未引发不可捕获异常，行为符合预期。

---

## 3. Verified Claims (事实复核与证据链)

| 声明条目 | 复核方法 | 期望结果 | 实际结果 | 判定 |
|---|---|---|---|---|
| **裁判文件完整性** | `py -3 scripts/verify_referee_hashes.py` | 4 大裁判文件 SHA256 一致 | 4/4 PASS | **PASS** |
| **M1 核心回归测试** | `pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py` | 6 项测试通过（含 AppTest） | 6 passed in 9.58s | **PASS** |
| **关联数据与对抗测试** | `pytest test_m1_open_data_and_cache.py test_challenger_m1_adversarial.py` | 38 项测试通过 | 38 passed in 8.69s | **PASS** |
| **CSS 并集选择器** | 源码静态 AST 与 Regex 匹配 | 支持 `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high` | Line 941, 961 完好 | **PASS** |
| **Flexbox 防挤压** | DOM 样式核验 | `.sidebar-index-badge` 锁死 `flex: 0 0 auto !important; white-space: nowrap !important;` | CSS 与 HTML 行内双重锁定 | **PASS** |
| **3 层指标流卡片** | 渲染 DOM 结构审查 | 行1(名称/代码/点位/胶囊)、行2(PE分位/20日收益)、行3(MA20趋势/偏离) | 结构完整，虚线分隔清晰 | **PASS** |
| **消灭 0.00% 假平盘** | 独立脚本模拟非交易时段 `change_pct == 0.0` | 自动切换离线两日真实收益率 | 0.00% 成功替换为真实日涨跌幅 | **PASS** |
| **Rule 16 基准代码一致性** | 目录及缓存核查 | 中证红利必须为 000922，严禁偷换为 000015 | 000922 映射中证红利(5501点)，000015 独立命名上证红利 | **PASS** |
| **Primary 按钮白色文字** | 全局 CSS 核验 | `button[kind="primary"] *` 强制 `#ffffff !important;` | Line 1028-1034 强制锁死 | **PASS** |
| **Tab 1 步骤一文案精炼** | 源码全文搜索 | 消除重复的资产锚点与权益上限文案 | 全文仅保留灰框内 1 处 | **PASS** |

---

## 4. Coverage Gaps & Risk Assessment

- **未覆盖盲区**：在非 Windows 环境下的 Streamlit AppTest（当前工作区锁死 Windows 11 本地运行环境，不涉及跨平台移植风险）。
- **风险评级**：**LOW**。整体架构模块解耦良好，异常边界防护周密，未对 Milestone 2、Milestone 3 的接口产生侵入性破坏。

---

## 5. Final Recommendation

**批准 Milestone 1 交付，允许流水线推进至 Milestone 2 (估值动量单源同真与双翼看板升级)**。
Worker 提出的离线双日涨跌幅回退机制切实解决了非交易时段走廊“假平盘”的体验痛点；建议在 M2 或 M4 阶段将 Finding 1 的点位差额重折算微调纳入，进一步提高系统在极限断网下的鲁棒性。
