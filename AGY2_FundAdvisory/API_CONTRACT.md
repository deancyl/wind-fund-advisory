# AGY2 跨端客户端 RESTful API 契约规范 (v1.0.0)

本文件是 AGY2 智能投顾系统面向未来 Windows 电脑版（Tauri + React `.exe`）与 Android 手机版（Capacitor / Flutter `.apk`）的唯一权威跨端接口契约。
后端独立启动命令：`python api_server.py --host 127.0.0.1 --port 18501`。
所有 `/api/v1/*` 接口遵循 **纯净 JSON 原则（100% 剥离 HTML 标签与 Unicode Emoji，解释性文案统一收纳在 `help_tooltip` 字段中）**。

---

## 一、资产与持仓域 (Overview & Holdings)

### 1. `GET /api/v1/overview`
- **说明**：获取当前激活账本（或指定 `ledger_id`）的资产总览、盘中盈亏估算与大盘宏观定调。
- **参数**：`ledger_id` (可选，字符串)
- **返回示例**：
```json
{
  "ledger_id": "combat_29_funds",
  "total_equity": 27615.10,
  "available_cash": 1000.00,
  "intraday_pnl_pct": -1.66,
  "intraday_pnl_amount": -441.64,
  "market_stance": "防守控仓",
  "market_regime_code": "DEFENSIVE",
  "benchmark_hs300": {
    "point": 3954.6,
    "change_pct": -0.76
  },
  "ui_hints": {
    "title": "资产总览",
    "pnl_status": "negative",
    "help_tooltip": "综合展示当前账户总权益、可用现金池与盘中实时浮动盈亏估算。"
  }
}
```

### 2. `GET /api/v1/holdings`
- **说明**：穿透获取持仓基金全量明细与实时估值。
- **返回示例**：
```json
{
  "ledger_id": "combat_29_funds",
  "count": 29,
  "total_market_value": 26615.10,
  "items": [
    {
      "fund_code": "002351",
      "fund_name": "易方达裕祥回报债券A",
      "shares": 1950.2,
      "current_nav": 1.1153,
      "market_value": 2175.08,
      "weight_pct": 8.17,
      "intraday_chg_pct": -0.11,
      "total_gain_pct": 5.42,
      "is_tail": false
    }
  ]
}
```

### 3. `GET /api/v1/holdings/movers`
- **说明**：获取今日贡献 Top 3 与今日拖累 Top 3 红黑榜。
- **返回示例**：
```json
{
  "ledger_id": "combat_29_funds",
  "top_gainers": [
    {"fund_code": "005561", "fund_name": "创金合信红利低波A", "est_pnl": 12.50, "chg_pct": 0.28}
  ],
  "top_losers": [
    {"fund_code": "017436", "fund_name": "华安纳斯达克100A", "est_pnl": -98.20, "chg_pct": -5.62}
  ]
}
```

---

## 二、调仓决策与打卡执行域 (Rebalance & Check-in)

### 4. `GET /api/v1/rebalance`
- **说明**：获取按意图分组（清理尾仓、C转A省费、核心调仓、维持持仓）的调仓单与打卡状态。
- **返回示例**：
```json
{
  "ledger_id": "combat_29_funds",
  "is_empty": false,
  "tail_sweep": {
    "title": "清理尾仓 (19只)",
    "count": 19,
    "summary": "清扫 19 只免赎碎片尾仓，回收 562.89",
    "items": [
      {"fund_code": "000058", "fund_name": "华夏中小板ETF联接A", "action": "SELL", "action_text": "建议清仓归拢", "amount": 75.56, "reason": "清理碎片尾仓", "is_checked": true}
    ]
  },
  "c_replace": {
    "title": "C转A省费 (1组)",
    "count": 2,
    "summary": "将 1 只满30天免赎 C 类置换为 A 类，年省销售服务费约 0.40%",
    "items": [
      {"fund_code": "011613", "fund_name": "华夏科创50ETF联接C", "action": "SELL", "action_text": "C转A零费率置换", "amount": 1264.11, "reason": "已满30天免赎期，置换为A类省0.40%年费", "is_checked": false},
      {"fund_code": "011612", "fund_name": "华夏科创50ETF联接A", "action": "BUY", "action_text": "C转A零费率置换", "amount": 1264.11, "reason": "承接C类转入份额", "is_checked": false}
    ]
  },
  "core_trades": {
    "title": "核心调仓 (2只)",
    "count": 2,
    "items": []
  },
  "buffer_hold": {
    "title": "维持持仓 (6只)",
    "count": 6,
    "items": []
  }
}
```

### 5. `GET /api/v1/rebalance/checkin` 与 `POST /api/v1/rebalance/checkin`
- **说明**：读取或提交当日下单打卡状态。
- **POST 请求体**：
```json
{
  "fund_code": "005561",
  "action": "BUY",
  "amount": 500.0,
  "checked": true,
  "date_str": "2026-11-22"
}
```

---

## 三、复盘与历史回测域 (Review)

### 6. `GET /api/v1/review/{subview}`
- **支持的 `subview`**：
  - `timemachine`：历史时光机盲测（零未来函数回测收益率、最大回撤与夏普比率）。
  - `rolling_winrate`：近三年滚动胜率与收益比率。
  - `forward_audit`：样本外前瞻快照与未来净值真实胜率。
  - `shadow_race`：实盘 vs 原始 29 只躺平不动影子账本动态赛跑。

### 7. `GET /api/v1/backtest/summary`
- **说明**：全周期策略与宽基基准对比核心指标（纯 JSON，便于原生 ECharts 渲染）。

---

## 四、体检与穿透诊断域 (Diagnose)

### 8. `GET /api/v1/diagnose/{subview}`
- **支持的 `subview`**：
  - `risk_check`：主动风控哨（7天免赎硬红牌、C类超期置换、深度出血点预警）。
  - `exposure`：五维大类资产穿透（宽基/红利/QDII/纯债/商品）与赛道暴露。
  - `overlap`：前十大重仓股穿透重合度与隐性抱团告警。
  - `stress_test`：CVaR 99% 与历史 3 大单边下跌危机承压表。
  - `ten_dim_votes`：十维多空投票器明细与牛熊拐点对照尺。

---

## 五、推送告警与本地资产安全 (Alerts & Backup)

### 9. `GET /api/v1/alerts/push`
- **说明**：供 Windows 托盘与 Android 状态栏轮询（建议 60 秒轮询一次）获取未读通知。
- **返回示例**：
```json
{
  "ledger_id": "combat_29_funds",
  "alerts_count": 1,
  "alerts": [
    {
      "level": "warn",
      "short_title": "C类省费提醒",
      "summary": "持仓中存在持有满30天C类份额，建议置换为A类免长期服务费",
      "target_tab": "rebalance"
    }
  ],
  "timestamp": "2026-11-22 15:35:00"
}
```

### 10. `GET /api/v1/backups` 与 `POST /api/v1/backups/restore`
- **说明**：快照清册查询与一键无损回滚。
