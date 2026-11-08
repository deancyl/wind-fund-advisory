# Milestone 2 前端实施与实测审查报告 (Reviewer Handoff Report)

## 1. 观察 (Observation)

### 1.1 四大只读裁判文件与签约方法审计
- 执行命令：
  ```powershell
  git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
  ```
  输出结果为空，物理零修改。
- 执行命令：
  ```powershell
  git diff AGY2_FundAdvisory/data_loader.py | Select-String -Pattern "simulate_execution"
  ```
  输出结果为空，`DataLoader.simulate_execution` 函数签名与阶梯计提扣费逻辑完全保持只读锁定状态。

### 1.2 晨报信源指示徽章与时间戳真实性观测
- 源码位置：`AGY2_FundAdvisory/app_gui.py` 第 2581 至 2595 行及第 2633 至 2637 行：
  ```python
  is_realtime_news = bool(news_res.get("is_realtime", False))
  news_src_label = str(news_res.get("source", "东方财富 7x24快讯" if is_realtime_news else "离线快照"))
  if is_realtime_news:
      news_source_badge = (
          f'<span style="font-size: 10px; font-weight: 600; color: var(--color-down); '
          f'padding: 1px 6px; border-radius: 4px; background: rgba(34, 197, 94, 0.1); '
          f'border: 1px solid rgba(34, 197, 94, 0.25);">🟢 实时联网信源 ({news_src_label})</span>'
      )
  else:
      news_source_badge = (
          f'<span style="font-size: 10px; font-weight: 600; color: var(--accent-primary); '
          f'padding: 1px 6px; border-radius: 4px; background: rgba(245, 158, 11, 0.1); '
          f'border: 1px solid rgba(245, 158, 11, 0.25);">🟠 离线本地缓存快照 (网络未连接) ⏱️ 快照时间: {data_sense_time}</span>'
      )
  ```
  在首屏晨报标题右侧容器中，并列保留：
  ```html
  <div style="display: flex; gap: 8px; align-items: center;">
      {news_source_badge}
      <span style="font-size: 10px; color: var(--text-secondary);">⏱️ 数据感知时间: {data_sense_time}</span>
      <span style="font-size: 10px; color: var(--text-secondary);">全景量化串联 ｜ 历史拐点并列对照</span>
  </div>
  ```
- 底层数据源防伪锚定：在 `AGY2_FundAdvisory/data_loader.py` 第 400 至 406 行，当网络请求失败回退到磁盘缓存快照时，严格读取快照中的原始 `updated_at` / `timestamp` 或文件系统真实 `mtime`，兜底预置快照明确标注 `"2026-11-01 09:30:00 (离线预置)"`，杜绝使用 `datetime.now()` 冒充实时时间。

### 1.3 首屏 Top 3 机会赛道卡片风险收益对称展示观测
- 源码位置：`AGY2_FundAdvisory/app_gui.py` 第 2658 至 2690 行：
  - 四维子项得分完整解析与披露：
    ```python
    val_score = float(sub_s.get("valuation", sec.get("s_val", 0.0)))
    mom_score = float(sub_s.get("momentum", sec.get("s_mom", 0.0)))
    snr_score = float(sub_s.get("kaufman_snr", sec.get("s_er", 0.0)))
    crowd_score = float(sub_s.get("anti_crowding", sec.get("s_crowd", 0.0)))
    vol_20_val = float(sec.get("vol_20", 15.0))
    mdd_20_val = float(sec.get("mdd_20", 8.0))
    ```
  - 容器盒模型硬约束：
    `<div class="decision-card" style="padding: 10px 12px; height: 100%; min-height: 220px; overflow: visible !important; border-top: 2px solid {tag_color};">` 严格锁定 `min-height: 220px; overflow: visible !important;`。
  - 风险收益对称展示：
    第 2676 行呈现：`综合得分: {sec['total_score']} ｜ 估值:{val_score:.0f} 动量:{mom_score:.0f} 信噪:{snr_score:.0f} 拥挤:{crowd_score:.0f}`
    第 2679 行呈现：`🛡️ 风险指标: 20日波动 {vol_20_val:.1f}% ｜ 20日最大回撤 -{mdd_20_val:.1f}%`
    第 2682 行呈现：`💡 入选依据：{core_logic_txt}`（动态量化因果链）。

### 1.4 Tab 2 账本运维工具坞（`dock_tab3`）Brinson 归因全闭环观测
- 源码位置：`AGY2_FundAdvisory/app_gui.py` 第 5959 至 6052 行：
  1. **Brinson-Fachler 经典三维归因卡片**：
     - `col_b1`：`🏛️ 大类资产配置效应 (Allocation)`，披露 `alloc_yuan` 与 `alloc_pct`；
     - `col_b2`：`🎯 优选基金超额效应 (Selection)`，披露 `select_yuan` 与 `select_pct`；
     - `col_b3`：`🛡️ 交易摩擦及惩罚规避 (Friction)`，披露 `fric_yuan` 与 `fric_pct`（精准统计 `<7天` 1.50% 惩罚费与 C 类临期赎回费）。
  2. **9 大资产大类归因明细表**：
     调用 `st.dataframe(df_breakdown, use_container_width=True, hide_index=True)`，完整呈现资产大类、实盘权重、基准权重、权重偏离、实盘收益、基准收益、配置效应(元)、选基效应(元)、合计增厚(元)。
  3. **买方投顾穿透复盘点评**：
     基于 `primary_driver = brinson_attr.get("primary_driver", "大类资产配置效应")`，自适应区分超额正增厚与踩雷负偏离双分支，动态输出包含具体金额、主导归因因子与风控拦截金额的买方投顾穿透复盘文案。
  4. **HTML 纯化与 CommonMark 4+ 空格缩进防御**：
     所有卡片 HTML 统一收口至 `safe_markdown_html`，内部通过 `_clean_html` 强制过滤空行并执行 `line.strip()`，从语法根源彻底消除 CommonMark 代码块误判与 HTML 标签外泄风险。

### 1.5 自动化测试与对抗性边界实测
1. **指定自动化测试套件执行**：
   ```powershell
   py -3 -m pytest tests/test_infra.py tests/test_g8_ux_and_realtime_fusion.py tests/test_gui_multi_ledger_stress.py -v
   ```
   **实测输出**：`31 passed, 62 warnings in 55.41s`，退出码 0，100% 通过。
2. **专项回归套件回归测试**：
   ```powershell
   py -3 -m pytest tests/test_adv_final_closure.py -v
   ```
   **实测输出**：`14 passed, 59 warnings in 28.34s`，退出码 0，100% 通过。
3. **对抗性边界实测**：
   - 零资产/空持仓：Brinson 归因平账，无除以零异常；
   - 复杂跨大类调仓：`abs(alloc_yuan + select_yuan - total_active_add_yuan) < 1e-4` 恒等式严格平账；
   - 极端负超额踩雷情景：算法自适应降级，点评自适应切换至风险防御提示；
   - 跨会话/重启基线持久化：`_export_state_dict` 与 `_import_state_dict` 能够 100% 留存并还原 `initial_baseline_snapshot`，不被新持仓覆盖。

---

## 2. 逻辑链 (Logic Chain)

```
[观察 1.1: 裁判文件与 DataLoader.simulate_execution 零修改]
    │
    └─► 证明 Worker 严格恪守只读红线，无作弊越权行为。

[观察 1.2: 晨报徽章依据 is_realtime_news 区分绿色与琥珀色，并列数据感知时间，离线使用快照时间]
    │
    └─► 证明信源验真与真数据防幻觉要求 100% 达成，彻底杜绝离线伪造当前时间。

[观察 1.3: Top 3 卡片完整披露四维子项、vol_20、mdd_20、动态证据链与 220px 容器硬约束]
    │
    └─► 证明风险与收益对称呈现，避免信息截断，完全满足 UX 几何不变量与决策要求。

[观察 1.4: dock_tab3 完整实装 Brinson 三维卡片、9大类明细表、自适应复盘点评并收口 safe_markdown_html]
    │
    └─► 证明复盘归因具备专业买方投顾深度，CommonMark 语法防御闭环。

[观察 1.5: 自动化回归套件 45 项全部 PASSED，对抗性边界全量闭环]
    │
    └─► 证明系统稳定性强，零回归缺陷，代码已就绪推进至 Milestone 3。
```

---

## 3. 局限与前提假设 (Caveats)

- **No caveats**：四大裁判文件零修改，生产代码无硬编码欺诈，所有指定测试项与对抗性压力验证均 100% 通过。

---

## 4. 结论与裁决 (Conclusion & Verdict)

**审查裁决**：**APPROVE**

Milestone 2 中 `AGY2_FundAdvisory/app_gui.py` 与 `portfolio_manager.py` 的前端呈现与后端归因逻辑实现完整、严谨、真实，严格遵循量化因果律、CommonMark 安全渲染与物理红线底线。

---

## 5. 独立验证方法 (Verification Method)

独立复核人员可通过以下步骤复现审查结果：

1. **裁判文件与契约零修改复核**：
   ```powershell
   git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
   ```
2. **核心测试套件回归验证**：
   ```powershell
   py -3 -m pytest tests/test_infra.py tests/test_g8_ux_and_realtime_fusion.py tests/test_gui_multi_ledger_stress.py -v
   ```
3. **Brinson 数学恒等式与持久化极速校验**：
   ```powershell
   py -3 -c "import sys; sys.path.insert(0, 'AGY2_FundAdvisory'); from portfolio_manager import PortfolioManager; pm = PortfolioManager(db_path=':memory:'); pm.add_or_update_holding('005561', 20000, 1.5, 1.4); pm.add_or_update_holding('050025', 20000, 1.5, 1.2); audit = pm.evaluate_rebalance_audit(); b = audit['brinson_attribution']; assert abs(b['allocation_effect_yuan'] + b['selection_effect_yuan'] - b['total_active_add_yuan']) < 1e-4; state = pm._export_state_dict(); assert 'initial_baseline_snapshot' in state; print('PASS!')"
   ```
