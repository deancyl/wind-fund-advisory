# Handoff Report — Financial & Regulatory Facts Survey (Section 1)

## 1. Observation

### 1.1 红利低波代码错配
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
  - 第 29 行：`"benchmark_index": "000978",`
  - 第 31 行：`"index_code": "000978",`
  - 该赛道配置对象为 `RADAR_SECTOR_CATALOG["dividend_low_vol"]`。
  - 事实背景：`000978` 为官方“中证医药100指数”（CSI Medicine 100 Index），绝非红利低波指数；而中证红利低波动全收益指数代码为 `H30269`（价格指数 930955）。
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py`
  - 第 225 行：`{"code": "H30269", "secid": "0.H30269", "name": "红利低波", "type": "cs_parquet", "cs_code": "H30269", "parquet": "data/processed/csindex_H30269.parquet", "aliases": ["000978"]},`
  - 本地湖仓文件 `data/processed/csindex_H30269.parquet` 存在且包含 2018-01-01 至 2026-10-27 共 2,139 行完整数据，字段包含 `['日期', '收盘', '涨跌幅', '滚动市盈率']`。

### 1.2 QDII 基金交割清算与估值标签
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\trading_clock_fee.py`
  - 第 288-320 行 `calculate_settlement_dates()` 默认入参为 `confirm_cycle="T+1"`, `arrive_cycle="T+2"`，未对 QDII 海外品种（如 `050025` 标普500、`001071` 华安纳指、`013402` 恒生科技）提供跨时区交割清算参数分支与提示。
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`
  - 第 6096 行 `calculate_rebalance_routes()`：
    `if s_comp and b_comp and s_comp == b_comp:`
    未排除 QDII 与跨 TA 品种，导致同一公司下的国内基金与 QDII 基金（如博时标普500 050025 与博时信用债 050027）被错误撮合为 `PRIORITY_1_SWITCH`（同公司 T+1 转换）。
  - 第 5848 行 `calculate_rebalance_net_utility()`：
    `is_same_company = bool(from_company and to_company and from_company == to_company)`
    同样未排除 QDII 品种。
  - 第 6858-6965 行执行调仓流水生成 `PendingOrder` 时，全量调用了默认的 `calculate_settlement_dates(now_dt)`，未能给美股 QDII 赋予 T+2 确认与 T+6~T+8 到账。
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
  - Tab 1 建仓执行单（第 3143-3169 行 `df_bp`）与 Tab 2 主持仓表（第 3866-3920 行 `df_table` / `st.data_editor`）未在估值或指引列中区分「指数高准度」、「债基看久期票息」、「美股休市·看隔夜期指」、「季报重仓估算」4 类置信度标识。
  - Tab 2 在途对账中心（第 4323-4355 行 `dock_tab4`）展示在途订单时，未对美股 QDII 标明 `「T+2 确认份额 · 赎回 T+6~T+8 到账（跨时区清算，不可用于 T+2 极速换仓）」`。

### 1.3 违规“保本”词汇出现位置
通过对全仓拉网式 grep 检索，发现以下违规文本：
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`:
  - 第 2728 行：`保本率 <b>{_no_loss:.0f}%</b> ｜ 跑赢货基 <b>{_beat_cash:.0f}%</b> ｜ 中位年化 <b>{_med_ann:.1f}%</b>`
  - 第 2736 行：`- **保本率 (收益 $\ge 0\%$)**：持有期满本金不亏损的概率。纯债配置较高时此项较高，但不可与“达标胜率”混为一谈；`
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\winrate_engine.py`:
  - 第 70 行：`"no_loss_rate": "【绝对保本率】：扣除全部交易摩擦成本后，持有期满账面累计净收益率 ≥ 0.0%（本金不发生亏损）的概率。",`
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py`:
  - 第 4684 行：`# 计算三周期条件胜率表（含保本率、跑赢货基率、95%尾部底线）`
- `d:\Google\Workspace\Wind\src\analysis\market_temperature.py`:
  - 第 164 行：`advice = "市场估值处于历史 80% 以上极度高估水位，ERP性价比严重透支。坚决大幅减持权益资产，防守保本，锁利并等待估值回踩。"`
- 豁免项（法定否定式免责声明）：`README.md:260` 及 `src/advisory/rules_engine.py:110` 中的“不构成保本或保收益承诺”，按监管规定必须保留。

### 1.4 14 大赛道动量与 Bias20 分红平滑
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
  - 第 275-325 行 `_calc_dynamic_sector_metrics()`：
    红利类指数在无 `fallback_parquet` 时直接读取 `aligned_matrix_total_return.parquet` 中由全收益指数（H00922, H30269）构成的列。
  - 遇到 5~7 月分红密集期，全收益指数在除息日自动累加再投资分红，导致单日跳升 $+0.5\% \sim +2\%$，从而使得最新收盘价 $P_t$ 相对于 20 日均线 $MA20$ 产生虚假的正乖离偏误脉冲（Bias20 虚增至 $+4\% \sim +6\%$），触发误判超买。
  - 本地 `data/processed/indices/000922.SH.parquet` 数据仅到 `2019-01-30`，不可作为 2026 年实时日线直接读取；而 `csindex_H30269.parquet` 与 `csindex_H00922.parquet` 数据时效最新（均至 `2026-10-27`）。

---

## 2. Logic Chain

1. **红利低波代码逻辑链**：
   - 由观察 1.1 知，`RADAR_SECTOR_CATALOG["dividend_low_vol"]` 的 `benchmark_index` 为 `000978`（医药100）；
   - 在 `advisory_engine.py:358-375`，`get_sector_valuation_percentile()` 取 `candidates = [benchmark_index, symbol, index_code, cs_code]`，在 `val_map` 中检索；
   - 因 `data_loader.py:225` 之前因别名补偿写入了 `"aliases": ["000978"]`，导致代码在逻辑上拿医药100索引红利低波；
   - 纠正对策：将 `benchmark_index` 与 `index_code` 修改为 `"H30269"`，并在 `RADAR_SECTOR_CATALOG["dividend_low_vol"]` 添加 `"fallback_parquet": "data/processed/csindex_H30269.parquet"`；
   - 同时清除 `data_loader.py:225` 的 `"aliases": ["000978"]`，使 `IndexValuationEngine` 单源同真直接映射 H30269，杜绝交叉污染。

2. **QDII 跨时区与同公司转换逻辑链**：
   - 由观察 1.2 知，QDII 基金具有外汇额度限制、境外托管行与跨时区结算特点，份额登记 TA 与境内基金不同；
   - 因此同一基金公司旗下的 QDII 基金与普通 A 股基金物理上不能支持 T+1 转换，且资金赎回通常需 T+6~T+8 到账；
   - 现行代码在 `portfolio_manager.py:6096` 仅凭借 `s_comp == b_comp` 即判定同公司转换，导致逻辑脱靶；
   - 必须通过 `is_qdii_fund(code, name)` 识别美股与海外品种，在同公司转换路由中执行 `if is_qdii_fund(s_code) or is_qdii_fund(b_code): continue`；
   - 在交割推算中注入美股 QDII 规则（T+2 确认、T+6~T+8 到账），并在 Tab 2「T+2 在途踏空风险」计算中排除 QDII；
   - 针对 4 大类资产特性，在前端建立动态估值可信度分级体系（指数高准度 / 债基看久期票息 / 美股休市·看隔夜期指 / 季报重仓估算）。

3. **监管保本合规清理逻辑链**：
   - 由观察 1.3 确认，全站界面有 2 处前端展示出现“保本率”，核心量化引擎与投顾建议中有 3 处使用“保本”；
   - 根据证监会投顾合规法规，将用户可见的“保本率”统一替换为“正收益概率 (≥0%)”（符合量化模型对于账面累计净收益率 $\ge 0.0\%$ 的严谨定义），或“本金安全率”；
   - 确保全站 UI 源码中不再残留任何肯定句式的“保本”承诺用语。

4. **价格指数与分红平滑逻辑链**：
   - 由观察 1.4 知，全收益指数在分红季由于红利再投资产生的单日收益率跳升，导致 20 日均线乖离率 Bias20 被虚假抬高；
   - 针对红利赛道，在 `_calc_dynamic_sector_metrics()` 中：
     优先以 `data/processed/csindex_H30269.parquet` 等独立日线作为基准；
     若使用全收益序列，对最近 20 日日度收益序列中属于分红再投资的孤立脉冲跳空进行移动中位数平滑，重构无偏价格路径；
     由此计算出的 Bias20 将真实反映二级市场价格动量，消除虚假超买报警。

---

## 3. Caveats

1. **海外标普 500 数据源**：美股交易日历与 A 股不同（美股存在圣诞节、感恩节等休市日），本期重点在于规范交易时钟与国内交收端规则（T+2 确认、T+6~T+8 到账），境外本地日历已通过现存 `global_indices.parquet` 覆盖。
2. **000922 历史切片**：`data/processed/indices/000922.SH.parquet` 虽仅到 2019 年，但 `data/processed/csindex_H00922.parquet` 数据已更新至 2026-10-27，因此平滑算法应直接作用于 `H00922` 全收益序列或 `aligned_matrix_total_return.parquet`。
3. **只读裁判文件严禁修改**：`tests/test_infra.py`、`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 为只读底座，本项调查提出的修改方案严格隔离在 `advisory_engine.py`、`data_loader.py`、`trading_clock_fee.py`、`portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py` 及新增测试用例中。

---

## 4. Conclusion

已完整锁定 Section 1 涉及的 4 项金融事实与合规修改方案：
1. **红利低波指数纠偏**：`advisory_engine.py` 中 `benchmark_index` 与 `index_code` 由 `000978` 纠偏为 `H30269`，`data_loader.py:225` 移除别名 `000978`；
2. **QDII 交割规则与估值标签**：
   - `trading_clock_fee.py` 新增 `is_qdii_fund` 与 `get_qdii_delivery_label`，美股 QDII 推算 T+2 确认、T+7 到账；
   - `portfolio_manager.py` 及 `strategy_bridge.py` 的同公司转换与 T+2 踏空风险计算中彻底排除 QDII；
   - Tab 1 建仓单与 Tab 2 调仓单、在途对账单统一标注 `「T+2 确认份额 · 赎回 T+6~T+8 到账（跨时区清算，不可用于 T+2 极速换仓）」`；
   - Tab 1/Tab 2 估值列动态展示 4 档置信度标签；
3. **“保本”违规词汇清理**：全站替换 `app_gui.py`、`winrate_engine.py` 中的“保本率”为“正收益概率 (≥0%)”或“本金安全率”；
4. **动量与乖离率分红平滑**：`advisory_engine.py` 的 `_calc_dynamic_sector_metrics()` 引入分红脉冲平滑机制。

---

## 5. Verification Method

后续实施智能体与测试代理可通过以下方式进行独立验证：

### 5.1 静态 AST 与文本断言
1. 断言 `advisory_engine.py` 中 `RADAR_SECTOR_CATALOG["dividend_low_vol"]["benchmark_index"] == "H30269"`，绝不等于 `"000978"`；
2. 断言 `app_gui.py` 源码中 `grep "保本率"` 返回 0 结果；
3. 断言 `trading_clock_fee.py` 或 `portfolio_manager.py` 中对标的 `050025` 调用交割规则返回跨时区 T+2 确认、T+6~T+8 标签，且同公司转换路由无法匹配该基金。

### 5.2 单元测试用例
运行针对性测试用例：
```bash
pytest tests/ -k "dividend or qdii or winrate" -v
```
预期结果：全部通过，且 000922 点位严格保持在 5000~6500 区间，050025 不进入同公司 T+1 转换池。
