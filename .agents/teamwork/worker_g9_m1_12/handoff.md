# Milestone 1 (M1) 工序交付报告：底层量化因果律与数据真实性严苛纠偏

- **交付代理**: `worker_g9_m1_12` (Role: Quant Implementation Worker)
- **完成时间**: 2026-11-08T06:18:00Z
- **目标路径**: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12\handoff.md`

---

## 1. Observation (客观事实与直接代码证据)

### 1.1 缺陷定位与修复
在初始状态下执行对抗测试套件：
```powershell
py -3 -m pytest tests/test_challenger_g9_m2_adversarial.py
```
**报错截获**:
```text
FAILED tests/test_challenger_g9_m2_adversarial.py::TestFrictionAndFeeSavingsAdversarial::test_friction_saving_7day_and_class_c_penalties
E AttributeError: property 'holding_days' of 'FundHolding' object has no setter
tests\test_challenger_g9_m2_adversarial.py:517: AttributeError
```

**根因定位**:
在 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 295-300 行：
```python
    @property
    def holding_days(self) -> int:
        """悲观最短持有天数 (FIFO 惩罚锁防线)"""
        if getattr(self, "batches", None):
            return min((b.holding_days for b in self.batches), default=30)
        return 30
```
该类只声明了只读属性 `@property def holding_days(self)`，缺少 `@holding_days.setter`，导致直接赋值 `h.holding_days = 15` 时抛出 `AttributeError`。

**代码修改实施**:
在 `AGY2_FundAdvisory/portfolio_manager.py` 第 302-321 行添加批次感知的 `@holding_days.setter`：
```python
    @holding_days.setter
    def holding_days(self, val: int):
        val = int(val)
        if getattr(self, "batches", None):
            for b in self.batches:
                b.holding_days = val
                b.safety_lock = (val < 7)
        else:
            self.batches = [
                HoldingBatch(
                    batch_id=f"B_{self.fund_code}_001",
                    buy_date="",
                    shares=self.shares,
                    cost_nav=self.cost_price,
                    holding_days=val,
                    safety_lock=(val < 7)
                )
            ]
```
修复后再次运行 `tests/test_challenger_g9_m2_adversarial.py`：
`14 passed in 3.15s` (100% 通过)。

---

### 1.2 R3 核心量化因果律各要点直接观测与核验

1. **滞后一期因果律对齐与双边换手摩擦扣除**:
   - 文件: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (第 469-534 行)
   - 观测: `P_eff = P[:-1, :, :]` 作用于 `R_eff = R[1:, :]`，严格阻断同日未来函数；`friction_cost = 0.0020 * daily_to`，从毛收益率 `gross_R_p` 中真实扣除双边 20 bps (单边 10 bps) 换手摩擦得到 `net_R_p`，累乘净值 `nav = np.cumprod(1.0 + net_R_p, axis=0)`。
   - 年化无风险利率扣减: 严格从日均净收益中减去 `rf_daily = 0.02 / 250.0`，计算年化夏普比率 `((mean_r - rf_daily) / std_r) * np.sqrt(250.0)`。
   - 自动化测试: `test_causal_evaluator_lag1_alignment`、`test_turnover_friction_deduction`、`test_sharpe_ratio_rf_deduction` 全部绿灯。

2. **样本外推进式滚动演化 (Walk-Forward Rolling Trajectory)**:
   - 文件: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (第 633-765 行)
   - 观测: 全文零 `lam = (t + 1) / 60.0` 线性插值。实装 12 个切片（每切片 5 个交易日，共 60 个交易日样本外演化），每个切片严格使用 cutoff 日期之前的历史数据训练求解，样本外逐日基于当日历史特征决策。二阶差分 `diff2_val != 0`，证实为真实非线性演化。
   - 自动化测试: `test_walk_forward_rolling_trajectory_genuine` 绿灯。

3. **跨市场 A 股交易日历对齐与清除假序列**:
   - 文件: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (第 272-385 行)
   - 观测: 以 `H00300` 交易日历为基准索引 `target_dates = base_dates[-window_days:]`，所有赛道执行 `reindex(target_dates).ffill().bfill()`。缺失数据置 `np.ones`（收益率严格为 0，经扣除 2% 无风险利率后夏普为负自然淘汰），彻底根除 `np.linspace` 伪造序列。长周期估值分位结合 5 年估值缓存与 120 天长周期中枢去趋势测算。

4. **主动风控 ActiveRiskSentry 穿透与适当性**:
   - 文件: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (第 1759-1831, 1926-1984 行)
   - 观测: 规模反查执行“传入参数 -> DataLoader.get_fund_metadata -> 核心策略池/扩展目录”三级穿透，彻底移除 `else: aum = 2.5`。无规模时返回 `PENDING_VERIFICATION`（黄色预警），规模 $<0.5$ 亿返回 `LIQUIDATION_DANGER`（红色预警）。
   - 投资者适当性: C1-C5 风险上限（20%, 40%, 78%, 85%, 95%）巡检，超配 $\ge 15\%$ 或 C1 持有高波资产确定性触发 `red` 级强预警，输出超配金额与降波动作。

5. **末端 K 线全量重算与动态量化依据**:
   - 文件: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (第 1136-1185, 1236-1268 行)
   - 观测: 废除算术相加，将盘中实时价格更新至 `s_rt[-1]`，全量重算 MA20、Bias20、Slope20、ER20、Vol20、MDD20。静态方法 `_synthesize_quantitative_evidence` 基于真实四维得分（估值、动量、信噪比、反拥挤）输出 100% 自洽的文案。

6. **Brinson 3D 归因严格数学恒等式平账**:
   - 文件: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` (第 6681-6920 行)
   - 观测: 初始快照基线跨会话持久化。大类资产配置效应、选基超额效应与交易摩擦及惩罚费规避（$<7$ 天 1.50% 与 C 类 7~29 天 0.50%）严格平账：`assert abs(alloc_yuan + select_yuan - total_active_add_yuan) < 1e-4`。

---

### 1.3 四大只读裁判文件与 DataLoader.simulate_execution 100% 零修改确认
运行裁判文件哈希与签名核验：
```powershell
py -3 scratch/check_referee_hashes.py
```
**核验结果**:
- `AGY2_FundAdvisory\judge_engine.py`: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be` (未变动)
- `AGY2_FundAdvisory\holdout_vault.py`: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a` (未变动)
- `AGY2_FundAdvisory\AGENT_SPEC.md`: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957` (未变动)
- `tests\test_infra.py`: `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100` (未变动)
- `AGY2_FundAdvisory\data_loader.py`: `simulate_execution` 默认入参签名 `(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)` 与 1.50% 阶梯扣除逻辑完全保持只读。

---

## 2. Logic Chain (推理链条)

1. **观察 1.1**: `test_friction_saving_7day_and_class_c_penalties` 在为持有期赋值 `h2.holding_days = 15` 时因缺失 setter 导致 `AttributeError`。
2. **推导**: 在 `FundHolding` 中实现 `@holding_days.setter`，当存在 `batches` 时逐一更新各批次的 `holding_days` 与 `safety_lock = (val < 7)`；当不存在时生成初始批次。此修改遵循面向对象封装，完全向下兼容，并使 FIFO 悲观最短持有天数属性计算保持严格一致。
3. **观察 1.2**: 基因演化模型中 $P[:-1]$ 对应 $R[1:]$，双边换手摩擦在净值生成中真实扣除，无风险利率 2.0% 在夏普比率中强制扣减；12 切片 Walk-Forward 非线性推进；交易日历严格对齐，清零 `np.linspace` 与 2.5 亿规模兜底；适当性检测与 Brinson 三维归因平账。
4. **推导**: 所有 R3 契约要求在底层量化模型与风控代码中均已确切落地，并由专属自动化测试严格覆盖。
5. **推导结论**: 经此修复，量化因果律缺陷全部闭环，所有目标测试与压力测试 100% 绿灯。

---

## 3. Caveats (局限性与注意事项)

1. **在线接口网络回退**: 盘中快讯与基金元数据反查在外网接口不可用时会自动使用本地缓存快照，回退路径下严格遵循不伪造时间戳与规模原则。
2. **专属写权限遵守**: 本工序严格遵守排他性写入约定，未修改 `AGY2_FundAdvisory/app_gui.py`（留待 M2 代理操作），`data_loader.py` 与四大裁判文件 100% 只读。

---

## 4. Conclusion (工序结论)

Milestone 1 (M1) “底层量化因果律与数据真实性严苛纠偏”所有目标要求已 100% 高质量达成：
- `FundHolding.holding_days` setter 成功实装并支持批次联动与安全观察锁联动；
- R3 六大金融量化因果律（防未来函数、双边换手摩擦、扣除无风险利率、样本外 Walk-Forward、A 股日历对齐、清除假序列与假规模、C1-C5 适当性预警、Brinson 三维归因）全部验证闭环；
- 四大只读裁判文件与 `DataLoader.simulate_execution` 保持 100% 原始只读状态；
- 所有 38 项目标测试用例全量绿灯通过。

---

## 5. Verification Method (验证方法与复现指令)

任何审计员或下游工序均可通过以下命令直接独立复现全部验证结果：

1. **裁判文件哈希只读核验**:
   ```powershell
   py -3 scratch/check_referee_hashes.py
   ```
   预期输出: 4 个裁判文件的 SHA256 与基线完全一致。

2. **M1 目标因果律、Brinson 归因、对抗测试与挑战者测试**:
   ```powershell
   py -3 -m pytest tests/test_g9_causal_brinson_and_suitability.py tests/test_causality_adversarial_m1.py tests/test_challenger_g9_m1_adversarial.py tests/test_challenger_g9_m2_adversarial.py
   ```
   实际执行结果: `38 passed in 6.19s` (100% 通过)。

3. **合规审计与压力测试集成核验**:
   ```powershell
   py -3 -m pytest tests/test_challenger_g9_m2_stress.py tests/test_auditor_g9_m2_integrity.py
   ```
   实际执行结果: `20 passed in 17.65s` (100% 通过)。
