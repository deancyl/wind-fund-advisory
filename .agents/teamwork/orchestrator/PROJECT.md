# Project: 量化引擎抗白噪音与市场节奏自适应升级 + UI逻辑收官修复

## Architecture
- **Language & Runtime**: Python 3.11, Streamlit 1.32+, DuckDB / Parquet lakehouse.
- **Pure Mathematical Invariant**: 100% 纯数学因果演绎（No Look-Ahead Bias），零未来函数，零外部大模型 API。
- **Physical Safety Invariants (Strict Read-Only)**:
  - `judge_engine.py` (只读裁判文件)
  - `holdout_vault.py` (盲盒验证金库)
  - `AGENT_SPEC.md` (策略基准约束)
  - `tests/test_infra.py` (裁判回归测试基建)
- **Target Components**:
  - `strategy_bridge.py`: 考夫曼信噪比卡尔曼滤波变速器、自适应动量窗口、动量二阶导（加速度衰竭）与复合动量衰竭预警、动态梯级防追高联动。
  - `data_loader.py`: `denoise_covariance_matrix(corr_matrix, n_obs=60, shrink_alpha=0.15)` 算子实现并在 `compute_ewma_volatility_and_correlation` 中接入。
  - `portfolio_optimizer.py`: 在 `_compute_hrp_weights` 及协方差矩阵构建中接入 RMT 去噪算子。
  - `winrate_engine.py`: `monte_carlo_winrate` 升级为 70% 循环分块自助法 (Circular Block Bootstrap, block_size=10) + 30% Student-t ($\nu=5$) 厚尾扰动，输出 95% CVaR 指标。
  - `app_gui.py`: 顶部看板 `top_c2` 与步骤二白盒面板 `c_sig2` 实时渲染信噪比与动量加速度，严格保障 5 项既有交互闭环。
  - `tests/`: 编写针对性单元测试与 AppTest 用例，全量回归测试套件。

## Code Layout & Write Boundaries
| Milestone | Worker Role | Primary Owned Files | Read-Only Files |
|-----------|-------------|---------------------|-----------------|
| M1 | Agent-1 (Adaptive Signal & State Machine) | `AGY2_FundAdvisory/strategy_bridge.py` | `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` |
| M2 | Agent-2 (Matrix Denoising & Bootstrap Stress) | `AGY2_FundAdvisory/data_loader.py`, `AGY2_FundAdvisory/portfolio_optimizer.py`, `AGY2_FundAdvisory/winrate_engine.py` | Same read-only invariants |
| M3 | Agent-3 (UI Interaction & White-Box Display) | `AGY2_FundAdvisory/app_gui.py` | Same read-only invariants |
| M4 | Agent-4 (E2E Regression, Audit & Service Health) | `AGY2_FundAdvisory/tests/*.py` | Same read-only invariants |

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Kaufman Efficiency Ratio (ER 信噪比) | $ER_t = \frac{\|P_t - P_{t-w}\|}{\sum \|P_{t-i} - P_{t-i-1}\|} \in [0, 1]$ 区分单边趋势与锯齿白噪音 | M1 | R1, Explorer 1 |
| 2 | 1D Kalman Filter Noise Stripper | 一维卡尔曼滤波，观测噪声方差 $R_t$ 随 $1 - ER_t$ 动态放大，提取真实趋势与斜率 | M1 | R1, Explorer 1 |
| 3 | Dynamic Adaptive Momentum Window | 自适应窗口 $W_{\text{eff}} = \text{int}(60 - 40 \times ER_t) \in [20, 60]$，极速跟进主升浪与平滑过滤白噪音 | M1 | R1, Explorer 1 |
| 4 | Momentum Second Derivative (Acceleration) | $\text{Accel} = \text{Mom}_{15} - 0.25 \times \text{Mom}_{60}$ 监控动能二阶导与高位衰退 | M1 | R2, Explorer 1 |
| 5 | Momentum Exhaustion Tri-Factor Warning | 进攻状态下“高拥挤度 + 动量加速度转负 (<= -2.0%) + 期权 iVIX 跳升”三联触发预警与防追高削减 35% 仓位 | M1 | R2, Explorer 1 |
| 6 | RMT Marchenko-Pastur Denoising | 特征值分解，$\lambda \le \lambda_+ = (1 + \sqrt{N/T})^2$ 替换为白噪音均值（迹守恒），重构去噪相关矩阵 | M2 | R3, Explorer 2 |
| 7 | Ledoit-Wolf Diagonal Shrinkage | $\tilde{C}_{\text{final}} = (1 - \alpha)\tilde{C} + \alpha I$，$\alpha=0.15$，条件数大幅下降，最小特征值 $\ge 0.15$ 保证正定 | M2 | R3, Explorer 2 |
| 8 | Circular Block Bootstrap + Student-t Heavy Tail | 70% 循环分块 ($b=10$) 保留波动率聚集 + 30% Student-t ($\nu=5$) 厚尾扰动，计算 95% CVaR | M2 | R4, Explorer 2 |
| 9 | UI R5 交互收官保护与验证 | 保持 Tab 1 模式 B 问卷测评、重算折叠步骤三、备选切换刷新、Tab 2 目标池切换、持仓变动缓存失效、盘中观察期防冲动勾选锁 | M3 | R5, Explorer 3 |
| 10 | UI 顶部看板与步骤二白盒展示 | 顶部看板 `top_c2` 与步骤二白盒面板 `c_sig2` 实时渲染信噪比与动量加速度，并展示衰竭预警 | M3 | R5, Explorer 3 |
| 11 | Full E2E Integration, Referee Hash Audit & Service Health | 全量单元测试与 AppTest 100% 通过，4 大裁判文件 SHA256 0 篡改，Streamlit 8501 存活 | M4 | AC, Explorer 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Adaptive SNR Kalman & Momentum Accel | R1 & R2 in `strategy_bridge.py` | Survey | DONE |
| M2 | RMT Covariance Denoising & Bootstrap Stress | R3 in `data_loader.py` & `portfolio_optimizer.py`, R4 in `winrate_engine.py` | Survey | DONE |
| M3 | UI Refinement & Real-Time Indicators | R5 in `app_gui.py` | M1, M2 | DONE |
| M4 | Final E2E Regression, Hash Audit & Service | Full test suite regression, referee integrity, 8501 service probe | M1, M2, M3 | DONE |

## Interface Contracts
### `strategy_bridge.py`
- `compute_market_snr_and_kalman_state(price_series, window=20, q_process=1e-4) -> Dict[str, Any]`
  - 返回字典含：`er_snr: float`, `effective_window: int`, `kalman_trend: float`, `kalman_slope: float`
- `compute_momentum_acceleration(price_series, fast_window=15, slow_window=60) -> float`
  - 返回二阶导数加速度数值（百分比，如 `+1.85` 或 `-2.40`）
- `StrategyBridge.get_latest_market_snapshot()`
  - 新增透传字段：`er_snr`, `effective_momentum_window`, `mom_accel`, `momentum_exhaustion_warning`, `momentum_exhaustion_text`
  - 保留原有旧字段兼容下游：`mom60_300`, `mom20_300`

### `data_loader.py` & `portfolio_optimizer.py`
- `denoise_covariance_matrix(corr_matrix, n_obs=60, shrink_alpha=0.15) -> Any`
  - 支持 DataFrame 与 ndarray，自适应处理协方差与相关性矩阵，输出条件数优化且严格正定的去噪矩阵。

### `winrate_engine.py`
- `monte_carlo_winrate(nav_series, holding_days, target_annual_return, n_paths=10000, block_size=10, include_friction=True, fund_type="A", seed=42) -> Dict[str, Any]`
  - 采用 70% Circular Block Bootstrap ($b=10$) + 30% Student-t ($\nu=5$)
  - 返回字典新增 `cvar_95` 与 `cvar_95_annualized`
  - 保留别名：`monte_carlo_simulation = monte_carlo_winrate`

### `app_gui.py`
- 读取 `snapshot.get('er_snr', 0.65)` 与 `snapshot.get('mom_accel', 0.0)`
- 顶部看板 `top_c2` 副标题追加：`📡SNR {snr:.2f} ｜ ⚡加速度 {accel:+.1f}%`
- 步骤二白盒面板 `c_sig2` 增补卡片项与预警高亮
- 100% 保持 5 项既有交互闭环（问卷定档、重算折叠步骤三、备选刷新、目标池切换与缓存失效、盘中防冲动锁）
