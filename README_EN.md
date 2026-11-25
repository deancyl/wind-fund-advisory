# AGY2-FundAdvisory v2.0.0 · Quantitative Mutual Fund Advisory & Rebalancing Workbench

<p align="center">
  <a href="README.md"><strong>[ 简体中文 ]</strong></a> &nbsp;|&nbsp; <strong>[ English ]</strong>
</p>

[![Release](https://img.shields.io/badge/Release-v2.0.0-brightgreen.svg)](https://github.com/deancyl/agy2-fund-advisory/releases/tag/v2.0.0)
[![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20TypeScript%20%2B%20Tailwind%20%2B%20ECharts-0A192F.svg)](web/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Python%203.10%2B-059669.svg)](AGY2_FundAdvisory/api_server.py)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AGY2-FundAdvisory** is a local-first, open-source quantitative mutual fund & ETF analysis and rebalancing workbench built with **React 19 + TypeScript + Tailwind CSS + ECharts** on top of a decoupled **FastAPI** quantitative engine.

> **Pure Advisory Positioning**: This software provides quantitative signals, portfolio health diagnostics, and rebalancing reference plans only. It does **not** connect to any broker or execute any trades. All portfolio data stays 100% local on your machine.

## Key Highlights in v2.0.0
- **Modern Decoupled Web Frontend**: Replaces the legacy monolithic UI with a crisp, sub-second React + ECharts single-port web app (`http://127.0.0.1:8000`) ready for future desktop (Tauri) and mobile (Capacitor) packaging.
- **Goal-Driven Multi-Factor Quant Selection**: Set your target return (%) and investment horizon (6M / 1Y / 2Y / 3Y), switch among 4 allocation models (*All-Weather*, *Risk Parity*, *Dividend Defense*, *Barbell Growth*) and C1–C5 risk tiers, and inspect rolling historical achievement probability alongside fund-detail multi-factor scores (Sharpe, Calmar, MaxDD, volatility, new-high rate, fees, and manager tenure).
- **10-Dimension Fund Detail Workbench**: Click any fund across the app to inspect interactive return & NAV curves, historical performance, customizable DCA simulator, 4-category / 8-metric analytics radar, asset/industry/top-10 stock holdings, current & historical managers, fund profile, trading/fee rules, and official announcements.
- **Portfolio Diagnostics & Rebalancing Reference**: Import holdings via text paste, local offline OCR, or manual entry; inspect asset/industry exposure gaps, NAV reconciliation, extreme stress scenarios, before-vs-after goal achievement deltas, quota-split calendars, and dividend reinvestment advice.

## Quick Start
```bash
git clone https://github.com/deancyl/agy2-fund-advisory.git
cd agy2-fund-advisory
python -m pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/` in your browser (or double-click `start-agy2-web.vbs` on Windows).
