# Wind 投顾终端核心 API 与协议规范

本规范整理了从 Wind 投顾终端前端逆向分析出的核心 RESTful API 端点、鉴权机制与请求/响应格式。

---

## 一、 通用鉴权与请求头规范

所有对投顾服务端（统一网关）的请求必须携带以下请求头：

```http
GET /pac-web/api/product/getHomePageFundInfo?a=1 HTTP/1.1
Host: ${ADVISORY_GATEWAY_HOST}
wind.sessionid: ${WIND_SESSION_ID_TOKEN}
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.120 Safari/537.36
Accept: application/json, text/plain, */*
Referer: https://${ADVISORY_GATEWAY_HOST}/WFC-WEB/WFCPC/home/index.html
```

* **`wind.sessionid`**：核心令牌（85 位数字字符串）。若已过期或未登录，接口统一返回：
  ```json
  {"message": "10011：SessionId无效或已过期，请重新获取SessionId！", "errorCode": 10011}
  ```

---

## 二、 核心业务 API 清单

### 1. 基金历史业绩走势对比接口
* **URL**：`GET /pac-web/api/product/getFundPerformanceYieldChart5`
* **参数**：
  * `windCodes`: 基金代码逗号分隔列表（如 `002910.OF,021179.OF,004320.OF`）
  * `startDate`: 起始日期（如 `2024-01-01`）
* **响应格式**：
  ```json
  {
    "data": {
      "002910.OF": [
        {
          "name": "易方达供给改革",
          "windcode": "002910.OF",
          "data": [
            {"x": 1761580800000, "y": 0.0},
            {"x": 1762185600000, "y": -1.69},
            {"x": 1792944000000, "y": 115.76}
          ]
        }
      ]
    },
    "errorCode": 0,
    "errorMsg": null
  }
  ```
  > `x` 为毫秒时间戳，`y` 为相对于起点的累计区间收益率百分比（%）。

### 2. 首页优选与推荐基金池
* **URL**：`GET /pac-web/api/product/getHomePageFundInfo?a=1`
* **参数**：
  * `issuerId`: 机构或基金管理人代码（可选）
  * `fundSize`: 规模筛选（可选）
  * `homeUser`: `true`

### 3. AI 投顾规划与配额查询
* **URL**：`GET /pac-web/api/chat/queryQuota`
* **用途**：查询当前用户针对 WindGPT / AI 理财规划师的调用次数与额度。
* **URL**：`POST /pac-web/chat/request2`
* **参数**：
  ```json
  {
    "chatId": "...",
    "question": "请对比易方达供给改革与华商均衡成长的风格特征",
    "customerid": "-1"
  }
  ```

### 4. 机构 CRM 与顾问身份
* **URL**：`GET /pac-web/api/crm/getUserCompanyInfo`
* **响应格式**：
  ```json
  {
    "companyId": "370FFFD2-E8C6-433B-9D4E-1A85B84ED3A8",
    "companyName": "招商银行股份有限公司上海分行",
    "userName": "梁可",
    "userRole": "S6"
  }
  ```

### 5. 单只标的智能简报接口
* **URL**：`GET /alice-fc/data/queryBriefing?windCode=002910.OF`
* **用途**：获取基金经理投资框架、重仓行业、换手率与风格箱评语。
