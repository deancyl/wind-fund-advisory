# AGY2-FundAdvisory v2.1.0 · Institutional Mutual Fund Quant & Rebalancing Workbench

<p align="center">
  <a href="README.md"><strong>[ 简体中文 ]</strong></a> &nbsp;|&nbsp; <strong>[ English ]</strong>
</p>

[![Release](https://img.shields.io/badge/Release-v2.1.0-brightgreen.svg)](https://github.com/deancyl/agy2-fund-advisory/releases/tag/v2.1.0)
[![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20TypeScript%20%2B%20Tailwind%20v4%20%2B%20ECharts-0A192F.svg)](web/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Python%203.10%2B-059669.svg)](AGY2_FundAdvisory/api_server.py)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AGY2-FundAdvisory** is a local-first, open-source institutional quantitative mutual fund & ETF research and rebalancing workbench built with **React 19 + TypeScript + Tailwind CSS v4 + ECharts** on top of a decoupled **FastAPI** quantitative engine.

> **Pure Advisory Positioning**: This software provides quantitative signals, portfolio health diagnostics, and rebalancing reference plans only. It does **not** connect to any broker or execute any trades. All portfolio data stays 100% local on your machine.

## Key Highlights in v2.1.0
- **Institutional Hybrid Workbench UI**: 48px minimalist top bar + 34px live market/lakehouse ticker strip + 4 focused workspaces (**Quant Lab**, **Market & Signals**, **Portfolio & Risk**, **Rebalance Execution**). Replaces vertical card bloat with high-density sortable data matrices, unified underline sub-tabs, and `?` methodology audit tooltips.
- **Controllable Full-Market Quant Sandbox**: Run SLSQP/HRP/CVaR optimization on the local 266-fund real adjusted-NAV lakehouse (screened from 28,177 funds), lock or exclude individual funds end-to-end across solver, backtest, scenarios, and rebalancing, compare up to 4 saved A/B snapshots under aligned 1Y & full-period horizons, and export Markdown/JSON research reports.
- **Non-Blocking Right Fund Inspector & `Ctrl/Cmd + K` Command Palette**: Click any fund to inspect allocation formulas, trailing 1Y curves, top-10 holdings, and lock/exclude controls without losing workspace context; search all funds or run commands via `Ctrl/Cmd + K`.
- **WYSIWYG Data & Ledger Center**: Unified modal for text/offline-OCR preview tables (edit amounts or remove false hits before committing via `/api/v1/import/commit`), multi-ledger management, immutable backup restoration, and anti-ban daily lakehouse sync — zero native browser `prompt/confirm/alert` popups.
- **Zero-Config Clean-Machine Deployment**: Ships with a self-contained trading calendar and 7 pure-public market baseline seed files (~4.9 MB, zero personal data).

## Quick Start
```bash
git clone https://github.com/deancyl/agy2-fund-advisory.git
cd agy2-fund-advisory
python -m pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/` in your browser (or double-click `start-agy2-web.vbs` on Windows).
