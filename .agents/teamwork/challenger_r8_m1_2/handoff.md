# Handoff Report — Challenger R8-M1-2

- **Author**: Challenger R8-M1-2 (critic, specialist)
- **Target**: Milestone 1 (Features 1-6)
- **Date**: 2026-11-05T02:24:30Z
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_2\`
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation (客观事实与运行证据)

### 1.1 工具命令与直接输出
1. **裁判文件哈希基线验证**：
   - 命令：`py -3 scripts/verify_referee_hashes.py`
   - 结果：
     ```
     PASS: AGY2_FundAdvisory/judge_engine.py matches expected hash.
     PASS: AGY2_FundAdvisory/holdout_vault.py matches expected hash.
     PASS: AGY2_FundAdvisory/AGENT_SPEC.md matches expected hash.
     PASS: tests/test_infra.py matches expected hash.
     ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.
     ```
2. **对抗性压力测试套件运行**：
   - 命令：`py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py -v`
   - 结果：`3 failed, 12 passed in 15.83s`
   - 失败用例 1：`test_calc_offline_2day_return_csi_dividend_scale_invariant`
     ```
     AssertionError: Rule 16 违反: 离线计算 000922 点位返回 12189.99，严重脱离 5000~6500 基线区间！原因: 误将 H00922 全收益指数点位作为 000922 价格指数点位返回！
     assert 12189.99 <= 6500.0
     ```
   - 失败用例 2：`test_fetch_custom_realtime_indices_offline_rule16_invariant`
     ```
     AssertionError: Rule 16 严重违例: 断网降级下 000922 点位为 12189.99，超出 5000~6500 区间！
     assert 12189.99 <= 6500.0
     ```
   - 失败用例 3：`test_weekend_flat_etf_change_amount_proportionality`
     ```
     AssertionError: 量纲严重错乱: 8.43元 ETF 的涨跌额被赋值为 40.33 元 (理论应为 0.239 元)！原因: 直接透传了现货指数 AU9999 的绝对涨跌额 off_chg，未按 ETF 点位折算！
     assert 40.091 < 0.05
     ```

### 1.2 源码定位
- `AGY2_FundAdvisory/data_loader.py` line 1317-1349 (`calc_offline_2day_return`):
  使用 `aligned_matrix_total_return.parquet` 中 `H00922` (12189.99)、`AU9999` (1465.02)、`SPX_CNY` (7812.21) 全收益/现货指数点位作为 `p_curr` 并直接 `return round(p_curr, 2), round(chg, 2), round(chg_pct, 2)`。
- `AGY2_FundAdvisory/data_loader.py` line 1666-1670 (`fetch_custom_realtime_indices`):
  ```python
  if pt <= 0.0:
      pt = off_pt
  if abs(chg_pct) < 1e-6 and abs(off_pct) > 1e-6:
      chg = off_chg
      chg_pct = off_pct
  ```
  在断网/离线时将 `pt` 直接设为 `off_pt = 12189.99`；在周末非交易时段将 `chg` 直接设为 `off_chg = 40.33`。

---

## 2. Logic Chain (推理与推导链)

1. **Rule 16 违例推导**：
   - 依据 `GEMINI.md` Rule 16：“数据抓取与大屏渲染必须配备点位基线校验（如中证红利必须处于 5000 ~ 6500 点区间，若拉取到 3300 点必须触发报警熔断与源切换），杜绝向用户展示失真点位。”
   - 观察 1.1 显示：断网或接口失败时，`calc_offline_2day_return("000922")` 输出 12189.99。
   - 导致 `fetch_custom_realtime_indices` 将中证红利走廊卡片点位呈现为 12189.99，超出 5000~6500 上界 87%，直接违反 Rule 16 铁律。

2. **周末平盘注入导致 ETF 涨跌额量纲错乱推导**：
   - 观察 1.1 与 1.2 显示：东财盘中/周末接口返回正常 ETF 点位 8.434 元，但涨跌幅返回 0.00% 假平盘时，代码触发回退逻辑。
   - 回退逻辑直接执行 `chg = off_chg`，而 `off_chg` 来自 1400 点的现货黄金指数（AU9999 每克涨跌额为 +40.33 元）。
   - 使得前端展示为：最新点位 8.434 元，涨跌额 +40.33 元，涨跌幅 +2.83%。
   - 8.434 元净值的 ETF 怎么可能单日上涨 +40.33 元（涨幅实际应对应 +0.239 元）？此乃严重的跨量纲透传 Bug。

3. **合规项核验**：
   - 全市场目录已扩充至 40 只（>=38只），覆盖 14 个大类板块（>=12板块）；
   - 自选缓存 `custom_watchlist.json` 在文件缺失、空文件、畸变 JSON 情况下均可安全兜底，无未捕获异常；
   - CSS `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high` 并集生效；
   - `button[kind="primary"]` 强制 `#ffffff !important` 白字；
   - AppTest 全站 0 exception, 0 error；
   - 4 大裁判文件 SHA256 完好无损。

---

## 3. Caveats (注意事项与假设)

1. **联网测试条件**：在联网且处于交易时段时，东财 API 返回有效点位与涨跌额，上述 2 个 Bug 处于潜伏状态；只有在触发“离线降级”或“周末 0.00% 假平盘回退”边界时才会显现。
2. **Review-only 约束**：作为 Challenger，严格遵守只读审阅原则，未修改任何生产代码，所有验证均通过独立测试脚本 `AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py` 严格复现。

---

## 4. Conclusion (结论与判定)

**判定结果**：**REQUEST_CHANGES**

Milestone 1 绝大多数功能（样式类名、自选持久化、目录完整性、AppTest 几何）符合验收标准，但 `AGY2_FundAdvisory/data_loader.py` 中存在的离线点位溢出（12189.99 击穿 Rule 16 5000~6500 点位红线）以及周末假平盘涨跌额跨量纲错位（8元 ETF 出现 +40 元涨跌额）属于严重缺陷，必须由 Worker 进行针对性修复后方可批准通过。

---

## 5. Verification Method (独立复核与修复指南)

### 独立复核命令
```powershell
# 运行对样本与对抗性压力测试（当前存在 3 项失败）：
py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py -v

# 验证裁判文件未被篡改：
py -3 scripts/verify_referee_hashes.py
```

### 修复指引（供 Worker 参考）
1. 在 `data_loader.py` 的 `calc_offline_2day_return` 中：
   - 明确 `aligned_matrix_total_return.parquet` 仅用于计算相对涨跌幅 `off_pct`；
   - 对于点位 `off_pt`：优先基于 `EXPANDED_INDEX_CATALOG[code]["fb_point"]` 基准点位；
   - 严格守死 Rule 16：对 `000922` 校验 `5000.0 <= off_pt <= 6500.0`；
   - 涨跌额 `off_chg` 必须根据 `off_pt * (off_pct / 100.0)` 精算。
2. 在 `data_loader.py` 的 `fetch_custom_realtime_indices`（line 1668-1670）中：
   - 严禁 `chg = off_chg` 盲目赋值；
   - 必须统一通过 `chg = round(pt * (off_pct / 100.0), 3 if is_etf else 2)` 保证涨跌额与当前点位量纲 100% 匹配。
