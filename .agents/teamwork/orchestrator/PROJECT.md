# Project: Wind 投顾系统全栈升级 (全市场自定义走廊、数据单源同真、7大机构定权模型、6维主动预警与压力测试)

## Architecture
- **Web UI & Visualization Layer**: `AGY2_FundAdvisory/app_gui.py`
  - 侧边栏核心指数行情走廊：3 层卡片指标流、东财/新浪实时批量接口与离线多日收盘价涨跌幅计算、CSS 并集选择器修复
  - 侧边栏右上角自选设置弹窗：3~15 只展示数量滑块、38+ 全市场指数/ETF 三模多选排序检索器、任意 6 位有效代码实时校验接入与 JSON 持久化
  - 左翼全市场机会雷达看板：Top 3 机会卡片 + 可展开 14 大赛道量化温度计总表 + 顶部 <=80 字今日市场脉搏晨报
  - 右翼六维主动风险预警哨：涵盖红牌锁仓、黄牌倒计时、C类置换、阶梯止盈与深套、赛道集中度与清盘线，配套一键跳转与减仓单动作按钮
  - UI 细节修复：`button[kind="primary"] * { color: #ffffff !important; }` 样式锁死，Tab 1 步骤一策略锚点重复文案合并精炼
- **Data & Single Source of Truth Layer**: `AGY2_FundAdvisory/data_loader.py`, `data/processed/aligned_matrix_total_return.parquet`, `data/processed/indices/*.parquet`
  - 单源同真（Single Source of Truth）：废除 `RADAR_SECTOR_CATALOG` 静态假常量，统一下潜至 `IndexValuationEngine` 与本地行情日线动态精算
  - 侧边栏与雷达双翼估值分位数绝对一致（浮点误差 < 1e-4）
  - 自选配置持久化：`data/cache/custom_watchlist.json`
- **Quant Strategy & Execution Layer**: `AGY2_FundAdvisory/advisory_engine.py`, `winrate_engine.py`, `portfolio_optimizer.py`
  - 7 大机构级量化定权求解算子：鲁棒双核HRP、核心-卫星杠铃、全天候风险平价、BL观点融合、条件胜率最优、尾部CVaR、凯利动量增强，权重和严格等于 1.0
  - 宏观状态自适应推荐路由逻辑与模型对比说明卡片
  - 历史黑天鹅压力测试器：2018 贸易摩擦熊市、2022 杀估值熊市、2024 微盘流动性危机三个历史切片的最大浮亏与回本天数测算
- **Physical Safety Redline Layer**:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（物理只读红线，SHA256 绝对锁定，严禁修改）

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 侧边栏样式类名修复 | 样式表支持 `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high` 并集选择器，极低估与过热徽章边框底色生效 | M1 | R1 |
| 2 | 真实行情与非交易日涨跌幅 | 优先东财/新浪批量实时接口，离线/非交易时段读取本地最新两交易日收盘价计算真实涨跌幅，杜绝整排 0.00% 假平盘 | M1 | R1 |
| 3 | 侧边栏卡片 3 层专业指标流 | 行1: 名称代码实时点位与涨跌幅胶囊(Flexbox防压扁)；行2: 真实PE/PB分位与近20日涨跌幅；行3: MA20趋势与偏离状态 | M1 | R1 |
| 4 | 全市场 38 只指数/ETF 目录与弹窗设置 | 内置 12 板块 38+ 标的(锁死000922)，侧边栏右上角设置弹窗支持 3~15 只滑块、拼音/代码/名称三模检索多选排序器、任意 6 位有效代码实时校验接入 | M1 | R1 |
| 5 | 自选走廊持久化缓存 | 自选配置落盘至 `data/cache/custom_watchlist.json`，支持冷启动恢复与默认列表兜底 | M1 | R1 |
| 6 | UI 细节修复与精炼 | `button[kind="primary"] *` 强制白色文字 (`#ffffff !important`)，Tab 1 步骤一合并消除重复资产锚点与权益上限描述 | M1 | R3 |
| 7 | 估值与动量单源同真 | 彻底废除 `RADAR_SECTOR_CATALOG` 静态硬编码字段，修正 parquet 路径，统一由 `IndexValuationEngine` 与本地矩阵动态精算 14 赛道指标 | M2 | R2 |
| 8 | 升级左翼全市场机会雷达 | Top 3 机会卡片下方提供可展开 14 大赛道量化温度计总表，顶部增加 <=80 字今日市场脉搏晨报 | M2 | R2 |
| 9 | 实装右翼六维主动风险预警哨 | 实装未满7天锁仓红牌(011612)、临免赎倒计时黄牌(011613)、C类30天置换、阶梯止盈与深套诊断(013841)、赛道集中度与重仓重叠、迷你基清盘与攻防线 | M2 | R2 |
| 10 | 预警卡片交互式动作按钮 | 每条预警卡片配备一键跳转 Tab 2 锁定未满 7 天标的或生成阶梯止盈减仓单的可交互动作按钮 | M2 | R2 |
| 11 | 实装 7 大机构量化定权求解算子 | 在 `QUANT_MODELS_CATALOG` 与 `WinRateOptimizer` 中实装 HRP、核心卫星、全天候、BL观点融合、条件胜率、CVaR、凯利动量增强，权重和严格等于 1.0 | M3 | R3 |
| 12 | 步骤一模型对比与宏观路由更新 | 同步更新 Tab 1 步骤一 7 大模型对比说明卡片与宏观环境推荐路由逻辑 | M3 | R3 |
| 13 | 历史黑天鹅压力测试器 | 在 Tab 1 步骤二与 Tab 3 推演结果中实装 2018、2022、2024 年初三大历史切片最大浮亏金额与回本天数测算卡片 | M3 | R3 |
| 14 | 物理裁判文件哈希锁定与只读审计 | 运行 `verify_referee_hashes.py` 验证 4 大只读文件 SHA256 完好无损 | M4 | R4 |
| 15 | 针对性单元测试套件全覆盖 | 验证 7 大模型权重和严格等于 1.0、6 维预警哨精准识别 011612/011613/013841、侧边栏与雷达估值分位 100% 同源一致 | M4 | R5 |
| 16 | Streamlit AppTest 回归与服务重启 | AppTest 验证深浅色主题全站 0 异常，遵循瞬态端口非破坏性甄别平滑重启 8501 端口服务 | M4 | R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 侧边栏核心指数走廊升级、全市场自由定制与 UI 细节修复 | Features 1-6 (R1, R3 UI): 样式并集选择器, 离线真实涨跌幅, 3 层指标流卡片, 38+ 目录与弹窗设置, Watchlist JSON 持久化, Primary 白字与步骤一文案精炼 | none | DONE |
| M2 | 估值动量单源同真与双翼看板升级 (机会雷达 + 六维预警哨) | Features 7-10 (R2): 废除静态常量, 路径纠正与 14 赛道动态精算, 脉搏晨报与温度计总表, 六维主动预警哨实装与快捷交互按钮 | M1 | DONE |
| M3 | 7 大机构级量化定权模型与历史黑天鹅压力测试器 | Features 11-13 (R3): 实装 7 大数学求解算子, 权重归一化严格等于 1.0, 宏观推荐路由, 2018/2022/2024 黑天鹅压力测试卡片 | M1, M2 | IN_PROGRESS |
| M4 | 物理红线哈希审计、全套自动化回归测试与服务平滑重启 | Features 14-16 (R4, R5): 裁判文件哈希审计, 7 模型归一化/6 维预警/估值同源针对性单元测试, AppTest 4-Tab 0 异常, 8501 端口平滑重启 | M1, M2, M3 | PLANNED |

## Interface Contracts
### M1 ↔ M2: Index Valuation & Sector Mapping Contract
- **File**: `data/cache/custom_watchlist.json` & `AGY2_FundAdvisory/data_loader.py`
- **Schema**:
  - `custom_watchlist.json`: `{"selected_symbols": ["000300", "000905", "000852", "000922", ...], "custom_added": [{"symbol": str, "name": str, "market": str}], "display_count": int}`
  - `IndexValuationEngine`: Benchmark symbols (e.g. `000922` for csi_dividend) must return identical percentile in both sidebar and radar.
- **Rule 16 Invariant**: CSI Dividend benchmark symbol is strictly `000922` (never `000015`).

### M2 ↔ M3: Radar Views & Black-Litterman Input Contract
- **File**: `AGY2_FundAdvisory/advisory_engine.py` ↔ `winrate_engine.py`
- **Contract**:
  - `OpportunityRadarEngine.get_top_opportunity_sectors(k=3)` returns `{sector_id: expected_excess_return}` as Bayesian P / Q views for Model 4 (Black-Litterman).
  - All 7 quantitative weighting models must output weights $w_i \ge 0$ such that $|\sum w_i - 1.0| < 1e-6$.

### M3 ↔ M4: Mathematical Invariants & Test Verification
- **Contract 1 (Weight Sum Unity)**: All 7 models must satisfy `sum(weights.values()) == 1.0` within floating precision `1e-6`.
- **Contract 2 (Penalty Lock & FIFO Holding)**: Holding $<7$ days (011612) strictly locks shares at lower bound in optimizer.
- **Contract 3 (Zero Exception AppTest)**: Streamlit `AppTest` executes all 4 tabs with `assert not at.exception` in both light and dark themes.

## Code Layout
- `AGY2_FundAdvisory/`
  - `app_gui.py`: 侧边栏行情走廊、设置弹窗、双翼看板渲染、黑天鹅卡片与全局样式 (M1, M2, M3)
  - `data_loader.py`: 实时行情获取、离线收盘价涨跌幅、估值分位引擎 (M1, M2)
  - `advisory_engine.py`: 单源同真雷达引擎、14 赛道量化温度计、六维主动风险预警哨 (M2)
  - `winrate_engine.py`: 7 大机构定权模型算子、黑天鹅压力测试测算逻辑 (M3)
  - `portfolio_optimizer.py`: 调仓路径优化、惩罚锁仓硬约束 (M2, M3)
  - `tests/`: 自动化单元测试与回归测试 (M4)
- `tests/`:
  - `test_infra.py`: 只读裁判测试基线（物理只读）
  - `test_r8_quant_models_and_sentry.py`: 增量针对性测试套件 (M4)
