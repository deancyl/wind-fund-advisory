# Dispatch Instructions

## 2026-11-08T05:46:41Z

[Message] timestamp=2026-11-08T05:46:41Z sender=d23af1d4-4a8a-4a0d-b138-955d2548f18d priority=MESSAGE_PRIORITY_HIGH content=启动 G9 世代外傻内精渐进式披露交互降噪重构与底层量化因果律严苛纠偏闭环任务，在坚守底层量化模型与风控规则的前提下，重构 Streamlit GUI 为 L1 傻瓜操作层 + L2 机构白盒层并彻底修复 HTML 源码泄露，纠偏因子演化中的未来函数、无风险利率扣除、假序列等问题，完成视觉验收与全量单测归档。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 投顾决策引擎：`advisory_engine.py`
  - 组合管理与风险监控：`portfolio_manager.py`
  - 数据加载与回测执行：`data_loader.py`
  - 四大只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- 审计参考文档：
  - `c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md`
  - `c:\Users\deanc\Downloads\agy2_app_gui.md`

## Verification Resources
- 自动化测试套件：`pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py` 及针对 G9 交互降噪与量化纠偏新增的专项测试用例。
- 本地 Streamlit 服务端点与健康探针（`http://127.0.0.1:8501/_stcore/health`），配合 `/browser` 工具进行多模态视觉走查。
- 参考审计文档：`c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md` 与 `c:\Users\deanc\Downloads\agy2_app_gui.md`。

## Requirements

### R1. 核心设计哲学、安全底线契约与只读约束
- 实行“外傻内精”原则（L1 傻瓜操作层 + L2 机构白盒层）：绝不阉割任何底层专业量化模型与风控规则，L1 默认视图坚持结论先行、AI 自动托管最优参数、一步直达交易清单；将复杂的参数微调、蒙特卡洛 10,000 次分布、历史黑天鹅明细与选基漏斗大表收纳进 L2 专业白盒折叠抽屉中，做到新手 3 秒无脑跟单、专家一键下钻看透底层证据。
- 严禁修改四个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
- 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 严禁破坏现有 50+ 项自动化测试套件的兼容性（保留现有测试依赖的关键 `session_state` 键名与函数入口），确保原有测试与新增测试 100% 绿灯通过。
- 严禁触碰全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md`，所有经验规范必须写入当前工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### R2. 全局交互降噪、HTML 纯化与傻瓜化操作流重构（修改 app_gui.py）
- 彻底修复大屏裸露 HTML 代码块缺陷（Rule 27）：在首屏“全市场优选赛道 · Top 3 优选自选”下方，“历史三大牛熊拐点实盘对照尺”（`render_historical_inflection_ruler_html`）及所有富文本 HTML 组件，强制使用 `_clean_html(...)` 剥离每行首尾空格与空行，并通过统一入口 `safe_markdown_html(...)` 渲染，彻底杜绝 CommonMark 4+ 空格缩进导致的原始 HTML 源码大面积泄露，实现全屏零代码泄露。
- 首屏双翼看板瘦身与今日一句话傻瓜行动总开关：
  - 在双翼看板最上方提炼渲染一条高辨识度的“今日投顾行动总开关”：用一句大白话告诉用户今天到底要不要操作（例如“🟢 今日建议：按兵不动安心吃息”或“🟡 今日建议：14:30 尾盘有 1 项免赎置换机会”），并配上一键直达对应工作区的按钮。
  - 双翼看板左翼默认仅展示精炼市场脉搏与 Top 3 优选赛道卡片（展示今日实时涨跌、动态量化推荐依据与优选基金代码）；将 14 大赛道温度计总表与基因进化 60 日轨迹图保持在折叠框或 Popover 内按需查看。右翼预警哨移除开发口号尾缀，容器高度自适应无截断。
- Tab 1 新资建仓：参数 AI 智能托管与一键直出全案：
  - 简化步骤一前置输入：在 L1 默认层，用户只需设定拟投资总本金（带中文万元防错核对）与期望目标收益/风险档位（C1 至 C5），系统根据当前宏观同温层自动托管匹配最优量化定权模型（如鲁棒双核 HRP）、优选基金只数（默认 6 只）、持有期与限购过滤；并在旁边提供一个精致的“⚙️ 机构级模型与参数微调（已智能托管）”折叠面板，点开即可自由调整 7 大定权模型、3 至 15 只基金数量与风险测评问卷。
  - 推演与生成建仓单合流提速：主操作按钮默认一键完成量化推演并直接展示底部的实盘建仓执行单与一键复制下单小抄，免去用户先点步骤二再滑到底部点步骤三的二次点击。
  - 收敛步骤二的 16 张卡片轰炸：在 L1 默认层，仅并排展示最核心的 3 张人话结论大卡（预期达标胜率与年化票息安全垫、最坏回撤金额与最长水下回本天数、攻防仓位分配逻辑）；将历史三大黑天鹅承压卡片、10,000 次蒙特卡洛块重采样 CVaR 面板、2.8 万只六维选基漏斗评分表统一收进带关键指标摘要标题的“🔬 展开机构级量化压力测试与选基白盒证据”折叠面板中，让页面垂直长度缩短 60%。
- Tab 2 持仓调仓：首屏极致降噪与极速录基弹窗化：
  - 合并顶部概览卡与安全垫看板：将 4 张资产概览卡与浮盈安全垫破净临界点浓缩为紧凑的顶栏看板，将 -3%、-5%、-10% 三级大盘急跌承压卡片收进看板内的可展开详情中，消除首屏大面积色块堆叠。
  - 将原本占据整行的 5 列极速录基吧台改造为持仓明细表上方工具栏中的“➕ 极速录基”Popover 弹出框，平时完全不占用垂直高度，点击即弹、录完即合。
  - 严格落实双视图物理隔离：在“持仓诊断与智能调仓”主模式下，绝不渲染底部的账本工具坞；仅当切换至“账本运维与实盘复盘档案”模式时，才在主画布平铺展示粘贴导入、FIFO 批次透视、实盘净值与 Brinson 复盘账单、T+1 对账及同公司转换模块。清理全页重复出现的免折腾缓冲带滑块（全页仅保留一处）。

### R3. 底层量化因果律与数据真实性严苛纠偏（修改 advisory_engine.py、portfolio_manager.py 与 data_loader.py）
- 根除 `OnlineHeuristicFactorEvolver` 中的同日未来函数、夏普未扣无风险利率与伪造轨迹：
  - 在 `_evaluate_population` 中，第 t 日基于收盘特征 $F[t]$ 选出的赛道权重 $P[t]$，必须严格滞后一期作用于第 t+1 日的真实收益率 $R[t+1]$（即 $P[:-1]$ 对应 $R[1:]$），并在合成动态净值序列 `nav_dynamic` 时从日度收益率中真实扣除单边 10 bps 的换手摩擦成本。
  - 计算夏普比率时，严格遵照 `AGENT_SPEC.md` 从日均收益中扣除 2.0% 年化无风险利率（`0.02 / 250.0`）。
  - 废除 `get_60d_rolling_nav_and_trajectory` 中的 `lam` 人工线性插值公式，改为按每 5 个交易日推进式样本外滚动演化（Walk-Forward），真实记录各期四维权重与样本外净值。
- 跨市场交易日严格对齐、清除假序列与 2.5 亿假规模兜底：
  - 在 `_extract_sector_price_matrix` 中以 A 股交易日历为基准索引对齐 14 大赛道价格序列，彻底废除缺失数据时使用 `np.linspace(1.0, 1.05, window_days)` 伪造单边上涨直线的做法。
  - 在 `ActiveRiskSentry.inspect_portfolio` 中，当 `fund_metadata` 缺少规模字段时，主动穿透 `DataLoader` 与基金目录反查真实规模，废除 `else: aum = 2.5` 的静默假规模兜底。
  - 在 `evaluate_sector` 中将盘中实时涨跌幅更新至价格序列末尾重算真实的 MA20、Bias20、Slope20 与 ER20，动态生成与指标方向 100% 一致的量化入选依据；在 `ActiveRiskSentry` 中新增投资者适当性越界预警（检测实盘持仓是否超出 C1 至 C5 风险上限），并在 `evaluate_rebalance_audit` 中实装 Brinson 三维超额归因（配置效应、选基效应、摩擦节省）。

### R4. 多模态视觉验收、全量单测与 Git 归档闭环
- 彻底重启 8501 端口服务并清理缓存，调用 `/browser` 打开 `http://localhost:8501` 以挑剔的新手与专业买方双视角走查：确认首屏一眼看懂今日行动总开关；确认“历史三大牛熊拐点实盘对照尺”及全屏无裸露 HTML 源码块泄露；确认 Tab 1 与 Tab 2 默认视图清爽傻瓜、无卡片堆砌；展开 L2 专业折叠面板时所有高阶图表、蒙特卡洛、热力图与四象限散点图完整清晰、零文字重叠、640px 窄屏零水平溢出。
- 运行全量自动化测试套件（包含 `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`）并补充 G9 专项断言，确保 100% 绿灯通过。
- 确认四个只读裁判文件零修改，确认 `data/ledgers_index.json` 仅保留干净的主实盘账本，清理所有临时脚本。
- 更新项目根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`，执行 `git add -A`、`git commit`、`git tag -a v3.9-G9` 并推送至 GitHub 远端（严禁创建任何 GitHub Release）。
- 最终必须通过独立的胜利审计（Victory Audit）确认。
- 在报告末尾输出一段供下一轮直接复制执行的 G10 世代进化指令（直接以 `/goal /boost /teamwork` 开头，包含 `/browser` 调用，保持纯文本无特殊符号排版，包含全量测试与 Git Tag 同步要求）。
