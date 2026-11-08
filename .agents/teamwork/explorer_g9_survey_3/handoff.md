# G9 世代量化因果律、测试基线兼容性与视觉走查/自举验收方案调研报告 (handoff.md)

**执行智能体**: explorer_g9_survey_3 (Role: Test Baseline Explorer)  
**工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_3`  
**调研范围**: R1 核心安全底线契约、R4 测试兼容性基线与视觉走查/自举验收方案  
**基线时间**: 2026-11-08  

---

## 1. Observation (客观事实与直接观测)

### 1.1 四大只读裁判文件 SHA-256 哈希基线与只读契约验证
通过 Windows PowerShell `Get-FileHash -Algorithm SHA256` 测算，四大只读裁判文件的物理路径与 SHA-256 绝对散列值如下：
1. `D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py`:
   - SHA-256: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
2. `D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py`:
   - SHA-256: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
3. `D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md`:
   - SHA-256: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
4. `D:\Google\Workspace\Wind\tests\test_infra.py`:
   - SHA-256: `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100`

`git status -s` 直接观测确认：上述 4 个文件完全处于未跟踪变更的纯净只读状态，零修改。

### 1.2 `DataLoader.simulate_execution` 函数签名与默认扣费逻辑观测
在 `AGY2_FundAdvisory/data_loader.py` 第 1379-1495 行，`simulate_execution` 现行代码如下：
```python
@staticmethod
def simulate_execution(
    weights_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    is_otc: bool = True,
    penalty_days: int = 7,
    penalty_rate: float = 0.015,
    etf_impact: float = 0.001
) -> pd.DataFrame:
```
- **T+1 延迟执行**: 第 1414 行 `w_exec = w_df[asset_cols].shift(1).fillna(0.0)`，首日持仓采用初始目标。
- **惩罚性费率与阶梯赎回**:
  - `holding_days < penalty_days` (7 天)：扣除 `penalty_rate = 0.015` (1.50%) 严厉惩罚性费率。
  - `holding_days < 30`：C 类 0.50% / A 类 0.75%。
  - `holding_days < 180`：A 类 0.50%，C 类免赎回费 0.00%。
  - `holding_days < 365`：A 类 0.25%，C 类免赎回费 0.00%。
  - `holding_days >= 365`：免赎回费 0.00%。
- **场内 ETF 冲击**: 买入与卖出均计提 `etf_impact = 0.0010` (单边 10 bps)。
- **返回结构**: 返回 DataFrame 包含 `['date', 'nav', 'daily_return', 'turnover', 'friction']`。
- **只读契约**: 函数默认入参签名、参数名列表与默认数值完全保持只读契约，未被任何代码改动。

### 1.3 现有四大测试套件运行实测
执行命令：
`py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`
运行输出：
```
============================= test session starts =============================
collected 50 items

tests\test_infra.py ..............                                       [ 28%]
tests\test_adv_final_closure.py ..............                           [ 56%]
tests\test_g3_evolution_loop.py ............                             [ 80%]
tests\test_gui_multi_ledger_stress.py ..........                         [100%]

================= 50 passed, 121 warnings in 71.02s (0:01:11) =================
```
50 项现有核心基线测试用例 100% 绿灯全部通过。

### 1.4 全自动化扫描测试套件对 GUI (`app_gui.py`) 的依赖目录 (Session State & Widget Keys)
通过独立脚本 `scripts/catalog_session_state_and_widgets.py` 遍历扫描全量测试文件与 `app_gui.py` 源码：
1. **测试直接依赖断言的 13 个 `session_state` 键名**（GUI 重构时必须 100% 保持键名与行为兼容）：
   - `active_ledger_id`: 当前激活账本 ID (默认 `"main_live"`)
   - `active_tier_val`: 当前激活风险等级 (`"C1"` ~ `"C5"`)
   - `mlm`: 全局 `MultiLedgerManager` 实例
   - `pm`: 当前激活的 `PortfolioManager` 实例
   - `sel_tab2_active_ledger`: Tab 2 账本切换下拉框绑定的状态键 (与 `active_ledger_id` 双向同步)
   - `slider_target_return`: 预期目标收益率滑块状态键
   - `tab1_step_reached`: Tab 1 建仓步骤步进标记 (取值 1, 2, 3)
   - `tab1_trigger_sim`: Tab 1 一键推演触发标记 (布尔型)
   - `tab2_diag_cache`: Tab 2 持仓诊断结果缓存容器
   - `tab2_diagnosed`: Tab 2 是否已完成诊断标记 (布尔型)
   - `tab2_rebal_cache`: Tab 2 调仓推演方案缓存容器
   - `tab2_rebalanced`: Tab 2 是否已生成调仓方案标记 (布尔型)
   - `target_return_val`: 目标收益率浮点数值容器

2. **测试直接交互或断言的 18 个 Widget Key**：
   - `btn_apply_bp_tier`: 蓝图档位确认按钮
   - `btn_bar_add_holding`: 极速录基添加按钮
   - `btn_confirm_cash_pop_tb`: 现金池调整确认按钮
   - `btn_pop_del_confirm_tab2`: 删除账本确认按钮
   - `btn_sync_holdings_tab2`: 同步持仓按钮
   - `btn_tab2_all`: Tab 2 诊断并调仓一键合流按钮
   - `btn_tab2_diagnose`: Tab 2 诊断按钮
   - `btn_undo_t1_overwrite`: 撤销 Tab 1 覆盖主实盘按钮
   - `chk_confirm_t1_overwrite`: Tab 1 覆盖主实盘二次确认复选框
   - `rad_tab2_view_mode`: Tab 2 双视图切换单选钮 (`"持仓诊断与智能调仓"` vs `"账本运维与实盘复盘档案"`)
   - `sel_backtest_tier_sub`: Tab 3 策略档位选择器
   - `sel_pk_ledger_1`: Tab 3 双账本 PK 账本 1 选择器
   - `sel_pk_ledger_2`: Tab 3 双账本 PK 账本 2 选择器
   - `sel_tab2_vwap_schedule_item`: Tab 2 微观执行标的选择器
   - `sel_tab4_target_type`: Tab 4 穿透组合对象选择器
   - `slider_target_return`: 目标收益率输入滑块
   - `tab1_sel_model_type`: Tab 1 机构级定权模型选择器
   - `tab2_rebal_buf_slider`: Tab 2 免折腾缓冲带滑块

3. **测试对 `app_gui.py` 源码的静态文本/AST 强约束断言**：
   - `test_adv_final_closure.py`:
     - 必须包含：`FundHolding, HoldingItem`, `calculate_portfolio_yield_cushion`, `evaluate_rebalance_audit`, `行情源状态`, `is_realtime_src`, `🟢 实时盘中源已连接`, `🎯 回测模式`, `📂 选择目标账本或方案`, `双账本同屏 PK`, `📂 选择穿透体检组合对象`, `resolve_fund_display_name`, `<b>{len(pm.holdings)} 只</b>`, `coloraxis_showscale=False`, `height=380`。
     - 严禁包含：`option_key_map.get(sel_target_type`, `target_options = [opt_cur_ledger]`, '`{len(pm.holdings)} 只`'。
   - `test_g3_evolution_loop.py`:
     - 必须包含：`evaluate_dynamic_correlation_mutation`, `0.75`, `10,000 次蒙特卡洛块重采样`, `CVaR 99%`, `最大流动性折价损失预估`, `calculate_vwap_execution_slippage`, `VWAP优化执行滑点`, `vwap_rebal_orders`, `买入快速冲击模拟损耗`, `sel_tab2_vwap_schedule_item`。
   - `test_g8_ux_and_realtime_fusion.py`:
     - 必须包含：`rad_tab2_view_mode`, `is_t2_main_mode`, `dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6`, `sub_tab1, sub_tab2, sub_tab3`, `tab2_rebal_buf_slider`, `with st.container(height=380):`。
     - 严禁包含：`[主动风险预警哨 · 四维巡检升级版]`。

---

## 2. Logic Chain (推理链条与技术推导)

### 2.1 契约不可侵犯性推导
- **推导 1 (裁判防作弊)**: 基于观测 1.1，4 个裁判文件是评判模型防过拟合、因果律、AST 特征和盲测防作弊的外部最高裁判。任何对这些文件的修改都属于判题作弊，必须守死 SHA-256 零变动。
- **推导 2 (回测模拟执行算子只读)**: 基于观测 1.2，`DataLoader.simulate_execution` 包含标准的 T+1 执行算子、7天 1.50% 阶梯惩罚费率与 ETF 冲击模型。测试套件 `test_infra.py` 与 `test_challenger_g9_m2_stress.py` 通过 `inspect.signature` 强制核验其函数签名和默认参数，任何破坏参数名称或默认值的行为都会直接导致裁判红牌。

### 2.2 GUI 重构对现有自动化单测兼容性推导
- **推导 3 (L1/L2 交互重构防回退)**: 用户要求将 Tab 1 与 Tab 2 重构为“L1 傻瓜操作层 + L2 机构白盒层”，收敛大量卡片。然而，基于观测 1.4，`test_gui_multi_ledger_stress.py` 使用 `streamlit.testing.v1.AppTest` 对 `app_gui.py` 进行了全状态机测试，直接向 `at.session_state` 注入并读取 `active_ledger_id`, `active_tier_val`, `pm`, `sel_tab2_active_ledger`, `tab1_step_reached`, `tab1_trigger_sim` 等 13 个键；同时测试静态检查了 18 个 Widget Key 和特定的模块导入/展示文本。
- **结论推导**: 重构 L1 时，绝不能删除或重命名这 13 个 session_state 键与 18 个 widget key。必须将高级参数和复杂组件放入 `st.expander` 或 `st.popover`（例如 `⚙️ 机构级模型与参数微调`、`🔬 展开机构级量化压力测试与选基白盒证据`、`➕ 极速录基`），既满足 L1 视口降噪 60%，又保证 AppTest 与静态断言 100% 兼容。

### 2.3 HTML 源码泄露根因与防范推导
- **推导 4 (CommonMark 4+ 空格缩进陷阱)**: Streamlit 在执行 `st.markdown(html, unsafe_allow_html=True)` 时，底层 Markdown 渲染器遵循 CommonMark 规范：任何以 4 个及以上空格开头的文本行，会被强制判定为 Indented Code Block（缩进代码块），从而将原本应解析为 DOM 的 `<div>`、`<span>` 等直接转义并打印为灰色代码块。
- **修复逻辑**: 
  1. 所有返回 HTML 字符串的函数（如 `render_historical_inflection_ruler_html`、`render_portfolio_cushion_and_stress_card_html`）必须在返回值处强制包裹 `_clean_html(...)`，物理剥离每行首尾空格与空行。
  2. 首屏与其他页面严禁直接调用原生 `st.markdown(f"""...""", unsafe_allow_html=True)` 传入多层缩进的 HTML 片段，强制统一收口至 `safe_markdown_html(...)`，实现全屏零 HTML 源码泄露。

---

## 3. Caveats (局限性与审计留白)

1. **测试套件运行时间**: 全量 50 项测试在 Windows 环境下运行约需 70~80 秒（主要由于 `test_gui_multi_ledger_stress.py` 中的 Streamlit AppTest 冷加载以及 `test_g3_evolution_loop.py` 中的 10,000 次蒙特卡洛块重采样）。在验证测试时应保证足够的超时阈值（如 `--timeout=120`）。
2. **`test_ui_pro_redesign_verification.py` 的历史版本差异**: 观测发现该测试文件属于早期 G7 重构遗留（仍断言旧版分类“医药医疗健康”及已废除的“🎯 选择当前穿透体检的组合对象”），而当前官方认可的核心回归套件严格收口为 DISPATCH 中规定的 4 大套件（`test_infra.py`、`test_adv_final_closure.py`、`test_g3_evolution_loop.py`、`test_gui_multi_ledger_stress.py`）及新增的 G9 专项测试。
3. **8501 端口常驻守护**: 在本地进行视觉走查前，必须确认 8501 端口无僵死无窗口进程，探活探针必须以 `http://127.0.0.1:8501/_stcore/health` 返回 HTTP 200 为唯一可信准则。

---

## 4. Conclusion & New G9 Test Specification (结论与新增 G9 测试规范)

### 4.1 新增 G9 测试断言规范 (Design of New G9 Test Assertions)

针对 DISPATCH 要求的 10 大核心量化与工程领域，制定具体可落地的测试用例设计规范：

#### 断言 1: 因果律滞后一期 ($P[:-1] \to R[1:]$) 与双边换手摩擦内扣
- **测试靶点**: `OnlineHeuristicFactorEvolver._evaluate_population`
- **设计断言**:
  1. 构造时间长度 $T=20$ 的特征张量 $F$ 与全零收益率矩阵 $R$；在 $t=8$ 处对赛道 5 注入暴涨冲击 $R[8, 5] = +5.0$。
  2. 验证基线收益与冲击收益在 $t \le 7$ 时的日度组合收益率差值严格等于 0（`abs(R_p[7, 0] - R_p_base[7, 0]) < 1e-9`）。
  3. 即便在 $t=8$ 当天将特征 $F[8, 5, :]$ 飙升至 99.0，也绝不能改变 $t=8$ 当日捕获的收益（因为 $t=8$ 当日的收益只能由 $t=7$ 收盘生成的权重决定）。
  4. 换手摩擦内扣验证：构造高频轮动特征张量，验证净收益率矩阵满足 `net_R_p = gross_R_p - 0.0020 * daily_to`，动态净值序列末端值严格小于零摩擦净值 `actual_final_nav < (1.0 + gross_r)**(T-1)`。

#### 断言 2: 夏普比率强制扣减 2.0% 年化无风险利率
- **测试靶点**: `OnlineHeuristicFactorEvolver._evaluate_population`
- **设计断言**:
  1. 构造日收益率均值为微弱正收益 $r_{\text{day}} = 0.00004$ (年化约 1.0%，低于 2.0% 无风险利率) 的收益率矩阵。
  2. 验证计算得到的夏普比率 `metrics["sharpe"][0]` 严格为负数（`sharpe < 0.0`），彻底消除低波纯债资产凭借接近 0 的波动率白嫖虚高夏普的漏洞。

#### 断言 3: 5 交易日推进式 Walk-Forward 滚动演化轨迹真实性
- **测试靶点**: `OnlineHeuristicFactorEvolver.get_60d_rolling_nav_and_trajectory`
- **设计断言**:
  1. 验证返回结构包含 60 个交易日的 `dates`, `nav_dynamic`, `nav_static`, `trajectory`。
  2. 提取 60 日四维权重轨迹序列，计算其二阶差分 `np.diff(w_val, n=2)`。
  3. 断言二阶差分绝不能恒为 0（`not np.allclose(diff2, 0.0, atol=1e-6)`），且存在显著非零波动（`np.any(np.abs(diff2) > 1e-4)`），从数学上彻底证明已废除 `lam = (t+1)/60.0` 伪线性插值。

#### 断言 4: A 股交易日历基准对齐与彻底消灭 `np.linspace` 假序列
- **测试靶点**: `OnlineHeuristicFactorEvolver._extract_sector_price_matrix`
- **设计断言**:
  1. 验证 14 大赛道价格矩阵严格以 A 股交易日历 `target_dates` 对齐（基于 `reindex(target_dates).ffill().bfill()`）。
  2. 缺失数据严查：在 `advisory_engine.py` 源码中静态正则断言 `np.linspace(1.0, 1.05` 出现次数严格为 0。
  3. 当某一赛道全部缺失时，返回的常数数组收益率为 0，夏普为负，绝无人工单边上涨直线。

#### 断言 5: 真实规模三级穿透反查与彻底废除 2.5 亿假规模兜底
- **测试靶点**: `ActiveRiskSentry.inspect_portfolio` (第 1757-1830 行)
- **设计断言**:
  1. 传入基金规模为 0.30 亿元 (<0.5亿) 的迷你基，验证触发 `level="red"`, `aum_status="LIQUIDATION_DANGER"`，标题明确提示 `<0.5亿清盘警戒线`。
  2. 故意传入不含任何规模字段且不在本地库中的未知代码（如 `"999002"`），验证触发 `level="yellow"`, `aum_status="PENDING_VERIFICATION"`，标题明确提示 `规模待核验`。
  3. 静态检查 `advisory_engine.py`，断言源码中严禁存在 `else: aum = 2.5`。

#### 断言 6: 赛道评估中盘中末端 K 线重算与动态量化证据链方向自洽
- **测试靶点**: `OpportunityRadarEngine.evaluate_sector` 与 `_synthesize_quantitative_evidence`
- **设计断言**:
  1. 传入包含最新估值涨跌幅 `gszzl = +3.5%` 的实时行情快照，验证末端 MA20, Bias20, Slope20 与 ER20 基于最新价重新精算。
  2. 验证动态证据链文案生成：当估值分位 $\le 20\%$ 时，文案必须包含“处于历史极低估黄金击球区”；当正乖离 $> 6.0\%$ 时，文案必须包含“触发反超买均值回归约束”；当信噪比 $\ge 0.60$ 时，必须包含“趋势纯净度高”。文案与数值方向 100% 自洽。

#### 断言 7: 投资者适当性 C1-C5 越界超配与一键降波巡检
- **测试靶点**: `ActiveRiskSentry.inspect_portfolio` (第 1930-1985 行)
- **设计断言**:
  1. 构造权益资产占比达 60%（含高波科技半导体）的组合。
  2. 巡检 C1 保守型客户（上限 20% 权益）：验证确定性触发 `level="red"`, `dimension="投资者适当性"`, `action_type="rebalance_sector"`，且在建议文案中精确输出超配的人民币金额 `¥40,000.00`。
  3. 巡检 C5 进取型客户（上限 95% 权益）：验证 60% 权益持仓合法合规，适当性警报数量为 0。

#### 断言 8: Brinson-Fachler 经典模型三维超额收益拆解与数学平账
- **测试靶点**: `PortfolioManager.evaluate_rebalance_audit`
- **设计断言**:
  1. 验证返回字典包含 7 大兼容性顶级键名：`current_actual_equity`, `shadow_hold_equity`, `rebalance_value_add`, `rebalance_value_add_pct`, `saved_penalty_and_buffer_fees`, `baseline_date`, `shadow_holdings_count`, `brinson_attribution`。
  2. 验证 Brinson 归因严格满足数学恒等式：
     - `abs(allocation_effect_yuan + selection_effect_yuan - total_active_add_yuan) < 1e-4`
     - `abs(allocation_effect_pct + selection_effect_pct - total_active_add_pct) < 1e-4`
  3. 验证 `category_breakdown` 大类明细表包含 9 大类别权重、收益与分项效应。

#### 断言 9: HTML 源码纯化与 CommonMark 4+ 空格缩进防泄露静态断言
- **测试靶点**: `AGY2_FundAdvisory/app_gui.py` 全局渲染入口
- **设计断言**:
  1. 静态扫描 `app_gui.py`：所有返回 HTML 字符串的渲染函数（如 `render_historical_inflection_ruler_html`、`render_portfolio_cushion_and_stress_card_html`）其代码末尾必须包含 `return _clean_html(...)`。
  2. 验证前端富文本渲染统一收口至 `safe_markdown_html(...)`。
  3. 针对 `render_historical_inflection_ruler_html` 生成的真实字符串断言：`all(not line.startswith("    ") for line in html.splitlines())`。

#### 断言 10: Tab 1 与 Tab 2 L1/L2 渐进式披露键名与容器契约
- **测试靶点**: `AGY2_FundAdvisory/app_gui.py` (L1 傻瓜操作层 + L2 机构白盒层)
- **设计断言**:
  1. Tab 1 L1 层暴露 `plan_capital_input`, `tab1_tier_selector`，一键合流直出执行单；L2 收纳于 `⚙️ 机构级模型与参数微调（已智能托管）` 折叠面板中，保留 `tab1_sel_model_type` 等键。
  2. Tab 1 步骤二 L1 层仅展示 3 张人话大卡；蒙特卡洛 10,000 次 CVaR、三大黑天鹅及漏斗大表收纳进 `🔬 展开机构级量化压力测试与选基白盒证据` 折叠抽屉中。
  3. Tab 2 顶部合并看板并收纳三级急跌承压；录基改造为 `➕ 极速录基` Popover（`st.popover`）；主视图模式下物理跳过 6 大运维工具箱展开项，全页仅保留一处 `tab2_rebal_buf_slider`。

---

## 5. Verification Method (独立核验与验收全流程)

### 5.1 自动化单测验证流程
运行核心自动化测试命令：
```powershell
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py
```
- **预期结果**: 全部用例 100% 绿灯通过，0 错误，0 失败。

### 5.2 本地 Streamlit 8501 服务平滑重启与健康探活
执行服务平滑重启脚本：
```powershell
py -3 scripts/restart_service.py
```
- **健康判定条件**:
  1. 使用 Windows 原生 `CREATE_NO_WINDOW` 静默模式托管。
  2. 探测 `http://127.0.0.1:8501/_stcore/health`，收到 HTTP 200 响应。

### 5.3 `/browser` 多模态视觉走查方案
调用 `/browser` 工具访问 `http://localhost:8501`：
1. **桌面视口 (1280x800)**:
   - 核查首屏双翼看板上方是否清晰渲染“今日投顾行动总开关”，确认大白话提示与跳转按钮。
   - 核查“历史三大牛熊拐点实盘对照尺”及首屏晨报，确认全屏零灰色 HTML 源码代码块泄露。
   - 核查左翼 Top 3 赛道卡片的四维指标与动态因果链文案；右翼预警哨的适当性越界预警与清盘排雷。
   - 切换 Tab 1：确认 L1 仅需本金与风险档位，一键直出全案；展开 L2 抽屉确认高阶模型与压力测试图表正常渲染。
   - 切换 Tab 2：确认顶部紧凑看板与“➕ 极速录基”Popover 弹窗正常工作；确认双视图物理隔离生效。
2. **移动端视口 (640px)**:
   - 调整浏览器视口为 640px 宽度，核查对照尺、行情药丸与表格是否启用横向滚动容器 (`overflow-x: auto`)，确认零文字重叠、零半截被切、零水平溢出。

### 5.4 Git 版本归档与 G10 纯文本指令生成协议
1. 校验四大裁判文件哈希与 `DataLoader.simulate_execution` 100% 未变动。
2. 校验 `data/ledgers_index.json` 仅保留干净的主实盘账本，清理临时测试脚本。
3. 执行 Git 归档（严禁创建 GitHub Release）：
   ```powershell
   git add -A
   git commit -m "feat(G9): 外傻内精渐进式披露交互降噪重构与底层量化因果律严苛纠偏闭环"
   git tag -a v3.9-G9 -m "Release v3.9-G9"
   git push origin HEAD
   git push origin --tags
   ```
4. 输出严格遵循规范的 G10 纯文本指令：以 `/goal /boost /teamwork` 开头，包含 `/browser` 调用，全文无任何表情符号、星号、反引号、数学符号或装饰线。

---
**报告完成标志**: 本报告已完整覆盖 R1 核心安全底线与 R4 测试兼容性/验收规范，请调用 `send_message` 向 `orchestrator_12` 汇报完成。
