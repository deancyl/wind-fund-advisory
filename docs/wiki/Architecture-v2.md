# 系统架构与 5 层洁净分层 (v2.0.0)

AGY2-FundAdvisory v2.0.0 采用严格的单向依赖分层架构，彻底消除循环导入与前后端耦合：

## 1. 前端展示层 (`web/`)
- **技术栈**：React 19 + TypeScript + Vite 6 + Tailwind CSS v4 + ECharts 5 + Lucide Icons
- **核心页面**：
  - `SignalPage.tsx`：今日大势定调、目标收益×4套模型选基生成器、5档多周期联动回测、历史情景回测、短期偏离与拥挤度象限
  - `HoldingsPage.tsx`：多模持仓导入空态引导、3-KPI 概览、体检预警、资产大类缺口与行业穿透双图、调仓效果追踪、极端行情压力测试、持仓明细/净值对账表（支持行内编辑与 CSV 导出）
  - `RebalancePage.tsx`：调仓前后目标达成率对比、分组参考清单与本地保存、增量新钱定投、大额限购分批计划、分红方式建议
  - `FundDetailPage.tsx`：全站一键进入的 10 维度基金深度详情工作台
  - `ProAnalysisDrawer.tsx`：自选检索增删、热门场内 ETF 溢价预警、A/C 费率对比器、十维量化投票、冷备快照还原
- **可扩展性**：通用自适应 `EChartBox.tsx` 组件天然支持未来平滑接入 K 线图（Candlestick + Volume + MA/MACD）模块。

## 2. 后端 REST 接口与静态托管层 (`AGY2_FundAdvisory/api_server.py`)
- 基于 FastAPI 提供零 HTML、零 Emoji 污染的结构化 `/api/v1/*` JSON 契约（同步导出至 `docs/openapi_v1.json`）；
- 当 `web/dist/index.html` 存在时自动以单端口 `127.0.0.1:8000` 托管静态页面，实现零跨域与单进程运行。

## 3. 核心业务与量化引擎层 (`AGY2_FundAdvisory/`)
- **Layer-0 领域模型**：`domain_models.py`（零业务模块依赖，承载核心数据结构与基金池元数据）
- **路径隔离层**：`runtime_paths.py`（支持 `AGY2_DATA_DIR` 环境变量隔离，兼容桌面端与移动端打包）
- **量化决策引擎**：`goal_driven_selector.py`、`fund_detail_service.py`、`strategy_bridge.py`、`advisory_engine.py`、`portfolio_manager.py`
