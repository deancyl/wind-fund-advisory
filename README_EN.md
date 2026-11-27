# AGY2-FundAdvisory v2.3.0 · Institutional China OTC Mutual Fund Quant & Take-Profit Workbench

<p align="center">
  <a href="README.md"><strong>[ 简体中文 ]</strong></a> &nbsp;|&nbsp; <strong>[ English ]</strong>
</p>

[![Release](https://img.shields.io/badge/Release-v2.3.0-brightgreen.svg)](https://github.com/deancyl/agy2-fund-advisory/releases/tag/v2.3.0)
[![CI Gate](https://img.shields.io/badge/CI-Quality%20Gate-059669.svg)](https://github.com/deancyl/agy2-fund-advisory/actions/workflows/ci-quality-gate.yml)
[![Daily Data](https://img.shields.io/badge/Data_Bundle-data--latest-0284C7.svg)](https://github.com/deancyl/agy2-fund-advisory/releases/tag/data-latest)
[![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20TypeScript%20%2B%20Tailwind%20v4%20%2B%20ECharts-0A192F.svg)](web/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Python%203.10%2B-059669.svg)](AGY2_FundAdvisory/api_server.py)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AGY2-FundAdvisory** is a local-first, open-source institutional quantitative mutual fund research, staged-entry, and trailing take-profit workbench tailored for **China OTC open-end mutual fund investors** (bank / Alipay / Tiantian buyers), built with **React 19 + TypeScript + Tailwind CSS v4 + ECharts** on top of a decoupled **FastAPI** quantitative engine.

> **Pure Advisory Positioning**: This software provides quantitative signals, portfolio health diagnostics, take-profit risk alerts, and rebalancing reference plans only. It does **not** connect to any bank or broker or execute any trades. All personal ledgers and cashflows stay 100% local on your machine.

## Key Highlights in v2.2.0 – v2.3.0
- **China OTC Mutual Fund Hygiene & True Walk-Forward OOS (`v2.2.0`)**:
  - 13-bucket OTC taxonomy (including a dedicated `short_bond` duration shield) backed by `fund_catalog.parquet` & `fund_trading_rules.parquet`; strictly excludes lockup/holding-period funds, exchange-only ETFs, and mislabeled overseas/gold funds so buy recommendations are 100% actionable OTC open-end funds.
  - Strict 70/30 out-of-sample split + rolling Walk-Forward blind verification, aligned macro kernel with bear-market left-tail damping, and real A/C share-class fee mapping.
  - Automated GitHub Actions daily public data pipeline (`daily-market-data.yml`) publishing SHA256-verified `data-latest` bundles with proxy-free domestic mirror sync.
- **Make-Money & Protect-Gains Workflow Closed Loop (`v2.3.0`)**:
  - **Staged Entry Wizard (`/api/v1/plan/staged_entry`)**: Generates 3–6 tranche entry schedules calibrated to current macro temperature and valuation regime.
  - **14:30 Cutoff Quick-Action Bar (`/api/v1/trading/cutoff_brief`)**: Aligned with China mutual fund 15:00 T-day cutoff, surfacing actionable orders, 7-day punitive redemption-fee guards, and T+1/T+2 confirmation dates.
  - **Holding-Level 3-Stage Trailing Take-Profit Radar**: Tracks profit targets and peak-to-trough drawdown triggers per holding to lock in gains before full round-trips.
  - **Exact XIRR & Private Per-Ledger Cashflows (`/api/v1/ledger/cashflows`)**: Local-only (`data/cashflows_*.json`, gitignored) cashflow ledger with Newton-Raphson exact annualized XIRR calculation.
  - **Institutional Private-Wealth WebUI Polish**: Warm `#F4F7FB` canvas, fluid `rem` KPI typography, `color-mix(in oklab, ...)` semantic surfaces, native `<dialog>` modals, zero horizontal overflow at `1440px` and `390px`, and zero ECharts label overlap.

## Quick Start
```bash
git clone https://github.com/deancyl/agy2-fund-advisory.git
cd agy2-fund-advisory
python -m pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/` in your browser (or double-click `start-agy2-web.vbs` on Windows).

### Docker Deployment (NAS / Linux Server)
```bash
AGY2_HOST_PORT=8000 docker compose up -d --build
```
The official `Dockerfile` bundles public market baseline seeds and master catalogs into `/app/seed_data` (`AGY2_SEED_DIR`) and automatically bootstraps missing seeds into `/app/data` on startup without touching personal ledgers or cashflows.

### Verification Suite
```bash
python -m pytest -q tests/test_phase2_money_making_workflow.py tests/test_phase1_quant_integrity.py tests/test_akshare_compat_and_seed_bootstrap.py tests/test_infra.py tests/test_g17_advisory_real_data_and_ten_dimension.py
```
