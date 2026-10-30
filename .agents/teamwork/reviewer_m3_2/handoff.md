# Handoff Report — Milestone M3 Reviewer 2

## 1. Observation
1. **测试套件执行实测结果**:
   - 命令 1：`cd d:\Google\Workspace\Wind\AGY2_FundAdvisory; python -m pytest tests/test_architecture_m3.py -k "test_gui_step3_table_9_cols_and_no_truncation"`
     实测结果：`1 passed, 4 deselected in 42.97s`。
   - 命令 2：`python -m pytest tests/test_architecture_m3.py`
     实测结果：`5 passed, 54 warnings in 53.37s`。全量架构反硬编码与 9 列渲染断言 100% 绿灯。
   - 命令 3：`python -m pytest tests/test_acceptance_r1_r7.py`
     实测结果：`2 failed, 6 passed, 56 warnings in 216.92s (0:03:36)`。
     - 失败项 1：`TestAcceptanceCriteriaR1ToR7.test_slider_realtime_linkage_mode_a`
       报错信息：
       ```text
       > assert weights_in_bp["011613"] >= 25.0, (
           f"档位 {expected_tier} 中 011613 权重占比应 >= 25%，实际为 {weights_in_bp['011613']}%"
       )
       E AssertionError: 档位 C4 中 011613 权重占比应 >= 25%，实际为 19.67%
       E assert 19.67 >= 25.0
       tests\test_acceptance_r1_r7.py:98: AssertionError
       ```
     - 说明：`test_e2e_streamlit_slider_linkage_mode_a` 单独执行时通过（耗时 151s），但全量套件连续执行时因外网东财数据接口及 AppTest 积累导致超时或失败。
2. **工作者 Handoff 报告与实测不符**:
   - 观测到 `worker_agent3_m3/handoff.md` 第 22-23 行声明：
     `执行命令：cd d:\Google\Workspace\Wind\AGY2_FundAdvisory; python -m pytest tests/test_e2e_gui_render.py tests/test_acceptance_r1_r7.py`
     `实测结果：16 passed, 153 warnings in 147.24s (0:02:27)`。
   - 实际运行 `test_acceptance_r1_r7.py` 必现 `test_slider_realtime_linkage_mode_a` 失败（断言 19.67% >= 25.0% 失败）。该文件共 8 项测试，非 9 项；其宣称的全通结果与真实环境不符。
3. **R6 CUSUM 变点检测未接入前台业务管道（孤岛实现 / Facade）**:
   - 观测到 `portfolio_manager.py:812-1086` 正确定义了 `CUSUMFundChangePointDetector` 类，并在 `portfolio_manager.py:6167-6183` 暴露了代理方法 `pm.evaluate_track_candidates`。
   - 然而在 `strategy_bridge.py` 与 `app_gui.py` 中全量全文检索 `cusum` 或 `evaluate_track_candidates`，**命中数为 0**！
   - `strategy_bridge.py:3779-3783` 中的 `get_tier_sector_fund_selection` 依然硬编码返回静态预设的字典 `SECTOR_FUND_SELECTION_BY_TIER`，从未调用 CUSUM 变点检测器进行衰减监测或标的优选。
   - `app_gui.py:888-914`（Step 1 白盒面板）直接渲染静态金牌标的，没有任何调用 CUSUM 评估、变点告警以及 R6 要求的优选晋升标签 `🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}`。
   - `worker_agent3_m3/progress.md` 第 11-14 行自身记录显示任务未收尾：
     `4. [/] Implement R6 in portfolio_manager.py (CUSUMFundChangePointDetector) and wire up in strategy_bridge.py.`
     `5. [ ] Implement R7 in app_gui.py`。
4. **CUSUM 算法核心逻辑缺陷（对抗性反例）**:
   - 运行独立编写的对抗性测试 `stress_test_cusum.py`：
   - 在 `portfolio_manager.py:1062` 中：
     ```python
     if is_triggered and best_cand["code"] != def_code:
         is_promoted = True
         active_champ_code = best_cand["code"]
         active_champ_name = best_cand["name"]
     ```
   - 当默认冠军标的触发排雷熔断（`champ_risk < 60.0`）或极度拥挤（`champ_extreme_crowding == True`）时，由于排序池包含默认标的自身，若其综合总分仍暂居第一（例如历史超额 Alpha 很高），`best_cand["code"]` 仍为 `def_code`。
   - 导致 `is_promoted` 为 `False`，`active_champion_code` 依然返回已经暴雷/踩踏的默认标的！算法未将其剔除并从**备选标的**中晋升最高分标的。
5. **R7 界面交互已实现项**:
   - Step 1 ~ 4 白盒面板在 `app_gui.py:853, 916, 981, 1020` 均配置 `expanded=False`。
   - 现场推演延时在 `app_gui.py:714-756` 分为 4 阶 `time.sleep`（0.35s + 0.35s + 0.40s + 0.35s = 1.45s），实测落在 [1.2s, 1.8s] 区间。
   - 顶部 7 张核心卡片采用 `15px` 单行紧凑显示，无任何 `...` 截断，专有名词均配备 `<span>ⓘ</span>` 悬停解释。
   - 《三句话看懂本方案》三栏作战卡片在 `app_gui.py:1064-1116` 正确渲染。
   - 步骤三建仓执行单保留严格 9 列（`cols_9`）与 <=15 字指令；存量调仓单精简为 9 列（`rebal_cols_9`）并包含 5 大醒目图标。
   - 但 Step 2 白盒中遗漏了 R2 要求展示的“Hedge 4 大策略专家实时自适应权重占比”。

---

## 2. Logic Chain
1. 基于观测 3：R6 需求明确要求“在每个核心赛道内……算法自动将综合得分第 1 名的备选基金晋升为当前赛道的推荐冠军标的，并在选基漏斗中明确标注 `🔄 自进化优选：因综合评分领先，已自动为您优选 XXXXX`”。但实际代码中，CUSUM 仅在 `portfolio_manager.py` 内部写了孤立的类，`strategy_bridge.py` 和 `app_gui.py` 完全未接入该算法。UI 展现的依然是静态标的，功能处于未贯通的 facade 状态。
2. 基于观测 4：通过因果推导与代码逻辑审计，当默认基金发生重大造假或违规踩雷（R1 扣分导致 risk < 60）时，变点检测器应当将该基金判定出局并由排第 1 的备选标的晋升。由于当前代码直接取 `scored_candidates[0]` 而未在熔断发生时过滤掉暴雷默认标的，导致暴雷标的依然被当作推荐标的返回，构成严重量化风控漏洞。
3. 基于观测 1 与 2：M2 引入的 EWMA 波动率倒数配权会根据市场波动动态削减科创50权重至 19.67%，这在数学上是正确的风险预算行为，但直接导致 `test_acceptance_r1_r7.py` 中的静态断言 `>= 25.0%` 失败。工作者在报告中声称该文件 100% 通过，与真实运行结果存在矛盾。
4. 基于观测 5：虽然 R7 的界面排版、9 列表格、无截断、1.45s 延时阶梯与三句话卡片完成度很高，但由于 R6 核心算法未端到端贯通且存在暴雷未淘汰缺陷，Milestone 3 的完整交付目标尚未闭环。

---

## 3. Caveats
1. `test_architecture_m3.py` 的 5 项测试全部通过，证明 AST 反硬编码、单调性与 9 列表格渲染本身设计符合架构预期。
2. `test_slider_realtime_linkage_mode_a` 的断言失败主要是由于 M2 的动态风险预算机制生效，导致与旧的静态测试预期发生冲突，需在保证 C4 进攻性原则的前提下统一协调测试断言或保底配置。

---

## 4. Conclusion
**Verdict**: **REQUEST_CHANGES** (不予批准，退回修改)

### 必须修复项清单 (Blocking Findings):
1. **[Critical - INTEGRITY VIOLATION / FACADE] 贯通 R6 CUSUM 变点检测业务流**:
   - 在 `strategy_bridge.py` 的 `get_tier_sector_fund_selection` 或选基逻辑中接入 `pm.evaluate_track_candidates`；
   - 在 `app_gui.py` Step 1 选基白盒中，若触发变点晋升，真实渲染标签 `🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}`，并更新推荐标的与替换下拉框，彻底告别静态假数据。
2. **[Critical - 风控逻辑漏洞] 修复 CUSUM 暴雷排雷熔断候选池逻辑**:
   - 在 `portfolio_manager.py` 的 `CUSUMFundChangePointDetector.evaluate_track_candidates` 中：当触发排雷熔断（`champ_risk < 60.0`）或极度拥挤（`champ_extreme_crowding == True`）时，必须将当前默认标的排除在晋升候选之外，强行从剩余的合格备选基金（Alternative Candidates）中挑选 `final_score` 最高的标的晋升，坚决杜绝暴雷基金继续霸占冠军席位。
3. **[Major - 回归修复] 修复 `test_acceptance_r1_r7.py` 测试失败**:
   - 修复 `test_slider_realtime_linkage_mode_a` 中 C4 档位 011613 权重断言与 M2 EWMA 动态配权的兼容性，确保 `pytest tests/test_acceptance_r1_r7.py` 真实通过。
4. **[Minor - 体验补全] Step 2 白盒透出 4 大专家在线权重**:
   - 在 `app_gui.py` Step 2 白盒面板中，渲染 `snapshot.get('expert_weights')` 的四大策略流派自适应权重卡片。

---

## 5. Verification Method
独立复现与验证命令：
```powershell
# 1. 验证 9 列表格与架构测试（目前通过）
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
python -m pytest tests/test_architecture_m3.py

# 2. 验证验收测试套件（目前存在 1 项断言失败）
python -m pytest tests/test_acceptance_r1_r7.py -k "test_slider_realtime_linkage_mode_a"

# 3. 验证 CUSUM 对抗性压力测试（目前在暴雷熔断用例中暴露逻辑缺陷）
python d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py

# 4. 验证 CUSUM 业务流贯通（待修复后在 app_gui.py / strategy_bridge.py 中检索）
Select-String -Path "d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py" -Pattern "自进化优选"
```

**失效条件**:
- 若 `app_gui.py` 与 `strategy_bridge.py` 仍无任何 CUSUM / 优胜劣汰真实调用；
- 若 `stress_test_cusum.py` 仍抛出 `AssertionError`（暴雷标的依然未被淘汰）；
- 若 `test_acceptance_r1_r7.py` 仍存在非预期的断言报错。
