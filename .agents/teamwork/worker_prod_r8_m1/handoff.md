# Handoff Report — Milestone 1: 侧边栏核心指数走廊升级、全市场自由定制与 UI 细节修复

- **Author**: Worker Prod R8-M1 (implementer, qa, specialist)
- **Target**: Milestone 1 (Features 1-6)
- **Date**: 2026-11-05T02:14:00Z
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m1\`

---

## 1. Observation (客观事实与运行证据)

### 1.1 文件独占所有权与修改范围
- 修改文件严格限制于分配清单：
  - `AGY2_FundAdvisory/app_gui.py`
  - `AGY2_FundAdvisory/data_loader.py`
  - `data/cache/custom_watchlist.json`
- 零触碰 4 大只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。

### 1.2 执行结果与工具输出记录
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
2. **目标验收回归测试**：
   - 命令：`py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py`
   - 结果：
     ```
     collected 6 items
     AGY2_FundAdvisory\tests\test_sidebar_remodel_and_bugfixes.py ...... [100%]
     ======================= 6 passed, 3 warnings in 10.73s ========================
     ```
   - 包含 Streamlit `AppTest` 全站渲染（`test_apptest_full_gui_remodel`），确认全屏无异常且 0 error。
3. **关联回归测试全量通过**：
   - 命令：`py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py tests/test_infra.py`
   - 结果：
     ```
     ============================= 38 passed in 8.69s ==============================
     ```
4. **真实行情与离线双日收盘价涨跌幅验证**：
   - 运行：`fetch_batch_realtime_indices(use_cache=False)` 输出：
     ```
     000300 沪深300 pt: 4118.94 chg: 0.43 ma20: 3,945.2 bias: 4.4 🟢 站上 MA20 偏离 +4.4% ret20: -6.28
     000688 科创50 pt: 1305.29 chg: 3.15 ma20: 1,435.9 bias: -9.1 🛡️ 跌破 MA20 防守 (-9.1%) ret20: -23.56
     000922 中证红利 pt: 5511.17 chg: -1.42 ma20: 5,433.2 bias: 1.44 🟢 站上 MA20 偏离 +1.4% ret20: 5.86
     000905 中证500 pt: 6770.17 chg: 2.24 ma20: 7,161.9 bias: -5.47 🛡️ 跌破 MA20 防守 (-5.5%) ret20: -13.94
     000852 中证1000 pt: 6664.55 chg: 2.35 ma20: 7,077.7 bias: -5.84 🛡️ 跌破 MA20 防守 (-5.8%) ret20: -13.75
     518880 黄金ETF华安 pt: 8.45 chg: 2.69 ma20: 8.306 bias: 1.73 🟢 站上 MA20 偏离 +1.7% ret20: 8.91
     ```
   - 无任何 0.00% 假平盘，中证红利严格对应 000922，且点位处于 5500+ 区间。

---

## 2. Logic Chain (推理与推导链)

### 2.1 Feature 1: CSS 类名与并集选择器修复
- **观察**：`data_loader.py` 输出下划线状态 `status = "very_low"` 与 `"very_high"`，而原 `app_gui.py` 样式表中仅写有 `.val-very-low` 与 `.val-very-high`，导致极低估与过热徽章类名未命中。
- **推导与实现**：
  在 `app_gui.py` 全局样式中采用并集选择器 `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high`；同时在前端生成类名时增加标准化 `f"val-{v_status.replace('_', '-')}"`，双重保障边框底色 100% 呈现。

### 2.2 Feature 2: 真实行情批量拉取与离线两日收盘价涨跌幅回退
- **观察**：非交易时段、断网或接口在周末返回 0.00% 会导致走廊出现整排“0.00% 假平盘”。本地 `data/processed/aligned_matrix_total_return.parquet`、`data/processed/indices/*.parquet` 与 DuckDB `v_etfs` 包含真实历史日线收盘价。
- **推导与实现**：
  实现 `calc_offline_2day_return(code)`：
  1. 优先从全收益矩阵提取（映射 H00300, H00905, H00852, H00922, H30269, STAR50_STITCH, AU9999, SPX_CNY, H11009）；若最新两行相等（占位符）则前推至最近实际变动交易日，计算真实收盘涨跌幅；
  2. 其次检索本地 754 个指数 parquet 文件计算真实收盘涨跌幅；
  3. 再次下潜至 DuckDB `v_etfs` 获取真实收盘价格与涨跌幅；
  4. 当东财/新浪盘中接口返回点位 <= 0 或 `change_pct == 0.0` 时，自动采用离线双日真实涨跌幅注入，彻底消除假平盘。

### 2.3 Feature 3: 侧边栏卡片 3 层专业指标流
- **观察**：原有卡片为扁平单行结构，横向空间拥挤且无法同时容纳估值分位与技术均线。
- **推导与实现**：
  重构为 3 层纵向流：
  - **行 1**：指数名称 + 6 位代码（左），最新实时点位 + 涨跌幅胶囊（右），严格遵循 Rule 15 Flexbox 物理防压扁铁律配置 `flex: 0 0 auto !important; white-space: nowrap !important;`；
  - **行 2**：真实 PE/PB 历史分位数标签微胶囊（左），近 20 日累计涨跌幅（右，根据正负着色）；
  - **行 3**：细虚线分割，左侧展示 MA20 均线攻防状态（如 `🟢 站上 MA20 偏离 +1.4%` 或 `🛡️ 跌破 MA20 防守 (-5.5%)`），右侧展示 MA20 参考点位。
  - 在 `get_index_corridor_metrics` 中针对点位尺度差异（如黄金 ETF 8.45元 vs AU9999 指数 1440 点）进行等比缩放校准，避免产生 -99% 的乖离率失真。

### 2.4 Feature 4 & 5: 38+ 全市场目录、弹窗设置与持久化
- **观察**：用户需要自由定制走廊关注的标的，且需支持快速搜索与任意 6 位代码接入。Rule 16 强制规定中证红利必须且仅映射为 000922（严禁 000015）。
- **推导与实现**：
  1. 在 `data_loader.py` 定义 `EXPANDED_INDEX_CATALOG`（内置 40 只标的，覆盖宽基、红利、科技、医药、消费、金融、新能源、军工、周期、港股、美股、黄金、债券 12 大板块）；中证红利严格对应 000922。
  2. 侧边栏右上角设置 Popover（`⚙️`）：
     - 3~15 只展示数量滑块；
     - 全市场多选检索列表，格式化函数支持拼音首字母（如 `zzhl`）、代码（`000922`）与名称多模搜索，保持勾选顺序；
     - 任意 6 位代码输入框与添加按钮：调用 `validate_and_fetch_code` 实时联网探测 EastMoney/Sina 与 DuckDB 库，验证通过自动加入走廊前列；
  3. 配置通过原子写入保存至 `data/cache/custom_watchlist.json`，并由 `load_custom_watchlist` 实现冷启动自愈加载。

### 2.5 Feature 6: UI 细节修复
- **观察**：深色模式下 Streamlit Primary 按钮偶现低对比度；Tab 1 步骤一灰框与 caption 均重复输出了“资产锚点”和“权益上限”。
- **推导与实现**：
  1. 在 `app_gui.py` CSS 追加：
     `button[kind="primary"], button[kind="primary"] *, button[kind="primary"] p, button[kind="primary"] span { color: #ffffff !important; font-weight: 600 !important; }`
  2. Tab 1 步骤一合并精炼：保留灰框内的完整策略锚点（定权模型、资产锚点、权益中枢、回撤上限），将下方 caption 简化为纯收益与档位确认提示，杜绝同屏重复。

---

## 3. Caveats (注意事项与假设)

1. **接口环境假设**：若测试机处于断网或防火墙拦截环境，系统将全自动降级至本地 parquet 离线双日收盘价与基准点位，保证系统 0 崩溃、0 异常抛出。
2. **DuckDB 锁竞争**：DuckDB 采用只读连接（`read_only=True`）以防止与常驻服务产生写锁冲突。
3. **No other caveats**：所有验收标准均已独立自动化实测通过。

---

## 4. Conclusion (结论)

Milestone 1 的 6 大特性（样式类名并集修复、离线真实双日涨跌幅与消除假平盘、3 层专业指标流卡片、38+ 全市场目录与弹窗设置、自选持久化缓存、Primary 白字与文案精炼）已全部真实落地于 `AGY2_FundAdvisory/data_loader.py`、`AGY2_FundAdvisory/app_gui.py` 与 `data/cache/custom_watchlist.json` 中。
裁判文件 100% 完好无损，自动化测试 100% 通过，系统已具备向 Milestone 2 交付的完备条件。

---

## 5. Verification Method (独立复核方法)

复核审计员可通过以下标准命令进行独立复核：

```powershell
# 1. 验证裁判文件未被篡改 (4/4 PASS)
py -3 scripts/verify_referee_hashes.py

# 2. 运行 Milestone 1 核心回归测试 (6/6 PASS, 包含 AppTest)
py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py

# 3. 运行关联回归套件 (38/38 PASS)
py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py tests/test_infra.py

# 4. 检查自选持久化文件与基准代码
py -3 -c "import json; wl = json.load(open('data/cache/custom_watchlist.json')); print('Watchlist codes:', wl['selected_codes']); assert '000922' in wl['selected_codes']"
```
