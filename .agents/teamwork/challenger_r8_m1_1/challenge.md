# Adversarial Challenge Report — Milestone 1 (Challenger R8-M1-1)

**Target**: Milestone 1 (侧边栏核心指数走廊升级、全市场自由定制与 UI 细节修复)  
**Author**: Challenger R8-M1-1 (critic, specialist)  
**Date**: 2026-11-05T02:22:00Z  
**Verdict**: **REQUEST_CHANGES**  

---

## Challenge Summary

**Overall risk assessment**: **CRITICAL**

通过编写并执行经验对抗性测试套件 `scripts/test_challenger_r8_m1_empirical.py`，模拟断网、东财/新浪超时以及非交易时段 0.00% 假平盘全场景注入，发现 **2 项 Critical 缺陷** 与 **1 项 High 缺陷**：
1. **Critical 缺陷 1**：离线点位尺度严重失真（全收益点位污染价格指数与低单价 ETF），导致中证红利离线点位篡改为 12,189.99 点，直接击穿 `GEMINI.md` Rule 16 物理红线；黄金 ETF 现价 8.45 元被篡改为 1,465.02 元（173 倍失真）；标普 500 ETF 现价 2.656 元被篡改为 7,812.21 元（2941 倍失真）。
2. **Critical 缺陷 2**：周末假平盘回退时，涨跌额（`change`）直接取全收益指数的点位差值（`off_chg`），导致黄金 ETF（现价 8.45 元）出现“涨跌额 +40.33 元、涨跌幅 +2.83%”的荒谬数学矛盾（单日涨跌额是股票单价的 4.8 倍）。
3. **High 缺陷 3**：短融/货币 ETF（如 511360）因 `round(chg_pct, 2)` 过度舍入将 `0.002%` 截断为 `0.0%`，导致离线回退失效，依然残留 `0.00%` 假平盘。

---

## Challenges

### [Critical] Challenge 1: 离线回退点位尺度严重失真 (全收益点位污染价格指数与ETF) 触发 Rule 16 违规

- **Assumption challenged**: 假设 `aligned_matrix_total_return.parquet` 中提取的 `p_curr` 可以直接充当价格指数（Price Index）或场内 ETF 的离线现价 `off_pt`。
- **Attack scenario**:
  模拟东财/新浪断网故障或未获取到最新盘中点位（`pt <= 0.0`）：
  `fetch_custom_realtime_indices` 触发 `offline_calc = calc_offline_2day_return(c)`。
  在 `calc_offline_2day_return` 中，优先从 `aligned_matrix_total_return.parquet` 提取 `matrix_cols`。
  但该矩阵存放的是**全收益指数（Total Return Index）**或现货指数：
  - `000922`（中证红利）映射至 `H00922`（全收益），最新点位为 `12189.99`（真实价格指数仅为 `5518.95`）；
  - `518880`（黄金ETF）映射至 `AU9999`，最新点位为 `1465.02`（真实 ETF 单价仅为 `8.434` 元）；
  - `513500`（标普500ETF）映射至 `SPX_CNY`，最新点位为 `7812.21`（真实 ETF 单价仅为 `2.656` 元）；
  - `000300`（沪深300）映射至 `H00300`，最新点位为 `6175.66`（真实价格指数为 `4118.94`）；
  - `511260`（十年国债ETF）映射至 `H11009`，最新点位为 `251.25`（真实 ETF 单价为 `135.809` 元）。
  
  系统直接执行 `if pt <= 0.0: pt = off_pt`，随后将该点位传入 `get_index_corridor_metrics`。
  导致：
  1. 中证红利点位在离线时展示为 `12,189.99` 点，**直接违反 `GEMINI.md` Rule 16**（“点位合理性范围核验：数据抓取与大屏渲染必须配备点位基线校验，如中证红利必须处于 5000 ~ 6500 点区间，杜绝向用户展示失真点位”）；
  2. 黄金 ETF 卡片展示现价 `1,465.02` 元，MA20 展示为 `1,440.1` 元；标普 500 ETF 展示现价 `7,812.21` 元。
- **Blast radius**: 极度危险。用户在离线或弱网冷启动时，看到持仓基准 ETF 单价被放大上千倍、中证红利暴涨 120% 翻倍，完全击毁系统量化基线。
- **Mitigation**:
  1. 在 `calc_offline_2day_return` 中明确分离“点位基线”与“变动百分比”：若代码在 `EXPANDED_INDEX_CATALOG` 中，点位基线应锁定 `item_meta.get("fb_point")`，全收益矩阵仅用于计算两交易日真实变动百分比 `off_pct`；
  2. 或在 `fetch_custom_realtime_indices` 中：当 `pt <= 0.0` 时，点位优先取 `item_meta.get("fb_point", 1000.0)`，涨跌额按 `chg = round(pt * (off_pct / 100.0), 3 if pt < 100 else 2)` 计算，严禁直接把全收益指数绝对值赋给 ETF。

---

### [Critical] Challenge 2: 周末假平盘回退时涨跌额 (change) 与点位尺度脱钩数学矛盾

- **Assumption challenged**: 假设 `calc_offline_2day_return` 返回的 `off_chg` 可以直接赋值给 `chg`。
- **Attack scenario**:
  周末、节假日休市或盘后，东财/新浪接口正常返回盘中点位（例如 518880 现价 `8.45` 元，513500 现价 `2.656` 元，000922 现价 `5511.17` 点），但由于休市，接口返回 `change_pct = 0.00`。
  `fetch_custom_realtime_indices` 触发修复逻辑（lines 1668-1670）：
  ```python
  if abs(chg_pct) < 1e-6 and abs(off_pct) > 1e-6:
      chg = off_chg
      chg_pct = off_pct
  ```
  此时 `off_chg` 是在全收益矩阵（点位 1465 或 7812）上算出的点位绝对变化：
  - 对 518880（黄金ETF）：`off_chg = 40.33`，`off_pct = +2.83%`；
  - 对 513500（标普500ETF）：`off_chg = 115.75`，`off_pct = +1.50%`；
  - 对 000922（中证红利）：`off_chg = 6.98`，`off_pct = +0.06%`。
  
  由于 `pt` 已有有效值（8.45 元），系统未改动 `pt`，却把 `off_chg` 直接赋给了 `chg`！
  最终前端渲染输出：
  - **黄金ETF 518880**：最新价 `8.450` 元，涨跌额 `+40.330` 元，涨跌幅 `+2.83%`！
  - **标普500ETF 513500**：最新价 `2.656` 元，涨跌额 `+115.750` 元，涨跌幅 `+1.50%`！
  - **中证红利 000922**：最新价 `5511.17` 点，涨跌额 `+6.98` 点，涨跌幅 `+0.06%`（5511.17 的 0.06% 实际仅为 3.31 点）！
- **Blast radius**: 一个 8.45 元的基金，卡片显示当日上涨了 40.33 元，上涨百分比却是 2.83%！小学数学级别的荒谬矛盾直接暴露在 UI 走廊第一行，极度损害专业度。
- **Mitigation**:
  在 `fetch_custom_realtime_indices` 中，涨跌额 `chg` 必须严格根据当前标的实际点位 `pt` 与百分比 `chg_pct` 进行乘积计算：
  ```python
  if abs(chg_pct) < 1e-6 and abs(off_pct) > 1e-6:
      chg_pct = off_pct
      chg = round(pt * (chg_pct / 100.0), 3 if pt < 100.0 else 2)
  ```
  彻底杜绝跨尺度绝对点位直接硬套。

---

### [High] Challenge 3: 货币/短债 ETF 精度舍入截断致使假平盘 (0.00%) 残留

- **Assumption challenged**: 假设 `round(float(chg_pct), 2)` 不会抹掉货币/短债品种的微小涨跌。
- **Attack scenario**:
  在 `calc_offline_2day_return` 检索 DuckDB `v_etfs`（lines 1406-1408）：
  ```python
  p_curr, chg, chg_pct = r[0]
  if abs(float(chg_pct or 0.0)) > 1e-4:
      return round(float(p_curr), 3), round(float(chg), 3), round(float(chg_pct), 2)
  ```
  在本地 DuckDB 中，`511360 短融ETF` 的真实日涨跌幅为 `0.002%`（万分之二，货币与超短债基金的正常单日波动）。
  执行 `round(0.002, 2)` 后，返回值被四舍五入为 `0.0`！
  `calc_offline_2day_return('511360')` 返回了 `(114.109, 0.002, 0.0)`。
  随后在 `fetch_custom_realtime_indices` 中：
  `if abs(chg_pct) < 1e-6 and abs(off_pct) > 1e-6:`
  由于 `off_pct` 为 `0.0`，条件不成立，`chg_pct` 无法得到替换，最终走廊卡片中 `511360 短融ETF` 依然输出 `0.00%`！
- **Blast radius**: 违反验收标准中“非交易时段基于本地最新两个交易日收盘价计算真实涨跌幅，杜绝整排 0.00% 假平盘”与“Verify no flat 0.00% rows appear across all corridor items”。
- **Mitigation**:
  对于微小涨跌幅，若 `abs(float(chg_pct)) > 1e-6`，严禁直接截断为 `0.0`：
  ```python
  pct_rounded = round(float(chg_pct), 2)
  if abs(pct_rounded) < 1e-4 and abs(float(chg_pct)) > 1e-6:
      pct_rounded = round(float(chg_pct), 3) if abs(float(chg_pct)) >= 0.001 else (0.01 if float(chg_pct) > 0 else -0.01)
  ```
  并在 `fetch_custom_realtime_indices` 中增加保底：若 `off_pct` 为 0，允许回退至 `fb_chg`（例如 0.01%）。

---

## Stress Test Results

| 测试用例 / 场景 | 预期行为 | 实际行为 | 判定 |
|-----------------|---------|---------|------|
| 1.1 `calc_offline_2day_return` 核心指数点位与变动有效性 | 返回各标的真实点位与非零涨跌幅 | 中证红利点位返回 12189.99（失真 2.2 倍）；沪深300返回 6175.66 | **FAIL** |
| 1.2 断网模拟（东财/新浪抛 TimeoutError）下 `fetch_batch_realtime_indices` | 平滑回退，6 只标的点位与涨跌幅正常 | 点位尺度严重失真（黄金ETF 1465元，中证红利 12189点） | **FAIL** |
| 1.3 周末休市 0.00% 假平盘模拟（东财返回 `f3=0`） | 涨跌幅与涨跌额匹配当前点位平滑替换 | 黄金ETF 8.45 元被注入 +40.33 元涨跌额（单日涨跌 480%） | **FAIL** |
| 1.4 全量 40 只目录标的离线回退压力测试 | 40/40 标的无 0.00% 假平盘 | 39/40 通过，511360 短融ETF 因四舍五入返回 0.00% | **FAIL** |
| 2.1 估值分位标签与 PE-TTM 合理性核验 | 核心指数分位在 [0, 100]，状态合法 | 沪深300(66.7%)、中证500(64.2%)、科创50(68%)全合规 | **PASS** |
| 2.2 黄金ETF与 AU9999 乖离率尺度自适应 | 黄金 ETF Bias20 处于 [-30%, +30%]，杜绝 -99% | MA20=8.306, Bias20=+1.73%, Ret20D=+8.91% | **PASS** |
| 2.3 边界测试（latest_pt=0.0 / None / 未知代码 999999） | 0 崩溃，0 除零错误 | 均优雅降级处理 | **PASS** |
| 3.1 物理裁判文件哈希基线审计 | 4 大裁判文件 SHA256 完好无损 | 4/4 PASS (`verify_referee_hashes.py`) | **PASS** |
| 4.1 UI 细节与自选持久化 (CSS Primary White, Watchlist JSON) | 样式类名生效，按钮强制白字，000922在自选中 | 全部合规 (100% 匹配) | **PASS** |

---

## Unchallenged Areas

- **Black-Litterman 与 7 大定权模型数学求解算子**：属于 Milestone 3 交付范畴，本轮暂不纳入。
- **六维风险预警哨与双翼机会雷达**：属于 Milestone 2 交付范畴，本轮暂不纳入。

---

## 结论与建议动作 (Verdict & Recommendation)

**裁定**：**REQUEST_CHANGES**

建议 Worker Prod R8-M1 针对上述 3 项缺陷进行定向修复：
1. **修正 `calc_offline_2day_return` 点位输出**：若查询全收益矩阵 `aligned_matrix_total_return.parquet`，点位基线锁定 `EXPANDED_INDEX_CATALOG[code]["fb_point"]`，仅提取百分比变动 `off_pct`；
2. **修正 `fetch_custom_realtime_indices` 涨跌额计算**：在用 `off_pct` 替换平盘 `chg_pct` 时，强制按 `chg = round(pt * (chg_pct / 100.0), 3 if pt < 100.0 else 2)` 重新精算 `chg`，严禁跨尺度直接套用 `off_chg`；
3. **修正 DuckDB `v_etfs` 涨跌幅舍入**：对微小数值保留足够精度（或保底 0.01%），彻底消灭 511360 的 0.00% 假平盘。
