# Handoff Report — Explorer M3 Fix 2 (CUSUM 暴雷熔断风控探索)

## 1. Observation

### 1.1 `stress_test_cusum.py` 实测失败现象与报错
执行命令：
```powershell
py -3.11 d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py
```
运行输出：
```text
PASS: test_normal_no_decay
PASS: test_cusum_decay_accumulation_and_promotion
Traceback (most recent call last):
  File "d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py", line 108, in <module>
    test_instant_risk_meltdown()
  File "d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py", line 65, in test_instant_risk_meltdown
    assert res["is_promoted"]
           ~~~^^^^^^^^^^^^^^^
AssertionError
```
测试在第 3 项 `test_instant_risk_meltdown` 发生 `AssertionError`。经代码走查，若放行第 3 项，第 4 项 `test_instant_extreme_crowding` 同样会在 `assert res["is_promoted"]` 必现断言失败。

### 1.2 源码现状走查 (`portfolio_manager.py`)
在 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 1023~1067 行：
```python
1023:         # 排序：按 final_score 降序
1024:         scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)
1025: 
1026:         best_cand = scored_candidates[0]
1027:         max_score = best_cand["final_score"]
1028: 
1029:         champ_cand = next((c for c in scored_candidates if c["code"] == def_code), None)
...
1047:         # 结构性变点触发判定:
1048:         trigger_reasons = []
1049:         if c_curr >= self.threshold_h:
1050:             trigger_reasons.append(f"CUSUM 衰减指标 ({c_curr:.2f}) 突破阈值 {self.threshold_h:.1f}，超额持续落后")
1051:         if champ_risk < 60.0:
1052:             trigger_reasons.append(f"R1 底层排雷健康分 ({champ_risk:.1f}) 跌破 60 分安全警戒线，触发排雷熔断")
1053:         if champ_extreme_crowding:
1054:             trigger_reasons.append("R3 机构极度抱团松动预警，触发反拥挤避险换仓")
1055: 
1056:         is_triggered = len(trigger_reasons) > 0
1057:         is_promoted = False
1058:         active_champ_code = def_code
1059:         active_champ_name = champ_name
1060:         promotion_label = ""
1061: 
1062:         if is_triggered and best_cand["code"] != def_code:
1063:             is_promoted = True
1064:             active_champ_code = best_cand["code"]
1065:             active_champ_name = best_cand["name"]
1066:             promotion_label = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"
```

### 1.3 数学评分与因果反例现场还原
在 `test_instant_risk_meltdown` 测试用例中：
```python
candidates = [
    {"code": "100032", "name": "富国中证红利A", "er_score": 95, "fee_score": 90, "risk_score": 55, "sm_score": 90, "te_score": 90},
    {"code": "090010", "name": "大成中证红利A", "er_score": 85, "fee_score": 85, "risk_score": 95, "sm_score": 85, "te_score": 85},
]
```
多因子计算公式：
$S_{f,t} = 0.35 \times ER + 0.25 \times (100 - Fee) + 0.15 \times Risk + 0.15 \times SM + 0.10 \times (100 - TE)$
- 默认标的 `100032`（暴雷标的）：
  $0.35 \times 95 + 0.25 \times 90 + 0.15 \times 55 + 0.15 \times 90 + 0.10 \times 90 = 33.25 + 22.50 + 8.25 + 13.50 + 9.00 = 86.50$
- 备选标的 `090010`（安全标的）：
  $0.35 \times 85 + 0.25 \times 85 + 0.15 \times 95 + 0.15 \times 85 + 0.10 \times 85 = 29.75 + 21.25 + 14.25 + 12.75 + 8.50 = 86.50$
- 由于两者总分均为 86.50 分，且默认标的在候选列表排首位，Python 的 Timsort 保持稳定排序，使得 `scored_candidates[0]` 依然是默认暴雷标的 `100032`。
- 因此 `best_cand["code"] == "100032" == def_code`，第 1062 行 `best_cand["code"] != def_code` 判定为 `False`。
- 即使第 1051 行捕获了 `champ_risk = 55.0 < 60.0` 并记录了 `trigger_reasons`，第 1062 行跳过晋升赋值，导致：
  `is_promoted = False`，`active_champ_code = "100032"`（暴雷基金）！系统直接向用户推荐了暴雷标的！
- 在更恶劣的场景下：若默认基金发生造假（`risk_score = 40.0`），但过去 1 年 Alpha 极高（`er_score = 100`），其总分高达 91.0 分，远高于安全备选的 86.50 分，`best_cand` 更是稳居第 1 名，导致暴雷标的永远无法被系统淘汰换出！

### 1.4 历史测试中的冲突根源发现 (`test_adversarial_m3_challenger1.py`)
走查 `tests/test_adversarial_m3_challenger1.py` 第 434~449 行：
```python
434:     # 5.2 防呆守则：变点触发但原冠军依然是最高分 (严禁向自身晋升)
435:     candidates_self_best = [
436:         {"code": def_code, "name": def_name, "er_score": 85.0, "fee_score": 85.0, "risk_score": 55.0, "smart_money_score": 80.0, "te_score": 80.0},  # risk<60 触发变点
437:         {"code": alt_code, "name": alt_name, "er_score": 60.0, "fee_score": 60.0, "risk_score": 60.0, "smart_money_score": 60.0, "te_score": 60.0}   # 备选得分更低
438:     ]
439:     res_self = detector.evaluate_track_candidates(
440:         sector_id="bond",
441:         default_champion_code=def_code,
442:         candidates=candidates_self_best,
443:         c_prev=0.0
444:     )
445:     assert res_self["is_triggered"] is True  # 变点被 risk<60 触发
446:     assert res_self["is_promoted"] is False  # 但原冠军得分最高，不发生自我晋升
447:     assert res_self["active_champion_code"] == def_code
448:     assert res_self["promotion_label"] == ""
```
**关键发现**：
Challenger 1 先前编写的用例 5.2 混淆了“不可向自身晋升（即不可出现标签：优选了自己）”与“暴雷风控强淘汰”两项原则。该用例错误地假定“当冠军因 risk<60 暴雷但分数比备选高时，不应该换仓，应继续推荐暴雷冠军”。Worker 3 先前为了迎合该断言，写出了第 1062 行的 `if is_triggered and best_cand["code"] != def_code:`，直接埋下了当冠军暴雷时无法出局的严重量化风控隐患。

---

## 2. Logic Chain

1. **因果推导 1（排雷与反拥挤属于一票否决式硬约束）**：
   依据用户原始需求 R1、R6 以及 Wind 量化投顾风控铁律，底层穿透排雷评分（$Risk < 60.0$）代表标的底层资产出现财务造假、重大违约或立案调查风险；反拥挤预警（$ExtremeCrowding == True$ 或 $SM < 60.0$）代表微观结构踩踏与机构筹码松动。此类风险在量化选基中属于**硬性资格门禁（Hard Constraint Gate）**，绝不能被超额 Alpha 或低费率的加权分数所稀释覆盖。
2. **因果推导 2（剥夺资格与备选池清洗）**：
   当默认冠军标的触发排雷熔断（$Risk < 60.0$）或极度拥挤（$ExtremeCrowding$）时，系统必须在决策树第一顺位**剥夺其冠军推荐资格**。随后，晋升池必须将该默认标的彻底剔除，仅在剩余的“合格备选标的（Eligible Alternatives）”中进行选拔。
3. **因果推导 3（合格备选标的定义）**：
   备选标的同样必须满足安全门禁：$Risk \ge 60.0$ 且未处于极度拥挤状态。若某个备选标的自身也处于暴雷状态（例如 $Risk = 40.0$），则绝不能用“次级暴雷标的”替换“默认暴雷标的”。
4. **因果推导 4（替代晋升与状态标签流转）**：
   - 若合格备选标的池非空，选择其中 `final_score` 最高者晋升为新冠军标的；
   - 设定 `is_promoted = True`，`active_champ_code = promoted_cand["code"]`，`active_champ_name = promoted_cand["name"]`；
   - 生成符合 R6 规范的自进化优选标签：`f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"`。
5. **因果推导 5（纯 CUSUM 表现衰减与暴雷熔断的双轨解耦）**：
   - **轨道一（暴雷/拥挤硬熔断）**：默认标的资格被剥夺，只要存在合格备选，即强制触发晋升；
   - **轨道二（纯 CUSUM 累积衰减超标）**：默认标的本身健康（$Risk \ge 60.0$ 且未拥挤），仅当合格备选标的的得分实质性领先默认标的（`eligible_alternatives[0]["final_score"] > champ_score`）时才放行晋升。若默认标的健康且当下总分仍领先，则坚守防呆底线，不向更低分标的逆向晋升。

---

## 3. Caveats

1. **极端空池与全员暴雷边界场景**：
   - 若候选列表为空（`candidates == []`），或赛道内所有备选基金均处于暴雷/极度拥挤状态（无一合格），此时缺乏可承接资产，系统无法执行安全晋升。在此极端防御边界下，系统维持 `is_promoted = False` 并保留原始标的标识（但 `trigger_reasons` 明确如实记录排雷报警），避免抛出越界异常（`IndexError`）。
2. **测试用例对齐注意事项**：
   - 修复后，Reviewer 2 编写的对抗性测试 `stress_test_cusum.py` 将 100% 绿灯通过；
   - 但先前 Challenger 1 编写的 `tests/test_adversarial_m3_challenger1.py` 中的用例 5.2（第 434~449 行）包含错误的前提假设。执行修复时，负责测试或业务代码的 Worker 需同步修正该用例中的断言预期（由原本期望“暴雷时不晋升”更正为“暴雷时强制晋升至安全备选标的 `002351`”），否则该旧对抗用例会因旧断言而报错。
3. **自进化标签文案一致性**：
   - 标签格式严格保持 `f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"`，既契合 R6 原始需求规范，又完美兼容现有测试用例对“自进化优选”子串的断言。

---

## 4. Conclusion

### 4.1 核心修复方案设计
在 `portfolio_manager.py` 的 `CUSUMFundChangePointDetector.evaluate_track_candidates` 中，将第 1056~1067 行重构为“熔断剥夺 + 备选合格清洗 + 双轨晋升”架构：

#### 拟替换代码对比 (Diff Patch Blueprint)
```python
<<<<
        is_triggered = len(trigger_reasons) > 0
        is_promoted = False
        active_champ_code = def_code
        active_champ_name = champ_name
        promotion_label = ""

        if is_triggered and best_cand["code"] != def_code:
            is_promoted = True
            active_champ_code = best_cand["code"]
            active_champ_name = best_cand["name"]
            promotion_label = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"
====
        is_triggered = len(trigger_reasons) > 0
        is_champ_meltdown = bool(champ_risk < 60.0 or champ_extreme_crowding)

        # 备选基金合格性筛选 (排除默认冠军自身，且必须未发生暴雷与极度拥挤)
        # scored_candidates 已经按 final_score 降序排列
        eligible_alternatives = [
            c for c in scored_candidates
            if c["code"] != def_code
            and c.get("risk_score", 0.0) >= 60.0
            and not c.get("is_extreme_crowding", False)
        ]

        is_promoted = False
        active_champ_code = def_code
        active_champ_name = champ_name
        promotion_label = ""
        best_cand_out = best_cand

        if is_triggered:
            if is_champ_meltdown:
                # 默认冠军触发硬性排雷熔断或极度拥挤，立即剥夺推荐资格
                # 从剩余合格备选基金中挑选最高分者晋升
                if eligible_alternatives:
                    promoted_cand = eligible_alternatives[0]
                    is_promoted = True
                    active_champ_code = promoted_cand["code"]
                    active_champ_name = promoted_cand["name"]
                    best_cand_out = promoted_cand
                    promotion_label = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"
            else:
                # 默认冠军未暴雷，仅因 CUSUM 累积衰减超标
                # 要求备选标的合格且得分领先于原冠军 (严禁向自身晋升或向更低分标的晋升)
                if eligible_alternatives and eligible_alternatives[0]["final_score"] > champ_score:
                    promoted_cand = eligible_alternatives[0]
                    is_promoted = True
                    active_champ_code = promoted_cand["code"]
                    active_champ_name = promoted_cand["name"]
                    best_cand_out = promoted_cand
                    promotion_label = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"
>>>>
```
并在返回字典中（约第 1084 行）将 `"best_candidate": best_cand` 更新为 `"best_candidate": best_cand_out`。

### 4.2 关联回归测试对齐建议 (`test_adversarial_m3_challenger1.py`)
在 `tests/test_adversarial_m3_challenger1.py:445-448` 中，将用例 5.2 对齐为正向风控淘汰逻辑：
```python
    assert res_self["is_triggered"] is True  # 变点被 risk<60 触发
    assert res_self["is_promoted"] is True   # 原冠军暴雷资格剥夺，触发合格备选标的强制晋升
    assert res_self["active_champion_code"] == alt_code
    assert res_self["active_champion_name"] == alt_name
    assert "自进化优选" in res_self["promotion_label"]
```

---

## 5. Verification Method

### 5.1 独立复现与验证步骤
后续执行 Agent（Worker / Reviewer）在应用代码方案后，执行以下验证：

1. **运行 Reviewer 2 压力测试套件（直接检验目标修复效果）**：
   ```powershell
   py -3.11 d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py
   ```
   **期望结果**：
   ```text
   PASS: test_normal_no_decay
   PASS: test_cusum_decay_accumulation_and_promotion
   PASS: test_instant_risk_meltdown
   PASS: test_instant_extreme_crowding
   PASS: test_empty_candidates_graceful
   PASS: test_same_company_bonus_tilt
   ALL ADVERSARIAL STRESS TESTS PASSED!
   ```

2. **运行 Challenger 对抗测试套件（检验整体变点检测与风控机制）**：
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_adversarial_m3_challenger1.py
   ```
   **期望结果**：全量 7 项对抗测试 100% 通过（需包含对齐后的用例 5.2）。

3. **失效判定条件**：
   - 若 `stress_test_cusum.py` 仍报 `AssertionError`（说明暴雷标的依然未能被剔除晋升）；
   - 若当所有备选基金均暴雷时抛出 `IndexError` 异常（说明备选池空指针防御未生效）；
   - 若默认标的未暴雷但被更低分的备选标的反向逆向晋升（说明双轨解耦失效）。
