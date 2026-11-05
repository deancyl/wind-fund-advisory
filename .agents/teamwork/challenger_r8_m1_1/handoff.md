# Handoff Report — Milestone 1 对抗性质询与审核结果

- **Author**: Challenger R8-M1-1 (critic, specialist)
- **Target**: Milestone 1 (侧边栏核心指数走廊升级、全市场自由定制与 UI 细节修复)
- **Date**: 2026-11-05T02:23:00Z
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_1\`
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation (客观事实与运行证据)

### 1.1 经验对抗测试套件运行实证
- 编写并执行测试脚本：`py -3 scripts/test_challenger_r8_m1_empirical.py`
- 运行结果：
  ```
  STRESS TEST SUMMARY: 117/119 PASSED
  FAILED TESTS (2):
    - CSI Dividend 000922 pt=12189.99 in [4000, 7000] range (Rule 16)
    - Offline all 38: ZERO items have 0.00% flat return (zero count = 1)
  ```

### 1.2 源码缺陷定位与具体表现
1. **点位尺度失真与全收益污染 (Rule 16 违规)**：
   - 文件：`AGY2_FundAdvisory/data_loader.py` lines 1317-1351 与 lines 1661-1675。
   - 观察：`calc_offline_2day_return` 优先查询 `aligned_matrix_total_return.parquet` 并返回 `p_curr`。对于全收益指数（H00922、AU9999、SPX_CNY、H00300、H11009），点位与价格指数/ETF 存在巨大尺度差异。
   - 运行证据：
     ```powershell
     py -3 -c "from AGY2_FundAdvisory.data_loader import fetch_custom_realtime_indices; from unittest.mock import patch; with patch('urllib.request.urlopen', side_effect=TimeoutError('offline')): print(fetch_custom_realtime_indices(['000922', '518880', '513500'], use_cache=False))"
     ```
     输出结果：
     - `000922` 点位展示为 `12189.99`（违背 Rule 16 要求的 5000~6500 点合理基线）；
     - `518880` 黄金ETF 点位展示为 `1465.02`（真实 ETF 单价仅为 8.434 元，失真 173 倍）；
     - `513500` 标普500ETF 点位展示为 `7812.21`（真实 ETF 单价仅为 2.656 元，失真 2941 倍）。

2. **周末假平盘回退时涨跌额计算矛盾**：
   - 文件：`AGY2_FundAdvisory/data_loader.py` lines 1668-1670。
   - 观察：
     ```python
     if abs(chg_pct) < 1e-6 and abs(off_pct) > 1e-6:
         chg = off_chg
         chg_pct = off_pct
     ```
     当东财返回现价 `pt = 8.45` 且 `chg_pct = 0.00` 时，系统保留 `pt = 8.45`，但将 `chg` 替换为 `off_chg`（全收益点位差值 `+40.33`）。
   - 运行证据：
     - 黄金 ETF 518880 卡片显示：最新价 `8.450`，涨跌额 `+40.330`，涨跌幅 `+2.83%`（8.45 元股票单日暴涨 40.33 元，荒谬不成立）。

3. **短融 ETF 精度舍入抹除微小涨跌幅**：
   - 文件：`AGY2_FundAdvisory/data_loader.py` lines 1406-1408。
   - 观察：
     ```python
     if abs(float(chg_pct or 0.0)) > 1e-4:
         return round(float(p_curr), 3), round(float(chg), 3), round(float(chg_pct), 2)
     ```
     对于 `511360 短融ETF`，DuckDB 中 `change_pct = 0.002`。执行 `round(0.002, 2)` 后变为 `0.0`，导致返回 `(114.109, 0.002, 0.0)`。
   - 运行证据：在离线模拟下，`511360` 依然输出 `0.00%` 平盘，未能实现“杜绝 0.00% 假平盘”要求。

4. **只读裁判文件 SHA256 完好**：
   - 命令：`py -3 scripts/verify_referee_hashes.py`
   - 结果：4/4 ALL PASS。

---

## 2. Logic Chain (推理与推导链)

1. **推导 1 (全收益点位污染价格指数)**：
   - 观察 1.2.1 显示 `calc_offline_2day_return` 将 `H00922` 的全收益累计值 `12189.99` 作为价格指数 `000922` 的离线现价返回；
   - 在 `data_loader.py:1666` 中，当网络超时或无法获取盘中点位时（`pt <= 0.0`），执行 `pt = off_pt`；
   - 这一赋值直接导致前端侧边栏走廊展示出 12,189.99 点，而 `GEMINI.md` Rule 16 明确规定“中证红利必须处于 5000 ~ 6500 点区间，杜绝向用户展示失真点位”；
   - 黄金 ETF（518880）与标普 500 ETF（513500）同样被赋以 `AU9999`（1465.02）与 `SPX_CNY`（7812.21）的点位，导致 ETF 价格失真千倍。

2. **推导 2 (涨跌额与现价脱钩)**：
   - 观察 1.2.2 显示周末盘后东财返回现价 `pt = 8.45` 且 `chg_pct = 0.00`；
   - `data_loader.py:1669` 仅将 `chg` 赋值为 `off_chg`，而 `off_chg` 是基于 1400 多点计算出的差值（`40.33`）；
   - 现价 8.45 与涨跌额 40.33 拼接在同一张卡片上，导致涨跌额是单价的近 5 倍，数学关系 `change = point * change_pct` 被严重打破。

3. **推导 3 (截断导致 0.00% 假平盘残留)**：
   - 观察 1.2.3 显示 DuckDB 中 511360 的真实涨跌幅为 0.002%；
   - `round(0.002, 2)` 被舍入为 `0.0`，导致下游 `abs(off_pct) > 1e-6` 为假，511360 未被修复，走廊仍出现 0.00% 假平盘。

---

## 3. Caveats (注意事项与假设)

1. 联网实时行情在交易时段（工作日 09:30~15:00）正常工作，上述问题主要集中在**断网、网络超时、非交易时段、周末/节假日接口返回 0.00% 假平盘**等边缘与降级场景。
2. 裁判文件未被任何篡改，哈希完全一致。
3. 样式类名修复、Primary 白字穿透与自选持久化经实测均符合预期。

---

## 4. Conclusion (结论与审核裁定)

**审核裁定**：**REQUEST_CHANGES**（需要返工修复）

尽管 Worker Prod R8-M1 完成了基础功能搭设，但在极端与离线对抗场景下存在 **2 项 Critical 缺陷**（全收益点位污染击穿 Rule 16、ETF涨跌额脱钩荒谬）与 **1 项 High 缺陷**（511360 短融ETF残留假平盘）。
必须由 Worker Prod R8-M1 针对上述问题进行定向修正后方可进入 Milestone 2。

### 明确修复建议清单：
1. **修正 `calc_offline_2day_return` 点位输出**：
   - 对 `matrix_cols` 标的，若存在于 `EXPANDED_INDEX_CATALOG` 中，点位基准取 `meta["fb_point"]`，全收益矩阵仅用于精算 `off_pct`；
   - 计算涨跌额：`off_chg = round(base_pt * (off_pct / 100.0), 3 if base_pt < 100 else 2)`。
2. **修正 `fetch_custom_realtime_indices` 涨跌额赋值**：
   - 严禁 `chg = off_chg`；
   - 强制采用 `chg = round(pt * (chg_pct / 100.0), 3 if pt < 100.0 else 2)`，确保数学一致性。
3. **修正 DuckDB `v_etfs` 涨跌幅舍入**：
   - 对微小涨跌幅保留 3 位小数，或当 `abs(float(chg_pct)) > 1e-6` 且 `round(float(chg_pct), 2) == 0.0` 时保底取 `0.01%`（或保留原始精度），杜绝 511360 产生 0.00% 平盘。

---

## 5. Verification Method (独立复核方法)

复核审计员与 Worker 可通过以下命令验证修复情况：

```powershell
# 1. 运行对抗性经验测试套件 (必须达到 119/119 ALL PASS)
py -3 scripts/test_challenger_r8_m1_empirical.py

# 2. 模拟断网点位校验 (中证红利必须在 5000~6500 区间，黄金ETF单价必须在 7~10 元区间)
py -3 -c "from AGY2_FundAdvisory.data_loader import fetch_custom_realtime_indices; from unittest.mock import patch; with patch('urllib.request.urlopen', side_effect=TimeoutError('offline')): res = fetch_custom_realtime_indices(['000922', '518880', '513500'], use_cache=False); print([(x['code'], x['point'], x['change'], x['change_pct']) for x in res]); assert 5000 <= res[0]['point'] <= 6500; assert res[1]['point'] < 20.0"

# 3. 运行裁判文件哈希验证
py -3 scripts/verify_referee_hashes.py
```
