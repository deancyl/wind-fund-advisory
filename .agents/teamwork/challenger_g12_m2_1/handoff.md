# Milestone 2 独立实证挑战报告 (Empirical Challenge Report)

- **挑战专员**: `teamwork_challenger` (Milestone 2, Instance 1)
- **审查角色**: critic, specialist
- **挑战目录**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g12_m2_1\`
- **审查目标**: Milestone 2 移动止盈右侧破位逃顶、高水位回撤保护与多分支相互作用
- **裁决结论**: **APPROVE (批准通过)**

---

## 1. 观察事实 (Observation)

### 1.1 被测实现代码与逻辑结构
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (第 1707 至 1850 行)
- **实现事实**:
  1. **右侧破位逃顶分支** (第 1783 至 1810 行):
     ```python
     is_right_side_breakdown = (
         pnl_pct >= 10.0
         and bias_20 < 0.0
         and (slope_20 < 0.0 or single_day_drop > 1.5 * daily_vol)
     )
     ```
     触发时输出级别为 `"level": "red"`，维度为 `"dimension": "移动止盈"`，`"action_type": "take_profit"`，`"take_profit_ratio": 0.50`。
  2. **高水位浮盈回撤保护分支** (第 1790 至 1824 行):
     ```python
     is_hwm_drawdown_risk = (
         pnl_pct >= 10.0
         and hwm_dd >= 8.0
     )
     ```
     触发时输出级别为 `"level": "yellow"`，维度为 `"dimension": "移动止盈"`，`"action_type": "take_profit"`，`"take_profit_ratio": 0.40`。
  3. **高水位回撤 60 日峰值探测回退梯级** (第 1754 至 1781 行):
     梯级 1: `h.hwm_dd` / `h.hwm_drawdown` 直接提供浮点数；
     梯级 2: `h.peak_nav_60` 结合 `cur_nav` 测算 `(peak - cur) / peak * 100.0`；
     梯级 3: `radar_engine.sector_price_series[sec_id][-60:]` 截取近 60 日峰值；
     梯级 4: `h.history_navs[-60:]` 截取近 60 日净值列表最高点；
  4. **原有分支保留与优先级次序**:
     `is_right_side_breakdown` (先) -> `is_hwm_drawdown_risk` (次) -> `bias_20 > 6.0` (超买) -> `pnl_pct >= 15.0 and bias_20 > 5.0` (阶梯止盈) -> `pnl_pct <= -12.0` (深套诊断)。

### 1.2 独立实证测试套件构建
- **文件路径**: `tests/test_g12_m2_empirical_challenge.py`
- **规模与分类**: 共设计实装 4 大模块、37 项针对性压力与模糊测试：
  - **Module 1**: `TestRightSideBreakdownBoundaries` (12 项用例)
    - PnL 临界截断: 9.90% (不触发) vs 10.00% (触发)；9.994% vs 10.010%
    - 均线偏离度 Bias 截断: 0.0000% (未跌破，不触发) vs -0.0001% (严格跌破，触发)；+0.0001% (不触发)
    - 均线斜率 Slope 截断: 0.0000% (平盘，无急跌不触发) vs -0.0100% / -0.0001% (转负触发)
    - 单日急跌 Single Day Drop vs 1.5 * daily_vol: 1.5000% (不触发) vs 1.5001% (触发)
    - 日均波动率保底: `daily_vol = max(vol_20 / 15.811, 0.5)`，纯债低波下 0.74% 不触发 vs 0.76% 触发
    - 行情跌幅源反查: `fund_quotes[code]["gszzl"]`、`["change_pct"]`、`["chg_pct"]`；正收益行情绝对不被误计为跌幅
  - **Module 2**: `TestHighWaterMarkDrawdownProtection` (10 项用例)
    - HWM 回撤截断: 7.90% / 7.99% (不触发) vs 8.00% / 8.01% (触发 YELLOW 0.40)
    - 浮盈门槛约束: 即使回撤达 25%，若当前 PnL < 10.0% (如 9.9%) 亦绝不误报浮盈回撤
    - 60 日峰值探测 5 大机制全覆盖: `hwm_dd`、`hwm_drawdown`、`peak_nav_60`、`radar_engine.sector_price_series`、`history_navs`
    - 60 日时间窗口截断: 75 天前的超大历史峰值自动被裁剪忽略，仅以近 60 日真实最高点测算
  - **Module 3**: `TestBranchInteractionsAndPrecedence` (10 项用例)
    - 右侧破位与 HWM 回撤同时满足时，右侧破位 RED 0.50 绝对优先接管
    - HWM 回撤优先于常规阶梯止盈接管
    - 超买 (>6%) 与常规阶梯止盈独立触发与 ratio=0.40 保留
    - 深度套牢 (<= -12%) 独立触发
    - 6 只异构持仓多标的组合同时巡检，互不干扰、互不遮蔽、零串扰
    - 字典持仓 (`dict`) 与对象持仓 (`MockHolding`) 100% 对齐
  - **Module 4**: `TestPropertyBasedGenerativeFuzzing` (5 项用例)
    - 300 组伪随机连续状态参数向量 (seed=42) 全状态空间蒙特卡洛模糊测试
    - 状态向量区间: PnL [-30%, +50%], Bias [-15%, +15%], Slope [-5%, +5%], Drop [0%, 10%], HWM [0%, 30%], Vol [1%, 40%]
    - 严格验证数学不变量: 100% 逻辑判定自洽、单一持仓最多触发一条 Dim 4 警报、take_profit_ratio 严格收敛于 0.40 或 0.50、NaN/Inf/None 容错无崩溃。

### 1.3 自动化实证执行结果
```powershell
# 1. 独立挑战测试套件 (37 项通过)
py -3 -m pytest tests/test_g12_m2_empirical_challenge.py -v
# 结果: 37 passed in 20.38s

# 2. Worker Milestone 2 交付测试套件 (13 项通过)
py -3 -m pytest tests/test_g12_stop_profit_and_sensors.py -v
# 结果: 13 passed in 3.56s

# 3. 四大裁判文件哈希与只读红线测试 (14 项通过)
py -3 -m pytest tests/test_infra.py -v
# 结果: 14 passed in 6.17s
```
- **测试总计**: 64 项自动化测试 100% 绿灯全过，0 失败，0 错误，0 告警。
- **只读文件**: `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 哈希完全一致，零修改。

---

## 2. 逻辑推导链 (Logic Chain)

1. **边界精度推导**:
   - 依赖 1.1 与 1.2 观察，实测验证了在浮点数计算与比较中，`pnl_pct >= 10.0` 在 9.994% 与 10.000% 之间、`bias_20 < 0.0` 在 0.0000% 与 -0.0001% 之间、`slope_20 < 0.0` 在 0.0000% 与 -0.0001% 之间、`hwm_dd >= 8.0` 在 7.99% 与 8.00% 之间均表现出清晰确定的二值截断，无模糊震荡或浮点下溢误判。
2. **波动率自适应与保底机制推导**:
   - 依赖 1.1 观察，`daily_vol` 计算采用了 `max(vol_20 / 15.8113883, 0.5)`。实测验证了对于纯债类极端低波标的（`vol_20 = 2.0`），日均波幅自动触发 0.50% 底线保护，使单日急跌判定阈值（$1.5 \times 0.50\% = 0.75\%$）具备物理防护能力，杜绝了低波纯债因 0.1% 的日常微扰而误触发逃顶锁利。
3. **多分支优先级与互斥因果律推导**:
   - 依赖 1.1 与 1.2 观察，右侧破位（RED 0.50）在系统架构中代表趋势崩塌的最高紧急度，当其与近 60 日高水位回撤保护（YELLOW 0.40）同时满足时，`if ... elif` 严格确保了更高比例（50%）锁利优先输出，未发生预警降级或双重警报污染。
   - 当标的处于高位超买（`bias_20 > 6.0%`）或阶梯止盈（`bias_20 > 5.0%`）时，因 `bias_20 > 0` 严格互斥，右侧破位绝对不会误触发；而当大阴线砸破均线时，原先会失声的超买/阶梯止盈分支被右侧破位无缝承接，彻底消除了“浮盈坐过山车抹平”的历史风控盲区。
4. **蒙特卡洛全域不变量推导**:
   - 依赖 1.2 观察，对 300 组随机连续状态向量的检验表明：在连续参数空间内，`ActiveRiskSentry` 的判决函数与理论数学分段函数完全同构，且对于任意单只基金在维度 4 内绝不产生矛盾的多重动作。

---

## 3. 注意事项与边界假设 (Caveats)

1. **赛道序列与基金历史日线的优先级**:
   - 观察发现，当基金属于 14 大标准赛道时，`advisory_engine.py` 第 1766 行优先使用 `OpportunityRadarEngine` 的对应赛道日线计算高水位回撤；仅当标的未映射到 14 大赛道时，才会回退至持仓自身的 `history_navs`。这一设计符合投顾雷达对系统性赛道风险的宏观研判优先原则。
2. **非只读挑战代码隔离**:
   - 本次挑战测试套件严格收口于 `tests/test_g12_m2_empirical_challenge.py`，未向 `.agents/teamwork/` 写入任何 Python 测试或数据代码，严格遵守工作区布局准则。

---

## 4. 结论 (Conclusion)

- **综合风险评估**: **LOW (低风险，健壮稳定)**
- **正式裁决**: **APPROVE (批准通过 Milestone 2 交付)**
- **依据**:
  1. Milestone 2 实现的右侧破位逃顶、60 日高水位回撤保护、多源先行感知与日线原子自愈完全符合项目规范与契约要求；
  2. 独立实证测试套件 37 项压力与蒙特卡洛测试 100% 绿灯通过；
  3. 四大裁判文件哈希与只读红线 100% 完整无损。

---

## 5. 独立验证方法 (Verification Method)

任何接收智能体或审计员均可通过执行以下命令独立复现本报告的全部实证结论：

```powershell
# 1. 运行 Milestone 2 独立实证挑战压力与模糊测试套件 (37 项)
py -3 -m pytest tests/test_g12_m2_empirical_challenge.py -v

# 2. 运行 Worker Milestone 2 交付测试套件 (13 项)
py -3 -m pytest tests/test_g12_stop_profit_and_sensors.py -v

# 3. 运行四大只读裁判文件防作弊红线测试 (14 项)
py -3 -m pytest tests/test_infra.py -v
```

**失效条件 (Invalidation Conditions)**:
- 若修改 `ActiveRiskSentry` 导致 `bias_20 == 0.0` 时误触发右侧破位；
- 若修改 `pnl_pct` 导致低于 10.0% 时误触发移动止盈；
- 若 `take_profit_ratio` 在右侧破位时偏离 0.50；
- 上述命令中任一项出现 FAIL 或 ERROR 即视本报告结论失效。
