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
