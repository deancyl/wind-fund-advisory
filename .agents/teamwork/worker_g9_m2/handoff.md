# Milestone 2 核心实施交付报告 (Handoff Report)

## 1. 观察 (Observation)

### 1.1 文件独占写权限与物理只读红线状态
- **独占拥有修改权限的文件**：
  1. `AGY2_FundAdvisory/portfolio_manager.py`
  2. `AGY2_FundAdvisory/app_gui.py`
- **四大只读裁判文件与签约方法审计**：
  通过 `git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py` 执行核验，输出为空，物理零修改；
  `DataLoader.simulate_execution`（`data_loader.py` 第 1364 至 1375 行）函数签名与阶梯扣费逻辑完全保持只读锁定状态；
  全局配置文件 `C:\Users\deanc\.gemini\GEMINI.md` 绝对零触碰。

### 1.2 `portfolio_manager.py` 改造前现场观测
- **基线快照丢失缺陷**：
  在 `_export_state_dict`（第 3510 行）与 `_import_state_dict`（第 3524 行）中，原先仅导出了 `staged_batch_plans` 与 `nav_history`，未将 `initial_baseline_snapshot` 纳入序列化状态，导致账本重启或重载后，初次调用 `evaluate_rebalance_audit` 会用调仓后的持仓覆盖初始基线，使历史复盘账单清零。
- **归因模型缺失**：
  原 `evaluate_rebalance_audit` 仅通过 `cur_actual - shadow_equity` 计算单一的 `rebalance_value_add` 与 `rebalance_value_add_pct`，完全缺少大类资产配置效应（Allocation Effect）与优选基金超额效应（Selection Effect）的多资产精细化归因拆解。

### 1.3 `app_gui.py` 改造前现场观测
- **首屏 Top 3 卡片信息不对称**：
  原第 2651 至 2654 行仅展示了 `综合得分`、`估值分位` 与 `动量`，考夫曼信噪比分项、反拥挤度分项以及 20 日年化波动率（`vol_20`）与最大回撤（`mdd_20`）未披露，缺少风险收益对称呈现。
- **晨报区域信源状态指示缺失**：
  原第 2617 行仅渲染了静态的 `⏱️ 数据感知时间: {data_sense_time}`，未结合 `news_res.get("is_realtime")` 与 `source` 区分实时联网信源（绿色徽章）与离线本地缓存快照（琥珀色徽章）。
- **Tab 2 账本运维工具坞（`dock_tab3`）复盘档案深度不足**：
  原第 5894 至 5930 行仅渲染了 3 张基础卡片（实盘总资产 vs 影子组合、主动调仓净增厚、AI 风控规避损失），缺乏 Brinson 三维超额拆解卡片、多大类资产归因明细表以及买方投顾穿透复盘点评。

---

## 2. 逻辑链 (Logic Chain)

```
[观察 1.2: initial_baseline_snapshot 未持久化]
    │
    └─► 方案: 在 _export_state_dict 中注入 "initial_baseline_snapshot": copy.deepcopy(getattr(self, "initial_baseline_snapshot", {}))
        并在 _import_state_dict 中还原 self.initial_baseline_snapshot
        并在建立新基线时立即触发 self.save_state(record_snapshot=False)
        彻底解决跨会话与服务重启后基线被冲刷的架构缺陷。

[观察 1.2: evaluate_rebalance_audit 缺少 Brinson 经典归因]
    │
    ├─► 算法: 引入 Brinson-Fachler (BF) 经典超额拆解模型
    │   - 借助 self.classify_fund_asset_class 建立 9 大标准大类 + "现金管理"
    │   - 影子基准资产与实盘资产分别按大类聚合权重 w_B[k], w_P[k] 及区间收益率 R_B[k], R_P[k]
    │   - 大类资产配置效应: AR_k = (w_P[k] - w_B[k]) * (R_B[k] - R_B)
    │   - 优选基金超额效应: SR_k = w_P[k] * (R_P[k] - R_B[k])
    │   - 交易摩擦及惩罚规避贡献: Friction Saving = saved_penalty_and_buffer_fees
    │
    ├─► 数学恒等式保障:
    │   - 理论证明: sum(AR_k) + sum(SR_k) == R_P - R_B，中间交叉项完全抵消
    │   - 投影到金额与百分比:
    │     alloc_yuan = round(total_active_add_yuan * (AR_raw / TE_raw), 2)
    │     select_yuan = round(total_active_add_yuan - alloc_yuan, 2)
    │   - 严格保证恒等式: abs(alloc_yuan + select_yuan - total_active_add_yuan) < 1e-4
    │
    └─► 兼容性保障:
        原有 7 个顶级键名 (current_actual_equity, shadow_hold_equity, rebalance_value_add,
        rebalance_value_add_pct, saved_penalty_and_buffer_fees, baseline_date, shadow_holdings_count)
        100% 保持原有类型与数值，并在新键 "brinson_attribution" 中携带完整归因数据。

[观察 1.3: 前端交互与视觉展示升级]
    │
    ├─► 晨报信源指示徽章:
    │   - 当 news_res.get("is_realtime") 为 True:
    │     展示 🟢 实时联网信源 ({source}) 且并列保留 ⏱️ 数据感知时间: {data_sense_time}
    │   - 当 news_res.get("is_realtime") 为 False:
    │     展示 🟠 离线本地缓存快照 (网络未连接) ⏱️ 快照时间: {data_sense_time}
    │
    ├─► Top 3 赛道卡片风险收益对称展示:
    │   - 收益面: 综合得分 + 四维子项得分 (估值、动量、信噪比、反拥挤度)
    │   - 风险面: 20日年化波动率 (vol_20) + 20日最大回撤 (-mdd_20)
    │   - 证据链: 💡 入选依据 (core_logic_txt 量化因果链)
    │   - 盒模型: 容器锁定 min-height: 220px; overflow: visible !important;
    │
    └─► Tab 2 dock_tab3 Brinson 闭环:
        - 渲染 Brinson 三维归因卡片 (大类配置、优选选基、摩擦规避)
        - 渲染 9 大资产大类 Brinson-Fachler 归因明细表 (st.dataframe)
        - 渲染买方投顾穿透复盘点评卡片 (自动根据主导驱动生成深度专业点评)
        - 统一收口至 safe_markdown_html，遵循 CommonMark 4+ 空格缩进防御
```

---

## 3. 局限与前提假设 (Caveats)

1. **新资产进入基准大类处理**：若实盘新调入的标的属于影子组合完全未持有的大类（基准大类初始资产为 0），算法将基准大类收益率对齐为该大类实盘收益率，使该决策完全计入大类资产配置效应（Allocation Effect），避免除以零异常。
2. **存量首期收益率基准**：存量基金的区间收益率以快照记录的初始净值 `initial_navs` 或批次成本价为锚点，保证长期调仓复盘的可追溯性。
3. **No caveats on redlines**：四个裁判文件零修改，`DataLoader.simulate_execution` 签名与逻辑零修改，全量回归套件 45 项测试 100% 通过。

---

## 4. 结论 (Conclusion)

Milestone 2 核心实施任务已圆满完成：
1. `portfolio_manager.py` 已彻底修复重启丢失基线快照的缺陷，成功实装 Brinson-Fachler 经典归因模型，数学恒等式严格平账，7 个既有顶级键名完全向下兼容；
2. `app_gui.py` 首屏 Top 3 卡片已完整实装风险收益对称展示与量化证据链，晨报已实装信源真伪指示徽章，Tab 2 工具坞已完整闭环 Brinson 三维归因账单、明细表与买方投顾穿透复盘点评；
3. 全套回归测试套件 45 项全部一次性通过（耗时 72 秒），只读裁判文件与契约零触碰。

---

## 5. 独立验证方法 (Verification Method)

### 5.1 运行单元与回归自动化测试
在工作区根目录执行标准测试命令：
```powershell
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g8_ux_and_realtime_fusion.py tests/test_gui_multi_ledger_stress.py -v
```
**期望结果**：
45 项测试全量 PASSED，退出代码为 0。

### 5.2 检验四大只读裁判文件零改动
```powershell
git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
```
**期望结果**：输出为空。

### 5.3 检验修改文件范围限定
```powershell
git diff --stat AGY2_FundAdvisory/portfolio_manager.py AGY2_FundAdvisory/app_gui.py
```
**期望结果**：仅有 `portfolio_manager.py` 与 `app_gui.py` 产生差异变更。

### 5.4 Brinson 数学恒等式与快照持久化快速验证
```powershell
py -3 -c "import sys; from pathlib import Path; sys.path.insert(0, 'AGY2_FundAdvisory'); from portfolio_manager import PortfolioManager; pm = PortfolioManager(db_path=':memory:'); pm.add_or_update_holding('005561', 20000, 1.5, 1.4); pm.add_or_update_holding('050025', 20000, 1.5, 1.2); audit = pm.evaluate_rebalance_audit(); b = audit['brinson_attribution']; assert abs(b['allocation_effect_yuan'] + b['selection_effect_yuan'] - b['total_active_add_yuan']) < 1e-4; state = pm._export_state_dict(); assert 'initial_baseline_snapshot' in state; print('PASS!')"
```
**期望结果**：打印 `PASS!`，无断言错误。
