# Milestone 2 评审与对抗性审计报告 (Review & Adversarial Audit Report)

- **评审员/对抗批评家**: `teamwork_reviewer` (Instance: reviewer_g12_m2_1)
- **评审对象**: Milestone 2 交付物 (`worker_g12_m2/handoff.md`)
- **评审裁决 (Verdict)**: **APPROVE (完全批准通过)**
- **评审时间**: 2026-11-08T16:19:00Z
- **工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g12_m2_1\`

---

## 1. 观察事实 (Observation)

### 1.1 `ActiveRiskSentry` 维度 4 移动止盈与右侧破位实装检查
- **文件路径**: `AGY2_FundAdvisory/advisory_engine.py` (第 1708 至 1850 行)
- **事实**:
  - `is_right_side_breakdown = (pnl_pct >= 10.0 and bias_20 < 0.0 and (slope_20 < 0.0 or single_day_drop > 1.5 * daily_vol))` 准确实装，触发 RED 警报 (`level: "red"`，`dimension: "移动止盈"`，`action_type: "take_profit"`，`take_profit_ratio: 0.50`)。
  - `is_hwm_drawdown_risk = (pnl_pct >= 10.0 and hwm_dd >= 8.0)` 准确实装，触发 YELLOW 警报 (`level: "yellow"`，`dimension: "移动止盈"`，`action_type: "take_profit"`，`take_profit_ratio: 0.40`)。
  - 原有短期超买 (`bias_20 > 6.0%`, `take_profit_ratio: 0.40`)、浮盈阶梯止盈 (`pnl_pct >= 15.0% and bias_20 > 5.0%`, `take_profit_ratio: 0.40`) 与深套诊断 (`pnl_pct <= -12.0%`) 分支 100% 完整保留。
  - `daily_vol = max(vol_20 / 15.8113883, 0.5)` 设定了下界 0.5%，且代码中并无除以 daily_vol 的操作（为乘法 `1.5 * daily_vol`），杜绝了 ZeroDivisionError。
  - 对 `single_day_drop` 采用 `abs()` 归一化处理，兼容正负号传入。
  - 未发现任何针对测试标的（如 `008888`、`161725`、`000216`）的硬编码作弊或特例 bypass 逻辑。

### 1.2 `app_gui.py` 动态止盈比例与晨报先行指标呈现检查
- **文件路径**: `AGY2_FundAdvisory/app_gui.py` (第 2880-2915 行, 第 3120-3130 行, 第 4625-4650 行)
- **事实**:
  - 第 3126 行：主动预警哨点击处置时，将原本静态的 0.40 改造为动态读取预警字段：
    `st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": float(alert.get("take_profit_ratio", 0.40))}`。
  - 第 4632 行：Tab 2 顶部横幅动态渲染比例 `下调目标权重 {int(tp_info.get('ratio', 0.4)*100)}%`（当比率为 0.50 时呈现 50%）。
  - 第 2885-2910 行：首屏双翼晨报 `pulse_card_html` 中紧凑嵌入 `🔥 舆情情绪温度: {sent_score:.0f}分 ({sent_label})` 与 `🌐 跨市场联动: 10Y国债 {cgb_10y_str} ｜ {gold_summary} ｜ {nasdaq_summary}`，并具备根据得分阈值自适应渲染红绿主色调的能力。

### 1.3 `data_loader.py` 四大新增函数真逻辑与健壮性检查
- **文件路径**: `AGY2_FundAdvisory/data_loader.py` (第 2440 至 2930 行)
- **事实**:
  1. `calc_financial_news_sentiment`: 构建包含 45 个金融看多词汇与 45 个金融看空词汇的极性词典，计算净多空占比 `(pos - neg) / total` 并线性映射至 `[10.0, 95.0]` 区间，空输入或无命中时返回 `(50.0, "中性均衡")`。
  2. `fetch_macro_cross_market_indicators`: 优先读取本地 `data/macro/chinabond_yield_curve.parquet` 获取中债 10 年期国债收益率，联网采集新浪行情 `sh518880`（黄金 ETF）与 `gb_ixic`（纳斯达克综合指数），具备 60 秒内存 TTL 缓存与完备本地离线兜底。
  3. `fetch_sector_core_etf_metrics`: 单次 HTTP 请求批量拉取 14 只核心 ETF 的东财实时量能放量比 (`f10`) 与折溢价率 (`f43`)，具备 30 秒内存 TTL 缓存及 14 只 ETF 全量离线回退。
  4. `auto_heal_sector_parquets`: 探测本地细分赛道 Parquet 最新日期与全收益对齐矩阵 `aligned_matrix_total_return.parquet` 的缺口，通过东财日 K 线 API 或对齐矩阵进行增量补全，按日期排序去重后通过 `.tmp` 临时文件与 `os.replace` 进行原子替换写入，天然免疫文件损坏风险；二次执行时检测到 `last_date >= target_latest_date` 自动跳过，保证幂等。

### 1.4 四大只读裁判文件与契约零触碰核验
- **Git Diff 状态**:
  - `AGY2_FundAdvisory/judge_engine.py`: **0 变动 (Clean)**
  - `AGY2_FundAdvisory/holdout_vault.py`: **0 变动 (Clean)**
  - `AGY2_FundAdvisory/AGENT_SPEC.md`: **0 变动 (Clean)**
  - `tests/test_infra.py`: **0 变动 (Clean)**
  - `DataLoader.simulate_execution` 默认入参与 7 天 1.50% 扣费逻辑: **0 变动 (Clean)**
  - 全局 `c:\Users\deanc\.gemini\GEMINI.md`: **0 变动 (Clean)**

### 1.5 独立执行测试套件记录
- `py -3 -m pytest tests/test_infra.py -v`: 14 passed in 5.81s
- `py -3 -m pytest tests/test_g12_stop_profit_and_sensors.py -v`: 13 passed in 3.29s
- `py -3 -m pytest tests/test_adv_final_closure.py -v`: 14 passed in 38.12s
- `py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v`: 11 passed in 20.12s
- **总计**: 52 项用例 100% 绿灯通过，无任何失败或错误。

---

## 2. 逻辑推导链 (Logic Chain)

1. **从观察 1.1 到量化有效性**:
   - 右侧破位逻辑结合了“收益安全垫存量”（$\text{pnl} \ge 10\%$）与“趋势逆转三要素”（跌破 MA20、均线斜率转负、单日跌幅超过 $1.5\sigma_{\text{day}}$）。相较于原仅在超买（$\text{bias} > 5\%$）时提示，有效弥补了突发见顶大阴线破位时系统失声的严重漏洞，使止盈减仓 50% 的决策逻辑具备坚实的因果链条。
2. **从观察 1.2 到端到端交互闭环**:
   - `take_profit_ratio` 成功打通了从 `advisory_engine.py` (计算产生) $\rightarrow$ `app_gui.py` (按钮点击注入 `session_state.tab2_pending_take_profit`) $\rightarrow$ Tab 2 (横幅展示与传参) $\rightarrow$ `strategy_bridge.py` (执行减仓 50%) 的完整链路。无断点、无假假常数截断。
3. **从观察 1.3 到底座自愈与感知真实性**:
   - `auto_heal_sector_parquets` 通过原子临时文件替换覆写，既消除了历史赛道 Parquet 日期落后的数据断层，又杜绝了多线程并发读写导致 Parquet 损坏的隐患；宏观先行指标与 ETF 放量比均具备双轨缓存与离线保护，保证在任何极端网络波动下 Streamlit 前端 0 崩溃。
4. **从观察 1.4 到契约守正与零作弊认定**:
   - 四大裁判文件哈希与 git diff 均为 0，无未来函数，无伪随机数，无门禁绕过，无反作弊作弊。

---

## 3. 注意事项与边界假设 (Caveats)

1. **极端网络超时与离线假定**:
   - 当东财或新浪行情端点在盘中发生极端网络断连（超时 > 2.5s）时，先行指标与 ETF 放量比会自动回退至静态/本地缓存。该兜底保证了系统的健壮性，但在极端无网状态下无法反映日内毫秒级突变，此为合理设计。
2. **高水位回撤回溯长度**:
   - HWM 回撤当前默认取近 60 个交易日窗口，对于新上市或持仓不足 5 个交易日的极端次新基，系统会安全跳过 HWM 计算并依靠跌破 MA20 或深套诊断进行保护。

---

## 4. 结论与裁决 (Conclusion & Verdict)

**最终裁决: APPROVE (完全批准通过)**

- **完整性**: Milestone 2 所有指定任务（Sentry 维度 4 移动止盈右侧破位、高水位回撤保护、GUI 动态比例注入、晨报先行指标、Parquet 原子自愈、宏观/ETF/舆情感知算子）100% 达成。
- **真实性**: 零假常数，零作弊绕过，零 facade 假实现，所有测试均通过真实逻辑与极限边界挑战。
- **安全性**: 四大裁判文件零变动，52 项自动化测试 100% 绿灯。准予进入 Milestone 3 (7D GP 基因进化与弹窗 UI 闭环)。

---

## 5. 独立验证方法 (Verification Method)

后续任何人均可通过以下标准命令进行独立无偏差复现核验：

```powershell
# 1. 核验四大裁判文件 0 变动
git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py

# 2. 运行 Milestone 2 专项测试套件 (13 项)
py -3 -m pytest tests/test_g12_stop_profit_and_sensors.py -v

# 3. 运行裁判文件与红线守卫测试 (14 项)
py -3 -m pytest tests/test_infra.py -v

# 4. 运行投顾全功能闭环回归测试 (14 项)
py -3 -m pytest tests/test_adv_final_closure.py -v

# 5. 运行 Milestone 1 核心风控专项测试 (11 项)
py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v
```
