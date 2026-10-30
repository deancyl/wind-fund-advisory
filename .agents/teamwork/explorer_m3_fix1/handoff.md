# Handoff Report — Explorer M3 Fix 1 (CUSUM 前台与业务流贯通勘测)

## 1. Observation (直接客观观测)

### 1.1 业务调用链断层实测 (CUSUM 0 调用)
1. **代码全文检索命中数**:
   - 在 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py` 全文检索 `cusum`、`evaluate_track_candidates`、`changepoint`，**匹配结果为 0 行**。
   - 在 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 全文检索 `cusum`、`evaluate_track_candidates`、`自进化优选`，**匹配结果为 0 行**。
2. **`strategy_bridge.py:3779-3783` 现状**:
   ```python
   @classmethod
   def get_tier_sector_fund_selection(cls, tier: str = "C3") -> Dict[str, Dict[str, Any]]:
       """获取当前档位对应的赛道、冠军标的与备选基金池 (R2/R5)"""
       t = str(tier).upper().strip() if tier else "C3"
       return dict(SECTOR_FUND_SELECTION_BY_TIER.get(t, SECTOR_FUND_SELECTION_BY_TIER["C3"]))
   ```
   该方法仅做静态字典浅拷贝返回，完全未接入 `PortfolioManager.cusum_detector` 变点检测引擎，导致各档位赛道推荐完全处于静态死锁。
3. **`app_gui.py:888-914` Step 1 白盒面板现状**:
   界面直接将 `sec_data['champion_code']` 与固定理由写出，完全未进行任何变点检测，也从未渲染需求 R6 明确规定的标签：
   `🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}`。
4. **`app_gui.py:916-978` Step 2 白盒面板现状**:
   目前仅展示了 4 张宏观信号卡片（沪深300生命线、60日风格动量、大小盘结构温度、股债性价比与衍生品），完全遗漏了 R2 明确要求的“Hedge 四大策略专家在线自适应权重占比卡片”（`snapshot.get('expert_weights')`）。

### 1.2 CUSUM 变点检测算法缺陷实测 (`stress_test_cusum.py`)
运行 Reviewer 2 编写的对抗性压力测试：
- 执行命令：`& "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py`
- 实测输出：
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
- **缺陷代码定位 (`portfolio_manager.py:1062`)**:
  ```python
  if is_triggered and best_cand["code"] != def_code:
      is_promoted = True
      active_champ_code = best_cand["code"]
      active_champ_name = best_cand["name"]
      promotion_label = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"
  ```
  在 `test_instant_risk_meltdown` 中，默认标的 `100032` 排雷分只有 55（<60 暴雷），触发 `is_triggered = True`。然而由于其历史 Alpha 较高，在综合多因子排序中仍名列第一（`best_cand["code"] == def_code`）。因此 `best_cand["code"] != def_code` 判定为 `False`，导致 `is_promoted` 未被置为 `True`，系统依然返回暴雷标的作为冠军！同理，在极度拥挤度踩踏预警（`is_extreme_crowding`）时存在相同漏洞。

### 1.3 `test_acceptance_r1_r7.py` 测试失败实测
- 执行命令：`cd d:\Google\Workspace\Wind\AGY2_FundAdvisory; python -m pytest tests/test_acceptance_r1_r7.py -k "test_slider_realtime_linkage_mode_a"`
- 报错信息：
  ```text
  AssertionError: 档位 C4 中 011613 权重占比应 >= 25%，实际为 19.67%
  ```
- 根因分析：在 `strategy_bridge.py:3570-3580`，M2 引入 EWMA 滚动 60 日波动率倒数加权：科创50（`STAR50_STITCH`）EWMA 年化波动率达 37.3%，缩放系数 `0.18 / 0.37265 = 0.483`，导致 C4 基础权重 30% 被削减至 14.49%，随后边界投影仅回补至 19.67%，低于既有测试中对进取型 C4 进攻底仓的硬性断言 `>= 25.0%`。

---

## 2. Logic Chain (推理演绎链)

1. **从断层现象推导业务影响**:
   - 依据观测 1.1，因为 `get_tier_sector_fund_selection` 仅返回静态字典且 `app_gui.py` 从未调用 `evaluate_track_candidates`，即使底层 `CUSUMFundChangePointDetector` 数学模型完备，前台所有用户看到的金牌标的与备选列表全部是硬编码写死的。
   - 当底层发生基金造假、排雷扣分或长期跑输时，系统无法向用户发出自进化晋升信号，违背了需求 R6 的初衷，形成了 Reviewer 2 所指出的“Facade（孤岛实现）”。
2. **从算法对抗推导风控漏洞**:
   - 依据观测 1.2，CUSUM 变点检测的核心目的在于“优胜劣汰”。当默认标的触发 `champ_risk < 60.0`（暴雷熔断）或 `champ_extreme_crowding == True`（极度抱团踩踏）时，默认标的已丧失担任冠军资格。
   - 当前逻辑未在候选池中剥离已暴雷的默认标的，直接取 `scored_candidates[0]`，在默认标的综合得分仍暂居第一时触发死锁，导致暴雷标的继续作为活跃冠军向用户推荐，构成严重风控隐患。
3. **从业务闭环推导端到端架构**:
   - 为实现 100% 纯因果演绎与真实端到端贯通：
     - `StrategyBridge.get_tier_sector_fund_selection(tier)` 必须作为统筹层，调用 `pm.evaluate_track_candidates` 获取当前赛道最新评估结果，并动态更新活跃冠军、晋升状态与备选排序；
     - `StrategyBridge.get_tier_quant_selection_table` 必须直接消费该动态结果，将晋升标的标记为 `🏆 冠军标的 (自进化优选)`，原默认标的转为 `备选 (原默认标的 (被反超))`；
     - `StrategyBridge.generate_zero_start_blueprint` 与 `app_gui.py` 存量调仓必须将晋升标的自动代入目标权重 `target_weights_funds`，使建仓执行单、调仓建议与白盒漏斗 100% 对齐；
     - `app_gui.py` Step 1 依据 `is_promoted` 真实渲染 `🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}` 提示框；Step 2 补齐 Hedge 4 大专家实时权重卡片。

---

## 3. Caveats (约束与前置边界)

1. **探索员只读红线**:
   - 本报告仅提供技术勘测、因果论证与代码级伪代码方案，探索员未修改任何工程源码。具体代码变更由后续 Fixer / Worker Agent 实施。
2. **算力与界面防抖缓存 (Anti-Throttling)**:
   - `evaluate_track_candidates` 在无缓存情况下对 20 只候选基金进行六维打分需耗时约 10~15 秒。在 `StrategyBridge` 中必须增加内存级防抖缓存（TTL 建议 30 秒），避免 Streamlit 每次交互与滑块拖动产生重复计算。
3. **测试用例兼容性协调**:
   - 对于 `test_slider_realtime_linkage_mode_a` 中 C4 档位 `011613` 权重断言 `>= 25.0%` 的问题，在 `compute_dynamic_tier_weights` 中为 C4/C5 进取型进攻标的设置不低于 25% 的保底，或协同维护测试断言，确保 EWMA 风险预算机制与测试用例平滑兼容。

---

## 4. Conclusion & Actionable Proposals (结论与落地方案)

针对 Reviewer 2 提出的退回项，需按以下四步实施闭环修复：

### 方案一：修复 `portfolio_manager.py` 中的 CUSUM 暴雷熔断缺陷
**目标文件**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` (约 1045~1070 行)
**具体修改逻辑**:
当检测到默认标的暴雷（`champ_risk < 60.0`）或极度拥挤（`champ_extreme_crowding`），或者 CUSUM 衰减突破阈值（`c_curr >= self.threshold_h`）时，合格晋升标的必须从**合规备选池**（`qualified_alts`）中按最高分选取：

```python
# -------------------------------------------------------------
# portfolio_manager.py / CUSUMFundChangePointDetector.evaluate_track_candidates
# -------------------------------------------------------------
# 1. 结构性变点触发判定:
trigger_reasons = []
is_decay_breakout = (c_curr >= self.threshold_h)
is_risk_meltdown = (champ_risk < 60.0)
is_crowding_meltdown = bool(champ_extreme_crowding)

if is_decay_breakout:
    trigger_reasons.append(f"CUSUM 衰减指标 ({c_curr:.2f}) 突破阈值 {self.threshold_h:.1f}，超额持续落后")
if is_risk_meltdown:
    trigger_reasons.append(f"R1 底层排雷健康分 ({champ_risk:.1f}) 跌破 60 分安全警戒线，触发排雷熔断")
if is_crowding_meltdown:
    trigger_reasons.append("R3 机构极度抱团松动预警，触发反拥挤避险换仓")

is_meltdown = is_risk_meltdown or is_crowding_meltdown
is_triggered = len(trigger_reasons) > 0

# 2. 筛选合格备选标的池 (排除默认标的与暴雷/踩踏标的)
qualified_alts = [
    c for c in scored_candidates
    if c["code"] != def_code and c.get("risk_score", 100.0) >= 60.0 and not c.get("is_extreme_crowding", False)
]

is_promoted = False
active_champ_code = def_code
active_champ_name = champ_name
promotion_label = ""

# 3. 优胜劣汰晋升逻辑:
if is_triggered and qualified_alts:
    best_alt = qualified_alts[0]
    # 若发生排雷/拥挤熔断，或累积超额衰减突破且备选标的领先
    if is_meltdown or is_decay_breakout or (best_alt["final_score"] >= champ_score):
        is_promoted = True
        active_champ_code = best_alt["code"]
        active_champ_name = best_alt["name"]
        promotion_label = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"
```

### 方案二：在 `strategy_bridge.py` 中贯通 `get_tier_sector_fund_selection`
**目标文件**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py`
1. **添加缓存与联动逻辑**:
   ```python
   _cached_tier_sector_selections: Dict[str, Tuple[float, Dict[str, Any]]] = {}

   @classmethod
   def get_tier_sector_fund_selection(
       cls,
       tier: str = "C3",
       enable_cusum_auto_promote: bool = True,
       force_reload: bool = False
   ) -> Dict[str, Dict[str, Any]]:
       """获取当前档位对应的赛道、冠军标的与备选基金池，全面接入 CUSUM 变点检测与冠军自动优胜劣汰 (R6)"""
       t = str(tier).upper().strip() if tier else "C3"
       cache_key = f"{t}_{enable_cusum_auto_promote}"
       now_ts = time.time()

       if not force_reload and cache_key in cls._cached_tier_sector_selections:
           cached_ts, cached_data = cls._cached_tier_sector_selections[cache_key]
           if now_ts - cached_ts < 30.0:
               return copy.deepcopy(cached_data)

       raw_dict = SECTOR_FUND_SELECTION_BY_TIER.get(t, SECTOR_FUND_SELECTION_BY_TIER["C3"])
       res_dict = copy.deepcopy(raw_dict)

       if enable_cusum_auto_promote:
           pm = cls._get_portfolio_manager()
           snapshot = cls.get_latest_market_snapshot()
           for sec_key, sec_data in res_dict.items():
               def_champ_code = str(sec_data["champion_code"]).strip().zfill(6)
               def_champ_name = str(sec_data["champion_name"])
               candidates = sec_data.get("alternatives", [])

               eval_res = pm.evaluate_track_candidates(
                   sector_id=f"{t}_{sec_key}",
                   default_champion_code=def_champ_code,
                   candidates=candidates,
                   snapshot=snapshot
               )
               sec_data["cusum_eval"] = eval_res
               sec_data["default_champion_code"] = def_champ_code
               sec_data["default_champion_name"] = def_champ_name
               sec_data["is_promoted"] = bool(eval_res.get("is_promoted", False))
               sec_data["promotion_label"] = str(eval_res.get("promotion_label", ""))
               sec_data["trigger_reasons"] = eval_res.get("trigger_reasons", [])
               sec_data["cusum_value"] = eval_res.get("cusum_value", 0.0)

               if sec_data["is_promoted"]:
                   new_code = str(eval_res["active_champion_code"]).strip().zfill(6)
                   new_name = str(eval_res["active_champion_name"])
                   sec_data["champion_code"] = new_code
                   sec_data["champion_name"] = new_name
                   sec_data["champion_reason"] = (
                       f"【自进化优选晋升】综合评分领先（得分 {eval_res.get('max_score', 0):.1f}），"
                       f"触发 CUSUM 变点轮换，已自动晋升为当前赛道推荐冠军标的。"
                   )

                   # 自动重排备选池：将原默认冠军置入备选头部并标记为 (原默认)，剔除已晋升的冠军
                   orig_entry = next((c for c in candidates if str(c.get("code")).strip().zfill(6) == def_champ_code), None)
                   if orig_entry is None:
                       orig_entry = {"code": def_champ_code, "name": f"{def_champ_name} (原默认)", "share_class": "A", "tag": "原默认金牌标的"}
                   else:
                       orig_entry = copy.deepcopy(orig_entry)
                       orig_entry["name"] = f"{def_champ_name} (原默认)"
                       orig_entry["tag"] = "原默认标的 (被反超)"

                   filtered_alts = [
                       a for a in sec_data.get("top_alternatives", [])
                       if str(a.get("code")).strip().zfill(6) not in [new_code, def_champ_code]
                   ]
                   sec_data["top_alternatives"] = [orig_entry] + filtered_alts

       cls._cached_tier_sector_selections[cache_key] = (now_ts, copy.deepcopy(res_dict))
       return res_dict
   ```

2. **在 `generate_zero_start_blueprint` 中对齐自进化冠军标的**:
   在 `target_weights_funds = cls.compute_dynamic_tier_weights(...)` 之后追加：
   ```python
   # 接入 CUSUM 自进化赛道冠军权重对齐 (R6)
   sec_selection = cls.get_tier_sector_fund_selection(tier=tier)
   for sec_data in sec_selection.values():
       if sec_data.get("is_promoted"):
           def_c = sec_data.get("default_champion_code")
           act_c = sec_data.get("champion_code")
           if def_c and act_c and def_c in target_weights_funds and act_c != def_c:
               w_auto = target_weights_funds.pop(def_c)
               target_weights_funds[act_c] = round(target_weights_funds.get(act_c, 0.0) + w_auto, 4)
   ```
   并在 `fund_rules` 中补充 `090010`（大成中证红利指数A）规则。

### 方案三：在 `app_gui.py` Step 1 与 Step 2 真实渲染
**目标文件**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
1. **Step 1 选基漏斗与冠军卡片渲染 (约 890~915 行)**:
   ```python
   sec_selection = StrategyBridge.get_tier_sector_fund_selection(active_tier)
   cols_sectors = st.columns(len(sec_selection))
   for idx, (sec_key, sec_data) in enumerate(sec_selection.items()):
       with cols_sectors[idx]:
           champ_code = sec_data["champion_code"]
           champ_name = sec_data["champion_name"]
           is_promoted = sec_data.get("is_promoted", False)

           st.markdown(f"**{sec_data['sector_name']}**")

           # R6: 真实渲染自进化优选晋升标签
           if is_promoted and sec_data.get("promotion_label"):
               st.success(sec_data["promotion_label"])
               st.markdown(f"🏆 **金牌标的**：`{champ_code}` {champ_name} ✨")
           else:
               st.markdown(f"🏆 **金牌标的**：`{champ_code}` {champ_name}")

           if sec_data.get("trigger_reasons"):
               st.caption(f"⚡ 变点触发：{'; '.join(sec_data['trigger_reasons'])}")
           st.caption(f"理由：{sec_data['champion_reason'][:36]}...")

           alt_options = [f"🏆 金牌: {champ_code} {champ_name}"] + [
               f"备选 {alt['code']} {alt['name']} ({alt.get('tag', '')})"
               for alt in sec_data.get("top_alternatives", [])
           ]
           current_choice = st.selectbox(
               f"替换备选标的",
               alt_options,
               key=f"sel_alt_{sec_key}_{active_tier}",
               label_visibility="collapsed"
           )
           if not current_choice.startswith("🏆"):
               chosen_code = current_choice.split()[1]
               st.session_state.custom_fund_overrides[champ_code] = chosen_code
               if sec_data.get("default_champion_code"):
                   st.session_state.custom_fund_overrides[sec_data["default_champion_code"]] = chosen_code
           else:
               if champ_code in st.session_state.custom_fund_overrides:
                   del st.session_state.custom_fund_overrides[champ_code]
               if sec_data.get("default_champion_code") in st.session_state.custom_fund_overrides:
                   del st.session_state.custom_fund_overrides[sec_data["default_champion_code"]]
   ```

2. **Step 2 白盒面板补齐 Hedge 四大专家权重展示 (约 975 行)**:
   ```python
   exp_weights = snapshot.get("expert_weights")
   if exp_weights and isinstance(exp_weights, dict):
       st.markdown("##### 🤖 《Hedge 在线多专家自适应乘性权重占比 (R2 在线学习)》")
       st.caption("四大正交分析流派每日根据风险调整后净效用 $u_{i,t}$ 在线乘性更新，胜率高、回撤小者自动获配更高权重：")
       w_c1, w_c2, w_c3, w_c4 = st.columns(4)
       expert_meta = [
           ("① 趋势动量专家", "trend_momentum", "#ef4444", "捕捉中长期均线突破与主升浪动量"),
           ("② ERP宏观估值专家", "erp_macro", "#38bdf8", "锚定股债性价比与历史估值安全边际"),
           ("③ 均线逆向专家", "ma_contrarian", "#34d399", "利用短周期负乖离与超卖反抽逆向布局"),
           ("④ 流动性与基差专家", "liquidity_basis", "#f59e0b", "跟踪资金面松紧度与期指年化贴水率")
       ]
       for col, (title, key, color, desc) in zip([w_c1, w_c2, w_c3, w_c4], expert_meta):
           with col:
               weight_val = float(exp_weights.get(key, 0.25)) * 100.0
               st.markdown(f"""
               <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px; text-align: center;">
                   <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px;">{title}</div>
                   <div style="font-size: 20px; font-weight: bold; color: {color}; margin-bottom: 4px;">{weight_val:.1f}%</div>
                   <div style="font-size: 11px; color: #64748b;">{desc}</div>
               </div>
               """, unsafe_allow_html=True)
   ```

3. **存量调仓场景 (约 1335 行)**:
   调仓目标权重生成时同样应用 `sec_selection` 中 `is_promoted` 的标的替换，确保调仓执行单与从0建仓蓝图完全对齐。

### 方案四：`test_acceptance_r1_r7.py` 断言兼容性
在 `strategy_bridge.py:3575` 处，对 C4 进取型档位的科创50核心进攻底仓设置不低于 25.0% 的保底，或协同将测试断言与 M2 EWMA 风险预算机制相协调，确保 `pytest tests/test_acceptance_r1_r7.py` 全绿通过。

---

## 5. Verification Method (独立检验方法)

后续实施完成后，按以下步骤进行独立闭环检验：

```powershell
# 1. 验证 CUSUM 暴雷与踩踏熔断压力测试 (必须 100% PASS)
& "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py

# 2. 验证 strategy_bridge 与 app_gui 中存在 CUSUM / 自进化优选贯通代码
& "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -c "
with open(r'd:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py', 'r', encoding='utf-8') as f:
    text = f.read()
    assert 'evaluate_track_candidates' in text, 'strategy_bridge 未接入 evaluate_track_candidates'
with open(r'd:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py', 'r', encoding='utf-8') as f:
    text = f.read()
    assert '自进化优选' in text, 'app_gui 未渲染自进化优选标签'
    assert 'expert_weights' in text, 'app_gui 未展示四大专家自适应权重'
print('STATIC AUDIT PASSED: All integrations confirmed!')
"

# 3. 运行端到端 GUI 渲染与验收测试
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
& "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_e2e_gui_render.py
& "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_acceptance_r1_r7.py
```

**失效条件 (Invalidation Conditions)**:
- 若 `stress_test_cusum.py` 仍抛出 `AssertionError`（暴雷标的依然未被淘汰）；
- 若 `strategy_bridge.py` 中的 `get_tier_sector_fund_selection` 仍为仅返回静态字典的假实现；
- 若 `app_gui.py` Step 1 中未能真实渲染 `🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}`；
- 若 `test_acceptance_r1_r7.py` 仍存在失败项。
