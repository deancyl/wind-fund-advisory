# 快速启动、单端口部署与 OpenAPI 契约

## 1. 本地部署与一键启动
```powershell
git clone https://github.com/deancyl/agy2-fund-advisory.git
cd agy2-fund-advisory
py -3 -m pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
py -3 -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000
```
- 访问 `http://127.0.0.1:8000/` 即可使用完整工作台；
- Windows 用户可直接双击 `start-agy2-web.vbs` 无黑框静默启动并以 Edge 独立窗口打开；
- 访问 `http://127.0.0.1:8000/docs` 查看交互式 Swagger OpenAPI 文档。

## 2. 核心 `/api/v1/*` 接口速览
| 端点 | 功能说明 |
| :--- | :--- |
| `GET /api/v1/overview` | 组合总览、三大指数实时行情与大势定调 |
| `GET /api/v1/recommend/blueprint` | 目标收益×周期×4模型×多因子评分选基方案 |
| `GET /api/v1/funds/{code}/detail` | 10 维度基金深度详情与自定义定投测算 |
| `GET /api/v1/charts/backtest_curves` | 多周期联动累计净值、回撤与仓位变迁曲线 |
| `GET /api/v1/charts/scenario_backtest` | 历史情景回测（多起点零未来函数验证） |
| `GET /api/v1/charts/crowding_quadrant` | 短期偏离与交易拥挤度四象限分布 |
| `GET /api/v1/holdings` / `DELETE` / `POST /cash` | 持仓明细、净值对账、删基与现金管理 |
| `GET /api/v1/rebalance` / `POST /checkin` | 调仓参考方案、目标达成对比与本地保存 |
| `POST /api/v1/cashflow/plan` | 增量新钱定投分配方案 |
| `GET /api/v1/tools/etf_premiums` & `/dividend_advice` | 热门场内 ETF 溢价预警与宏观分红方式建议 |
