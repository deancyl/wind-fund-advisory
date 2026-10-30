# Explorer 3 调查与架构勘测报告 (AGY2_FundAdvisory)

**报告作者**：Explorer 3 (Track 3: portfolio_manager, app_gui, tests)  
**工作区路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory`  
**基准时间**：2026-10-30T01:08:00Z  

---

## 1. Observation (客观观察与实证数据)

### 1.1 测试套件架构与执行机制观察
- **根目录与配置冲突**：
  - 在工作区根目录 `D:\Google\Workspace\Wind` 下存在 `pyproject.toml`。
  - 当在 `d:\Google\Workspace\Wind\AGY2_FundAdvisory` 目录下直接运行 `pytest tests/test_infra.py` 时，pytest 自动将根目录识别为 `rootdir: D:\Google\Workspace\Wind`，导致 Python `sys.path` 仅挂载父目录，抛出异常：
    ```text
    ModuleNotFoundError: No module named 'data_loader'
    ```
  - **实证解决指令**：设置 `$env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"` 后，`tests/test_infra.py` 15 项测试全部通过（6.57 秒），`tests/test_portfolio_manager.py` 22 项测试全部通过（9.68 秒），`tests/test_strategy_bridge.py` 9 项测试全部通过（6.58 秒）。
  - **既有测试总量**：`AGY2_FundAdvisory/tests/` 目录共收集 **246 项测试用例**（分布在 17 个测试模块中）。
  - **网络延迟与警告观察**：运行 `test_acceptance_r1_r7.py` 时耗时 132 秒（8 项全部通过），主要原因为 `app_gui.py` 渲染表格时对东方财富接口发出未经缓存的实时估值拉取，产生了 214 条 `InsecureRequestWarning`。单元测试套件需对外部网络调用保持 Mock 或使用纯离线本地缓存。

### 1.2 系统只读裁判基建文件完整性验证 (R1 红线)
4 个只读裁判基建文件均位于 `d:\Google\Workspace\Wind\AGY2_FundAdvisory`，代码与哈希完整无损：
1. `judge_engine.py` (绝对路径: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py`, 42,175 字节, 844 行)
   - 核心类: `JudgeEngine`，关键函数: `compute_ast_hash()`, `scan_ast_for_calendar_cheating()`, `probe_look_ahead_bias()`。
2. `holdout_vault.py` (绝对路径: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py`, 5,685 字节, 162 行)
   - 核心类: `HoldoutVault`，异常: `HoldoutVaultExhaustedError`，硬编码硬限: `MAX_HOLDOUT_ATTEMPTS = 3`，盲测隔离日期: `2025-07-01`。
3. `AGENT_SPEC.md` (绝对路径: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md`, 8,237 字节, 110 行)
   - 包含四大关卡（检验A因果探针、检验A+ AST静态扫描、检验B 6风格切片全量回归、检验C扰动高原、检验D DSR惩罚计数器）。
4. `tests/test_infra.py` (绝对路径: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py`, 10,524 字节, 264 行)
   - 包含 15 个基础单元测试，直接 `from data_loader import DataLoader`，`from judge_engine import JudgeEngine`。
   - **红线结论**：开发过程中严禁修改此 4 个文件中的任何一个字符！

### 1.3 `portfolio_manager.py` 选基漏斗与六维评分现状观察
- **核心策略池定义**：`portfolio_manager.py` 第 306~708 行定义全局元数据字典 `CORE_STRATEGY_POOL`，覆盖 30+ 只公募基金的交易属性（代码、中文名、基金公司、A/C份额、限额 `daily_limit`、备选代码 `fallback_code`、结算周期等）。
- **赛道金牌标的与备选池**：
  - `portfolio_manager.py` 第 714~805 行定义 `SECTOR_FUND_SELECTION`：
    - `CORE_DIVIDEND`: 冠军 `100032` (富国中证红利指数增强A)，备选 `090010`, `012643`, `008682`。
    - `BOND_SHIELD`: 冠军 `002351` (易方达裕祥回报债券A)，备选 `000086`, `018757`, `002352`。
    - `GOLD_HEDGE`: 冠军 `000216` (华安易富黄金ETF联接A)，备选 `002610`, `000217`, `002611`。
    - `TECH_GROWTH`: 冠军 `011613` (华夏上证科创板50成份ETF联接C)，备选 `016634`, `001053`, `013841`。
    - `GLOBAL_HEDGE`: 冠军 `050025` (博时标普500ETF联接A)，备选 `001071`, `017436`, `006075`。
  - `strategy_bridge.py` 第 290~797 行定义各风险档位分层的 `SECTOR_FUND_SELECTION_BY_TIER` (C1~C5)。
- **全市场四级选基漏斗统计**：
  - `get_fund_selection_funnel_stats()` (第 808~838 行)：
    - Level 1: 全市场公募基金池 28,177 只（从本地 DuckDB 或兜底）
    - Level 2: 硬指标合规初筛 6,850 只（成立 > 3年，规模 > 2亿）
    - Level 3: 5大赛道入围池 16~20 只（低费率 & 高 Alpha）
    - Level 4: 最终优选金牌组合 4~5 只
- **六维量化打分实现**：
  - `portfolio_manager.py` 第 3624~3783 行 `compute_fund_six_dimension_score()` / `_do_compute_six_dimension_score()`：
    1. 超额 Alpha 得分 (35% 权重)：读取 DuckDB `v_scorecards` 或 `v_fund_snapshot`。
    2. 低费率得分 (25% 权重)：读取 DuckDB `v_fund_trading_rules` 中的综合运营费率。
    3. 底层排雷健康分 (15% 权重)：调用 `screen_fund_look_through_risk()`，扣除商誉、存贷双高、质押、解禁、负FCF风险分，非A股资产（纯债、黄金、QDII）绝对免疫。
    4. 北向聪明钱流入分 (10% 权重)：读取 DuckDB `v_northbound_holdings`。
    5. 反拥挤度安全分 (10% 权重)：纯债/黄金 97，红利 95，核心蓝筹 91，科技成长 88。
    6. 衍生品与宏观契合度 (5% 权重)：期权 IV 与 IC/IM 贴水率匹配。
    - 权重计算：$Score = 0.35 \cdot \alpha + 0.25 \cdot Fee + 0.15 \cdot Risk + 0.10 \cdot SmartMoney + 0.10 \cdot Crowding + 0.05 \cdot Macro$。
- **现有变点检测状态**：
  - 全局搜索 `cusum` 或 `变点` 为 0 处命中，证明当前代码库中尚未实现 CUSUM 变点检测算法，为本次 R6 核心新增量化模块。

### 1.4 `app_gui.py` 界面架构与推演流程观察
- **顶部状态栏与触发线**：
  - 第 295~315 行：调仓网格日历与盘中紧急破位预警横幅。
    - 绑定 `rebal_grid['countdown_display']` 与 `rebal_grid['emergency_warning']`。
    - 数据源来自 `StrategyBridge.get_rebalance_grid_status()`（`strategy_bridge.py` 第 1585~1645 行）。
  - 第 316~438 行：7 列顶部状态大字号指标卡片（申赎时钟、AI 策略大脑、沪深300实时与偏离、股债性价比、宏观流动性DR007、今日预估浮盈亏、全组合总资产）。
- **步骤一：定目标 / 测风险** (第 533~690 行)：
  - 模式 A（滑块即拉即变 6%~60% -> C1~C5）与模式 B（问卷定档）。
- **步骤二：现场推演看好坏** (第 694~1117 行)：
  - 动态现场推演进度条 `st.status` (Step 1~4，第 708~768 行)。
  - 5 张大字号人话指标卡（最好情况冲刺、最坏情况大熊市、极端水下回本考验、目标胜率与达成周期、适合人群与策略灵魂，第 773~844 行）。
  - **四阶量化推演工作流白盒展开面板** (第 846~1058 行)：
    - Step 1: 全市场 28,177 只基金四级漏斗海选与金牌标的（4 列漏斗、六维加权公式、六维对比宽表 `df_quant`、金牌与备选替换下拉框）。
    - Step 2: 宏观与衍生品四维状态机实时定调（趋势生命线、风格动量、大小盘结构、股债性价比与期权期指卡片）。
    - Step 3: 2018-2026 跨牛熊 2,000+ 交易日实境压力测试（最好/最坏归因、水下回本推演、达成周期、市场环境适宜表）。
    - Step 4: 交易摩擦精算、限购拆单与实盘执行清单（手续费精算、股息回本周期、限购拆单与锁仓）。
  - **《三句话看懂本方案》三栏作战卡片** (第 1060~1117 行)：
    - 收益引擎拆解（怎么赚钱）
    - 反脆弱对冲机制（为什么能赢）
    - 底线与执行铁律（风险与铁律）
- **步骤三：拿方案去执行** (第 1119~1250 行)：
  - 场景一（从 0 开始建仓）与场景二（存量持仓诊断调仓）。
  - **9 列精简执行表格**（基金代码、基金名称、份额、目标占比%、精确买入金额、最新净值、实时估值涨跌%、排雷与拥挤度、实操分红与限购指引）。
  - 一键复制手机下单小抄卡片 (`st.code`)。

---

## 2. Logic Chain (推理链条与技术因果)

### 2.1 R6: 赛道冠军基金 CUSUM 变点检测与自动优胜劣汰推理
1. **现状与痛点**：目前每个赛道的金牌冠军标的（如高股息赛道 100032、纯债赛道 002351 等）由静态元数据指定。若 100032 的底层重仓股暴雷（如 R1 扣分严重）、或发生机构极度抱团踩踏（R3 拥挤度超标）、或其超额收益持续衰减跑输同赛道备选标的（如 090010 或 012643），系统仍会死板推荐 100032，导致实盘损失。
2. **CUSUM 衰减检测数学机制**：
   - 设赛道内备选基金集合为 $\mathcal{F}$，当前默认冠军基金为 $c$。
   - 对任意候选标的 $f \in \mathcal{F}$，基于其滚动动量超额 $ER_{f, t}$、跟踪误差惩罚 $TE_{f, t}$、运营与申赎费率损耗 $Fee_{f}$、R1 重仓股排雷健康分 $Risk_{f, t}$、以及 R3 聪明钱净流入与拥挤度安全分 $SM_{f, t}$，计算综合实时竞争力得分 $S_{f, t}$：
     $$S_{f, t} = 0.35 \cdot ER_{f, t} + 0.25 \cdot (100 - Fee_{f}) + 0.15 \cdot Risk_{f, t} + 0.15 \cdot SM_{f, t} + 0.10 \cdot (100 - TE_{f, t})$$
   - 针对当前默认冠军基金 $c$，维护单向累积和（Page's CUSUM）衰减监测指标 $C_{c, t}$：
     $$C_{c, 0} = 0$$
     $$C_{c, t} = \max\left(0, C_{c, t-1} + (\max_{f \in \mathcal{F}} S_{f, t} - S_{c, t}) - k\right)$$
     其中 $k \ge 0$ 为允许的正常波动松弛容忍带（如 $k = 2.0$ 分）。
   - **变点触发判定 (Change-Point Trigger)**：
     若出现以下任一条件，判定默认冠军标的触发结构性衰减变点：
     1. $C_{c, t} \ge h$（累积衰减超过变点阈值 $h$，如 $h = 8.0$ 分）；
     2. 或 $Risk_{c, t} < 60.0$（底层重仓股发生严重暴雷，直接触发 R1 熔断）；
     3. 或 $SM_{c, t}$ 触发严重拥挤踩踏预警（R3 极度拥挤）。
3. **自动晋升逻辑与白盒透传**：
   - 变点触发时，算法将当前赛道内综合得分排名第 1 的备选标的 $f^* = \arg\max_{f \in \mathcal{F}} S_{f, t}$ 自动晋升为当前赛道的金牌标的。
   - 标注显式自进化标签：
     `"🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name} (原默认标的评分衰减触发 CUSUM 轮换)"`。
   - 该晋升结果无缝透传至：
     - `SECTOR_FUND_SELECTION` / `SECTOR_FUND_SELECTION_BY_TIER`
     - `get_tier_quant_selection_table`（表格中标注标的身份）
     - `generate_zero_start_blueprint`（建仓单自动使用新冠军并记录 notes）
     - `app_gui.py` Step 1 白盒卡片与下拉框。

### 2.2 R7: Streamlit UI 交互升级与白盒仪式感推理
1. **四阶推演白盒展开面板 (Step 1 ~ Step 4)**：
   - **Step 1 (选基与 CUSUM)**：展示 28,177 漏斗与 CUSUM 动态晋升状态。当触发优胜劣汰时，以明显的高亮卡片标注 `🔄 自进化优选`。
   - **Step 2 (Hedge 专家与施密特)**：展示 `OnlineExpertWeightUpdater` 输出的四大专家实时权重柱状图/指标（趋势动量、ERP估值、均线乖离逆向、流动性期指，权重和恒等于 1.0），以及施密特迟滞状态机缓冲区指示（$[-1.5\%, +1.2\%]$ 锁定区间与当前状态）。
   - **Step 3 (压力测试与作战书)**：2018-2026 回测曲线与 5 张人话指标卡归因、环境适宜表。
   - **Step 4 (摩擦拦截与拆单)**：展示 $\Delta U$ 调仓净效用拦截详情、A/C 阶梯费率对照、同公司 SWITCH 零在途优势与限购自动拆单。
2. **三句话看懂本方案卡片**：
   - 确保卡片三栏紧扣：① 怎么赚钱（收益来源：高股息底仓 + 动量弹性 + 期指贴水）、② 为什么能赢（极低相关资产对冲 + 跨牛熊 1年胜率）、③ 风险与铁律（最大回撤底线 + 水下回本天数 + 7天惩罚费拦截 + 估值底部不割肉）。
3. **双向变盘触发线刚性防倒挂**：
   - 向上突破进攻线（结合施密特迟滞上轨 $+1.2\%$）点位严格高于现价：`surge_c300 > c300_price`；
   - 向下跌破防守线（结合施密特迟滞下轨 $-1.5\%$）点位严格低于现价：`breakdown_c300 < c300_price`；
   - 彻底杜绝历史版本中因口径不一致产生的倒挂，并与盘中实时点位联动。
4. **1080p 紧凑排版与零截断**：
   - 顶部 7 列卡片使用百分比自适应宽度与 `min-width`。
   - 步骤三 9 列表格中最后一列提炼为精炼动作（<=15 字），长篇原理解析统一收归表头 `help` (`ⓘ` 悬停提示)。

---

## 3. Caveats (局限性与风险假设)

1. **历史数据驱动假设**：CUSUM 变点检测依赖历史滚动截面指标（如 60 日超额收益与 DuckDB 中的历史财报排雷数据）。若 DuckDB 连接异常，必须具备完备的内置离线快照兜底，不得抛出未捕获异常。
2. **网络环境与 AppTest 测试耗时**：`fetch_realtime_fund_quote()` 在未命中本地缓存时会访问外网接口，导致 Streamlit AppTest 测试单次耗时达数十秒。建议在自动化测试中对实时接口设置默认快速 Mock 或加载离线快照，以提升 CI/CD 执行效率。
3. **只读裁判文件依赖**：`tests/test_infra.py` 直接从根命名空间 `import data_loader, judge_engine`，因此整个测试生命周期必须强制在带有 `PYTHONPATH` 的环境下运行，绝不能为了“迁就”测试而修改只读文件。

---

## 4. Conclusion & Actionable Recommendations (结论与精准植入点)

### 4.1 R6 关键实现与代码植入点 (portfolio_manager.py 与 strategy_bridge.py)

#### 植入点 1: `portfolio_manager.py` — 植入 `CUSUMFundChangePointDetector`
- **建议位置**：`portfolio_manager.py` 第 806 行（紧随 `SECTOR_FUND_SELECTION` 之后）或第 3784 行（紧随六维评分之后）。
- **接口设计**：
  ```python
  class CUSUMFundChangePointDetector:
      """
      基于 Page's CUSUM 变点检测的赛道冠军基金自动优胜劣汰引擎 (R6)
      """
      def __init__(self, slack_k: float = 2.0, threshold_h: float = 8.0):
          self.slack_k = slack_k
          self.threshold_h = threshold_h
          self._cusum_scores: Dict[str, float] = {}

      def evaluate_track_candidates(
          self,
          sector_id: str,
          default_champion_code: str,
          candidates: List[Dict[str, Any]],
          snapshot: Optional[Dict[str, Any]] = None,
          pm: Optional[Any] = None
      ) -> Dict[str, Any]:
          """
          计算各候选基金实时竞争力得分 S_{f, t} 与当前冠军的 CUSUM 衰减指标，
          若触发变点，自动将综合得分第 1 的候选标的晋升为推荐冠军标的。
          返回结构包含:
          - active_champion_code: 当前生效冠军代码
          - is_promoted: 是否触发自动轮换晋升
          - promotion_label: "🔄 自进化优选：因综合评分领先，已自动为您优选 XXXXX"
          - scored_candidates: 包含各项细分得分的排序列表
          """
  ```

#### 植入点 2: `strategy_bridge.py` — 桥接层多档位晋升与透传
- **位置**：`strategy_bridge.py` 第 3188 行 `get_tier_sector_fund_selection()` 与第 3200 行 `get_tier_quant_selection_table()`。
- **改动方式**：
  - 在 `get_tier_sector_fund_selection` 中调用 CUSUM 评估器，若某赛道原冠军发生衰减，动态替换当前生效的 `champion_code` 与 `champion_name`，并将 `promotion_label` 注入赛道字典。
  - 在 `get_tier_quant_selection_table` 中，若标的为自动晋升冠军，将其“标的身份”列标记为 `🏆 🔄 自进化优选冠军`，并在 UI 下拉框默认选中该新晋标的。
  - 在 `generate_zero_start_blueprint` (第 3269 行) 中，默认使用自进化优选出的冠军标的进行资金分配。

---

### 4.2 R7 关键实现与代码植入点 (app_gui.py)

#### 植入点 1: 4 阶推演白盒展开面板强化
- **位置**：`app_gui.py` 第 846~1058 行。
- **改动内容**：
  - **Step 1 (第 850~914 行)**：在 4 列漏斗卡片下方新增【CUSUM 动态优胜劣汰监测提示栏】，若检测到赛道标的被自动轮换，以橙/绿高亮横幅提示：`"🔄 自进化优选：因综合评分领先，已自动为您优选【XXXX】替代原默认标的"`。
  - **Step 2 (第 916~979 行)**：新增【Hedge 四大策略专家在线自适应权重与施密特防打脸校验】可视化卡片，展示 Trend, ERP, Bias, Liquidity 四大专家的实时权重配比（权重和为 100%），以及当前指数位于施密特迟滞缓冲环的锁定状态。
  - **Step 3 (第 981~1017 行)**：保留 2018-2026 实境压力测试与 5 张人话指标卡归因，表格字体与列宽优化。
  - **Step 4 (第 1019~1058 行)**：强化摩擦精算卡片，展示 $\Delta U$ 调仓净效用拦截器逻辑（同公司 SWITCH 转换 0 在途踏空，跨公司赎回再申购在途损耗折价核验）。

#### 植入点 2: 修复双向变盘触发线与施密特迟滞对齐
- **位置**：`strategy_bridge.py` 第 1597~1618 行与 `app_gui.py` 第 305~314 行。
- **改动内容**：
  - 向上突破进攻线：严格结合施密特迟滞上轨（$+1.2\%$）：
    $$surge\_c300 = \text{round}(c300\_price \times (1 + \max(0.012, \text{SchmittThreshold})), 1) > c300\_price$$
  - 向下跌破防守线：严格结合施密特迟滞下轨（$-1.5\%$）：
    $$breakdown\_c300 = \text{round}(c300\_price \times (1 - \max(0.015, \text{SchmittExitThreshold})), 1) < c300\_price$$
  - 严格保持 $breakdown\_c300 < c300\_price < surge\_c300$ 恒成立，彻底杜绝倒挂。

#### 植入点 3: 1080p 紧凑无滚动条与 ⓘ 悬停全面落地
- **位置**：`app_gui.py` 第 316~438 行（顶部指标卡）与第 1157~1223 行（步骤三 9 列表格）。
- **改动内容**：
  - 确保步骤三 9 列表格的最后一列字段名设为 `"实操分红与限购指引 ⓘ"`，单元格文本控制在 12 字以内（如“现金分红·满期免赎A”、“红利再投·弹性进攻C”、“现金分红·限额买500”），核心原理与计算公式完全放入 `help="..."`。
  - 设置 `st.dataframe(..., use_container_width=True)`，在 1080p 屏幕下彻底消除横向滚动条与省略号截断。

---

## 5. Verification Method (独立复现与验证步骤)

接手 Agent 可通过执行以下具体步骤与命令独立复现并验证本报告的所有结论：

### 5.1 验证命令与测试运行
1. **设置环境变量并运行只读基建测试**：
   ```powershell
   $env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   pytest tests/test_infra.py -v
   ```
   **断言**：15 项基建测试全部 PASS，耗时 < 10 秒。

2. **运行既有组合管理与策略桥接测试**：
   ```powershell
   $env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   pytest tests/test_portfolio_manager.py tests/test_strategy_bridge.py -v
   ```
   **断言**：31 项测试全部 PASS。

3. **运行 R1~R7 验收测试套件**：
   ```powershell
   $env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   pytest tests/test_acceptance_r1_r7.py -v
   ```
   **断言**：8 项验收测试全部 PASS。

4. **只读基建文件哈希完整性核对**：
   检查以下 4 个文件未被修改：
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py`
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py`
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md`
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py`
