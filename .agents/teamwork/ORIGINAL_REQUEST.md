# Original User Request

## Initial Request — 2026-10-30T00:57:05Z

启动纯金融量化启发式自进化引擎升级任务：在不依赖任何外部大模型 API、严格保持 100% 纯数学因果演绎（No Look-Ahead Bias）的前提下，根除当前系统中导致实盘亏钱的“均线锯齿打脸、跨公司 T+2 在途踏空忽略、固定专家权重、静态底仓风险失控、以及冠军基金超额衰减”五大深层漏洞，在 strategy_bridge.py、portfolio_manager.py、data_loader.py 与 app_gui.py 中植入 5 大启发式自我更新量化算法。请调度以下 4 个协同角色作业：Agent-1（在线学习与自适应状态机专家 - 负责 strategy_bridge.py）、Agent-2（动态风险平价与摩擦效用优化专家 - 负责 strategy_bridge.py 与 data_loader.py）、Agent-3（CUSUM 基金优胜劣汰与白盒 UI 架构师 - 负责 portfolio_manager.py 与 app_gui.py）、Agent-4（红队实盘损耗与因果验证测试员 - 负责 tests/）。

Working directory: d:\Google\Workspace\Wind\AGY2_FundAdvisory
Integrity mode: development

## Verification Resources
- 现有测试套件位于 `tests/` 目录（包含既有 222 项测试），以及系统只读的 4 个裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 由团队在 `tests/` 目录下编写新增自动化测试用例，覆盖在线专家自更新、施密特迟滞防打脸、EWMA波动率倒数配权、在途摩擦效用拦截与 CUSUM 基金轮换。

## Requirements

### R1. 物理安全红线与纯数学因果演绎准则
严禁触碰、修改或解锁已设为系统只读的 4 个裁判基建文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。在不依赖任何外部大模型 API 的前提下，严格保持 100% 纯数学因果演绎（No Look-Ahead Bias），不得引入未来函数。

### R2. Hedge 在线多专家乘性权重自更新算法（strategy_bridge.py）
植入 `OnlineExpertWeightUpdater`：
- 将四大正交分析流派（趋势动量专家、ERP宏观估值专家、均线乖离逆向专家、流动性与期指基差专家）定义为 $K=4$ 个独立输出目标权重的专家模型。
- 基于历史截面 $t \le T$ 的滚动窗口（半衰期 $\gamma = 0.985$），逐期计算每个专家组合的真实风险调整后净效用 $u_{i, t} = r_{i, t} - 0.5 \lambda \sigma_{i, t}^2 - c \cdot \text{Turnover}_{i, t}$。
- 采用在线乘性权重更新公式（Exponentially Weighted Average Forecaster）：
  $$P_{i, t+1} = \frac{P_{i, t}^\gamma \cdot \exp(\eta \cdot u_{i, t})}{\sum_{j=1}^K P_{j, t}^\gamma \cdot \exp(\eta \cdot u_{j, t})}$$
  实时动态更新今日四大专家的话语权权重 $P_{i, T}$。当某一流派在震荡市被连续打脸时权重自动衰减，胜率高、回撤小的流派自动获得更高权重，并在 UI 步骤二中透明展示当前四大策略专家的实时自适应权重占比。

### R3. 施密特迟滞缓冲环与 Sigmoid 连续仓位门控（strategy_bridge.py）
重构状态转移与仓位映射，根除硬阈值跳变与均线锯齿追涨杀跌：
- 双阈值施密特迟滞环：设定非对称进入与退出缓冲区。从防守/震荡态进入进攻态，要求指数向上突破 MA20 至少达到 $+1.2\%$（或综合进攻得分 $Z_t \ge +0.60$）；进入进攻态后，只有当指数有效跌破 MA20 超过 $-1.5\%$（或综合得分跌破 $+0.20$）时才退出进攻态。在 $[-1.5\%, +1.2\%]$ 噪音震荡带内保持原有状态锁定，严禁反复横跳。
- Sigmoid 连续仓位映射：综合趋势斜率、动量差、ERP 分位与期权 IV 构造连续得分 $Z_t$，通过 Sigmoid 函数 $g(Z_t) = \frac{1}{1 + \exp(-k \cdot Z_t)}$ 平滑调节进攻资产与防守资产的配比，消除极端阶跃突变。

### R4. 滚动 EWMA 波动率倒数与动态风险预算配权（strategy_bridge.py 与 data_loader.py）
在 `compute_dynamic_tier_weights` 中：
- 实时计算各候选资产过去 60 个交易日的指数加权移动平均（EWMA）年化波动率 $\sigma_{k, t}$ 与相关性矩阵。
- 在当前档位（C1~C5）的最大回撤与波动率预算下，各资产基础配置权重与其滚动波动率成反比调整：$w_{k, t} \propto \text{SignalScore}_{k, t} / \sigma_{k, t}$。当某类资产短期波动率异常放大或拥挤度超标时，算法自动收缩其风险敞口，将溢出的风险预算转移至低波纯债压舱石。

### R5. 调仓净效用拦截器与真实 A/C 阶梯费率及 T+2 在途踏空折价（portfolio_manager.py 与 strategy_bridge.py）
对每一笔拟生成的存量调仓指令，计算预期调仓净效用 $\Delta U$：
$$\Delta U = \text{ExpectedAlphaGain}_{20d} - \text{ExactRedemptionFee}(\text{FIFO持有天数}) - \text{SubscriptionFee} - \text{InTransitOpportunityCost}(\Delta t_{\text{arrive}}, \sigma_{\text{index}})$$
- 若调出基金与调入基金属于同一基金公司（支持 T+1 基金转换 `SWITCH`），在途踏空天数 $\Delta t_{\text{arrive}} = 0$；若属于跨公司赎回再申购，$\Delta t_{\text{arrive}} = 2 \sim 4$ 天，按当前市场波动率折算在途踏空风险成本。
- 只有当 $\Delta U > \text{MinNetBenefitThreshold}$（预期超额收益足以覆盖真实申赎费 + 在途踏空风险）时才放行调仓指令，否则自动拦截并标记为 `🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动`。在选基时，若同赛道备选基金与当前持仓同属一家基金公司，在选基评分中赋予转换便利度加分。

### R6. 基于 CUSUM 变点检测的赛道冠军基金自动优胜劣汰（portfolio_manager.py 与 strategy_bridge.py）
- 在每个核心赛道内，动态对比全部候选基金的滚动动量超额、跟踪误差、费率损耗、R1 底层重仓股排雷健康度与 R3 聪明钱流向，计算实时综合竞争力得分 $S_{f, t}$，并维护 CUSUM 衰减监测指标。
- 当原定默认基金出现底层重仓股暴雷（R1 扣分）、极度拥挤踩踏（R3 预警）或超额持续跑输同赛道备选基金时，算法自动将综合得分第 1 名的备选基金晋升为当前赛道的推荐冠军标的，并在选基漏斗中明确标注 `🔄 自进化优选：因综合评分领先，已自动为您优选 XXXXX`。

### R7. 透明推演白盒仪式感与大白话分层交互重构（app_gui.py）
- 保留并强化【四阶可展开透明推演白盒】：
  - Step 1：全市场 28,177 只基金四级漏斗与 CUSUM 动态优胜劣汰（点击可展开查看六维打分表与替换下拉框）。
  - Step 2：Hedge 四大策略专家在线自适应定调与施密特防打脸校验（点击可展开查看 4 大专家当前实时权重与市场信号卡）。
  - Step 3：2018-2026 跨牛熊实境压力测试与作战说明书（点击可展开查看五大人话指标深度归因与适宜环境表）。
  - Step 4：真实 A/C 阶梯费率、T+2 在途损耗拦截与限购拆单精算（点击可展开查看摩擦效用核验详情与手机下单小抄）。
- 新增《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》直观卡片（收益从哪来、为什么能赢、最大风险底线）。
- 修复双向变盘触发线：准确输出高于现价的【📈 向上突破进攻线（考虑施密特迟滞上轨）】与低于现价的【🛡️ 向下跌破防守线（考虑施密特迟滞下轨）】。
- 全面推行“大白话结论 + i 悬停原理解析”，生僻金融黑话转化为零门槛大白话主标题，专业公式与数值收纳进 `ⓘ` 悬停提示。
- 确保顶部卡片与步骤三 9 列表格文字精炼，在 1080p 屏幕下零省略号截断、零横向滚动条。

## Acceptance Criteria

### 算法功能与自适应验证
- [ ] 运行在线专家自更新测试，断言 `OnlineExpertWeightUpdater` 在不同历史切片行情下能够动态调整 4 大专家权重，权重和严格为 1.0，且近期表现最优的专家权重自动上升。
- [ ] 运行施密特迟滞防打脸测试，构造指数在 MA20 附近 $\pm 0.5\%$ 微幅震荡测试序列，断言施密特迟滞环能有效锁定状态，不触发频繁满仓换手。
- [ ] 运行 EWMA 波动率倒数配权测试，断言当资产短期波动率放大时，算法自动收缩其风险敞口并转移至低波纯债。
- [ ] 运行摩擦与在途效用拦截测试，断言当预期调仓超额收益低于赎回费 + T+2 在途风险成本时，调仓拦截器能够准确否决劣质换仓，并优先路由同基金公司 `SWITCH` 转换。
- [ ] 运行 CUSUM 基金轮换测试，断言当默认基金出现表现衰减或排雷扣分时，综合得分第一的备选基金自动晋升为推荐冠军标的。

### 交互与界面验证
- [ ] Streamlit 界面提供 4 个独立可展开/收起的推演白盒步骤面板，能正常展开并展示对应明细数据与状态。
- [ ] 界面展示《三句话看懂本方案》三栏卡片，向上突破进攻线严格高于现价，向下跌破防守线严格低于现价。
- [ ] 顶部卡片与步骤三表格在 1080p 屏幕下无文本省略截断，无横向滚动条，专业指标均配备 `ⓘ` 悬停提示。

### 安全红线与服务验证
- [ ] 4 个系统只读裁判基建文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）未被触碰或修改。
- [ ] 全量测试套件（含既有 222 项测试、新增自进化算法测试、以及 Streamlit AppTest 渲染测试）100% 通过。
- [ ] 本地 8501 端口 Streamlit 服务重启并健康运行。

## Follow-up — 2026-10-31T14:24:17Z

启动阶段一重构（后端核心算法与真数据闭环）：本次任务仅聚焦于 portfolio_manager.py、strategy_bridge.py、data_loader.py 与 tests/，严禁在前端打猴子补丁，严禁使用硬编码字典应付测试。请调度以下 4 个协同角色作业：Agent-1（实时限购与估值纠偏专家 - 负责 portfolio_manager.py）、Agent-2（全天候攻防盈利算法专家 - 负责 strategy_bridge.py 与 data_loader.py）、Agent-3（存量持仓调仓裁决与后果推演专家 - 负责 strategy_bridge.py 与 portfolio_manager.py）、Agent-4（红队反作弊与单元测试员 - 负责 tests/）。

Working directory: d:\Google\Workspace\Wind\AGY2_FundAdvisory
Integrity mode: development

## Verification Resources
- 现有测试套件位于 `tests/` 目录，以及系统只读的 4 个裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 由团队在 `tests/` 目录下补充编写完整的端到端与边界断言测试用例，覆盖实时限购与瀑布流拆单、QDII 盘中估值纠偏、全档位动态配权与三段式攻防、调仓适宜度四维裁决与强行调仓四大后果推演、以及双红利底仓协同豁免。

## Requirements

### R1. 物理安全红线与反作弊约束
- 严禁触碰、修改或解锁系统只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。
- 严禁使用 time.sleep 伪造耗时。
- 严禁将 daily_limit 写死为 500 或 1000。
- 严禁让 C3 档位绕过动态权重计算函数。
- 严禁在前端打猴子补丁，严禁使用硬编码字典应付测试。

### R2. 废除硬编码限额，实现实时限购获取与多级瀑布流拆单及 QDII 盘中估值纠偏（portfolio_manager.py）
- 在 `portfolio_manager.py` 中新增 `fetch_realtime_fund_quota(fund_code: str) -> Dict[str, Any]`：
  - 调用 `akshare.fund_purchase_em()` 获取全市场基金当日申购状态（开放申购/限制大额申购/暂停申购）与 `日累计限定金额`，并在本地 SQLite/Parquet 中建立带日期戳的缓存表（当日有效，断网时读取最近一次真实缓存）。
  - 返回结构：`{"fund_code": code, "status": "开放申购"|"限制大额"|"暂停申购", "daily_limit": float, "is_limited": bool}`。
- 重写 `generate_zero_start_blueprint()` 与调仓拆单逻辑中的限额分配算法（多级瀑布流拆单）：
  - 当某赛道首选基金分配金额 `target_amt > quota["daily_limit"]` 时：
    1. 首选基金仅分配 `min(target_amt, quota["daily_limit"])`（若暂停申购则为 0），其 `action_guide` 动态生成为 `f"单日限额¥{int(quota['daily_limit'])}·已拆单"`（严禁写死“限额买500”）；
    2. 剩余金额 `rem_amt` 按该赛道备选基金评分顺序逐只尝试分配，且每一只备选基金必须同样调用 `fetch_realtime_fund_quota(alt_code)` 检查其自身限额；
    3. 若备选基金自身不限购（`daily_limit >= rem_amt`），其 `action_guide` 必须显示为 `"承接超额·不限购正常买"`；若备选基金自身也限购（如限额 1,000 元），则该备选基金最多只分配 1,000 元，剩余未分配完的资金自动生成 `dca_plan`（如：`剩余¥4,500受全市场QDII限额约束，建议分5个交易日定投买入，或暂存货币/黄金底仓`）。
- 修复 QDII 与跨市场基金盘中估值（`gszzl`）失真：
  - 在 `fetch_realtime_fund_quote()` 中，对 QDII 标普/纳指及黄金联接基金，同时对比底层基准实时涨跌幅（`sh513500` / `gb_inx` / `sh518880`）。若基金估算涨跌幅 `gszzl` 与基准涨跌幅绝对偏差 `> 1.5%`（如 050025 显示 +0.49% 而 001071 异常显示 -4.92%），自动使用基准实时涨跌幅乘以 0.95 覆盖纠偏。

### R3. 清除静态权重劫持与打通三段式攻防闭环（strategy_bridge.py 与 data_loader.py）
- 清除静态权重劫持：
  - 检查 `generate_zero_start_blueprint()` 与 `get_latest_market_snapshot()`，确保 C1 至 C5 所有档位的目标基金配比 100% 由 `compute_dynamic_tier_weights()` 动态算出（融合 Hedge 四大专家实时权重与 EWMA 波动率倒数），严禁在 `tier == "C3"` 时直接返回写死的 `0.38 / 0.30 / 0.14 / 0.12 / 0.06` 常数。
- 在 `compute_dynamic_tier_weights()` 中植入完整低买高卖闭环：
  1. 左侧极值超卖吸筹：当 `erp_percentile >= 75.0` 且沪深300或科创50的 20 日均线乖离率 `bias_20 <= -4.5%`（极度超卖）时，自动从纯债仓位中划拨 `10% ~ 15%` 仓位逆向增配高弹性宽基（011613 / 001053），在底部左侧吃反弹。
  2. 右侧施密特迟滞防打脸：维持 `[-1.5%, +1.2%]` 均线迟滞缓冲带，在震荡噪音期锁定仓位不折腾。
  3. 右侧极端超买阶梯止盈：当进攻标的出现 `bias_20 >= +6.5%`（短期暴涨严重超买）或触发 `crowding_warning == True`（极度拥挤且聪明钱流出）时，不等跌破均线，主动将高波动成长仓位削减 `30% ~ 35%` 并落袋转入纯债（002351）与红利低波（005561），锁住牛市脉冲利润。
- 在回测与实盘算子中对齐 7天/30天/180天 真实阶梯赎回费。

### R4. 今日调仓适宜度裁决器与强行调仓四大后果推演器（strategy_bridge.py 与 portfolio_manager.py）
- 新增方法 `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3") -> Dict[str, Any]`：
  - 综合评估并返回：
    - `verdict_level`: `"SUITABLE"`（🟢 今日适合调仓） / `"HOLD_ON"`（🟡 今日建议按兵不动） / `"FORBIDDEN"`（🔴 今日不宜调仓·高损预警）
    - `verdict_title`: 一句话鲜明结论（如：`🟡 今日建议按兵不动：大盘处于均线震荡噪音带，且您的持仓最大偏离仅 1.2%`）
    - `reasons_4d`: 包含 `market_position_reason`（近期行情位置诊断）、`clock_window_reason`（15:00交易时钟诊断）、`deviation_utility_reason`（偏离度与净效用诊断）、`lockup_fee_reason`（FIFO批次锁定期诊断）4 个字段的详细白话字典。
- 新增方法 `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3") -> Dict[str, Any]`：
  - 同时计算并返回两种调仓模式的完整订单列表与四大后果对比数据：
    - `mode_gentle`（模式一：温和免伤调仓——仅卖出已满免赎回费期份额、优先同基金公司转换 `SWITCH`、遵循 3% 免折腾阈值）；
    - `mode_forced`（模式二：强行一步到位调仓——无视 3% 缓冲带与持有期限制，强行将所有持仓对齐至今日目标权重，供“如果今天一定要调仓”场景使用）；
    - 每个模式下均精确计算 `consequences` 字典：
      1. `fee_loss`: `{"redemption_fee": float, "penalty_fee_7d": float, "subscription_fee": float, "total_fee": float, "payback_days": int}`（精确到每一笔 FIFO 批次的实际持有天数阶梯费率）；
      2. `in_transit_risk`: `{"in_transit_amount": float, "in_transit_pct": float, "lock_days": str, "switch_saved_amount": float, "missed_rally_cost_est": float}`（跨公司换仓 T+2/T+4 在途资金空窗期与潜在踏空成本）；
      3. `risk_shift`: `{"equity_before": float, "equity_after": float, "vol_before": float, "vol_after": float, "mdd_before": float, "mdd_after": float, "div_yield_before": float, "div_yield_after": float}`；
      4. `lockup_reset`: `{"new_buy_amount": float, "reset_warning_text": str}`（新买入资金重新触发 7 天 1.5% 惩罚锁定期与 A 类免赎期清零提醒）。
- 修复 `calculate_stock_overlap_matrix()`：
  - 将策略推荐的双红利底仓对 `{"100032", "005561"}` 与限购伴生对 `{"050025", "001071"}` 均纳入组合协同豁免池，计算 `max_non_diag_unexcused`（非豁免最大重叠度），确保当用户持有标准推荐组合时绝不触发黄色伪分散警告。

### R5. 红队单元测试与断言覆盖（tests/）
- 对上述 3 个模块的真实返回值与边界条件进行严格断言测试。

## Acceptance Criteria

### 算法功能与真实数据闭环
- [ ] `fetch_realtime_fund_quota` 成功拉取全市场基金申购状态与限额并落盘带日期戳缓存，断网时能够正确回退读取最近一次真实缓存。
- [ ] 多级瀑布流拆单算法在限购时正确分配首选基金、备选基金并在全市场限购超额时生成 `dca_plan`，`action_guide` 动态生成且无硬编码数字。
- [ ] QDII 盘中估值异常（与基准偏差绝对值 > 1.5%）时，自动按基准涨跌幅 * 0.95 覆盖纠偏。
- [ ] C1 至 C5 全档位目标基金配比 100% 由 `compute_dynamic_tier_weights()` 动态算出，C3 档位不存在硬编码静态常数拦截。
- [ ] 三段式攻防逻辑（左侧极值吸筹、右侧施密特迟滞、右侧极端超买止盈）在对应行情与指标触发时准确执行仓位划拨与调整。
- [ ] 回测与实盘算子严格对齐 7天/30天/180天 真实阶梯赎回费。
- [ ] `evaluate_today_rebalance_suitability` 返回符合规定的 `verdict_level`、`verdict_title` 与包含 4 个维度的 `reasons_4d` 字典。
- [ ] `simulate_rebalance_modes_and_consequences` 正确输出 `mode_gentle` 与 `mode_forced` 两种调仓模式及其完整的 `consequences`（fee_loss, in_transit_risk, risk_shift, lockup_reset）量化推演数据。
- [ ] `calculate_stock_overlap_matrix` 正确豁免推荐双红利对与限购伴生对，标准推荐组合不产生伪分散误报。

### 安全红线与工程质量
- [ ] 4 个只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）未被修改或触碰。
- [ ] 代码中无 `time.sleep` 伪造耗时，前端未打猴子补丁，测试中无硬编码字典应付断言。
- [ ] 全量 pytest 测试套件 100% 通过。

## Follow-up — 2026-10-31T16:05:31Z

系统配额已恢复，请继续推进 Final Gate 终审大决战与全量验收任务。
