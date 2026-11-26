# AGY2 方案 A：全站图表、真实 MA20 乖离与跨页调仓全链路联动设计

- **日期**：2026-11-26
- **状态**：用户已批准（确认推进）
- **范围**：首页 4 处同页脱节（历史情景回测、短期拥挤度象限、全市场新基金 MA20 乖离盲区、净值区第 3 张图语义与脏参数提醒）+ 第 3 页调仓页目标自由输入与可选全市场目标对齐开关。

## 1. 目标与边界
- **目标**：消除全站一切“上方换了全市场组合，下方板块纹丝不动或回退旧 12 基静态模板”的割裂感，保证数据 100% 源自当前求解结果与本地 `266` 只真复权净值湖仓。
- **非目标 / 硬红线**：严禁修改 4 个只读裁判文件；默认存量持仓调仓保持低换手平滑边界（仅在用户主动切换开关时才对齐全市场新选基方案）。

## 2. 方案选型（已批准：方案 A）
- **方案 A（采用）**：首页全链路闭环 + 调仓页保留稳健边界并提供「对齐首页最新全市场选基方案」开关。兼顾“选基-回测-情景-拥挤度全联动”和“老持仓低换手保护”。
- **方案 B（未采用）**：仅修首页不改调仓页，会留下目标收益下拉写死（22% 切页错位）和 `tier="C3"` 硬编码断层。

## 3. 核心模块设计
1. **真实 MA20 乖离与拥挤度 (`portfolio_manager.py` + `/api/v1/charts/crowding_quadrant` + `CrowdingQuadrantChart.tsx`)**：
   - `get_fund_smart_money_crowding(code)` 优先从 `market_elite_nav_matrix.parquet` 读取该基金自身近 20 日真实复权净值计算 `ret_20d / bias_20 / vol_20d` 与 4 象限热度，找不到时才回退旧 `FUND_INDEX_PRICE_MAP`。
   - `/api/v1/charts/crowding_quadrant` 新增 `codes` 参数；首页默认联动「当前推荐方案标的（终选 N 只）」，可一键切回「当前账本持仓标的」。
2. **历史情景回测真联动 (`goal_driven_selector.py` + `/api/v1/charts/scenario_backtest` + `ScenarioBacktestPanel.tsx`)**：
   - 新增 `simulate_portfolio_scenario_backtest`，按当前求解的 `final_weights` 与 `elite_nav`（早于共同成立日的起点由 `proxy_early_df` 透明衔接并明文标注 `used_proxy_early=True` + `proxy_note`）实时重演任意买入起点的全扣费走势与 3m/6m/1y/至今 KPI。
3. **净值板块语义纠偏与脏参数提示 (`BacktestCharts.tsx` + `SignalPage.tsx`)**：
   - `_build_backtest_curves_payload` 输出 `weight_vs_pcr`；第 3 张图升级为「资金占比 vs 真实风险贡献 (PCR) 对照图」，动态反映每只入选基金的资金权与风险权；图 1 导读动态适配实际周期与日期区间。
   - `SignalPage` 在 `isDirty` 状态下为下方回测、极端周期与历史验证区展示统一的「当前展示上次求解结果 · 点击上方求解同步」角标。
4. **跨页状态同步与调仓双模式 (`App.tsx` + `RebalancePage.tsx` + `/api/v1/rebalance`)**：
   - `App.tsx` 托管已求解方案上下文；调仓页目标收益改为 `2%~60%` 自由数字输入，`goal_comparison` 使用用户真实档位；新增「稳健低换手（默认）」与「对齐首页最新全市场选基方案」双模式切换。
