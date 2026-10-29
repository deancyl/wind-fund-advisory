# Project: AGY2_FundAdvisory WindToolkit Advanced Research Capabilities Upgrade

## Architecture
- **Host System**: `AGY2_FundAdvisory` (AGY2 基金实盘组合接管与智能投顾管理系统)
- **Underlying Lakehouse & Toolkit**: `WindToolkit` (`src/toolkit/unified_sdk.py`), DuckDB (`data/storage.duckdb`, 41 SQL views), 122 Parquet files in `data/`
- **Data Flow**:
  1. `WindToolkit` (DuckDB / Parquet / Online API with 4-tier fallback) ➔
  2. `portfolio_manager.py` (Look-Through Risk Screen R1 & Smart Money Crowding R3) ➔
  3. `strategy_bridge.py` (Macro High-Frequency Liquidity Thermometer R2 & Dual-Track Radar & Rebalance Signals) ➔
  4. `app_gui.py` (Streamlit 8501 GUI Dashboard: Top Status Bar, Tab 1/2/4 Visuals) ➔
  5. `judge_engine.py` & `holdout_vault.py` (Strict Read-Only Invariants Preserved)

## Code Layout
- `AGY2_FundAdvisory/portfolio_manager.py`: Core portfolio logic, fund pool, look-through data, penetration risk calculation
- `AGY2_FundAdvisory/strategy_bridge.py`: Market snapshot, macro liquidity thermometer, dual-track radar, rebalance order generator
- `AGY2_FundAdvisory/app_gui.py`: Streamlit Web GUI (port 8501)
- `AGY2_FundAdvisory/tests/`: Test suite directory (existing 112 tests + new tests)
- `AGY2_FundAdvisory/tests/test_toolkit_integration.py`: New comprehensive integration test suite
- Read-Only Invariants (Strictly untouched, `IsReadOnly: True`):
  - `AGY2_FundAdvisory/judge_engine.py`
  - `AGY2_FundAdvisory/holdout_vault.py`
  - `AGY2_FundAdvisory/AGENT_SPEC.md`
  - `AGY2_FundAdvisory/tests/test_infra.py`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Goodwill Ratio Screen | 商誉占净资产比重 (>30% 预警, >40% 高危) | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Double-High Fraud Screen | 存贷双高造假特征探测 (货币资金>=100亿且有息负债>=150亿且负债/资金>=1.2) | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Controlling Shareholder Pledge | 控股股东质押比例 (>80% 击穿平仓线, 50-80% 临界预警) | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Lockup Expiration Calendar | 未来 30~90 天大额限售股解禁抛压测算 | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Look-Through Risk Rating | 重仓股单体与基金穿透排雷三色标签 (🟢健康 / 🟡关注 / 🔴预警) | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Portfolio Penetration Risk Index | 组合整体穿透风险指数 (0~100) 加权计算 | M1 | ORIGINAL_REQUEST §R1 |
| 7 | OMO Net Injection / Drainage | 央行公开市场 7D 逆回购每日净投放与全口径投放时序 | M2 | ORIGINAL_REQUEST §R2 |
| 8 | DR007 vs 7D OMO Spread | DR007 相对 7D OMO 政策基准利率偏离度 (bp) 动态计算 | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Macro Liquidity Status | 流动性状态判定 (泛滥/宽松/中性/收紧/偏紧) | M2 | ORIGINAL_REQUEST §R2 |
| 10 | Dual-Track Macro Radar | MA20/ERP 估值技术面 × 宏观流动性温度计双轨宏观雷达 | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Extreme Tightening Defense | 资金面极端收紧时触发纯债/黄金防御性资产配置建议 | M2 | ORIGINAL_REQUEST §R2 |
| 12 | Northbound Smart Money | 北向陆股通资金近 1 日 / 5 日重仓股加减仓动态 | M3 | ORIGINAL_REQUEST §R3 |
| 13 | Shareholder Concentration | 股东户数环比变动率与筹码集中度趋向判定 | M3 | ORIGINAL_REQUEST §R3 |
| 14 | Dragon & Tiger Seats | 龙虎榜机构专用席位买卖净额与机构博弈情绪 | M3 | ORIGINAL_REQUEST §R3 |
| 15 | Institutional Crowding Warning | 热门赛道资产筹码集中度与公募抱团松动风险提示 | M3 | ORIGINAL_REQUEST §R3 |
| 16 | Top Status Bar Liquidity Card | 顶部状态栏清晰渲染流动性温度计状态徽章与偏离度卡片 | M4 | ORIGINAL_REQUEST §R2, §R4 |
| 17 | GUI Risk Badges & Detail Table | Tab 1 候选池/建仓单三色标签与 Tab 2/4 排雷大宽表渲染 | M4 | ORIGINAL_REQUEST §R1, §R4 |
| 18 | GUI Smart Money & Crowding View | 选基详情与调仓建议中渲染聪明钱流入与抱团预警 | M4 | ORIGINAL_REQUEST §R3, §R4 |
| 19 | Read-Only Invariants Protection | 严格保持 judge_engine.py 等文件 IsReadOnly: True，零侵入 | M5 | ORIGINAL_REQUEST §R4 |
| 20 | Existing 112 Tests Pass | 既有 112 项测试 100% 全量通过，零回归 | M5 | ORIGINAL_REQUEST §R4 |
| 21 | Offline DuckDB Fallback | 本地 DuckDB + Parquet 四轨离线降级兜底，无外网稳定运行 | M5 | ORIGINAL_REQUEST §R4 |
| 22 | Streamlit GUI Zero-Error | Streamlit Web GUI (端口 8501) 启动与渲染零报错 | M5 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Look-Through Risk Screen Engine (R1) | `portfolio_manager.py` | none | DONE |
| M2 | Macro Liquidity Thermometer & Radar (R2) | `strategy_bridge.py` | none | IN_PROGRESS |
| M3 | Smart Money & Crowding Monitor (R3) | `strategy_bridge.py`, `portfolio_manager.py` | M1 | IN_PROGRESS |
| M4 | GUI Dashboard & Workstation Integration (R1+R2+R3) | `app_gui.py` | M1, M2, M3 | PLANNED |
| M5 | E2E Testing Pass (100%) & Coverage Hardening (R4) | `tests/test_toolkit_integration.py`, full suite | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### `portfolio_manager.py` ↔ `WindToolkit`
- `screen_fund_look_through_risk(fund_code: str) -> Dict[str, Any]`
  - Input: `fund_code` (e.g. "100032", "011613", "002351")
  - Output:
    ```python
    {
        "fund_code": str,
        "fund_name": str,
        "is_ashare_equity": bool, # False for bond 002351, gold 000216, qdii 050025 -> immune to ashare fraud
        "penetration_risk_score": float, # 0.0 ~ 100.0 (0 is safest, 100 is highest risk)
        "risk_level": str, # "Safe" | "Watch" | "Danger"
        "risk_badge": str, # "🟢 健康" | "🟡 关注" | "🔴 预警"
        "danger_count": int,
        "watch_count": int,
        "top_stocks_screen": List[Dict[str, Any]], # details per stock: symbol, name, goodwill, double_high, pledge, lockup
        "diagnosis_summary": str
    }
    ```
- `calculate_portfolio_penetration_risk() -> Dict[str, Any]`
  - Output:
    ```python
    {
        "portfolio_risk_index": float, # weighted average penetration risk 0.0 ~ 100.0
        "risk_level": str, # "Safe" | "Watch" | "Danger"
        "risk_badge": str, # "🟢 健康" | "🟡 关注" | "🔴 预警"
        "danger_stock_count": int,
        "watch_stock_count": int,
        "high_risk_reasons": List[str],
        "funds_breakdown": List[Dict[str, Any]]
    }
    ```

### `strategy_bridge.py` ↔ `WindToolkit`
- `get_liquidity_thermometer() -> Dict[str, Any]` (integrated in `get_latest_market_snapshot()`)
  - Output added to snapshot:
    - `dr007`: float
    - `policy_rate_7d`: float
    - `dr007_spread_bp`: float
    - `liquidity_status`: str ("宽松" / "中性" / "收紧")
    - `liquidity_badge`: str ("🟢 宽松" / "🟡 中性" / "🔴 收紧")
    - `recent_7d_net_injection_billion`: float
    - `dual_track_radar`: Dict[str, Any] (trend_stance, liquidity_stance, combined_action, defensive_triggered)

### `strategy_bridge.py` ↔ Smart Money & Crowding
- `get_fund_smart_money_crowding(fund_code: str) -> Dict[str, Any]`
  - Output:
    - `northbound_1d_net_million`: float
    - `northbound_5d_net_million`: float
    - `concentration_trend`: str ("筹码集中" / "筹码分散" / "筹码平稳")
    - `crowding_degree`: str ("极度拥挤" / "中度抱团" / "相对分散")
    - `crowding_warning`: bool
    - `advisory_tip`: str
