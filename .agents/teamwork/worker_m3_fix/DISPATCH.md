## 2026-10-30T03:34:22Z
你是 Milestone 3 返工实施专家 (Worker M3 Fix)。你的工作目录是：`d:\Google\Workspace\Wind\.agents\teamwork\worker_m3_fix\`。

### MANDATORY INTEGRITY WARNING
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 绝对红线
1. 严禁触碰、修改或解锁系统已设为只读的 4 个裁判基建文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
2. 严格保持 100% 纯数学因果演绎（No Look-Ahead Bias），零未来函数，零外部大模型 API，零日历硬编码。
3. 必须先完整阅读用户原始需求：`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`。
4. 必须深入阅读 3 位探索员的勘测报告：
   - `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix1\handoff.md` (前台业务流贯通与 UI 自进化优选标签设计)
   - `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix2\handoff.md` (暴雷熔断风控算法与双轨晋升修复设计)
   - `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3\handoff.md` (测试断言与动态配权兼容性设计)
   - `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py` (Reviewer 2 对抗测试脚本)

### 独占写入文件范围 (Write Ownership)
你拥有且仅拥有以下 4 个文件的独占修改权：
1. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`
2. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py`
3. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
4. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_adversarial_m3_challenger1.py`

### 具体实施任务清单

#### 任务 1：修复 `portfolio_manager.py` 中的 CUSUM 暴雷与拥挤熔断漏洞
- 位置：`portfolio_manager.py` 中的 `CUSUMFundChangePointDetector.evaluate_track_candidates` (约 1045~1070 行)
- 依据 `explorer_m3_fix2/handoff.md` 第 4 节实施“熔断剥夺 + 备选合格清洗 + 双轨晋升”：
  1. 定义 `is_champ_meltdown = bool(champ_risk < 60.0 or champ_extreme_crowding)`。
  2. 构造合格备选池 `eligible_alternatives`：从 `scored_candidates`（已按 final_score 降序）中筛选出 `c["code"] != def_code` 且 `c.get("risk_score", 0.0) >= 60.0` 且 `not c.get("is_extreme_crowding", False)` 的标的。
  3. 双轨解耦判断：
     - 若 `is_triggered` 且 `is_champ_meltdown`：默认冠军资格被剥夺，只要 `eligible_alternatives` 非空，即强制晋升最高分合格备选 `eligible_alternatives[0]`：
       `is_promoted = True`, `active_champ_code = promoted["code"]`, `active_champ_name = promoted["name"]`, `promotion_label = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"`，并令 `best_cand_out = promoted`。
     - 若 `is_triggered` 且非暴雷（纯 CUSUM 累积衰减超标）：要求 `eligible_alternatives` 非空且 `eligible_alternatives[0]["final_score"] > champ_score` 时放行晋升。
  4. 返回字典中，将 `"best_candidate"` 更新为 `best_cand_out`。

#### 任务 2：对齐 `tests/test_adversarial_m3_challenger1.py` 回归断言
- 位置：`tests/test_adversarial_m3_challenger1.py:445-448` 用例 5.2。
- 依据 `explorer_m3_fix2/handoff.md` 第 4.2 节对齐为正向风控淘汰逻辑：
  ```python
  assert res_self["is_triggered"] is True
  assert res_self["is_promoted"] is True
  assert res_self["active_champion_code"] == alt_code
  assert res_self["active_champion_name"] == alt_name
  assert "自进化优选" in res_self["promotion_label"]
  ```

#### 任务 3：在 `strategy_bridge.py` 中贯通 CUSUM 业务流与 C4 进攻性底仓保护
- 依据 `explorer_m3_fix1/handoff.md` 第 4 节：
  1. 重构 `StrategyBridge.get_tier_sector_fund_selection(cls, tier: str = "C3", enable_cusum_auto_promote: bool = True, force_reload: bool = False)`：
     - 实现 30 秒内存级防抖缓存 `_cached_tier_sector_selections`。
     - 启用时遍历赛道调用 `pm.evaluate_track_candidates`，若 `is_promoted` 则更新赛道 `champion_code`、`champion_name`、`champion_reason`、`is_promoted`、`promotion_label`、`trigger_reasons` 等。
     - 动态重排备选池：将原默认冠军以 `(原默认)` 置入备选头部，剔除晋升后的冠军。
  2. 在 `generate_zero_start_blueprint` 中对齐自进化冠军标的：将 `target_weights_funds` 中的默认冠军替换为晋升冠军代码，在 `fund_rules` 中支持 `090010`。
  3. 依据 `explorer_m3_fix3/handoff.md` 第 4 节：在 `generate_zero_start_blueprint` 紧随 C2/C3 SPX 兜底之后（约 3897 行），添加 C4/C5 进攻底仓校准保护：
     ```python
     if tier in ["C4", "C5"] and "011613" in target_weights_funds:
         if target_weights_funds["011613"] < 0.25:
             diff = round(0.25 - target_weights_funds["011613"], 4)
             if "100032" in target_weights_funds and target_weights_funds["100032"] >= (0.20 + diff):
                 target_weights_funds["100032"] = round(target_weights_funds["100032"] - diff, 4)
                 target_weights_funds["011613"] = 0.25
             elif "002351" in target_weights_funds and target_weights_funds["002351"] >= diff:
                 target_weights_funds["002351"] = round(target_weights_funds["002351"] - diff, 4)
                 target_weights_funds["011613"] = 0.25
     ```
  4. 确保存量调仓 `rebalance_portfolio` 路径同样消费自进化优选结果。

#### 任务 4：在 `app_gui.py` 中真实渲染自进化优选与四大专家在线权重
- 依据 `explorer_m3_fix1/handoff.md` 第 4 节：
  1. Step 1 (约 890~915 行)：
     - 若 `is_promoted` 且有 `promotion_label`，使用 `st.success(sec_data["promotion_label"])` 突出展示，并给金牌标的增加 `✨` 提示。
     - 渲染触发原因 `st.caption(f"⚡ 变点触发：{'; '.join(sec_data['trigger_reasons'])}")`。
     - 确保 `custom_fund_overrides` 适配变点后的标的代码。
  2. Step 2 (约 975 行)：
     - 读取 `snapshot.get('expert_weights')`，以四列卡片展示 Hedge 四大正交专家在线权重占比：
       ① 趋势动量专家 (`trend_momentum`)、② ERP宏观估值专家 (`erp_macro`)、③ 均线逆向专家 (`ma_contrarian`)、④ 流动性与基差专家 (`liquidity_basis`)。

### 验证标准（必须全部在终端实测跑通并记录在 handoff.md）
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
# 1. 对抗压力测试 (解决 Reviewer 2 否决项)
py -3.11 d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py

# 2. M3 架构与 Challenger 对抗单测
py -3.11 -m pytest tests/test_architecture_m3.py tests/test_adversarial_m3_challenger1.py tests/test_adversarial_m3_challenger2.py

# 3. 验收套件联动断言
py -3.11 -m pytest tests/test_acceptance_r1_r7.py -k "test_slider_realtime_linkage_mode_a"

# 4. M2 波动率脉冲防倒挂
py -3.11 -m pytest tests/test_adversarial_m2_challenger.py -k "test_adv_ewma_volatility_pulse_budget_transfer"
```
