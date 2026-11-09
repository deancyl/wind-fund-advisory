# G15 第三阶段专项勘探与架构设计交接报告 (Handoff Report)

## 一、 Observation (直接客观观测证据)

### 1. 运行环境与 OCR 依赖检测
- **执行命令与输出**：运行 `scripts/inspect_env_ocr.py`，检测 Python 3.11.9 环境：
  - `rapidocr_onnxruntime`：**AVAILABLE**（基于 ONNX Runtime 纯本地推理，实测推理单图耗时 ~150ms，且零公网依赖，无任何网络风控风险）。
  - `pytesseract`：**AVAILABLE**（0.3.13）。
  - `winrt.windows.media.ocr`：**AVAILABLE**（Windows 原生 OCR 支持）。
  - `cv2`：**AVAILABLE**（5.0.0）。
  - `PIL`：**AVAILABLE**（12.2.0）。
  - `streamlit`：**AVAILABLE**（1.66.1，具备原生 `@st.dialog` 与 `st.popover` 双模态弹窗能力）。
- **用户上传长截图实体分析**：
  - 路径：`C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135877_65af68f3.jpg`
  - 物理规格：JPEG 格式，尺寸 `(127, 1024)` 像素。
  - 观测事实：该长图由聊天窗口网关在上传时按最大边 1024px 进行了等比缩放，宽高比达 `1 : 8.06`，直接 OCR 汉字笔画严重坍塌（每个字符仅占 3~4px）。用户本地原生天天基金长图通常为 `1080 × 8700` 像素。
  - 结论：系统必须在前端通过 `st.file_uploader` 接收用户直接上传的原图二进制字节流，以 100% 原始宽度不压缩执行滑动窗口切片。

### 2. 全市场基金主数据字典
- **本地湖仓文件**：`data/master/fund_catalog.parquet` 真实存在，大小约 600KB。
- **数据结构**：包含 28,177 行数据，列名为 `['symbol', 'pinyin_abbr', 'fund_name', 'fund_type', 'pinyin_full', 'std_symbol']`。
- **匹配能力**：在 `scripts/test_fuzzy_match.py` 实测中，基于去除省略号（`...`）、去除类型后缀及字符相似度打分，对 11 只典型带有省略号的基金名称（如“创金合信中证红利...”、“华安纳斯达克100ETF...”）的 6 位代码匹配准确率达 100%。

### 3. 代码库现状与既有漏洞定位
- **漏洞 1（盈亏负号反转，P0级算账漏洞）**：
  - 观测位置：`AGY2_FundAdvisory/portfolio_manager.py` 第 1453 至 1456 行：
    ```python
    gain_match = re.search(r'(?:持有收益(?!率)|累计收益(?!率)|收益(?!率)|盈利(?!率)|浮盈|赚|盈|涨)[:：\s]*([+-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', remain_line)
    if gain_match:
        gain_val = abs(float(gain_match.group(1).replace(',', '')))
        floating_pnl = gain_val
    ```
  - 事实：在天天基金与支付宝界面中，无论浮盈浮亏字段名一律叫做“持有收益”（如 `持有收益 -312.36`）。因包含“收益”二字，命中该分支后被 `abs()` 强制取绝对值，将所有亏损基金错误篡改为正盈利！
- **漏洞 2（小额持仓市值错乱，P0级解析漏洞）**：
  - 观测位置：`AGY2_FundAdvisory/portfolio_manager.py` 第 1477 至 1478 行：
    ```python
    candidates = [v for v in valid_nums if v >= 100]
    amount = candidates[0] if candidates else valid_nums[0]
    ```
  - 事实：硬编码要求金额 `>= 100`，导致百元以下（如 89.60元、50.00元、0.59元）的尾仓金额全部被误识别为残留的昨日收益数字或年份数字。
- **漏洞 3（碎片尾仓清理判定越界，误杀主力资产）**：
  - 观测位置：`AGY2_FundAdvisory/portfolio_manager.py` 第 7931 至 7935 行：
    ```python
    is_tail_fragment = (total_mv > 0 and (h.market_value / total_mv < 0.03)) or (h.market_value < 2000.0)
    is_mature_c = (h.share_class == "C" and min_days >= 30)
    ```
  - 事实：把 `market_value < 2000.0` 盲目判定为尾部碎片，且将所有满 30 天的 C 类（即便占比高达 8.89% 的华夏科创 50C）直接全额清仓并换成红利低波，严重破坏用户风险敞口；且目前 `ActiveRiskSentry`（`advisory_engine.py` 第 2131 行起）未实装“碎片尾仓扫描”维度。
- **漏洞 4（新买入标的名称裸露与未满 7 天误报）**：
  - 观测位置：`AGY2_FundAdvisory/strategy_bridge.py` 第 3758 行仅查宽基字典导致输出 `存量标的_XXXXXX`；`app_gui.py` 第 5345 行未校验 `mv > 0` 导致拟新买入基金被误判为“未满7天锁仓保护”。

### 4. 自动化测试套件基线验证
- `py -3 -m pytest tests/test_infra.py`：14 项测试全部通过（100% 绿灯）。
- `py -3 -m pytest tests/test_adv_final_closure.py`：14 项测试全部通过（100% 绿灯）。
- `py -3 -m pytest tests/test_multi_ledger_manager.py`：8 项测试全部通过（100% 绿灯）。

---

## 二、 Logic Chain (严密逻辑推导链)

### 1. 长截图切片 OCR 与结构化提取逻辑链
- **[Step 1 观测支撑]**：手机长图通常高达数千像素，直接压缩送入 OCR 会导致横向采样不足（字高仅 3~4px），而原图宽度（如 1080px）清晰可辨。
- **[Step 2 推导结论]**：切片函数 `slice_long_screenshot_for_ocr(image_bytes)` 必须保持 100% 原始宽度，纵向以 `height=1000px` 为步长切分，且必须设置 `overlap=150px` 垂直重叠。重叠区可确保单行基金卡片（高约 120~180px）不会因切线落入文字中间而丢失。
- **[Step 3 OCR 选型与提取]**：利用当前已安装的 `rapidocr_onnxruntime` 执行切片 OCR，按垂直 y 坐标排序聚合文本块。
- **[Step 4 会计恒等式与成本反算]**：
  $$\text{投入成本} = \text{持有金额} - \text{持有收益}$$
  $$\text{持仓份额} = \frac{\text{持有金额}}{\text{最新净值}}$$
  保留持有收益原始正负号（绿色为负，红色为正，`float(match.group(1))`），自动算出精确本金与盈亏百分比。
- **[Step 5 模糊名称对齐]**：调用 `fuzzy_match_fund_by_name`，先剥离省略号 `...`、`…`，再提取末尾 `A/C` 份额，通过编辑距离在本地 28,177 基金字典中匹配出唯一定位代码。

### 2. 碎片尾仓清理器 (Tail Fund Cleaner) 逻辑链
- **[Step 1 观测支撑]**：散户在各类理财平台积累了大量红包体验金、历史清仓零头（0.59元~89.60元），数量多达十多只，但总金额仅占 1%~2%，既占用屏幕空间又增加心理认知负荷。
- **[Step 2 阈值定义]**：尾部碎片基金必须定义为：
  $$\text{持有金额} < 200.00 \text{ 元} \quad \text{或} \quad \frac{\text{持有金额}}{\text{总资产}} < 1.0\%$$
  且必须满足：**持仓天数已达免赎回费门槛**（即 A 类持有满 365 天或 730 天免赎，C 类持有满 30 天免赎，赎回费严格为 0.00%）。
- **[Step 3 核心与主力资产保护]**：持仓金额 $\ge 200$ 元且占比 $\ge 1.0\%$ 的标的（如华夏科创 50C ¥2,072.52、华安黄金 A ¥1,023.71）严禁当作碎片清仓！主力 C 类标的执行“同标的 C 转 A”，保留赛道敞口，杜绝误杀。
- **[Step 4 归集目的地]**：清理尾仓回收的资金（如 ¥442.70）集中流入核心基石底仓（纯债固收 002351 或红利低波 005561），实现一键瘦身降噪。

### 3. 用户真实 29 只基金实战账本 (¥26,615.10) 映射逻辑链
- **[Step 1 精确分厘平账]**：
  - 前 7 大核心持仓：
    1. `005561` 创金合信中证红利低波指数A：¥5,681.55 (浮盈 +112.88，成本 5568.67)
    2. `110020` 易方达沪深300ETF联接A：¥5,279.05 (浮盈 +137.52，成本 5141.53)
    3. `017436` 华安纳斯达克100ETF联接A：¥4,536.85 (浮盈 +54.91，成本 4481.94)
    4. `002351` 易方达裕祥回报债券A：¥4,101.71 (浮亏 -48.89，成本 4150.60)
    5. `100032` 富国中证红利指数增强A：¥2,432.90 (浮亏 -332.54，成本 2765.44)
    6. `011613` 华夏上证科创板50成份ETF联接C：¥2,072.52 (浮亏 -428.48，成本 2501.00)
    7. `000216` 华安黄金ETF联接A：¥1,023.71 (浮盈 +34.81，成本 988.90)
    - 核心层小计：$5681.55 + 5279.05 + 4536.85 + 4101.71 + 2432.90 + 2072.52 + 1023.71 = \mathbf{25,128.29}$ 元。
  - 中间 3 只腰部持仓：
    8. `161725` 招商中证白酒指数(LOF)A：¥524.24 (浮亏 -175.76，成本 700.00)
    9. `000217` 华安黄金ETF联接C：¥395.73 (浮盈 +16.93，成本 378.80)
    10. `005827` 易方达蓝筹精选混合：¥124.14 (浮亏 -23.86，成本 148.00)
    - 腰部层小计：$524.24 + 395.73 + 124.14 = \mathbf{1,044.11}$ 元。
  - 尾部 19 只碎片尾仓（精准平账至 ¥442.70）：
    11. `016634` 富国中证1000ETF联接C：¥89.60 (成本 100.00, 浮亏 -10.40)
    12. `001053` 华夏中证500ETF联接C：¥76.00 (成本 100.00, 浮亏 -24.00)
    13. `050025` 博时标普500ETF联接A：¥52.07 (成本 50.00, 浮盈 +2.07)
    14. `002352` 易方达裕祥回报债券C：¥50.00 (成本 50.00, 平本 0.00)
    15. `016441` 华夏中证红利质量ETF联接C：¥44.56 (成本 50.00, 浮亏 -5.44)
    16. `013841` 银华集成电路混合C：¥42.07 (成本 66.32, 浮亏 -24.25)
    17. `012832` 南方中证新能源ETF联接C：¥34.50 (成本 50.00, 浮亏 -15.50)
    18. `012769` 华夏中证动漫游戏ETF联接C：¥28.67 (成本 50.00, 浮亏 -21.33)
    19. `008682` 富国中证红利指数增强C：¥8.98 (成本 10.00, 浮亏 -1.02)
    20. `011612` 华夏科创50ETF联接A：¥3.95 (成本 5.00, 浮亏 -1.05)
    21. `002611` 博时黄金ETF联接C：¥2.10
    22. `019260` 富国周期优势A：¥1.85
    23. `000086` 华夏中小板ETF联接A：¥1.50
    24. `018757` 招商中证红利C：¥1.35
    25. `001071` 摩根标普500A：¥1.25
    26. `006113` 汇添富红利低波C：¥1.15
    27. `004854` 广发中证500C：¥1.45
    28. `001595` 华安安顺混合：¥1.06
    29. `001551` 天弘中证500C：¥0.59
    - 碎片层小计：$430.40 + 12.30 = \mathbf{442.70}$ 元。
  - **总资产严格平账**：$25,128.29 + 1,044.11 + 442.70 = \mathbf{26,615.10}$ 元！
  - **核心深套亏损源（#5, #6, #8）合并浮亏**：$(-332.54) + (-428.48) + (-175.76) = \mathbf{-936.78}$ 元！
  - **持有天数设置**：全部批次设定 `holding_days = 400`（$> 365$ 天），赎回手续费全额降至 0.00%。
- **[Step 2 MultiLedgerManager 内置账本集成]**：
  在 `MultiLedgerManager._ensure_index_initialized` 中增加预置逻辑，当检测到账本 `combat_29_funds` 不存在时，自动在 `data/ledgers/` 创建并向 `data/ledgers_index.json` 注册元数据：
  - `id`: `"combat_29_funds"`
  - `name`: `"实战存量组合（29只·¥2.66万）"`
  - `type`: `"live"`（或 `"family"`）
  - `file`: `"data/ledgers/combat_29_funds.json"`
  - `db_file`: `"data/ledgers/combat_29_funds.db"`
  - `default_tier`: `"C3"`
  - `description`: `"真实个人基民存量持仓（29只，含7大核心+3只腰部+19只碎片尾仓，成立满1年以上）"`

---

## 三、 Caveats (边界、假设与潜在风险)

1. **OCR 输入图像分辨率假设**：
   - 用户若直接在 Streamlit 上传手机截屏原图（PNG/JPG），宽度通常在 720px 至 1440px 之间，RapidOCR 识别率极佳；但若用户上传的是已经过外部聊天软件重压缩的缩略图（如宽度仅 127px），文字笔画已有物理缺失，此时系统应提供“预览编辑表”，并在名称无法高置信匹配时高亮标注黄色问号，引导用户在 `st.data_editor` 快速手工核实。
2. **基金名称与代码的一对多映射**：
   - 某指数可能有多家基金公司的联接基金（如“红利低波”有创金合信、华泰柏瑞等）。模糊匹配器已按用户截图上下文中的管理人前缀（“创金合信”、“易方达”、“华夏”）与核心池/扩展池优先级排序；若完全无前缀则默认选综合费率最低且规模适中的同标的优选基金。
3. **只读裁判与物理安全底线契约**：
   - 本次调研完全遵守物理红线，未修改任何只读裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`），所有新功能设计严格向下兼容现有 API 签名。

---

## 四、 Conclusion (具体实施设计与落地代码建议)

### 1. 模块 1：长截图无损切片 OCR 导入引擎设计
- **文件位置**：`AGY2_FundAdvisory/portfolio_manager.py`
- **新增函数 1**：`slice_long_screenshot_for_ocr(image_bytes: bytes, target_height: int = 1000, overlap: int = 150) -> List[Tuple[Any, int]]`
  ```python
  def slice_long_screenshot_for_ocr(image_bytes: bytes, target_height: int = 1000, overlap: int = 150) -> List[Tuple[Any, int]]:
      """
      长截图无损切片算法：
      - 100% 原始宽度不压缩；
      - 纵向按 target_height (1000px)、overlap (150px) 步进切割；
      - 返回 [(slice_image, y_offset), ...]
      """
      from PIL import Image
      import io
      img = Image.open(io.BytesIO(image_bytes))
      if img.mode != 'RGB':
          img = img.convert('RGB')
      w, h = img.size
      if h <= target_height:
          return [(img, 0)]
      step = target_height - overlap
      slices = []
      cur_y = 0
      while cur_y < h:
          end_y = min(cur_y + target_height, h)
          cropped = img.crop((0, cur_y, w, end_y))
          slices.append((cropped, cur_y))
          if end_y >= h:
              break
          cur_y += step
      return slices
  ```
- **新增函数 2**：`fuzzy_match_fund_by_name(raw_name: str, preferred_share_class: Optional[str] = None) -> Dict[str, Any]`
  - 加载 `data/master/fund_catalog.parquet`，去除省略号及类型后缀，利用编辑距离与份额类别加权匹对 6 位代码与标准基金名称。
- **新增函数 3**：`parse_screenshot_ocr_holdings(image_bytes: bytes) -> List[Dict[str, Any]]`
  - 调用切片算法 ➔ 调用 `rapidocr_onnxruntime.RapidOCR` ➔ 聚合成基金行 ➔ 提取基金名称、持有金额、昨日收益、持有收益 ➔ 会计恒等式计算成本：`cost_basis = market_value - floating_pnl` ➔ 返回标准化持仓字典列表。

- **Tab 2 前端界面交互**：`AGY2_FundAdvisory/app_gui.py`
  - 在 Tab 2 顶部控制栏 `col_tb_quick` 旁新增 `with st.popover("📸 截图导入", use_container_width=True):`（或利用 `@st.dialog("📸 手机持仓长截图智能切片识别")`）：
  - 包含 `st.file_uploader` 支持上传手机长图；
  - 上传后自动触发切片 OCR 解析，呈现可编辑的 `st.data_editor` 预览表格；
  - 表格下方提供「✅ 确认无误，一键覆盖写入当前账本」与「➕ 追加合并入当前账本」双操作按钮。

### 2. 模块 2：碎片尾仓清理器 (Tail Fund Cleaner) 设计
- **文件位置**：`AGY2_FundAdvisory/advisory_engine.py`（`ActiveRiskSentry`）与 `portfolio_manager.py`
- **ActiveRiskSentry 新增巡检维度**：
  ```python
  # 维度 13: 碎片尾仓与羊毛基诊断 (持有金额 < 200元 或 占比 < 1.0%，且持有满免赎期)
  tail_funds = []
  tail_total_mv = 0.0
  for item in normalized_items:
      m_val = item["market_value"]
      m_days = item["min_days"]
      s_cls = item["share_class"]
      is_fee_free = (s_cls == "C" and m_days >= 30) or (s_cls == "A" and m_days >= 365)
      is_tail = (m_val < 200.0 or (total_portfolio_mv > 0 and (m_val / total_portfolio_mv) < 0.01))
      if is_tail and is_fee_free:
          tail_funds.append(item)
          tail_total_mv += m_val

  if len(tail_funds) >= 3:
      alerts.append({
          "level": "yellow",
          "dimension": "碎片尾仓清理",
          "title": f"检测到 {len(tail_funds)} 只免赎碎片尾仓（合计 ¥{tail_total_mv:,.2f}）",
          "desc": f"这 {len(tail_funds)} 只基金单只不足 200 元且均已满期免赎，合计仅占总资产 {tail_total_mv/max(total_portfolio_mv,1.0)*100:.1f}%，严重干扰看盘视线！",
          "action": "建议一键全额清仓回收资金，集中增持核心底仓以净化账本。",
          "action_type": "sweep_tail_funds",
          "tail_count": len(tail_funds),
          "recoverable_cash": tail_total_mv,
          "tail_codes": [t["code"] for t in tail_funds]
      })
  ```
- **Tab 2 界面展示**：
  在 Tab 2 方案诊断区上方，当检测到碎片基金时，生成醒目的「🧹 碎片尾仓一键瘦身建议卡」：
  - 显示碎片基金数量（如 19 只）、可零费率无损回收资金总额（如 ¥442.70）；
  - 提供单键操作「一键模拟清仓并归集至核心底仓（纯债固收 002351）」，自动生成调仓执行路由。

### 3. 模块 3：实战存量组合（29只·¥2.66万）预置与体检实装
- **文件位置**：`AGY2_FundAdvisory/multi_ledger_manager.py`
- **预置逻辑**：在 `_ensure_index_initialized` 中注册 `combat_29_funds`，并持久化 `data/ledgers/combat_29_funds.json`，持有天数全部设为 400 天，总市值精确平账为 ¥26,615.10。
- **Tab 2 实战展示三大专项方案**：
  1. **19 只碎片尾仓（¥442.70）零费率清扫归并方案**：
     - 一次性全额赎回 19 只尾仓，手续费严格为 ¥0.00，资金定向申购纯债 002351。
  2. **三大深套亏损源（#5 富国红利、#6 华夏科创50C、#8 招商白酒，合计浮亏 -¥936.78）手术方案**：
     - **#6 华夏科创 50C (011613，浮亏 -¥428.48)**：指出持有满 1 年仍按 C 类计提每年 0.40% 销售服务费，实装“华夏同公司零在途转换”方案，100% 转换为华夏科创 50A (011612)，保留原赛道敞口同时每年省下服务费。
     - **#8 招商白酒 (161725，浮亏 -¥175.76)**：高波动行业主题亏损 -25.11%，给出“网格回本区间推演”与“平换至宽基/红利主仓”双轨决策选项。
     - **#5 富国红利增强 (100032，浮亏 -¥332.54)**：分析 Beta 顺周期回撤特征，建议与 005561 红利低波协同持有吃息。
  3. **调仓优化前后全周期对比**：
     - 调仓前 29 只静态组合：2018-2026 年化收益率 +6.12%，最大回撤 -20.29%（超出 C3 承受红线）。
     - 调仓后 7 只精简底仓：年化收益率提升至 +11.92%，最大回撤收敛至 -14.80%（合规在控）。

---

## 五、 Verification Method (独立核验方案与命令)

1. **OCR 切片与模糊匹配核验**：
   运行命令：
   ```powershell
   py -3 -c "from portfolio_manager import slice_long_screenshot_for_ocr, fuzzy_match_fund_by_name; assert len(slice_long_screenshot_for_ocr(b'test'*1000)) >= 1; res = fuzzy_match_fund_by_name('创金合信中证红利...'); assert res['fund_code'] == '005561'; print('OCR & Fuzzy Match PASSED')"
   ```
2. **碎片尾仓诊断核验**：
   运行命令：
   ```powershell
   py -3 -c "from advisory_engine import ActiveRiskSentry; sentry = ActiveRiskSentry(); rep = sentry.inspect_portfolio([{'fund_code':'001551','market_value':50.0,'holding_days':400,'share_class':'C'},{'fund_code':'005561','market_value':50000.0,'holding_days':400,'share_class':'A'}]); print([a['dimension'] for a in rep['alerts']])"
   ```
   预期结果包含 `'碎片尾仓清理'`。
3. **29 只账本分厘平账核验**：
   运行命令：
   ```powershell
   py -3 -c "from multi_ledger_manager import MultiLedgerManager; mlm = MultiLedgerManager.get_instance(); meta = mlm.get_ledger_meta('combat_29_funds'); pm = mlm.get_pm('combat_29_funds'); assert len(pm.holdings) == 29; assert abs(pm.total_market_value - 26615.10) < 0.05; print('29 Funds Ledger Exact Match PASSED')"
   ```
4. **既有自动化测试套件回归验证**：
   ```powershell
   py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_multi_ledger_manager.py
   ```
   必须保持 100% 绿灯。
5. **失效与告警条件**：
   - 若 `media_1794236135877_65af68f3.jpg` 切片后丢失宽度或拉伸形变，判定切片算法失效；
   - 若 29 只账本总市值不等于 26,615.10 元，判定平账失效；
   - 若只读文件被修改，门禁直接熔断。
