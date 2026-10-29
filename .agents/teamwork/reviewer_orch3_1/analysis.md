# 架构级重构独立审查与红队对抗评估报告 (Analysis Report)

**审查人**: Independent Architecture Reviewer & Critic (Reviewer-1)  
**评估基准**: `ORIGINAL_REQUEST.md`、`orchestrator_3/PROJECT.md`  
**审查对象**:
- `AGY2_FundAdvisory/strategy_bridge.py` (M1: Agent-1)
- `AGY2_FundAdvisory/portfolio_manager.py` (M2: Agent-2)
- `AGY2_FundAdvisory/app_gui.py` (M3: Agent-3)
- `AGY2_FundAdvisory/tests/test_architecture_m3.py` (M4: Agent-4)
- 4 个裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）

---

## 一、审查总决 (Executive Summary & Verdict)

**裁决**: **APPROVE (予以通过)**

经过针对 AST 抽象语法树源码深度扫描、逻辑推理链核查、独立运行测试套件（包括 `test_architecture_m3.py`、`test_acceptance_r1_r7.py` 全量用例）、全域点位与极端宏观输入对抗压力测试（Stress Testing）、以及 8501 端口服务健康度端点探测，Reviewer-1 确认：
本次 4 位 Worker 完成的重构**未发现任何作弊、虚假实现或诚信违规行为**，各项架构契约严格落地，点位倒挂彻底根除，77 只金融机构硬编码白名单被完全清除，代码具备极高的通用量化鲁棒性与界面优雅度。

---

## 二、对抗性诚信红线专项审计 (Integrity Violation Audit)

依据 Reviewer & Critic 诚信准则，实施专项对抗排查：

| 诚信排查项 | 审查结论 | 实证依据 |
|---|---|---|
| **硬编码测试结果 / 静态预期打桩** | **未检出 (PASS)** | AST 静态分析证实 `portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py` 零硬编码 6 位股票代码 if/else 分支，零 `financial_codes` 集合，零静态 `cat_map`。 |
| **虚假外壳 / 假实现 (Facade Implementation)** | **未检出 (PASS)** | `compute_dynamic_tier_weights` 真实实现均线、ERP、IV、贴水多维驱动；选基打分接入真实 DuckDB 视图；排雷引擎接入真实申万行业与经营现金流 CFO 数据。 |
| **绕过任务核心要求 (Shortcuts)** | **未检出 (PASS)** | 未采用任何代理工具跳过计算，所有 9 类资产动态推导，建仓单与调仓表代码中严格使用 `cols_9` 与 `rebal_cols_9` 9 列结构。 |
| **伪造测试验证日志 / 虚假报告** | **未检出 (PASS)** | Reviewer-1 独立重新执行全套测试，实测输出与 Worker 报告数据真实吻合。 |
| **自认证行为 (Self-certifying work)** | **未检出 (PASS)** | 由 Reviewer-1 编写独立脚本进行全域点位（10.0 ~ 50,000.0）与异常行情状态对抗压力测试，脱钩验证通过。 |

---

## 三、各模块架构级重构审查与实证

### 1. `strategy_bridge.py` (M1: Agent-1) 审查
- **动态风险预算模型 (`compute_dynamic_tier_weights`)**:
  - 核心逻辑基于均线多空状态、ERP 股债性价比、DR007 资金面、期指贴水与期权 IV，自适应映射为 `BULL`、`OSCILLATING`、`BEAR` 三大状态。
  - **单调性实证**:
    - 牛市主升浪态: $Equity(C1)=20\% < C2=53\% < C3=74\% < C4=82\% < C5=92\%$
    - 震荡收息态: $Equity(C1)=20\% < C2=51\% < C3=74\% < C4=78\% < C5=90\%$
    - 熊市破位态: $Equity(C1)=10\% < C2=25\% < C3=35\% < C4=50\% < C5=65\%$
    - 在全部市场截面下，全截面严格满足单调递增性 $Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)$，无任何倒挂。
    - 熊市态下所有档位算法止损并向纯债黄金避险切换，避险仓位 C1: 90%, C2: 75%, C3: 65%, C4: 50%, C5: 35%。
- **双向变盘触发点位修复 (`get_rebalance_grid_status`)**:
  - 原代码在 4,053.0 价格下计算防守线为 4,180.5（反向高出现价 +3.15%）的致命倒挂已彻底修复。
  - 新模型采用全收益同口径动态折算系数 $scale\_ratio = c300\_price / c300\_curr$，将 MA20/MA60/MA120 映射到价格刻度；
  - 辅以 `breakdown_c300 = min(cand_breakdown, round(c300_price * 0.988, 1))` 刚性门禁与 `assert breakdown_c300 < c300_price < surge_c300` 强校验；
  - 在全域价格测试中，向上进攻线严格高于现价，向下防守线严格低于现价，输出了明确的变盘后调仓方向指令。

### 2. `portfolio_manager.py` (M2: Agent-2) 审查
- **77 只金融机构代码白名单彻底铲除**:
  - 原代码 3874-3889 行硬编码的 77 只金融机构股票代码（`"600000", "600015", ...`）及 `financial_codes` 变量已被完全删除。
- **三层通用基本面排雷引擎 (`screen_fund_look_through_risk`)**:
  - 第一层（金融业态识别）：依据股票名称或行业属性动态识别银行、证券、保险、金融机构，依据行业商业模式豁免工商企业存贷双高模型，风险扣分记为 0；
  - 第二层（战略硬科技与公用事业重资产现金流校验）：对半导体、芯片、公用事业、电力等高资本开支企业，引入经营造血现金流 $CFO > 0$（通过 `v_stock_financials` 的 `ocf_per_share`）进行交叉检验，造血健康则判定为“重资产正常经营/现金流健康”并豁免；
  - 第三层（真伪造假红灯）：对高息高负债且 CFO 持续恶化或受限资金异常的真造假标的坚决亮红灯预警扣分。
- **全局统一资产分类解析器 (`classify_fund_asset_class`)**:
  - 动态解析基金名称、跟踪指数、投资类型与底层重仓股，精准归类为 9 大标准大类（`"纯债固收"`, `"黄金对冲"`, `"美股海外对冲"`, `"A股红利高股息"`, `"A股红利低波"`, `"科技成长进攻"`, `"中小盘成长"`, `"中盘均衡"`, `"核心蓝筹"`）；
  - 无法识别时安全兜底至 `"其他权益资产"`，彻底消除了被误归为废弃分类“其他存量资产”的漏洞。
- **真实多因子六维选基动态评分 (`compute_fund_six_dimension_score`)**:
  - 真正打通本地 DuckDB 湖仓真实视图：
    - Alpha 历史超额（35% 权重）：读取 `v_scorecards` 综合评分与夏普比率；
    - 低费率得分（25% 权重）：读取 `v_fund_trading_rules` 真实综合费率并经 Min-Max 正规化映射；
    - 底层排雷健康（15% 权重）：实时调用穿透排雷引擎打分；
    - 北向聪明钱（10% 权重）：读取 `v_northbound_holdings` 真实流入；
    - 反拥挤度安全（10% 权重）：基于资产大类流动性与估值拥挤度赋权；
    - 衍生品宏观契合（5% 权重）：接入 IC/IM 期指基差年化贴水率与期权 IV 恐慌度。
  - 彻底铲除了静态字典依赖与虚假伪造打分。

### 3. `app_gui.py` (M3: Agent-3) 审查
- **静态 `cat_map` 字典移除**:
  - 原代码 1869-1874 行的硬编码 16 只基金字典被彻底删除，全局资产占比与条形图统一调用 `pm.classify_fund_asset_class`。
- **四阶量化推演工作流白盒与 1.45s 节奏**:
  - 步骤二及切换档位时，配置了 4 阶递进反馈（0.35s + 0.35s + 0.40s + 0.35s = 1.45s），精确落在用户体验最佳的 [1.2, 1.8] 秒黄金心理区间；
  - 提供了 Step 1（漏斗海选+PK明细）、Step 2（四维决策信号卡片）、Step 3（2018-2026 跨牛熊实境回测）、Step 4（交易摩擦与限购拆单路由）共 4 个独立面板，默认全部设为 `expanded=False`。
- **《三句话看懂本方案》三栏实战作战卡片**:
  - 部署在步骤二推演与步骤三执行之间：
    - 栏一：💰 怎么赚钱？（核心红利打底 + 动态动量进攻 + 智能拆单超额 Alpha）
    - 栏二：🛡️ 为什么能赢？（跨大类低相关对冲 + 跨牛熊 1 年持有高胜率）
    - 栏三：🚨 风险与铁律（历史最极端浮亏金额与水下天数 + 7天不赎免惩罚 + 估值底部便宜区绝不割肉两条铁律）。
- **顶部 7 张核心卡片 15px 零截断**:
  - 指标数值统一配置 `font-size: 15px` 单行紧凑显示，无任何 `...`、`…`、`&hellip;` 截断符号；
  - 专业黑话（申赎时钟、因果状态机、乖离率、股债利差、期权 IV 等）全部封装进 `<span>ⓘ</span>` 悬停提示框。
- **步骤三建仓执行单与存量调仓单 9 列精简**:
  - 建仓执行单代码严格声明 `cols_9 = [...]` 9 列，最后一列“实操分红与限购指引”控制在 15 字以内；
  - 存量调仓单重构为严格 9 列：`["基金代码", "基金名称", "份额", "当前市值(元)", "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)", "建议操作", "实操要点"]`，引入 `➕ 建议加仓`、`➖ 建议减仓`、`🔒 未满7天锁仓保护`、`⏳ 临近30天免赎期缓卖`、`✅ 维持持有` 5 类醒目图标，1080p 分辨率下彻底消除了横向滚动条。

### 4. 4 个裁判基建文件物理只读与哈希校验
通过 PowerShell `Get-FileHash -Algorithm SHA256` 进行比对，4 个基建文件 SHA256 绝对一致，100% 保持未修改：
- `AGY2_FundAdvisory/judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
- `AGY2_FundAdvisory/holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
- `AGY2_FundAdvisory/AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
- `AGY2_FundAdvisory/tests/test_infra.py`: `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A`

---

## 四、对抗性挑战与边界压力测试发现 (Adversarial Stress Test Findings)

Reviewer-1 实施了 5 项对抗性场景测试（详见 `stress_test.py`）：

### 1. 极端与冲突宏观输入下风险预算稳定性 (Passed)
- 输入 `None`、`{}`、`NaN`、负现价、超大现价、以及状态码与文本冲突（如 `market_state_code="GROWTH_BULL"`, `regime="BEAR"`）；
- 结果：状态机均能安全降级或依优先级决策，归一化权重之和严格等于 1.0，全截面单调性 $Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)$ 100% 维持。

### 2. 微小极端价格下的点位舍入边界 (Minor Finding)
- **现象**: 当传入极端测试现价 $c300\_price = 0.01$ 时，由于 `round(p * 1.039, 1)` 保留 1 位小数导致 $surge = 0.0$，触发 `assert breakdown < current < surge` 异常。
- **影响评估**: **极低 (Minor)**。A 股沪深300指数真实点位常年运行在 2,000 ~ 6,000 点区间，10.0 ~ 50,000.0 区间内断言 100% 成立。生产环境中不会出现 0.01 点的点位输入。
- **建议**: 在未来进一步精细化迭代时，可为现价 $< 10.0$ 的极端微小数值设置动态精度 `round(..., 2)` 兜底。

### 3. DuckDB 跨多组件高频并发连接 (Validated)
- 经代码审查，所有组件在连接 `data/storage.duckdb` 时，均显式指定了 `read_only=True`，彻底杜绝了只读查询霸占 DuckDB 单写互斥锁引发的并发阻塞与崩溃风险。

---

## 五、独立实证检验记录 (Independent Verification Results)

| 验证指令 | 检验目标 | 预期结果 | 实测结果 | 结论 |
|---|---|---|---|---|
| `python -m pytest tests/test_architecture_m3.py -v` | AST 静态反硬编码审计、单调性、网格点位、AppTest 渲染 | 4 项用例全过 | `4 passed, 48 warnings in 22.72s` | **PASS** |
| `python -m pytest tests/test_acceptance_r1_r7.py -v` | 核心业务验收标准 R1 ~ R7 端到端校验 | 8 项用例全过 | `8 passed, 17 warnings in 77.03s` | **PASS** |
| `python stress_test.py` | 全截面极端对抗边界压力测试 | 5 项压力测试通过 | `=== ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! ===` | **PASS** |
| `python -m pytest tests/ -q --tb=short` | 全工程全量单元与端到端自动化测试回归 | 226 项全部通过 | `226 passed, 530 warnings in 249.15s (0:04:09)` | **PASS** |
| `Get-NetTCPConnection -LocalPort 8501` | 本地 Streamlit 服务监听状态 | 处于 Listen 状态 | `State: Listen, PID: 18900` | **PASS** |
| `Invoke-RestMethod -Uri http://127.0.0.1:8501/_stcore/health` | Streamlit 服务健康探测 | 返回 `ok` | `ok` | **PASS** |

---

## 六、审查结论

本次交付的架构级重构产物在**功能完整性**、**量化严密性**、**反硬编码鲁棒性**及**人机交互体验**各方面均达到高水准，完全符合用户原始需求与架构契约要求。裁决为 **APPROVE**。
