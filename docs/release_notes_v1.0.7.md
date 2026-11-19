# AGY2-FundAdvisory v1.0.7 正式发布说明 (Release Notes)

- **发布版本**：`v1.0.7` (Official Release)
- **发布日期**：2026-11-19
- **版本代号**：官方净值与盘中双轨对账、秒级批量湖仓引擎、实战组合自洽重塑与三层渐进式终端 (Official Dual-Track Reconciliation, Sub-Second Batch Lakehouse, Combat Rebalance & 3-Tier Progressive Terminal)
- **工程宪法**：服从最高《工程宪法 v6.0》，34 处违规硬编码常数彻底物理清零，四大只读裁判文件 SHA256 100% 锁定
- **测试状态**：G28/G27/G26/G25 专项门禁 100% PASS，Pytest 核心测试 23/23 绿灯通过，Browser 双视口实机审计零报错

---

## 🚀 核心更新概要 (Executive Summary)

**AGY2-FundAdvisory v1.0.7** 是系统迈向全面工业级生产就绪的里程碑版本。本版本基于**《AGY2 智能投顾产品哲学与工程宪法 v6.0》**，彻底终结了历史遗留的技术债务，全面确立了**「收盘官方净值最高主权 + 盘中实时估值双轨独立不覆盖」**的对账体系；首创**「单次 HTTP 批量拉取 + 多线程并发补齐」**的毫秒级高可用行情管道，将 29 只基金组合全量刷新与对账耗时从 10+ 秒压缩至 **0.95 秒**；实装**实战 29 只基金重塑账本与尾仓清扫引擎**，彻底消灭逆向加仓与冗余开仓；实施**「奥卡姆剃刀与三层渐进式信息架构」**革命，提供首屏裁决台、双横向抽屉、宽屏逐基对账单及核心图表白话导读胶囊，并在桌面与移动双视口下完成真机实测闭环。

---

## 🌟 核心新特性与工程突破 (Key Features & Engineering Breakthroughs)

### 1. 真实数据零造假与反作弊铁律 (Engineering Constitution v6.0)
- **34 处违规常数物理清零**：全库生产代码彻底删除所有硬编码的美元汇率（`7.2385`）、中债收益率（`4.4200`）与静态万点基准（`11569.50`），全部接入权威实时接口与本地列存湖仓真实最新截面，极端断网缺失时诚实标记 `is_fallback=True`；
- **官方收盘净值最高主权 (Official NAV Supremacy)**：优先拉取东财移动端官方清算接口 `FundMNFInfo`，基于真实交易日历校验净值日期 `>= latest_completed_trade_str` 确定官方净值，一旦公布立即采信官方实际涨跌幅，严禁后置估值算法覆盖；
- **盘中实时估值双轨独立对账**：盘中及盘后官方净值未出前，以官方实时估值（`GSZZL`）为主源，四级穿透为缺失兜底；晚间官方净值公布后，估算值完整保留归档，输出逐基 MAE 误差分析与归因解释；
- **4 位小数修约与 C 类日费精算**：计算涨跌幅时采用严格的 4 位小数净值修约（如 `0.9343`），并针对 C 类份额精算扣除销售服务费日均成本（约 0.1~0.15 bps/日）；
- **联接基金动态 Beta 与元数据修复**：修复 `get_calibrated_feeder_beta` 判定死代码，增加 `fund_name` 参数与对齐矩阵内存缓存；纠偏二级债基 `018757` 元数据单一真源；
- **凌晨非交易时段防写脏**：锁定 `00:00~09:34` 禁止写脏归档文件，盘中仅归档有效估算。

### 2. 实战 29 只基金重塑账本与调仓自洽 (Combat-29 Fund Ledger)
- **真实资产组合全面接管**：新增 `combat_29_funds` 实盘实战账本，完全覆盖投资者 29 只基金的真实成本、份额与盈亏事实；
- **碎片尾仓（< 200元）强制清扫归拢**：凡市值 `< 200元` 且已满 7 天免罚期的碎片尾仓（共 19 只），调仓目标权重强制归零（`0.00%`），操作锁定为「🧹 建议清仓归拢」，杜绝逆向追买；
- **同赛道纯债底仓自动去重合并**：当前持有核心纯债主锚（`002351` 易方达裕祥回报）时，自动将策略池同属性纯债（`000086`）的目标权重全额合并至 `002351`，杜绝凭空新开仓买入冗余纯债；
- **核心持仓与尾仓操作语义隔离**：市值 `>= 500元` 的底仓调整严格标记为「➖ 建议减仓」，杜绝在数千元核心持仓上误贴“清扫碎片”标签；
- **C 转 A 零费率置换闭环**：持有满 30 天的 `011613`（科创50C）自动触发零费率置换为 `011612`（科创50A），降低长期持仓摩擦。

### 3. 极致性能突破：单次批量请求与秒级湖仓 (Sub-Second Batch Engine)
- **单次 HTTP 批量拉取 (`prefetch_batch_fund_quotes`)**：利用东财 `FundMNFInfo` 的 `Fcodes` 能力，在 1 次 HTTP 请求（< 0.3 秒）内一次性获取全部 29 只持仓基金数据，未命中项通过 `ThreadPoolExecutor` 多线程并发补齐，批次结束仅执行 1 次磁盘写入；
- **全组合秒级极速刷新**：29 只基金全量行情拉取、净值同步与盘中盈亏对账总耗时压缩至 **0.95 秒**（远低于 1.5 秒硬门禁），彻底根除 N+1 串行网络瓶颈；
- **盘中刷新剥离低频爬虫**：盘中极速刷新剥离历史 PE 网页爬虫，十年估值分位数全走本地列存湖仓。

### 4. 奥卡姆剃刀与三层渐进式终端 (3-Tier Progressive UI Architecture)
- **第一层（首屏直显裁决台，<= 110px）**：1 行核心结论 + 仓位因果传导公式 + 5 颗精炼人话胶囊（<= 20 字），普通投资者 3 秒掌握今日定调；
- **第二层（默认折叠横向双抽屉）**：「🔭 Top 3 机会雷达与主动风控哨」和「🧭 十维投顾量化投票与拐点对照尺」，风控哨严格绑定当前账本 `>= 200元` 真实持仓；
- **第三层（四大工作台核心）**：
  * **宽屏逐基对账单**：对账单脱离狭小 `st.popover` 迁入原生宽屏 `st.expander`，外置「官方净值已公布 (26/29只)」、「官方vs估算 MAE (0.21%)」、「双源平均分歧 (0.15%)」与「4位修约准则」四大指标卡；
  * **五大深度图表两行白话导读**：在回撤（`fig_dd`）、大类演进（`fig_area`）、赛道相关性（`fig_corr`）、月度热力图（`fig_heat`）与风险收益四象限图（`fig_quad`）正上方，统一配置 `💡 怎么看` 与 `🎯 行动信号` 双行白话导读；
  * **响应式双视口自适应**：移动端（`?view=mobile`）自动切换 4 列极简决策表与 2×2 指标网格，消除横向滚动条，根除 `ValueError` 解构与列名重复异常；
  * **生产级环境纯净化**：物理删除 `btn_mock_pending_order` 模拟假按钮，确保系统纯粹面向买方实战。

### 5. 智能 OCR 截图切片识别与多模检索增强
- **截图 OCR 识别与文本智能解析**：支持手机持仓截图自动切片识别与批量自然文本智能解析入库；
- **匹配置信度安全预警**：OCR 导入预览表增设「原图识别名」与「匹配置信度」，置信度 `<0.85` 时显式标黄提示人工复核；
- **多模代码/拼音/中文快速定标**：支持通过拼音缩写（如 `hldb`）、中文简称（`红利低波`）或指数代码（`H30269`）极速检索并对齐标的。

---

## 🧪 自动化测试套件与安全门禁 (Verification Gates)

| 门禁项 / 测试脚本 | 验证范围与核心断言 | 测试结果 |
| :--- | :--- | :---: |
| **G28 生产级清理门禁** (`verify_g28_production_readiness.py`) | 动态 Beta、十维中立门禁、宽屏展开、图表导读 | **100% PASS** |
| **G28 债务根治门禁** (`verify_g28_clean_debt_gate.py`) | 核心代码硬编码清零扫描、联接基金反向边界 | **100% PASS** |
| **四大裁判文件 SHA256** (`verify_readonly_hashes.py`) | 锁定 `judge_engine`, `holdout_vault`, `AGENT_SPEC`, `test_infra` | **100% 一致** |
| **G27 路由与反作弊门禁** (`verify_g27_anticheat_and_routing_gate.py`) | 真实行情分治路由、29 只对账误差 MAE < 20bps | **100% PASS** |
| **G26 双轨对账门禁** (`verify_g26_valuation_vs_official_reconciliation.py`) | 4 位修约、基准映射、双轨独立不覆盖 | **100% PASS** |
| **G25 极速性能与自洽门禁** (`verify_g25_realtime_and_consistency.py`) | 29 只基金批量刷新耗时 < 1.5s (实测 0.95s)，同赛道去重 | **100% PASS** |
| **Pytest 核心套件** | `tests/test_infra.py` + `test_adversarial_m3_combat29_challenger.py` | **23 passed (7.58s)** |
| **Browser 双视口实机审计** | 移动端 390x844 对账单展开，桌面端 1440x900 持仓表格渲染 | **0 Error / 100% PASS** |

---

## 📦 安装与快速启动 (Quick Start)

```bash
git fetch --all --tags
git checkout v1.0.7
pip install -r requirements.txt
streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501
```

启动后在浏览器中访问 `http://localhost:8501`，即可体验秒级刷新、双轨对账、实战 29 只基金自洽重塑与三层渐进式投顾工作台！
移动端请直接访问 `http://localhost:8501/?view=mobile`。

---

# AGY2-FundAdvisory v1.0.7 English Release Notes

- **Version**: `v1.0.7` (Official Production Release)
- **Release Date**: 2026-11-19
- **Codename**: Official Dual-Track Reconciliation, Sub-Second Batch Lakehouse, Combat Rebalance & 3-Tier Progressive Terminal
- **Constitution**: Compliant with Engineering Constitution v6.0; zero hardcoded constants; SHA256 verified for all 4 referee files
- **Test Status**: G28/G27/G26/G25 verification gates 100% passed; Pytest 23/23 passed; Browser dual-viewport live audit passed with zero errors

---

## 🚀 English Executive Summary

**AGY2-FundAdvisory v1.0.7** marks a milestone upgrade achieving full production-readiness. Built upon the **Engineering Constitution v6.0**, this release completely eliminates legacy technical debt:
1. **Dual-Track Valuation & Official Reconciliation**: Establishes Official NAV Supremacy via Eastmoney mobile clearing API while preserving intraday estimates for evening MAE precision reconciliation;
2. **Sub-Second Batch Lakehouse Engine**: Employs single-HTTP batch fetching (`Fcodes`) and concurrent threading, compressing 29-fund portfolio sync latency from 10+ seconds to **0.95 seconds**;
3. **Combat-29 Fund Ledger & Tail Sweeping**: Full support for the real-world 29-fund investor portfolio, auto-liquidating fragmented tail positions (< 200 RMB), merging pure-bond anchors, and triggering C-to-A class cost-free conversion;
4. **Occam's Razor & 3-Tier Progressive UI**: Features an executive verdict bar (<= 110px), horizontal analytical drawers, full-width expander reconciliation, plain-language chart reading guides, and responsive mobile adaptation (zero `ValueError` / duplicate column exceptions).
