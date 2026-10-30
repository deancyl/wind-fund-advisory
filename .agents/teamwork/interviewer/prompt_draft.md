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
