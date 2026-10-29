# AGY2 架构级重构独立鲁棒性与交互体验评审报告 (Reviewer-2 Analysis)

## 一、评审结论总览 (Review Summary)

**最终裁决 (Verdict)**: **APPROVE (正式通过)**
**整体系统鲁棒性与风险评估**: **LOW (低风险，高韧性，架构已具备生产级自适应能力)**

本独立评审员 (Reviewer-2) 兼对抗性审计员对 `AGY2_FundAdvisory` 重构产物进行了系统级鲁棒性推演、边缘行情压力测试、UI/UX 布局无头渲染审计及完整性审查。未发现任何硬编码欺诈、虚假通过 (Mock bypass) 或断言逃逸等完整性违规行为 (No Integrity Violations)。重构代码在业务逻辑真实性、极端行情自适应、1080p 零截断渲染与裁判基建保护方面表现优异。

---

## 二、关键审计项深度验证 (Verified Claims & Evidence)

### 1. 交互与视觉体验独立审计 (UI/UX AppTest & Visual Design)

| 审计维度 | 需求标准与断言 | 源码位置与实测实证 | 裁定结果 |
| :--- | :--- | :--- | :--- |
| **步骤二四阶白盒推演** | 1.2~1.8 秒舒适递进演算反馈；提供 4 个独立默认收起折叠面板 | `app_gui.py:710-766`<br>采用 4 阶 `time.sleep` (0.35s + 0.35s + 0.40s + 0.35s = 1.45s)，精确落入 [1.2, 1.8]s 区间。配合 `st.status` 动态递进展示海选、定调、回测、拆单。4 个白盒折叠框 (`st.expander`) 均显式声明 `expanded=False`。 | **PASS (优)** |
| **顶部 7 张核心卡片零截断** | 1080p 分辨率下主数值单行显示无省略号截断，黑话收纳进 ⓘ 悬停 | `app_gui.py:96-136, 316-438`<br>CSS 设置 `min-height: 94px; height: 94px; padding: 8px 10px; font-size: 15px;`。7 列各分得 ~240px，文案无硬编码省略号，专业概念（申赎时钟、因果状态机、乖离率、ERP、DR007、95%仓位折算）全部使用 `<span title="...">ⓘ</span>` 悬停解释。 | **PASS (优)** |
| **步骤三建仓执行单 9 列精简** | 严格保留 9 列，最后一列 <=15 字核心指令，表头 ⓘ 悬停 | `app_gui.py:1203-1223`<br>显式保留 `cols_9 = [...]` 变量定义与 9 列 DataFrame：`["基金代码", "基金名称", "份额", "目标占比(%)", "精确买入金额(元)", "最新净值", "实时估值涨跌(%)", "排雷与拥挤度", "实操分红与限购指引"]`。最后一列指令提炼为 10~11 字（如 `现金分红·限额买500`、`长钱持有·满期免赎A`），表头配置 ⓘ help 属性。 | **PASS (优)** |
| **步骤三存量调仓单 9 列精简与图标** | 控制在 9 列以内，醒目图标标明操作动作，<=15 字指令 | `app_gui.py:1430-1478`<br>显式保留 `rebal_cols_9 = [...]` 严格 9 列：`["基金代码", "基金名称", "份额", "当前市值(元)", "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)", "建议操作", "实操要点"]`。包含 5 类规范图标（`🔒 未满7天锁仓保护`、`⏳ 临近30天免赎期缓卖`、`➕ 建议加仓`、`➖ 建议减仓`、`✅ 维持持有`）。实操要点 9~12 字。 | **PASS (优)** |
| **三栏作战卡片《三句话看懂本方案》** | 收益引擎、反脆弱对冲、极端浮亏与底线铁律，位于步骤二与三之间 | `app_gui.py:1061-1116`<br>在步骤二与步骤三之间渲染三栏作战卡片。栏一拆解核心红利+动量进攻+拆单Alpha；栏二展示跨资产对冲与 1 年胜率；栏三量化历史最大极端浮亏金额与天数，并明确落实 7 天不赎、便宜区不割两条铁律，符合 `GEMINI.md` 实盘风控准则。 | **PASS (优)** |

### 2. 系统鲁棒性与极端行情压力测试 (Robustness & Extreme Scenarios)

#### 2.1 全局资产分类解析器 `classify_fund_asset_class` 边界压力测试
- **测试用例集**: 包含 `(None, None)`、`('', '')`、空白符、纯数字代码 `123456`、未知代码 `999999`、可转债、QDII 海外半导体、中证A500、科创50等 22 组极端样本。
- **测试实测结果**:
  - `(None, None)` 与未知测试标的平滑降级至合法兜底类别 `"其他权益资产"`，**100% 杜绝了已被废弃的 `"其他存量资产"` 产生**；
  - 核心池纯债标的 (`000086`, `002351`) 即使 `fund_name=None` 也可经由本地目录或 DuckDB 自动解析为 `"纯债固收"`；
  - 可转债标的 (`001234 某某可转债增强A`) 正确排除在纯债之外，识别为 `"其他权益资产"`；
  - 支持实例调用 (`pm.classify_fund_asset_class(...)`)、类调用 (`PortfolioManager.classify_fund_asset_class(...)`) 及模块级方法直调 (`classify_fund_asset_class(...)`) 三重多态兼容。

#### 2.2 动态多维风险预算 `compute_dynamic_tier_weights` 极端行情压力测试
针对 11 组极端或破坏性市场快照输入进行严苛测算：
1. `None snapshot`
2. `Empty snapshot ({})`
3. 异常类型字段 (`{'c300': 'bad', 'm20': None, 'market_state_code': 123}`)
4. NaN 价格序列 (`{'c300': float('nan'), 'm20': 4000, 'm60': 3800}`)
5. 极端超级大牛市 (状态码: `GROWTH_BULL`)
6. 极端超级大牛市 (纯价位推导: `c300=6000, m20=3500, m60=3200, m120=3000`)
7. 极端股灾深熊市 (状态码: `SEVERE_BEAR`)
8. 极端股灾深熊市 (纯价位推导: `c300=2000, m20=3800, m60=4000, m120=4200`)
9. 震荡收息基准态 (`STABLE_DIVIDEND`)
10. 流动性恐慌与深度贴水 (`DR007=18.5%, IV=75%, IC_Basis=-35%`)
11. 结构化中小盘主升浪 (`STRUCTURAL_500`)

**实测结果**:
- **权重求和与非负约束**: 11 组截面下所有档位权重之和 $\sum w_i \equiv 1.0000$（误差 $< 10^{-4}$），所有非零权重均严格 $> 0$；
- **全截面单调性 (Strict Monotonicity)**:
  - 牛市主升浪态: $\text{Equity}(C1): 0.20 < \text{Equity}(C2): 0.53 < \text{Equity}(C3): 0.74 < \text{Equity}(C4): 0.82 < \text{Equity}(C5): 0.92$
  - 震荡收息常态: $\text{Equity}(C1): 0.20 < \text{Equity}(C2): 0.51 < \text{Equity}(C3): 0.74 < \text{Equity}(C4): 0.78 < \text{Equity}(C5): 0.90$
  - 熊市破位止损态: $\text{Equity}(C1): 0.10 < \text{Equity}(C2): 0.25 < \text{Equity}(C3): 0.35 < \text{Equity}(C4): 0.50 < \text{Equity}(C5): 0.65$
  - 破坏性异常输入 (None / NaN / 类型错乱): 统一安全平滑收敛为震荡收息常态，单调性保持完全不破坏；
- **自适应避险与弹性进攻**: 熊市所有档位（含进取型 C4/C5）纯债与黄金防御敞口大幅扩充（C5 防御从 8% 提升至 35%，C4 防御从 18% 提升至 50%），高 Beta 弹性权益仓位严格算法止损；牛市状态下 C4/C5 均保证配置 `011613` $\ge 30\%$ 捕捉科技主升浪。

### 3. 系统只读裁判基建文件完整性验证 (Referee Invariant Check)

利用 `Get-FileHash -Algorithm SHA256` 与 `git status` 双向核对 4 个裁判基建文件：
- `AGY2_FundAdvisory/judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` (100% 一致)
- `AGY2_FundAdvisory/holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` (100% 一致)
- `AGY2_FundAdvisory/AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` (100% 一致)
- `AGY2_FundAdvisory/tests/test_infra.py`: `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` (100% 一致)
- `git status -s` 校验无任何未提交修改或文件时间戳漂移，基建红线绝对未遭侵犯。

### 4. 本地 8501 端口服务健康度实测

- 端口探测命令：`Get-NetTCPConnection -LocalPort 8501`
  - 状态：`State: Listen, OwningProcess: 18900`
- 健康探针接口调用：`Invoke-RestMethod -Uri 'http://127.0.0.1:8501/_stcore/health'`
  - 响应结果：`ok` (HTTP 200 OK，响应时间 < 20ms)。

### 5. 全套测试集回归独立审计 (Full Regression Suite)
- 执行命令：`python -m pytest AGY2_FundAdvisory/tests/ -q --tb=short`
- 实测结果：**`232 passed, 530 warnings in 350.67s`**
- 覆盖率：既有 222 项单元/集成测试 + 新增 10 项红队、GUI 与架构测试全部通过，通过率 100% (232/232 PASS)。

---

## 三、对抗性审查与红队挑战 (Adversarial Review Findings)

### 1. 静态反硬编码红队审查 (AST Static Code Inspection)
- 对 `strategy_bridge.py`、`portfolio_manager.py` 和 `app_gui.py` 进行了全 AST 语法树遍历：
  - 确认原 `portfolio_manager.py` 中的 77 只金融机构股票代码集合 `financial_codes` 与 `NON_ASHARE_CODES` 均已被彻底剔除；
  - 确认 `app_gui.py` 中不存在任何手写静态 `cat_map` 字典；
  - 确认 `screen_fund_look_through_risk` 采用了申万一级行业/名称关键词、造血现金流 (CFO > 0) 与存贷双高比率交叉验证的三层通用基本面排雷，不存在特异性针对某个股票代码跳过排雷的分支。

### 2. 双向变盘网格触发点位对抗性检验
- 验证针对 2800 ~ 5200 点任意市场价格输入，`StrategyBridge.get_rebalance_grid_status` 计算得到的向上突破进攻线点位严格高于现价，向下防守破位线点位严格低于现价：
  $$\text{breakdown\_threshold\_c300} < \text{c300\_current} < \text{surge\_threshold\_c300}$$
- 原代码中由于静态写死 `4180.5 / 4053.0` 导致的严重向下防守线倒挂高出现价问题已彻底绝迹。

### 3. 微小改进建议 (Minor Improvement Opportunity - 不阻碍审批)
- **发现**: 在 `app_gui.py` 中，四阶推演白盒采用了 4 个连续的 `time.sleep(0.35)` 阶梯来实现 1.45s 的人机交互等待节奏。在实际用户浏览器交互中体验良好，但在单元测试运行多个 AppTest 用例时会产生累积时间开销（如全套测试约需 4 分钟）。
- **建议**: 在后续版本维护中，可考虑在检测到环境变量 `PYTEST_CURRENT_TEST` 时自动将等待时间缩短至 `0.01s`，兼顾实盘交互质感与 CI/CD 极速回归。

---

## 四、评审裁决 (Final Verdict)

**VERDICT: APPROVE (批准通过)**

所有交付物均严格符合 `ORIGINAL_REQUEST.md` 与 `PROJECT.md` 的规范约定，系统鲁棒性坚固，交互与视觉体验达到了专业投顾桌面工作台的高水准要求。
