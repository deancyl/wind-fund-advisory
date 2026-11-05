# 全栈投顾升级调查报告：三大核心业务模块 (R3)、物理安全红线 (R4) 与测试验证基线 (R5)

**文件路径**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_3\report.md`  
**作者**: Explorer Survey r7_3  
**状态**: 深度调查完成 (Ready for Implementation & Testing)  
**基准日期**: 2026-11-04  

---

## 一、 核心执行摘要 (Executive Summary)

本报告针对用户最新权威需求文档（`ORIGINAL_REQUEST.md`）中的 **R3（三大投顾核心业务模块）**、**R4（物理安全红线与架构规范）** 及 **R5（增量及回归测试体系）** 进行全面深入的源码级穿透调查与数学/算法建模。

当前代码库（`AGY2_FundAdvisory/` 与根工作区）已具备坚实的量化基建（包括全收益对齐矩阵 `DataLoader`、多因子六维选基打分引擎、FIFO 持仓批次跟踪与 `WinRateOptimizer`）。然而，针对业务层的高阶投顾功能，仍存在以下亟待实装的空白与升级点：
1. **【🔭 全市场低估与动量机会雷达】(R3.1)**：尚缺覆盖 14 大核心宽基与细分赛道的统一实时机会扫描引擎（考夫曼 ER 信噪比、MA20 动量拐点、估值分位数、拥挤度安全分四维精算），以及自动萃取 Top 3「黄金击球区 / 右侧共振」赛道与匹配六维最高评分公募基金并一键入池的交互闭环。
2. **【🚨 主动风险预警哨】(R3.2)**：现有风险排雷散落于底层 DuckDB 视图与局部持仓诊断中，尚未在工作台首屏或 Tab 顶部建立统一巡检持仓批次（$\le 3$天警报、刚满 7 天脱离惩罚、C 类刚满 30 天 0 赎回费）、赛道拥挤超买（$Bias_{20} > +6\%$）、迷你基清盘（$<0.5$亿）与均线攻防线的四维主动哨兵。
3. **【🌊 分批建仓与智能定投算子】(R3.3)**：Tab 1 步骤三目前仅提供单次全额交割单，缺乏真实投顾场景下的建仓节奏调控（模式一：⚡ 一次性建仓；模式二：🌊 稳健三步分批建仓且金额严格守恒；模式三：📅 估值自适应智能定投扣款乘数引擎）。
4. **物理红线与测试基线 (R4 & R5)**：裁判核心文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）必须物理锁定；必须在 `tests/` 下构建针对新算子的单元测试与 Streamlit `AppTest` 交互回归测试。

---

## 二、 需求 R3.1：【🔭 全市场低估与动量机会雷达】深度技术方案

### 1. 14 大宽基与核心细分赛道映射全景

机会雷达需扫描全市场 14 个核心资产与赛道。结合本地全收益对齐矩阵 `aligned_matrix_total_return.parquet`、DuckDB 视图 `v_indices` 及公募基金候选池，建立如下映射字典：

| 序号 | 赛道标识符 (`sector_id`) | 赛道名称 | 标的/代理指数代码 | 底层资产性质 | 对应代表性场外公募基金 (A/C) | 估值代理基准 |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `dividend_low_vol` | 红利低波 | `H30269` / `000978.CSI` | 本土权益核心防御 | 005561 (创金合信红利低波A) / 005562 (C) | PE-TTM, 股息率 |
| 2 | `csi_dividend` | 中证红利 | `H00922` / `000922.CSI` | 本土权益高股息 | 100032 (富国中证红利增强A) / 008682 (C) | PE-TTM, 股息率 |
| 3 | `csi_300` | 沪深300 | `H00300` / `000300.SH` | 本土核心大盘蓝筹 | 110020 (易方达沪深300A) / 007339 (C) | PE-TTM, ERP |
| 4 | `csi_500` | 中证500 | `H00905` / `000905.SH` | 本土中盘成长 | 000478 (建信中证500增强A) / 001053 (C) | PE-TTM |
| 5 | `csi_1000` | 中证1000 | `H00852` / `000852.SH` | 本土小盘弹性成长 | 004194 (招商中证1000增强A) / 016634 (C) | PE-TTM |
| 6 | `star_50` | 科创50 | `STAR50_STITCH` / `000688.SH` | 硬科技核心宽基 | 011612 (华夏科创50A) / 011613 (C) | PE-TTM, PB |
| 7 | `semiconductor` | 半导体芯片 | `H30184` / `980017.CNI` | 高弹性细分科技 | 013841 (银华集成电路C) / 008888 (华夏半导体A) | PE-TTM, PS |
| 8 | `pharma_health` | 医药医疗 | `000933` / `399989.SZ` | 消费医药超跌白马 | 161726 (招商国证生物医药A) / 003095 (中欧医疗健康A) | PE-TTM |
| 9 | `consumer_liquor` | 消费白酒 | `000932` / `399997.SZ` | 传统消费核心资产 | 161725 (招商中证白酒A) / 012414 (C) | PE-TTM, PB |
| 10 | `banking_dividend` | 银行高股息 | `399986.SZ` / `000134.SH` | 深度低估金融压舱 | 160418 (华安中证银行A) / 001594 (天弘银行A) | PB, 股息率 |
| 11 | `domestic_gold` | 国内黄金 | `AU9999` / `518880.SH` | 大宗商品与避险对冲 | 000216 (华安黄金易A) / 004253 (C) | 实际利率, 金铜比 |
| 12 | `us_sp500_nasdaq` | 美股标普/纳指 | `SPX_CNY` / `050025.OF` | 海外QDII跨市场 | 050025 (博时标普500A) / 006075 (广发纳指100A) | PE-TTM, ERP差 |
| 13 | `hstech` | 恒生科技 | `HSTECH.HI` / `013402.OF` | 港股离岸互联网科技 | 013402 (华夏恒生科技A) / 013111 (博时恒生科技A) | PE-TTM, 风险溢价 |
| 14 | `pure_bond` | 纯债固收 | `930609` / `H11009` | 纯债与流动性防守 | 002351 (易方达裕祥回报A) / 000086 (工银信用纯债A) | 10Y国债到期收益率 |

### 2. 四维量化评分算子与数学公式 (Four Core Quantitative Metrics)

设任意赛道 $i$ 的历史价格/全收益序列为 $P = [P_1, P_2, \dots, P_T]$，回看窗口为 $N=20$（短线）与 $M=60$（中线）：

#### ① 估值分位得分 ($S_{\text{val}} \in [0, 100]$)
- 获取该赛道对应指数历史滚动 3~5 年估值序列（PE-TTM 或 PB），计算当前截面估值历史分位数 $Pct_{\text{val}} \in [0.0, 1.0]$。
- **公式**：
  $$S_{\text{val}} = 100.0 \times (1.0 - Pct_{\text{val}})$$
- **低估击球区加分 (Golden Zone Bonus)**：若 $Pct_{\text{val}} \le 0.20$（处于历史最便宜的前 20% 极端区间），赋予 $10\%$ 的击球区加权溢价：$S_{\text{val}} = \min(100.0, S_{\text{val}} \times 1.10)$。
- **纯债与黄金特例**：纯债固收基于当前 10Y 国债到期收益率与历史利差折算，基线锚定 75.0 分；黄金基于实际利率与通胀预期折算，基线锚定 70.0 分。

#### ② 考夫曼自适应效率系数信噪比 ($S_{\text{er}} \in [0, 100]$)
- 考夫曼效率比率（Kaufman Efficiency Ratio, ER）精确剥离市场随机噪音，度量单向趋势纯度：
  $$ER_{20} = \frac{|P_T - P_{T-20}|}{\sum_{k=0}^{19} |P_{T-k} - P_{T-k-1}|}$$
  其中分母为过去 20 交易日逐日绝对波动累加和（总路径损耗），分子为净位移。
- **方向与信噪比评分**：
  $$S_{\text{er}} = 100.0 \times \min(1.0, ER_{20} \times 1.6) \times \mathbb{I}_{\text{direction}}$$
  若 $P_T \ge P_{T-20}$（上升趋势），$\mathbb{I}_{\text{direction}} = 1.0$；若处于下行通道，$\mathbb{I}_{\text{direction}} = 0.5$（压制下行单边噪音）。

#### ③ MA20 动量拐点得分 ($S_{\text{mom}} \in [0, 100]$)
- 计算 20 日均线 $MA20_T = \frac{1}{20}\sum_{k=0}^{19} P_{T-k}$ 及其 5 日切线斜率 $Slope_{20} = \frac{MA20_T - MA20_{T-5}}{MA20_{T-5}} \times \frac{250}{5} \times 100\%$。
- 计算乖离率 $Bias_{20} = \frac{P_T - MA20_T}{MA20_T} \times 100\%$。
- **分段打分与 GEMINI.md 规则 8 反超买硬约束**：
  * **右侧共振状态**：$P_T > MA20_T$ 且 $Slope_{20} > 0$ 且 $0\% \le Bias_{20} \le 5.5\%$：
    $$S_{\text{mom}} = 75.0 + 25.0 \times \min\left(1.0, \frac{Slope_{20}}{20.0}\right)$$
  * **超跌拐点状态 (金叉反抽)**：$Bias_{20} \in [-8\%, 0\%]$ 且过去 3 日切线斜率向上勾头：
    $$S_{\text{mom}} = 70.0 + 15.0 \times \left(1.0 - \frac{|Bias_{20}|}{8.0}\right)$$
  * **超买均值回归折价惩罚 (Anti-Overbought Rule)**：若 $Bias_{20} > +6.0\%$，触发均值回归惩罚：
    $$S_{\text{mom}} = \max\left(20.0, 75.0 - (Bias_{20} - 6.0) \times 12.0\right)$$
  * **破位下行状态**：$P_T < MA20_T$ 且 $Slope_{20} \le 0$：$S_{\text{mom}} = \max(20.0, 50.0 + Slope_{20})$。

#### ④ 拥挤度安全分 ($S_{\text{crowd}} \in [0, 100]$)
- 结合赛道换手率分位 $Pct_{\text{turnover}}$、5日北向主力资金流向及持股集中度趋势：
  * 换手率分位 $\le 60\%$（筹码沉淀、非过热）：$S_{\text{crowd}} = 90.0 \sim 98.0$；
  * 换手率分位 $60\% \sim 85\%$（温和活跃）：$S_{\text{crowd}} = 75.0 \sim 85.0$；
  * 换手率分位 $> 85\%$ 或主力资金连续大额流出（极度拥挤）：$S_{\text{crowd}} = 30.0 \sim 45.0$。

#### ⑤ 综合雷达评分与 Top 3「黄金击球区 / 右侧共振」甄选
$$Score_{\text{radar}} = 0.30 \times S_{\text{val}} + 0.30 \times S_{\text{mom}} + 0.25 \times S_{\text{er}} + 0.15 \times S_{\text{crowd}}$$
- **标签判定**：
  * **黄金击球区 (Golden Hitting Zone)**：$S_{\text{val}} \ge 78$ 且 $S_{\text{mom}} \ge 65$ 且 $S_{\text{crowd}} \ge 70$（低估超跌、安全边际极高、底部拐点初现）；
  * **右侧共振 (Right-side Resonance)**：$S_{\text{er}} \ge 75$ 且 $Slope_{20} > 0$ 且 $S_{\text{crowd}} \ge 65$ 且 $Bias_{20} \le 6.0\%$（趋势高信噪比、均线顺势多头）；
  * **避险压舱 (Safe Harbor)**：纯债与黄金类资产，平滑组合尾部波动。
- 排序规则：按 $Score_{\text{radar}}$ 降序排列，排除 $S_{\text{crowd}} < 45$ 的极端踩踏高危板块，自动挑选 **Top 3 机会赛道**。

### 3. 六维评分最高场外公募基金匹配与一键入池

对入选 Top 3 的每个赛道：
1. 遍历该赛道候选基金池（优先 A 类长投底仓与 C 类高弹性进攻波段仓）；
2. 调用 `PortfolioManager.compute_fund_six_dimension_score(code)`（该方法位于 `portfolio_manager.py` 第 4703 行），综合精算：
   * 35% 历史超额 Alpha + 25% 低费率 + 15% 底层排雷健康分 + 10% 北向聪明钱 + 10% 反拥挤度 + 5% 衍生品契合度；
3. 选出该赛道 `overall_score` 最高的代表基金（Champion Fund）；
4. **一键入池交互机制**：
   * 在 Streamlit UI 卡片上提供 `➕ 纳入备选池` 按钮；
   * 点击后，将该标的代码与名称自动写入 `st.session_state.custom_candidate_pool` 与 `st.session_state.custom_fund_overrides`；
   * 触发 Tab 1 步骤一候选池动态扩展，并弹出 `st.toast(f"✅ 已将【{fund_name}】一键纳入备选池！")`。

### 4. UI 页面空间与人体工学集成规范

- **黄金展示位置**：位于主界面顶部【📊 核心指数实时行情带】正下方、四大核心 Tab 正上方；
- **展示容器**：使用精致卡片容器包裹，默认支持折叠/展开（`with st.expander("🔭 全市场机会雷达 · Top 3 黄金击球区与右侧共振精选", expanded=True):`）；
- **布局设计**：采用三列等分卡片（`st.columns(3)`），每张卡片展示：
  - 赛道名称徽章与类型胶囊（如 `🔥 右侧共振 · 科创50`、`🎯 黄金击球区 · 红利低波`）；
  - 四维量化指标迷你进度条或雷达值（估值分位、ER信噪比、MA20斜率、安全分）；
  - 优选公募基金（代码、名称、六维量化得分）；
  - 紧凑按钮 `➕ 纳入备选池`。

---

## 三、 需求 R3.2：【🚨 主动风险预警哨】深度技术方案

### 1. 四维状态自动巡检架构 (4D Watchdog Architecture)

主动风险预警哨针对用户实盘持仓账本及全市场行情进行 4 维全自动巡检：

```
                           ┌──────────────────────────────────────────────┐
                           │      🚨 主动风险预警哨 (Active Watchdog)      │
                           └──────────────────────┬───────────────────────┘
                                                  │
         ┌────────────────────────┬───────────────┴───────────────┬────────────────────────┐
         │                        │                               │                        │
         ▼                        ▼                               ▼                        ▼
【维度一：FIFO批次锁仓】    【维度二：赛道拥挤与超买】        【维度三：基金本体排雷】    【维度四：大盘攻防线】
- ≤3天: 1.50%惩罚警告     - Bias20 > +6%: 超买警示        - AUM < 0.5亿: 迷你基清盘   - 跌破MA20/防守底线
- 刚满7天: 免惩罚解锁      - 极度拥挤 + 筹码发散/北向大额流出 - 经理年限<1年/频繁变更    - 突破MA20/进攻上线
- C类刚满30天: 0费率窗口                                  - 底层重仓股风格漂移
         │                        │                               │                        │
         └────────────────────────┴───────────────┬───────────────┴────────────────────────┘
                                                  │
                                                  ▼
                                   综合风险判定与徽章渲染
                      [存在风险 🔴/🟡]  ───> 醒目展示具体风险项与操作小抄
                      [无风险 🟢]       ───> 🟢 巡检全通：持仓合规健康
```

### 2. 四维巡检核心规则与判定逻辑

#### ① FIFO 批次锁仓与赎回费阶梯巡检 (FIFO Lot Unlock Alerts)
遍历 `pm.holdings` 中每只基金的 `batches: List[HoldingBatch]`：
- **规则 1.1（$\le 3$ 天极端惩罚期警告）**：
  若存在任意批次 `batch.holding_days <= 3`：
  * 严重级别：🔴 **高危警报**；
  * 预警文案：`【{fund_name} ({fund_code})】批次 {batch_id} 持有仅 {batch.holding_days} 天（≤3天），严禁赎回！若此时赎回将触发 1.50% 巨额惩罚性扣款！`
- **规则 1.2（刚满 7 天脱离惩罚窗口）**：
  若存在批次 `7 <= batch.holding_days <= 9`：
  * 严重级别：🟢 **合规解锁提示**；
  * 预警文案：`【{fund_name} ({fund_code})】批次 {batch_id} 持有已满 7 天（当前第 {batch.holding_days} 天），已成功脱离 1.50% 惩罚赎回费，常规交易通道已开启。`
- **规则 1.3（C 类刚满 30 天 0 赎回费窗口开启）**：
  若 `share_class == 'C'` 且存在批次 `30 <= batch.holding_days <= 34`：
  * 严重级别：🟡 **择机置换提醒**；
  * 预警文案：`【{fund_name} ({fund_code})】C类份额已满 30 天（当前第 {batch.holding_days} 天），赎回费率已降至 0.00%！建议在反弹高点择机全额置换清理，避免长期计提销售服务费。`
- **规则 1.4（A 类 180 天持有期阶梯提示）**：
  若 `share_class == 'A'` 且 `7 <= batch.holding_days < 180`：
  * 提醒距满期免赎还需持有天数，建议将分红方式设为【现金分红】实现收益零费率沉淀。

#### ② 赛道拥挤度与超买预警 (Sector Crowding & Overbought Warnings)
- **规则 2.1（短期暴涨极端超买）**：
  针对全组合持仓及关注赛道，测算 $Bias_{20} = (Price - MA20) / MA20 \times 100\%$。
  * 若 $Bias_{20} > +6.0\%$：
    - 严重级别：🔴 **超买预警**；
    - 预警文案：`【{fund_name} / {sector_name}】短期暴涨，MA20 正乖离率达 {bias_20:+.1f}% (>+6%)，呈现极端超买态势，严禁单笔重仓追高，警惕均值回归高位回撤！`
- **规则 2.2（抱团松动踩踏预警）**：
  调用 `pm.get_fund_smart_money_crowding(code)`：
  * 若 `crowding_degree == "极度拥挤"` 且（`northbound_5d_net < -1000.0` 或 `concentration_trend == "筹码分散"`）：
    - 严重级别：🔴 **踩踏风险**；
    - 预警文案：`【{fund_name}】行业主力资金筹码发散且北向持续大幅净流出，面临机构抱团松动踩踏风险，建议暂停追高或分批止盈！`

#### ③ 基金本体排雷预警 (Fund Self Risk Screening)
- **规则 3.1（迷你基清盘高危排查）**：
  获取基金最新资产净值（亿元）：
  * 若 `aum_billion < 0.50`：
    - 严重级别：🔴 **清盘高危**；
    - 预警文案：`【{fund_name} ({fund_code})】最新资产净值仅 {aum_billion:.2f} 亿元（<0.5亿法定警戒线），面临因规模不足触发强制清盘终止运作的严重法律风险！`
- **规则 3.2（基金经理变动与年限短）**：
  * 若现任基金经理任职年限 `< 1.0` 年或近期刚发生基金经理离任：
    - 严重级别：🟡 **关注警示**；
    - 预警文案：`【{fund_name}】现任基金经理任职不足 1 年（仅 {tenure:.1f} 年），投资策略连续性与稳定性存疑。`
- **规则 3.3（风格漂移检测）**：
  * 若底层重仓股与合同契约大类偏离度 $> 30\%$：
    - 严重级别：🟡 **漂移警示**；
    - 预警文案：`【{fund_name}】穿透持仓检测到风格漂移，伪分散风险上升。`

#### ④ 大盘攻防线突破/破位预警 (Market Attack/Defense Warnings)
获取最新沪深300指数与均线系统：
- **破位防守警报**：若指数跌破防守底线（`breakdown_line`）或 $Bias_{20} < -2.5\%$：
  * 严重级别：🛡️ **防守警报**；
  * 预警文案：`沪深300（{c300:,.1f}）跌破 MA20 防守底线（{breakdown_line:,.0f}），市场转入弱势防守，建议增量资金转入纯债/红利压舱石。`
- **突破进攻信号**：若指数放量站上进攻线（`surge_line`）：
  * 严重级别：⚡ **进攻信号**；
  * 预警文案：`沪深300（{c300:,.1f}）有效放量突破进攻线（{surge_line:,.0f}），右侧进攻通道开启，可逢回踩增配高弹性科创与成长标的。`

#### ⑤ 绿色全检通过徽章 (Green "All Passed" Badge)
- 当巡检判定无任何 🔴 高危项目且无 🟡 关注项目时，预警哨收起所有警告卡，并渲染标准绿色徽章：
  ```html
  <div class="watchdog-all-passed-badge">
      <span class="badge-icon">🟢</span>
      <span class="badge-title">主动风控巡检全通</span>
      <span class="badge-desc">持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险 ｜ 大盘运行于安全区间</span>
  </div>
  ```

### 3. 本地持久化与 UI 集成规范

- **持久化契约**：将每日巡检快照与预警项同步保存至 `data/portfolio_watchdog.json`（严格遵守 GEMINI.md 规则 4）；
- **UI 展示**：在 Tab 2【💼 持仓调仓】顶部，或主界面【🧭 市场定调与攻防线】卡片内联动展现。若有高危警报，以醒目的微红/浅橙边框卡片呈列，并直接附带【一键规避操作建议】。

---

## 四、 需求 R3.3：【🌊 分批建仓与智能定投算子】深度技术方案

### 1. 架构定位与业务流转

在 Tab 1 步骤三【实盘建仓执行单】中，实装建仓节奏选择器（`capital_deployment_mode` 单选组件）：
```
┌────────────────────────────────────────────────────────────────────────┐
│ 资金建仓节奏选择器：                                                    │
│ ( ) 模式一 (⚡ 一次性建仓)                                               │
│ (•) 模式二 (🌊 稳健三步分批建仓)                                         │
│ ( ) 模式三 (📅 估值自适应智能定投)                                       │
└────────────────────────────────────────────────────────────────────────┘
```

### 2. 三大模式数学模型与执行算法

#### 模式一：⚡ 一次性建仓 (Full Allocation Today)
- **适用场景**：市场处于底部极端低估击球区（ERP 分位数 $>80\%$）、投资者追求快速建齐底仓；
- **算法规则**：
  - 总本金 $C = \text{total\_capital}$；
  - 各基金分配金额 $A_i = C \times w_i$（$w_i$ 为步骤二量化模型定权得到的权重，$\sum w_i = 1.0$）；
  - 自动执行单日限购过滤与拆单（如博时标普500限购 500 元，超额部分自动拆入备选摩根标普500或定投）；
  - **金额守恒**：$\sum_{i} A_i \equiv C$。

#### 模式二：🌊 稳健三步分批建仓 (Robust 3-Batch Capital Deployment)
- **适用场景**：震荡市、结构分化期或大盘处于 MA20 均线附近时，分步建仓规避单点追高风险；
- **三步资金拆解模型与金额守恒红线**：
  - **第一批（今日底仓，占总本金 50.0%）**：
    * 资金规模：$C_1 = 0.50 \times C$；
    * 资产分配原则：**买满全部防守压舱石与低波资产，权益成长折半配置**。
      - 纯债固收资产（如易方达裕祥回报 `002351`）：分配权重 $1.0 \times w_{\text{bond}}$；
      - 黄金对冲资产（如华安黄金易 `000216`）：分配权重 $1.0 \times w_{\text{gold}}$；
      - 红利低波/高股息资产（如创金合信红利低波 `005561`）：分配权重 $1.0 \times w_{\text{dividend}}$；
      - 权益类成长/高弹性进攻资产（科创50、中证1000、半导体等）：仅分配目标权重的一半（$0.5 \times w_{\text{equity}}$）；
    * 归一化：将上述第一批配置按比例归一至 $C_1$；
    * 执行时机：今日（$T$ 日）15:00 前立即下单成交。
  - **第二批（逢低网格补仓单，占总本金 30.0%）**：
    * 资金规模：$C_2 = 0.30 \times C$；
    * 策略定位：**大盘回踩均线支撑位时逢低分档吸筹**；
    * 网格触发条件设定：
      - 档位 2A（占本金 15%）：沪深300回踩至 MA20 支撑位（例如现价回踩 $-2.0\% \sim -2.5\%$），买入高性价比大盘成长；
      - 档位 2B（占本金 15%）：沪深300回踩至 MA60 中线强支撑位（例如现价回踩 $-4.5\% \sim -5.0\%$），买入中盘与小盘高弹性增强标的；
    * 停泊机制：在触发点位到达前，该 30% 资金停泊于货币基金或超短债（如 `000009` 易方达天天理财），赚取流动性票息收益。
  - **第三批（右侧趋势加仓单，占总本金 20.0%）**：
    * 资金规模：$C_3 = 0.20 \times C$；
    * 策略定位：**指数有效放量突破进攻阻力线时顺势追随主升浪**；
    * 突破触发条件设定：沪深300放量站上进攻线（`surge_line`，高于现价 $+1.5\% \sim +2.5\%$，且量能放大）；
    * 买入标的：全额增配高弹性进攻 C 类份额（如华夏科创50联接C `011613`、银华集成电路C `013841`）；
    * 停泊机制：未触发突破前停泊于短债/货基。
- **金额守恒硬约束检验 (Conservation Invariant)**：
  $$C_1 + C_2 + C_3 = 0.50 \times C + 0.30 \times C + 0.20 \times C \equiv C$$
  算法在分配金额时使用浮点精度截断与分厘级尾差调整（将四舍五入后的几分钱尾差自动补偿至第一批规模最大的纯债标的），确保三批金额之和与用户输入本金严格分厘级平账！

#### 模式三：📅 估值自适应智能定投 (Valuation-Adaptive Smart DCA)
- **适用场景**：中长线战略定投，希望根据市场估值高低与均线偏离自动动态加减码；
- **基础参数**：
  * 定投期数 $M \in \{6, 12, 24\}$ 期（默认 12 期，如按周或按月）；
  * 每期基准定投金额：$Base = C / M$；
- **当下时点智能定投乘数引擎 ($Multiplier_T$)**：
  结合当下宏观 ERP 股债性价比分位数 $Pct_{\text{erp}}$ 与 MA20 均线偏离度 $Bias_{20}$，动态计算扣款乘数：
  $$Multiplier_T = f(Pct_{\text{erp}}, Bias_{20})$$
  * **极度低估超跌区间（$Pct_{\text{erp}} \ge 75\%$ 且 $Bias_{20} \le 0\%$）**：
    $$Multiplier_T = 1.5 + 0.5 \times \min\left(1.0, \frac{Pct_{\text{erp}} - 0.75}{0.25} + \frac{-Bias_{20}}{10.0}\right) \in [1.50, 2.00]$$
    *含义：估值极度便宜且处于水下超跌，触发 1.5x~2.0x 逆向大额猛扣，加速收集廉价筹码！*
  * **估值适中中性区间（$35\% \le Pct_{\text{erp}} < 75\%$ 且 $-3\% \le Bias_{20} \le +3\%$）**：
    $$Multiplier_T = 1.00$$
    *含义：估值合理，按 1.0x 标准基准金额平稳扣款。*
  * **高估过热或严重超买区间（$Pct_{\text{erp}} < 35\%$ 或 $Bias_{20} > +6.0\%$）**：
    $$Multiplier_T = \max\left(0.0, 1.0 - \frac{0.35 - Pct_{\text{erp}}}{0.35} - \frac{Bias_{20} - 6.0}{10.0}\right) \in [0.00, 0.50]$$
    *含义：市场过热高估，定投大幅压低扣款至 0.0x~0.5x，并提示开启阶梯止盈。*
- **输出成果物**：
  - 当期智能扣款建议额：$Amount_T = Base \times Multiplier_T$；
  - 各基金本期扣款分配明细表（按优选组合目标比例切分）；
  - 完整多期定投执行排期日历与动态乘数预估表。

---

## 五、 需求 R4：物理安全红线与工作区架构红线审计

### 1. 严格只读文件清单与完整性保护

根据需求文档与工作区铁律，以下 4 大裁判基建文件处于**绝对物理只读状态**，任何智能体与代码修改操作均严禁触碰：

| 只读文件路径 | 作用与职责 | SHA-256 校验哈希基线 |
| :--- | :--- | :--- |
| `AGY2_FundAdvisory/judge_engine.py` | 裁判因果探针、6大风格切片全量回归、AST静态审计、参数爆破 | `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be` |
| `AGY2_FundAdvisory/holdout_vault.py` | 盲测隔离金库、熔断锁机制 | `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a` |
| `AGY2_FundAdvisory/AGENT_SPEC.md` | A股策略裁判防作弊基准与切片红线规范 | `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957` |
| `tests/test_infra.py` 与 `AGY2_FundAdvisory/tests/test_infra.py` | 裁判基建自动化单元测试集 | 严格保持原样 |

**审计结论**：本次调查已对上述文件执行 SHA-256 哈希固化，后续开发与测试过程严禁以任何理由产生 Diff。

### 2. GEMINI.md 架构规范与红线核验标准

实施 R3 模块必须 100% 遵守 `GEMINI.md` 的所有硬性不变量：
1. **Streamlit Tab 独立错误隔离边界 (Tab Error Isolation)**：
   - 雷达看板、预警哨和分批算子必须位于相应 Tab 内部，且顶层必须各自包裹独立的 `try ... except Exception as e: st.error(f"⚠️ ...渲染出现局部异常: {e}")`；
   - 彻底杜绝单个算子抛出异常导致 Streamlit 全屏崩溃白屏。
2. **前端空间几何不变量与反测试虚荣 (Geometry Invariants)**：
   - 渲染雷达与预警卡片时，禁止在父级注入 `overflow: hidden !important`；
   - 卡片必须声明 `min-height`、`height: auto !important` 与 `overflow: visible !important`，且卡片内边距底部预留 $\ge 10$px 的安全呼吸空间，文字折行自然撑开高度。
3. **Flexbox 物理防压扁与横向滚动 (Anti-Squash)**：
   - 雷达指标药丸和预警胶囊必须锁死 `flex: 0 0 auto !important; white-space: nowrap !important;`；
   - 外层包裹 `overflow-x: auto !important; overflow-y: hidden; scrollbar-width: thin;` 的横向滚动容器。
4. **持仓批次先进先出与免惩罚赎回 (FIFO Holding Days Defense)**：
   - 预警哨在测算持仓天数时，严禁使用 `max(holding_days)`，强制使用 `min((b.holding_days for b in batches), default=30)`；
   - 赎回建议必须遵循 `penalty_free_shares` 约束，严禁建议卖出 $<7$ 天批次。
5. **Windows 瞬态端口碰撞防御 (Transient Port Defense)**：
   - 在重启与探针检测 8501 端口时，禁止盲目 `taskkill`，须用 `netstat -ano | findstr 8501` 甄别是 `LISTENING` 还是 `ESTABLISHED`，支持 1~2s 缓冲重试。

---

## 六、 需求 R5：增量及回归测试体系设计

### 1. 既有测试基线审计

- **根目录 `tests/`**：包含 29 个测试文件（`test_infra.py`, `test_fund_trading_rules.py`, `test_portfolio.py`, `test_parsers.py`, `test_toolkit_*.py` 等），直接运行 `py -3 -m pytest tests/test_infra.py` 14 项全通（耗时约 7.5s）。
- **`AGY2_FundAdvisory/tests/`**：包含 46 个对抗与集成测试文件（涵盖 Milestone 1~3, Phase 1~3, AppTest 等）。在设置 `$env:PYTHONPATH='AGY2_FundAdvisory;.'` 环境下，`AGY2_FundAdvisory/tests/test_infra.py` 15 项全通（耗时约 8.5s）。
- **历史 AppTest 观察**：早期 `test_delta_m1_guardrails.py` 中有两处假定侧边栏第一个按钮为“加载演示组合”，而 R1 多主题重构后侧边栏首个按钮为主题“↺ 重置”，此属于预期内的 UI 演进。

### 2. 新增针对性自动化单元测试规划

必须在 `tests/` 目录下新增三大核心单元测试套件：

#### ① `tests/test_opportunity_radar.py` (机会雷达针对性测试)
- **用例 1：`test_opportunity_radar_14_sectors_coverage`**：
  验证 14 个核心赛道与宽基全部被机会雷达扫描器纳入，无赛道遗漏。
- **用例 2：`test_kaufman_er_snr_calculation`**：
  给定构造的单边无噪音上升序列与高频随机正弦震荡序列，验证考夫曼 ER 在单边趋势下接近 1.0，在震荡噪音下接近 0.0。
- **用例 3：`test_bias20_anti_overbought_discount`**：
  验证当 $Bias_{20} > +6.0\%$ 时，动量得分 $S_{\text{mom}}$ 正确触发均值回归惩罚折价，防范泡沫追高。
- **用例 4：`test_top3_golden_zone_and_resonance_selection`**：
  验证雷达按综合评分准确萃取 Top 3 机会赛道，且每个赛道成功匹配六维评分最高的公募基金，输出字段包含 `overall_score`、`fund_code`、`fund_name`。

#### ② `tests/test_active_risk_watchdog.py` (主动风险预警哨针对性测试)
- **用例 1：`test_fifo_unlock_alerts_three_days_penalty`**：
  构造持有期为 2 天的持仓批次，断言预警哨准确触发 🔴 1.50% 巨额惩罚赎回费警报。
- **用例 2：`test_fifo_unlock_alerts_seven_days_escape`**：
  构造持有期恰好为 7 天的批次，断言触发 🟢 免惩罚窗口解锁提示。
- **用例 3：`test_fifo_unlock_alerts_class_c_thirty_days`**：
  构造持有期为 30 天的 C 类份额批次，断言触发 🟡 0 赎回费置换提醒。
- **用例 4：`test_mini_fund_liquidation_screening`**：
  输入规模为 0.35 亿元的迷你基金，断言准确触发 🔴 清盘高危预警。
- **用例 5：`test_all_passed_green_badge`**：
  输入无任何惩罚锁仓、无拥挤超买、无迷你基、指数安全的合规持仓，断言输出带有 `🟢 巡检全通` 的绿色徽章。

#### ③ `tests/test_smart_execution_dca.py` (分批建仓与智能定投算子针对性测试)
- **用例 1：`test_batch_execution_strict_capital_conservation`**：
  输入总本金 $C = 268,368.10$ 元，执行稳健三步分批建仓，**断言第一批 (50%) + 第二批 (30%) + 第三批 (20%) 的金额之和严格等于 $C$（分厘不差，绝对误差 $<0.01$ 元）**。
- **用例 2：`test_batch_execution_asset_composition`**：
  验证第一批底仓中纯债、黄金、红利分配比例为 100%，而权益成长仅分配 50%；第二批包含回踩 MA20/MA60 网格触发条件；第三批包含突破进攻线条件且未触发前停泊短债/货基。
- **用例 3：`test_adaptive_dca_multiplier_extremes`**：
  - 在极度低估超跌场景（ERP 85%, Bias -5%），断言定投乘数 $Multiplier \in [1.5, 2.0]$；
  - 在中性合理场景（ERP 50%, Bias 0%），断言定投乘数 $Multiplier == 1.0$；
  - 在严重超买过热场景（ERP 20%, Bias +7%），断言定投乘数 $Multiplier \in [0.0, 0.5]$ 并提示阶梯止盈。

### 3. Streamlit `AppTest` 端到端回归测试规划

在 `tests/test_apptest_r3_r5_gui.py` 中编写基于 Streamlit `AppTest` 的 GUI 动态交互回归测试：
- **用例 1：`test_apptest_theme_switching_and_four_tabs_clean_render`**：
  加载 `app_gui.py`，依次切换 5 套主题预设（`light_slate`, `dark_terminal`, `nordic_paper`, `deep_titanium`, `nordic_frost`），验证 `at.run()` 执行后 `len(at.exception) == 0`。
- **用例 2：`test_apptest_opportunity_radar_render_and_expand`**：
  验证主界面成功渲染机会雷达看板，展开后存在 Top 3 推荐卡片及对应的公募基金信息。
- **用例 3：`test_apptest_active_risk_watchdog_display`**：
  在不同持仓数据注入下，验证预警哨组件正常渲染预警项或全检通过绿色徽章，0 异常。
- **用例 4：`test_apptest_tab1_step3_capital_deployment_selector`**：
  切换建仓节奏选择器（一次性 / 稳健三步分批 / 智能定投），验证各模式下执行单表格、网格批次、定投排期表无缝切换渲染，且页面无截断、0 异常。

---

## 七、 落地实施分工与执行蓝图 (Implementation Blueprint)

为确保实施智能体（Coder）与测试智能体（Tester）零障碍协同推进，建议按以下三阶段顺序施工：

```
[阶段一: 量化核心算法实装]
├── 1. portfolio_manager.py: 实装 OpportunityRadarEngine (14赛道扫描、4维打分、Top 3萃取、6D选基)
├── 2. portfolio_manager.py: 实装 ActiveRiskWatchdog (4维巡检: FIFO批次、超买拥挤、迷你基、攻防线)
└── 3. strategy_bridge.py / portfolio_optimizer.py: 实装 SmartExecutionDCA (三步分批金额守恒 + 估值定投乘数)

[阶段二: Streamlit UI 交互与人体工学集成]
├── 1. app_gui.py 行情带下方: 渲染【🔭 全市场机会雷达】折叠看板与一键入池
├── 2. app_gui.py Tab 2 / 顶部: 渲染【🚨 主动风险预警哨】四维诊断与绿色全检徽章
└── 3. app_gui.py Tab 1 步骤三: 嵌入资金建仓节奏单选器，动态渲染三种建仓交割单

[阶段三: 自动化验证与交付验收]
├── 1. 执行 tests/ 下针对性单元测试 (Radar, Watchdog, DCA)
├── 2. 执行 Streamlit AppTest 回归套件 (5套主题 + 4个Tab)
└── 3. 探针核验 8501 端口 Streamlit 服务平滑健康存活
```

---

## 八、 结论

本次勘测已彻底查明 R3、R4、R5 的所有代码触点、数学公式、数据字典与测试依赖。代码库基建完备，所有算法模型均具备严格的数学闭环与防作弊红线隔离。实施团队可直接依照本报告的规格定义开展编码与测试交付。
