# Task Assignment for Lead Implementation Worker G17-1

## 🔒 Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 🔒 Physical Safety Redlines (STRICT ZERO TOLERANCE)
1. 严禁修改四个只读裁判文件：
   - `judge_engine.py` (或 `AGY2_FundAdvisory/judge_engine.py`)
   - `holdout_vault.py` (或 `AGY2_FundAdvisory/holdout_vault.py`)
   - `AGENT_SPEC.md`
   - `tests/test_infra.py` (或 `AGY2_FundAdvisory/tests/test_infra.py`)
2. 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
3. 严禁创建 GitHub Release（仅允许 git tag）。
4. 在任何报告或指令中，绝对禁止输出带冒号的 `slashCommand:` 格式，仅允许纯文本标签（/goal, /boost, /teamwork, /browser）。

## Input Documents to Read Before Starting
1. `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (User request)
2. `d:\Google\Workspace\Wind\PROJECT.md` (Architecture, Feature Inventory & Milestones)
3. `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_1\analysis.md` (Data & Quant Blueprint)
4. `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_2\analysis.md` (UI & Mobile Blueprint)
5. `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_3\analysis.md` (Backtest Friction & Screenshot Blueprint)

## Write Ownership
You have exclusive write ownership of:
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/data_loader.py`
- `AGY2_FundAdvisory/app_gui.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/strategy_bridge.py`
- `AGY2_FundAdvisory/tests/test_g17_advisory_real_data_and_ten_dimension.py`
- `AGY2_FundAdvisory/tests/test_g17_friction_and_screenshot.py`
- `AGY2_FundAdvisory/tests/test_g17_ui_mobile_and_ledger_routing.py`
- `.agents/teamwork/worker_g17_1/` (your own state files)

## Implementation Scope & Milestones

### Milestone 1: 拔除静态假常数、打通真实数据湖仓与十维因果传导
1. 修改 `data_loader.py` 与 `advisory_engine.py`:
   - 彻底清除 `snap.get("treasury_10y", 1.6258)`、`macro_multi.get("usdcnh_rate", 7.2450)`、`macro_multi.get("gold_price", 628.5)`、`macro_multi.get("nasdaq_change_pct", -0.25)` 等断裂键与静态假常数。
   - 对接 `data/macro/bond_zh_us_rate.parquet` 提取最新交易日中债 10Y (1.6376%)、美债 10Y (5.0000%)、中美利差 (-336.2bp) 及近 20 交易日变动 bp；
   - 对接 `data/global/global_indices.parquet` 提取纳指 (`IXIC` +0.82%, Bias -2.46%)、标普500 (`SPX` +0.70%)、恒生科技 (`HSTECH` -0.37%, Bias -6.32%)；
   - 对接离岸人民币汇率 `fetch_realtime_usdcnh_fx(use_cache=True)`，离线降级读取 `data/global/fx_rates.parquet` (6.6676)，绝不回退到 7.2450；
   - 区分黄金 ETF 518880 (¥8.29/份) 与 AU9999 现货回报指数 (1479.55)，文案严禁标注“国内黄金现价 ¥8.29/克”！
2. 实装「十维投顾量化投票模型」与「仓位推导因果传导公式」:
   - 在 `generate_chief_advisor_memo` 中，输出包含 10 个维度（①宏观经济、②货币政策、③股债ERP、④国际联动、⑤外汇锁汇、⑥产业估值、⑦资金情绪、⑧技术信噪比、⑨历史同温层、⑩期权IV与黑天鹅）的评分、投票与增减项；
   - 输出清晰的仓位推导因果链文本（例如：`基准权益中枢 60% + ERP极低估溢价(+10%) + 货币宽松(+5%) + 结构性机会(+5%) - 美债倒挂约束(-3%) = 当前建议权益仓位 77% (防守固收 23%)`）。

### Milestone 2: 手机端 2x2 四宫格、首屏裁决台合流 (<=110px)、存量自动路由与表格优化
1. 修改 `app_gui.py` CSS:
   - 在 `@media (max-width: 768px)` 与 `@media (max-width: 640px)` 中，强制将顶层四大功能主导航设为 **2x2 双排四宫格**：`grid-template-columns: repeat(2, 1fr) !important; gap: 6px !important;`，按钮高度 `40px !important; font-size: 13.5px !important;`，确保「🔍 穿透工具」在手机端 100% 完整可见！
   - 将顶部 4 张全局指标卡设为 **2x2 田字格紧凑布局**，节省 50% 首屏高度。
2. 重构首屏为「🧭 首席投顾今日裁决台」:
   - 彻底废除同时存在五维备忘录大框和今日投顾参谋折叠框的双重堆叠；
   - 默认直显区总高度严格控制在 **≤ 110px**：第一行「今日核心定调 + 仓位推导因果公式 + 数据截面时间」（flex-wrap 防挤压）；第二行以 **5 个紧凑胶囊（桌面 1x5，手机 2 列流式）** 展示 ≤20 字的人话结论；
   - 下方提供展开按钮「🔭 展开十维深度逻辑、Top 3 机会雷达与十三维风控体检详情」，平滑展开全文、3张赛道卡与风控哨。
3. 存量账本自动路由至 Tab 1 (`💼 持仓调仓`):
   - 在 `switch_active_ledger` 中，当切换至含存量持仓的账本（`len(new_pm.holdings) > 0`）时，自动注入跨 Tab 跳转指令（`tab_index: 1`），并激活 `tab2_diagnosed = True` 与 `tab2_rebalanced = True`，让用户直达 29 只基金实战诊断与三阶手术单。
4. 表格核心列优先与底部紧凑化:
   - 将 Tab 0 建仓表与 Tab 1 持仓表的「基金代码/名称、金额、盈亏率/占比、操作建议」排在前 3~4 列；
   - 表格底部按钮组手机端 2x2 排布，若流动性折价为 0.00 元自动折叠隐藏全 0 冗余大表。

### Milestone 3: 长截图双因子交叉验真与 Tab 3 全真公募摩擦扣减账单
1. 修改 `portfolio_manager.py`:
   - 在 `parse_screenshot_ocr_holdings` 中提取 `yesterday_pnl`，建立会计公式 $R_{\text{yesterday}} = \frac{\text{yesterday\_pnl}}{\text{market\_value} - \text{yesterday\_pnl}}$；
   - 在 `fuzzy_match_fund_by_name` 中增加 `yesterday_return` 参数，实现「名称关键字 + 昨日收益率（容差 ≤ 0.3%）」双因子交叉锁定；
   - 在 `df_preview` 预览表中增加核对状态标签与存疑修改支持。
2. 修改 `strategy_bridge.py` 与 `app_gui.py` Tab 3:
   - 在 Tab 3 时光机盲测与 29 基组合重构中，增加「🧾 中国公募交易规则全真摩擦扣减明细栏」，显式列出申购费、阶梯赎回费、C类销售服务费 (0.40%/年)、T+1/T+2 在途资金损耗与限购拆单次数；
   - 实证投顾重构后组合在最大回撤（-16.76% vs -17.24%）与最大回撤回本天数（394 交易日 vs 452 交易日，净节省 58 交易日）的真实优势。

### Milestone 4: 编写针对性测试并执行全量测试回归
1. 编写 Delta 测试套件：
   - `tests/test_g17_advisory_real_data_and_ten_dimension.py`: 严禁出现 628.5、-0.25%、7.2450 等魔法数字，断言十维投票与因果公式真实可用；
   - `tests/test_g17_friction_and_screenshot.py`: 双因子长截图锁定与全真摩擦账单断言；
   - `tests/test_g17_ui_mobile_and_ledger_routing.py`: AppTest 验证 2x2 CSS 存在性、首屏裁决台渲染与存量账本切换自动跳转 Tab 1。
2. 运行回归测试：
   - 运行针对性测试及既有核心测试，确保 100% 绿灯。
   - 验证 `tests/test_infra.py` 14 项基建测试全量通过。

## Output Deliverables
- 编写完整的实现代码与测试套件。
- 在 `.agents/teamwork/worker_g17_1/handoff.md` 输出五段式交付报告（Observation, Logic Chain, Caveats, Conclusion, Verification Results）。
- 通过 `send_message` 向主编排器汇报。


## 2026-11-11T15:04:52Z
**From**: f28642b6-8afb-4f49-b855-13ffba6400aa
**Context**: 上级最新实测问题修复通知
**Content**: 用户在点击「生成【C3 档位】实盘建仓单与限购拆单」时触发了 `Cannot serialize the return value (of type tuple) in _cached_fund_quote_and_screening()` 局部报错。根因是 `importlib.reload(portfolio_manager)` 导致 FundQuote 类在内存中重载，st.cache_data 无法通过 pickle 序列化。上级已将 `app_gui.py` 中的 `_cached_fund_quote_and_screening` 改为 `@st.cache_resource(ttl=600, show_spinner=False)`，并修复了 `portfolio_manager.py` 中 `search_funds_in_catalog` 与 `slice_long_screenshot_for_ocr` 的缩进。
**Action**: 请在编写与修改 `app_gui.py` 及 `portfolio_manager.py` 时务必保持 `@st.cache_resource` 与正确的函数缩进，切勿将其还原为 `@st.cache_data`，确保 C3 建仓单生成 100% 正常。
