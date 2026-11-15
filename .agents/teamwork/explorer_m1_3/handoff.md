# Handoff Report — Explorer M1-3
**Milestone**: M1 (十维真实投票与汇率校验及胶囊联动)  
**Focus**: Feature 6 (胶囊4存量病灶与胶囊5今日行动准则联动) 及 M1 全量测试套件覆盖与兼容性设计  
**Author**: Explorer M1-3  
**Date**: 2026-11-15T08:12:00Z  

---

## 1. Observation (客观法证观察)

### 1.1 胶囊4与胶囊5割裂现场真实复现
在 `AGY2_FundAdvisory/advisory_engine.py` 的 `generate_chief_advisor_memo` (第 4460~4833 行) 中：
1. **胶囊 4 (`portfolio_pathology`)** 能够正常检出持仓病灶：
   - 遍历 `holdings` 识别 `pl_ratio < -0.10` 的深套出血点（`deep_loss_list`）与持仓金额 < 200 元且免赎的碎片尾仓（`tail_fragments`）。
   - 提取 `sentry_rep` 中的预警哨信息。
2. **胶囊 5 (`action_directive`)** (第 4755~4776 行) 的逻辑如下：
   ```python
   c300_bias = float(snap.get("bias_20", 0.0))
   action_verdict = "维持底仓吃息"
   action_color = "var(--color-down)"
   if c300_bias > 5.0:
       action_verdict = "逢高适度止盈"
       action_color = "var(--color-up)"
       action_reason = "大盘短期超买正乖离偏高，尾盘严防脉冲追高，适合分批止盈高弹性波段仓位。"
   elif erp_pct > 75.0 and c300_bias < 0.0:
       action_verdict = "逆向定投吸筹"
       action_color = "var(--accent-primary)"
       action_reason = "大盘处于估值洼地与负乖离回踩共振带，建议在 14:30~14:50 执行原定投或逆向加仓。"
   else:
       action_verdict = "维持底仓吃息"
       action_color = "var(--color-down)"
       action_reason = "估值与均线处于平稳蓄势常态，全组合高股息纯债底仓稳健生息，无需频繁折腾。"
   ```
3. **真实实盘账本 `combat_29_funds` 现场实测输出**：
   运行命令：
   ```powershell
   py -3 -c "
   from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
   from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo
   mlm = MultiLedgerManager()
   pm = mlm.get_pm('combat_29_funds')
   memo = generate_chief_advisor_memo(holdings=pm.holdings)
   print('Pathology:', memo['portfolio_pathology'])
   print('Action Directive:', memo['action_directive'])
   "
   ```
   输出结果：
   - `Pathology`: `{'title': '🩺 存量持仓病灶', 'badge': '🩺 诊断排雷', 'deep_loss_count': 18, 'frag_count': 19, 'frag_amt': 442.7, 'content': '🔴 核心亏损拖累源：发现 18 只标的浮亏超 10%... 🧹 长尾碎片尾仓：检测到 19 只持仓金额小于 ¥200 的碎片/羊毛基 (合计沉淀资金 ¥442.70)...'}`
   - `Action Directive`: `{'title': '今日明确行动准则', 'badge': '⏱️ 14:30 决策: 维持底仓吃息', 'verdict': '维持底仓吃息', 'color': 'var(--color-down)', 'content': '定调结论：【维持底仓吃息】。14:30 尾盘决策依据：估值与均线处于平稳蓄势常态，全组合高股息纯债底仓稳健生息，无需频繁折腾。...'}`
   **法证结论**：胶囊 4 亮出 18 只深套出血点与 19 只碎片尾仓，胶囊 5 却在没有任何病灶感知的情况下，空谈大盘“全组合高股息纯债底仓稳健生息，无需频繁折腾”，二者左右互搏，完全割裂。

### 1.2 `app_gui.py` 首屏裁决面板渲染观察
在 `AGY2_FundAdvisory/app_gui.py` 中：
1. `render_chief_advisor_memo_card` (第 268~458 行)：
   - 第 288 行：`clean_ts = ts.split("｜")[0].replace("研判截面：", "").strip() if "｜" in ts else ts.replace("研判截面：", "").strip()`。当传入 `timestamp: None` 时抛出 `TypeError: argument of type 'NoneType' is not iterable`（导致对抗测试挂掉）。
   - 第 301 行：`usdcnh_v = float(m_intl.get("usdcnh_rate", 6.6676))` 仍残留 `6.6676` 假常数。
   - 第 306~315 行：
     ```python
     d_loss = int(m_path.get("deep_loss_count", 0))
     f_cnt = int(m_path.get("frag_count", 0))
     if d_loss > 0 or f_cnt > 0:
         path_capsule_sub = f"{d_loss}深套出血点 ｜ {f_cnt}碎片尾仓"
         path_badge = "🩺 诊断排雷"
     else:
         path_capsule_sub = "0深套 ｜ 结构优良"
         path_badge = m_path.get("badge", "🟢 健康良好")

     action_capsule_sub = f"{act_verdict} ｜ 未满7天禁卖"
     ```
   - 第 391 行（顶部裁决条）：直接展示 `🎯 今日裁决：【{act_verdict}】`。
   - 第 446~454 行（第 5 颗胶囊）：展示 `act_verdict` 与 `action_capsule_sub`。
   若 `act_verdict` 不联动病灶，顶部横幅与第五颗胶囊都将显示“维持底仓吃息”，用户一打开网页就会产生强烈的虚假安全感与指令矛盾感。

### 1.3 四大只读裁判文件与关键签名校验
通过 PowerShell `Get-FileHash` 核验四大只读裁判文件：
- `AGY2_FundAdvisory/judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF9DC227C0`
- `AGY2_FundAdvisory/holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670A880D41E`
- `AGY2_FundAdvisory/AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B8065B90772`
- `tests/test_infra.py`: `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` (14/14 tests PASSED)
- `AGY2_FundAdvisory/data_loader.py` 第 1436 行 `DataLoader.simulate_execution(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)` 签名与默认扣费参数完整，物理红线完好。

---

## 2. Logic Chain (推理逻辑链)

1. **病灶传递链 (Pathology Ingestion)**：
   - `generate_chief_advisor_memo` 既支持传入 `holdings`（由函数内部遍历测算 `deep_loss_count` 和 `frag_count`），也支持传入 `sentry_rep`（包含巡检 alerts）和 `portfolio_pathology` 显式字典。
   - 当 `is_weight_dict == False`（即存量持仓而非 Tab 1 拟建仓权重字典）且检测到 `frag_count > 0` 或 `deep_loss_count > 0` 或存在 `stop_profit_alerts` 时，账户存在明确处置需求。
2. **胶囊 4 与胶囊 5 优先级决策链 (Priority Resolution)**：
   - **最高优先级：尾仓清扫 + 深套置换** (`frag_count > 0 and deep_loss_count > 0`)：
     主结论 `action_verdict`: `f"清扫{frag_count}只尾仓·置换深套"` (如 "清扫19只尾仓·置换深套"，字符数 12，严格 <= 20)；
     副标题 `action_capsule_sub`: `f"清扫{frag_count}只尾仓 ｜ 置换{deep_loss_count}只深套"`；
     胶囊颜色 `action_color`: `var(--color-up, #ef4444)`；
     实战细则：优先执行 14:30 尾盘免赎清理尾仓归集资金，并将深套出血点转换为低费率指数联接或纯债底仓，再结合大盘中枢定投。
   - **次优先级 A：仅有尾仓需清扫** (`frag_count > 0 and deep_loss_count == 0`)：
     主结论 `action_verdict`: `f"清扫{frag_count}只尾仓"`；
     副标题 `action_capsule_sub`: `f"清扫{frag_count}只尾仓 ｜ 归集核心底仓"`；
     胶囊颜色 `action_color`: `var(--accent-primary, #3b82f6)`。
   - **次优先级 B：仅有深套需置换** (`deep_loss_count > 0 and frag_count == 0`)：
     主结论 `action_verdict`: `f"置换{deep_loss_count}只深套"`；
     副标题 `action_capsule_sub`: `f"置换{deep_loss_count}只深套 ｜ 止血控险"`；
     胶囊颜色 `action_color`: `var(--color-up, #ef4444)`。
   - **次优先级 C：红牌止盈/破位锁利** (`stop_profit_alerts` 存在)：
     主结论 `action_verdict`: `"右侧破位锁利"` 或 `"逢高阶梯止盈"`；
     副标题 `action_capsule_sub`: `"兑现高位浮盈 ｜ 锁定战果"`；
     胶囊颜色 `action_color`: `var(--color-up, #ef4444)`。
   - **底线默认：无病灶干净账本 / Tab 1 拟建仓** (`frag_count == 0 and deep_loss_count == 0 and not stop_profit_alerts`)：
     保留大盘 ERP 与 Bias20 驱动的宏观定调（"逆向定投吸筹" / "逢高适度止盈" / "维持底仓吃息"）；
     副标题：Tab 1 拟建仓展示 `f"{action_verdict} ｜ 按计划分批建仓"`，存量展示 `f"{action_verdict} ｜ 未满7天禁卖"`。
3. **前端首屏渲染闭环 (UI Consistency Invariant)**：
   - `render_chief_advisor_memo_card` 读取 `m_act.get("capsule_sub")` 或根据 `d_loss`、`f_cnt` 动态对齐副标题；
   - 顶部裁决条直显 `🎯 今日裁决：【{act_verdict}】`；
   - 胶囊 4 在拟建仓模式下渲染 `建仓标的分散 ｜ 结构优良`（使得 `test_g16_phase1_memo_and_combat29.py:219` 的 `assert "建仓标的" in call_arg` 100% 恢复绿灯）；
   - 拔除第 301 行 `6.6676` 默认值，防范 `ts: None` 导致的 `split` TypeError。

---

## 3. Caveats (注意事项与边界)

1. **Tab 1 拟建仓保护**：Tab 1 传入的 `holdings` 是权重字典（如 `{"005561": 0.35, "002351": 0.20, ...}`），`is_weight_dict` 判定为 True。此时绝不可报出“清扫尾仓”，必须判定为“结构均衡”，胶囊 5 保持按宏观定调建仓。
2. **持有天数悲观保护**：清扫尾仓必须遵循 $\ge 30$ 天（C 类）或 $\ge 365$ 天（A 类）免赎费红线，未满期者不计入 `frag_count`。
3. **既有测试兼容性调整**：
   - `tests/test_g15_phase2_memo_and_timemachine.py` 第 142 行：在 G15 旧版测试中，使用带 2 只尾仓与 1 只深套的模拟账本，却硬编码断言 `assert action["verdict"] == "逆向定投吸筹"`。这是 G15 世代尚未实装知行合一联动的旧断言，修改为知行合一后，应同步断言 `assert "清扫" in action["verdict"] or "置换" in action["verdict"]`，使其与 G19 规范对齐。
   - `tests/test_g16_phase1_memo_and_combat29.py` 第 219 行：断言 Tab 1 渲染卡片中包含 `"建仓标的"`。在 `app_gui.py` 补充 `path_capsule_sub = "建仓标的分散 ｜ 结构优良"` 即可通过。

---

## 4. Conclusion (结论与执行方案)

### 4.1 `AGY2_FundAdvisory/advisory_engine.py` 改造设计
在 `generate_chief_advisor_memo`：
1. 签名支持 `portfolio_pathology: Optional[Dict[str, Any]] = None`；
2. 若传入 `portfolio_pathology`，优先提取其中的 `deep_loss_count`、`frag_count`、`frag_amt`；
3. 提取 `sentry_rep` 中的 `stop_profit_alerts`（移动止盈/阶梯止盈/超买红牌）；
4. 当 `not is_weight_dict` 且存在持仓病灶时，胶囊 5 优先输出账户级实战指令；
5. 在 `action_directive` 字典中增加 `capsule_sub` 字段供卡片直显。

### 4.2 `AGY2_FundAdvisory/app_gui.py` 改造设计
在 `render_chief_advisor_memo_card`：
1. 防御 `timestamp: None`：`ts = memo_data.get("timestamp") or ""`；
2. 拔除第 301 行 `6.6676` 假常数，校准为 `7.2385`；
3. 补齐 `path_capsule_sub` 在建仓模式下的 `"建仓标的分散 ｜ 结构优良"`；
4. 胶囊 5 副标题与 `action_capsule_sub` 同步。

### 4.3 新建 `tests/test_g19_m1_ten_dimension_and_memo.py` 覆盖 Features 1-6
设计包含 6 个测试类、共计 22 项针对性测试用例，覆盖：
- Feature 1: 维度 6 真实产业估值 Top 3 均值与中位数定多空；
- Feature 2: 维度 7 资金情绪成交额、上涨家数比与 14 赛道拥挤度融合；
- Feature 3: 维度 10 期权隐波 option_iv_pct、期指贴水与避险；
- Feature 4: 黑天鹅/灰犀牛熔断门禁（ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60%）；
- Feature 5: 拔除 6.6676/5.0000 兜底常数与 [6.85, 7.60] 合理性校验哨；
- Feature 6: 胶囊 4 与胶囊 5 知行合一实战联动与首屏裁决条一致性。

---

## 5. Verification Method (验证方法与指令)

### 5.1 针对性测试验证指令
```powershell
py -3 -m pytest tests/test_g19_m1_ten_dimension_and_memo.py -v
```

### 5.2 胶囊联动与存量账本实测
```powershell
py -3 -c "
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo
mlm = MultiLedgerManager()
pm = mlm.get_pm('combat_29_funds')
memo = generate_chief_advisor_memo(holdings=pm.holdings)
act = memo['action_directive']
path = memo['portfolio_pathology']
print('Verdict:', act['verdict'])
print('Capsule Sub:', act.get('capsule_sub'))
assert '清扫' in act['verdict'] and '深套' in act['verdict']
print('SUCCESS: Unified coordination confirmed!')
"
```

### 5.3 既有测试回归验证
```powershell
py -3 -m pytest tests/test_infra.py tests/test_g17_advisory_real_data_and_ten_dimension.py tests/test_g16_phase1_memo_and_combat29.py -q
```

---

## 6. Proposed Implementation Details for Worker (具体代码落地方案)

### 方案 A: `AGY2_FundAdvisory/advisory_engine.py` 修改建议
在 `generate_chief_advisor_memo` 处：
```python
<<<<
def generate_chief_advisor_memo(
    snapshot: Optional[Dict[str, Any]] = None,
    holdings: Optional[Union[Dict[str, Any], List[Any]]] = None,
    radar_top3: Optional[List[Dict[str, Any]]] = None,
    sentry_rep: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
====
def generate_chief_advisor_memo(
    snapshot: Optional[Dict[str, Any]] = None,
    holdings: Optional[Union[Dict[str, Any], List[Any]]] = None,
    radar_top3: Optional[List[Dict[str, Any]]] = None,
    sentry_rep: Optional[Dict[str, Any]] = None,
    portfolio_pathology: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
>>>>
```

在 `advisory_engine.py` 第 4551 行与 4566 行拔除失真常数：
```python
<<<<
    usdcnh_rate = float(snap.get("spot_usdcnh") or snap.get("usdcnh_rate") or macro_multi.get("usdcnh_rate") or 6.6676)
...
    us_10y = float(snap.get("us_treasury_10y") or snap.get("us_10y_yield") or macro_multi.get("us_10y_yield") or macro_multi.get("us_treasury_10y", 5.0000))
====
    usdcnh_rate = float(snap.get("spot_usdcnh") or snap.get("usdcnh_rate") or macro_multi.get("usdcnh_rate") or 7.2385)
...
    us_10y = float(snap.get("us_treasury_10y") or snap.get("us_10y_yield") or macro_multi.get("us_10y_yield") or macro_multi.get("us_treasury_10y", 4.4200))
>>>>
```

在 `advisory_engine.py` 第 4755 行起重构胶囊 5 联动逻辑：
```python
    # ── 5. 今日明确行动准则 (14:30 尾盘知行合一实战联动) ─────────────
    c300_bias = float(snap.get("bias_20", 0.0))
    if c300_bias > 5.0:
        base_macro_verdict = "逢高适度止盈"
        base_macro_color = "var(--color-up)"
        base_macro_reason = "大盘短期超买正乖离偏高，尾盘严防脉冲追高，适合分批止盈高弹性波段仓位。"
    elif erp_pct > 75.0 and c300_bias < 0.0:
        base_macro_verdict = "逆向定投吸筹"
        base_macro_color = "var(--accent-primary)"
        base_macro_reason = "大盘处于估值洼地与负乖离回踩共振带，建议在 14:30~14:50 执行原定投或逆向加仓。"
    else:
        base_macro_verdict = "维持底仓吃息"
        base_macro_color = "var(--color-down)"
        base_macro_reason = "估值与均线处于平稳蓄势常态，全组合高股息纯债底仓稳健生息，无需频繁折腾。"

    # 提取预警哨中红牌止盈预警
    stop_profit_alerts = [
        a for a in alerts
        if a.get("action_type") == "take_profit"
        or a.get("dimension") in ("移动止盈", "超买拥挤", "阶梯止盈")
        or "止盈" in a.get("title", "")
        or "破位" in a.get("title", "")
    ]

    # 存量持仓病灶实战指令优先（知行合一消除互博）
    if not is_weight_dict and (frag_count > 0 or deep_loss_count > 0 or stop_profit_alerts):
        if frag_count > 0 and deep_loss_count > 0:
            action_verdict = f"清扫{frag_count}只尾仓·置换深套"
            action_capsule_sub = f"清扫{frag_count}只尾仓 ｜ 置换{deep_loss_count}只深套"
            action_color = "var(--color-up, #ef4444)"
            action_reason = (
                f"当前账本检出 <b>{frag_count}</b> 只免赎碎片尾仓（可回收现金 <b>¥{frag_amt:,.2f}</b>）与 <b>{deep_loss_count}</b> 只深套出血点，"
                f"14:30 尾盘优先输出账户级实战指令：一键免赎清扫尾仓归集底仓并置换深套出血点，消除资产拖累；大盘研判：{base_macro_reason}"
            )
        elif frag_count > 0:
            action_verdict = f"清扫{frag_count}只尾仓"
            action_capsule_sub = f"清扫{frag_count}只尾仓 ｜ 归集核心底仓"
            action_color = "var(--accent-primary, #3b82f6)"
            action_reason = (
                f"当前账本检出 <b>{frag_count}</b> 只免赎碎片尾仓（可回收现金 <b>¥{frag_amt:,.2f}</b>），"
                f"14:30 尾盘优先执行一键免赎清扫归集至核心底仓，净化持仓界面；大盘研判：{base_macro_reason}"
            )
        elif deep_loss_count > 0:
            action_verdict = f"置换{deep_loss_count}只深套"
            action_capsule_sub = f"置换{deep_loss_count}只深套 ｜ 止血控险"
            action_color = "var(--color-up, #ef4444)"
            action_reason = (
                f"当前账本检出 <b>{deep_loss_count}</b> 只深套出血点，"
                f"14:30 尾盘优先执行止血置换，转入低费率同赛道指数联接或纯债稳健底仓；大盘研判：{base_macro_reason}"
            )
        else:
            top_sp = stop_profit_alerts[0]
            action_verdict = "右侧破位锁利" if "破位" in top_sp.get("title", "") else "逢高阶梯止盈"
            action_capsule_sub = "兑现高位浮盈 ｜ 锁定战果"
            action_color = "var(--color-up, #ef4444)"
            action_reason = f"标的触发止盈预警（{top_sp.get('title', '')}），建议在 14:30 尾盘分批锁定高位浮盈；大盘研判：{base_macro_reason}"
    else:
        action_verdict = base_macro_verdict
        action_color = base_macro_color
        action_reason = base_macro_reason
        action_capsule_sub = f"{action_verdict} ｜ 按计划分批建仓" if is_weight_dict else f"{action_verdict} ｜ 未满7天禁卖"

    action_text = (
        f"<b>定调结论</b>：【<span style='color: {action_color}; font-size: 14px;'>{action_verdict}</span>】。<br>"
        f"<b>14:30 尾盘决策依据</b>：{action_reason}<br>"
        f"<b>纪律铁律</b>：持有未满 7 天份额严禁卖出（守死 1.5% 惩罚费红线）；C 类满 30 天择机转同标的 A 类节省长期服务费；红利类资产在磨底期务必设为【红利再投资】以份额滚雪球。"
    )
```

### 方案 B: `AGY2_FundAdvisory/app_gui.py` 修改建议
在 `render_chief_advisor_memo_card`:
```python
<<<<
    ts = memo_data.get("timestamp", "")
...
    clean_ts = ts.split("｜")[0].replace("研判截面：", "").strip() if "｜" in ts else ts.replace("研判截面：", "").strip()
...
    usdcnh_v = float(m_intl.get("usdcnh_rate", 6.6676))
====
    ts = memo_data.get("timestamp") or ""
...
    clean_ts = (ts.split("｜")[0].replace("研判截面：", "").strip() if "｜" in ts else ts.replace("研判截面：", "").strip()) if ts else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
...
    usdcnh_v = float(m_intl.get("usdcnh_rate", 7.2385))
>>>>
```
并补齐 `path_capsule_sub` 与 `action_capsule_sub`:
```python
    path_title = m_path.get("title", "")
    if "建仓" in path_title or "结构校验" in path_title:
        path_label = "📐 拟建仓组合结构校验"
        path_badge_title = "🟢 结构均衡"
        path_capsule_sub = "建仓标的分散 ｜ 结构优良"
    elif d_loss > 0 or f_cnt > 0:
        path_label = "🩺 存量持仓病灶"
        path_badge_title = "🩺 诊断排雷"
        path_capsule_sub = f"{d_loss}深套出血点 ｜ {f_cnt}碎片尾仓"
    else:
        path_label = "🩺 存量持仓病灶"
        path_badge_title = m_path.get("badge", "🟢 健康良好")
        path_capsule_sub = "0深套 ｜ 结构优良"

    action_capsule_sub = m_act.get("capsule_sub", "")
    if not action_capsule_sub:
        if d_loss > 0 and f_cnt > 0:
            action_capsule_sub = f"清扫{f_cnt}只尾仓 ｜ 置换{d_loss}只深套"
        elif f_cnt > 0:
            action_capsule_sub = f"清扫{f_cnt}只尾仓 ｜ 归集底仓"
        elif d_loss > 0:
            action_capsule_sub = f"置换{d_loss}只深套 ｜ 止血控险"
        elif "建仓" in path_title or "结构校验" in path_title:
            action_capsule_sub = f"{act_verdict} ｜ 按计划分批建仓"
        else:
            action_capsule_sub = f"{act_verdict} ｜ 未满7天禁卖"
```

### 方案 C: 全量新测试套件代码规划 (`tests/test_g19_m1_ten_dimension_and_memo.py`)
```python
# -*- coding: utf-8 -*-
"""
Milestone 1 (M1) Comprehensive Test Suite:
1. Feature 1: Dimension 6 产业估值真数据驱动 (14 赛道真实估值分位、Top3 均值与中位数定多空)
2. Feature 2: 维度 7 资金情绪多维融合 (成交额、上涨家数比与 14 赛道拥挤度融合)
3. Feature 3: 维度 10 期权衍生品与避险 (option_iv_pct、贴水与相关性突变)
4. Feature 4: 黑天鹅/灰犀牛一票否决熔断门禁 (ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60%)
5. Feature 5: 拔除 6.6676/5.0000 兜底常数与 [6.85, 7.60] 合理性校验哨
6. Feature 6: 胶囊 4（持仓病灶）与胶囊 5（今日行动准则）知行合一联动
"""
```
(完整代码结构见 report.md 与测试代码草案)
