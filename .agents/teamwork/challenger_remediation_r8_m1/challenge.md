# Adversarial Challenge & Stress Report — Remediation R8-M1

## Challenge Summary

**Overall risk assessment**: **LOW** (Defects fully remediated; mathematical invariants and physical safety boundaries verified intact)
**Verdict**: **APPROVE**

Worker Remediation R8-M1 针对此前质询发现的 3 项核心缺陷进行了精确且完备的根因重构：
1. **中证红利 000922 尺度解耦与基准保护（Rule 16）**：通过将全收益矩阵与现货价格/基期点位严格解耦，000922 离线点位稳定在 `5518.95`，双重断言防线彻底杜绝了 `12189.99`（全收益）与 `3248.31`（上证红利）的污染；
2. **ETF 涨跌额量纲对齐**：在回退注入相对涨跌幅时，强制使用目标标的真实单价进行比例测算（`chg = round(pt * chg_pct / 100, 3)`），彻底消除了将现货黄金 `+40.33` 元涨跌额塞入单价仅 `8.43` 元 ETF 的量纲错配；
3. **微小收益率精度保持与 0 假平盘**：通过微小变动保留 3~4 位有效精度（如 `0.002%`），消除截断误差，全市场 40 项走廊标的在离线与周末模拟下实现 100% 真实变动呈现，0 行假平盘。

---

## Challenges & Remediation Status

### [Resolved / Closed] Challenge 1: CSI Dividend 000922 Point Scale Decoupling (Rule 16 Invariant)
- **Assumption challenged**: 原代码假设可以直接将 `aligned_matrix_total_return.parquet` 中 `H00922` 的最新数值作为 000922 指数点位返回。
- **Attack scenario**: 该矩阵记录的是累积全收益序列（当前值约 12189.99 点），而非价格指数点位。直接返回导致点位膨胀超过 2 倍，且与 Rule 16 规定的 `[5000.0, 6500.0]` 严重背离。
- **Remediation verified**:
  - 全收益矩阵被约束为**仅用于提取相对百分比涨跌幅** `off_pct`；
  - 点位严格锚定至内置目录 `fb_point`（5518.95），并在末端设置 `5000.0 <= pt <= 6500.0` 强力断言，遇异常自动重置并重算涨跌额；
  - 经验测试实测 000922 离线点位为 `5518.95`，敌意网络注入测试（模拟服务端返回 3300.0 点）成功被守护拦截重置为 `5518.95`。
- **Status**: **FULLY RESOLVED**.

### [Resolved / Closed] Challenge 2: ETF Daily Change Amount Dimensional Mismatch
- **Assumption challenged**: 原代码在周末或网络平盘降级时，直接将离线计算的绝对涨跌额 `off_chg` 赋值给实时标的 `chg`。
- **Attack scenario**: 518880 黄金 ETF 对应底层现货数据为 `AU9999`（价格 ~1465 元），单日涨跌额达 `+40.33` 元。而 518880 ETF 真实单价仅 ~8.43 元。直接透传 `off_chg` 导致单日涨跌额高达单价的近 5 倍。
- **Remediation verified**:
  - 重构后严格遵循数学量纲比例：`chg = round(pt * (off_pct / 100.0), 3 if (is_etf or pt < 100.0) else 2)`；
  - 针对 518880 实测：现价 8.434 元对应涨跌额为 `+0.239` 元（涨跌幅 `+2.83%`），完全自洽；
  - 对目录中全部 29 只 ETF / 跨境 QDII / 大宗商品基金进行遍历检验，比例失真率严格为 0。
- **Status**: **FULLY RESOLVED**.

### [Resolved / Closed] Challenge 3: Precision Truncation & Flat 0.00% Micro-return Defect
- **Assumption challenged**: 原代码在离线格式化收益率时无差别使用 `round(val, 2)`。
- **Attack scenario**: 短融 ETF（511360）等超低波固收标的单日真实涨跌幅仅 `0.002%`，被无差别舍入为 `0.00%`，导致离线走廊出现假平盘。
- **Remediation verified**:
  - 实装 `_format_offline_return_pct`，对微小变动保留 3~4 位有效精度；
  - 离线全量 40 只标的遍历检验：0.00% 假平盘标的数量为 0，511360 真实呈现 `0.002%`。
- **Status**: **FULLY RESOLVED**.

---

## Stress Test Results

| # | 质询/压力测试场景 | 预期行为 | 实测结果 | 判定 |
|---|------------------|---------|---------|------|
| 1 | `verify_referee_hashes.py` 裁判哈希审计 | 4 大裁判文件 SHA256 100% 匹配 | 4/4 PASS，哈希无变动 | **PASS** |
| 2 | `test_challenger_r8_m1_2_stress.py` 对抗压力套件 | 15 项对抗性用例全部通过 | 15/15 PASS (12.64s) | **PASS** |
| 3 | `test_challenger_r8_m1_empirical.py` 经验对抗套件 | 119 项经验断言全部通过 | 119/119 PASS (7.0s) | **PASS** |
| 4 | `test_sidebar_remodel_and_bugfixes.py` 既有回归套件 | 6 项回归与 AppTest 全部通过 | 6/6 PASS (10.06s) | **PASS** |
| 5 | `000922` 离线点位基线校验 | 点位严格处于 [5000.0, 6500.0] | 实测 `5518.95`，完全合规 | **PASS** |
| 6 | `000922` 敌意异常点位注入（如 3300.0） | 触发强力熔断回退至基线 | 实测熔断回退至 `5518.95` | **PASS** |
| 7 | `518880` 黄金 ETF 涨跌额比例自洽 | `chg ≈ pt * chg_pct / 100`，彻底杜绝 +40.33 元 | 实测 pt=8.434, chg=+0.239, pct=+2.83% | **PASS** |
| 8 | 全目录 29 只 ETF 量纲对齐穷举遍历 | 遍历全部 ETF，无任何量纲溢出 | 29/29 比例误差均 < 0.005 | **PASS** |
| 9 | 全量 40 只标的离线断网回退 | 零假平盘行 (zero flat 0.00% count = 0) | 实测 0 只平盘，短融保留 0.002% | **PASS** |
| 10 | 极限输入鲁棒性 (latest_pt=0.0 / None) | 不抛 ZeroDivisionError，平滑回退最新收盘价 | 实测 MA20 均平滑计算，Bias20 处于安全界内 | **PASS** |

---

## Unchallenged Areas

- **Milestone 2 机会雷达与主动风险预警哨业务逻辑**：按项目计划（`PROJECT.md`）属于后续 Milestone 2 交付范畴，不在本次 Milestone 1 缺陷修复审计范围内。
- **Milestone 3 7 大机构定权模型算子求解**：按计划属于 Milestone 3 范畴，本次不做过度挑战。
