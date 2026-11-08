# Scope: G9 Generation Project Plan

## Architecture
- **Quant & Risk Engines**: `advisory_engine.py`, `portfolio_manager.py`, `data_loader.py`
  - 因果律对齐：$P[:-1]$ 对应 $R[1:]$；双边换手摩擦扣除（单边 10 bps）；夏普比率扣除 2.0% 无风险利率（`0.02 / 250.0`）。
  - 推进式 Walk-Forward 滚动演化：12 个 5 日切片，严格样本外收益结算，废除 `lam` 线性插值。
  - 数据真实性：以 A 股交易日历为基准索引对齐 14 大赛道价格，彻底清除 `np.linspace(1.0, 1.05)` 假序列；长周期 120 日估值中枢与官方估值分位融合。
  - ActiveRiskSentry：三级真实穿透反查 AUM（入参 -> DataLoader 湖仓 -> 核心/扩展目录），清除 `else: aum = 2.5` 兜底；C1-C5 投资者适当性越界预警。
  - 盘中末端 K 线重算：MA20, Bias20, Slope20, ER20；动态量化依据文本方向 100% 自洽。
  - Brinson-Fachler 经典模型：大类配置效应、选基效应、摩擦规避三维拆解，恒等式严格平账。
  - `FundHolding.holding_days` 添加 setter 修复 C 类赎回测试拦截。
- **Streamlit GUI Layer**: `AGY2_FundAdvisory/app_gui.py`
  - HTML 纯化（Rule 27）：`_clean_html` 剥离每行首尾空格与空行，全域 100% 收口至 `safe_markdown_html`，全屏 0 灰色代码块泄露。
  - 首屏双翼看板：顶端渲染“今日投顾行动总开关”大白话横幅 + 一键跳转工作区按钮；左翼 Top 3 赛道卡片精炼，14 赛道温度计与 60 日演化轨迹维持折叠/Popover；右翼预警哨容器高度自适应无截断。
  - Tab 1 新资建仓：L1 双输入（拟投资本金 + C1-C5 风险档位），AI 智能托管定权模型与基金只数；L2 机构级参数与 7 大模型折叠微调面板；一键合流直出建仓单；步骤二收敛为 3 张人话大卡（怎么赚钱/风险底线/为什么能赢），10k 蒙特卡洛、三大黑天鹅与选基漏斗大表收纳进 L2 白盒抽屉。
  - Tab 2 持仓调仓：顶部概览卡与安全垫看板合并为紧凑顶栏，-3%/-5%/-10% 急跌承压收进折叠详情；极速录基改造为表格工具栏中的“➕ 极速录基” Popover 弹窗；严格双视图物理隔离，单源 `tab2_rebal_buf_slider`。
- **Verification & Safe Release**:
  - 四大只读裁判文件与 DataLoader 只读契约零变动。
  - 8501 端口静默平滑重启与 `_stcore/health` 探针。
  - `/browser` 桌面与 640px 移动端多模态视觉走查。
  - 全量自动化测试 100% 绿灯。
  - Git commit, tag `v3.9-G9` (无 GitHub Release)，纯文本 G10 进化指令输出。
  - 独立胜利审计（Victory Audit）。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 防未来函数与滞后一期对齐 | P[:-1] -> R[1:], 双边换手摩擦扣除 (单边 10 bps) | M1 | R3 §1 |
| 2 | 夏普比率扣除 2.0% 无风险利率 | 严格日化 0.02 / 250.0 扣除，杜绝纯债虚高夏普 | M1 | R3 §1 |
| 3 | 5日推进式 Walk-Forward 滚动演化 | 废除 lam 线性插值，12 切片样本外滚动演化 | M1 | R3 §1 |
| 4 | A 股日历对齐与清除假序列 | 以 A 股日历为基准对齐，清除 np.linspace(1.0, 1.05) | M1 | R3 §2 |
| 5 | AUM 三级穿透与清除 2.5 亿假兜底 | 湖仓反查真实规模，清除 else: aum = 2.5 | M1 | R3 §3 |
| 6 | 盘中末端 K 线重算与动态证据链 | 末端更新重算指标，生成 100% 自洽量化依据 | M1 | R3 §4 |
| 7 | C1-C5 投资者适当性越界预警 | 巡检持仓权益占比上限，超额预警与一键降波 | M1 | R3 §5 |
| 8 | Brinson 三维超额收益归因拆解 | 配置效应 + 选基效应 + 摩擦节省，数学恒等式平账 | M1 | R3 §5 |
| 9 | FundHolding.holding_days setter 修复 | 补齐 setter 支持批次赋值，修复单测拦截点 | M1 | 调查捕获 |
| 10 | HTML 纯化与 safe_markdown_html 收口 | 清理 20 余处裸调，消除 CommonMark 4+ 空格泄露 | M2 | R2 §1 |
| 11 | 首屏双翼看板瘦身与行动总开关 | 顶端渲染 1 句白话指令总开关 + 一键跳转工作区 | M2 | R2 §2 |
| 12 | Tab 1 L1 双输入与 AI 参数智能托管 | 仅本金与 C1-C5 档位，自动托管模型与只数，L2 折叠专家面板 | M2 | R2 §3 |
| 13 | Tab 1 一键推演直出实盘建仓单 | 合流推演与建仓单生成，消除二次点击 | M2 | R2 §3 |
| 14 | Tab 1 步骤二 16 卡收敛为 3 人话大卡 | 赚钱/底线/赢因 3 大卡，黑天鹅/蒙特卡洛/漏斗收进白盒抽屉 | M2 | R2 §3 |
| 15 | Tab 2 顶部资产概览与安全垫合流 | 紧凑顶栏看板，-3%/-5%/-10% 急跌承压收纳进折叠详情 | M2 | R2 §4 |
| 16 | Tab 2 极速录基 Popover 弹窗化 | 5 列表单改为表格工具栏“➕ 极速录基” Popover，常态 0 高度 | M2 | R2 §4 |
| 17 | Tab 2 严格双视图隔离与缓冲带单源 | 主模式不渲染工具坞，保留单源 tab2_rebal_buf_slider | M2 | R2 §4 |
| 18 | 四大只读裁判与 DataLoader 契约保护 | 锁定 SHA-256 哈希与 simulate_execution 签名 | M3 | R1 |
| 19 | 本地 8501 端口平滑重启与探活 | 原生 CREATE_NO_WINDOW 托管，_stcore/health 返回 200 | M3 | R4 |
| 20 | /browser 桌面与 640px 视觉走查 | 桌面与 640px 窄屏全要素走查，确认 0 代码泄露与 0 截断 | M3 | R4 |
| 21 | 全量单测回归与 G9 专项断言 100% | 运行 50+ 项现有测试及 G9 专项用例，100% 绿灯 | M3 | R4 |
| 22 | Git 标签归档与 G10 纯文本指令自举 | commit, tag v3.9-G9, 禁 Release, 输出无特殊符号 G10 指令 | M3 | R4 |
| 23 | 独立胜利审计 (Victory Audit) | 独立智能体最终审计确认验收通过 | M3 | R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 底层量化因果律与数据真实性严苛纠偏 | Features 1-9 (advisory_engine.py, portfolio_manager.py, data_loader.py) | none | PLANNED |
| M2 | GUI 交互降噪、HTML 纯化与傻瓜化操作流重构 | Features 10-17 (app_gui.py) | none | PLANNED |
| M3 | 服务平滑重启、视觉走查、全量单测与 Git 归档自举 | Features 18-23 (tests, 8501 health, /browser, git tag, Victory Audit) | M1, M2 | PLANNED |

## Interface Contracts
### M1 ↔ M2: Data & Model Engine Interface to GUI
- `OnlineHeuristicFactorEvolver.get_60d_rolling_nav_and_trajectory`: returns dict `{'dates': list[str], 'nav_dynamic': list[float], 'nav_static': list[float], 'trajectory': list[dict]}`.
- `OpportunityRadarEngine.evaluate_sector`: returns dict with keys `ma20`, `bias_20`, `slope_20`, `er_20`, `sub_scores`, `quantitative_evidence`, `optimal_fund`.
- `ActiveRiskSentry.inspect_portfolio`: returns dict with key `alerts` (list of alert dicts with `level`, `dimension`, `title`, `detail`, `action_type`, `excess_mv`).
- `PortfolioManager.evaluate_rebalance_audit`: returns dict with `brinson_attribution` (keys: `allocation_effect_yuan`, `selection_effect_yuan`, `total_active_add_yuan`, etc.).
- `FundHolding`: contains `@property def holding_days` and `@holding_days.setter`.

### M2 ↔ M3: GUI Session State & Widget Key Contracts
- `session_state` keys preserved: `active_ledger_id`, `active_tier_val`, `mlm`, `pm`, `sel_tab2_active_ledger`, `slider_target_return`, `tab1_step_reached`, `tab1_trigger_sim`, `tab2_diag_cache`, `tab2_diagnosed`, `tab2_rebal_cache`, `tab2_rebalanced`, `target_return_val`.
- Widget keys preserved: `btn_apply_bp_tier`, `chk_confirm_t1_overwrite`, `btn_undo_t1_overwrite`, `btn_run_simulation_now`, `btn_t1_run_all`, `btn_bar_add_holding`, `btn_tab2_diagnose`, `btn_tab2_all`, `rad_tab2_view_mode`, `tab2_rebal_buf_slider`.
- Compatible comments: `# tab2_rebal_buf_slider_bot`.

## Code Layout
- `AGY2_FundAdvisory/`
  - `advisory_engine.py`: M1
  - `portfolio_manager.py`: M1
  - `data_loader.py`: M1
  - `app_gui.py`: M2
- `tests/`: M3
  - `test_infra.py` (READ-ONLY)
  - `test_adv_final_closure.py`
  - `test_g3_evolution_loop.py`
  - `test_gui_multi_ledger_stress.py`
  - `test_g9_causal_brinson_and_suitability.py`
