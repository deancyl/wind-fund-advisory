# Review Report — Milestone 1 (Features 4, 5, 6)

- **Reviewer**: Reviewer R8-M1-2 (reviewer, critic)
- **Target**: Milestone 1 (Features 4, 5, 6: EXPANDED_INDEX_CATALOG, 侧边栏设置弹窗, Watchlist持久化, UI细节修复)
- **Date**: 2026-11-05T02:18:30Z
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_r8_m1_2\`

---

## Review Summary

**Verdict**: **APPROVE**

经过对 `AGY2_FundAdvisory/data_loader.py`、`AGY2_FundAdvisory/app_gui.py`、`data/cache/custom_watchlist.json` 以及关联回归与压力测试套件的独立审查、代码断言、实测验证及对抗性压力测试，确认 Milestone 1 所有核心要求已高标准达成，4 项只读裁判文件 SHA256 哈希 100% 完好无损，无任何作弊或虚假实现（Zero Integrity Violation）。

---

## 1. Quality & Conformance Review

### 1.1 EXPANDED_INDEX_CATALOG 真实性与 Rule 16 红线审查
- **目录规模与板块覆盖**：
  - `EXPANDED_INDEX_CATALOG` 共收录 40 只指数/ETF（超过要求的 38+ 标的）。
  - 覆盖宽基核心、红利高股息、科技精选、医药生物、消费核心、金融大盘、绿色能源、国防军工、周期资源、港股海外、美股跨境、大宗商品、债券固收、现金管理等 14 大细分板块（超过要求的 12 板块）。
  - 字典字段完备度 100%：所有标的均包含 `code`, `name`, `secid`, `sym`, `pinyin`, `sector`, `asset_type`, `fb_point`, `fb_chg`，无缺失键。
- **Rule 16 红线绝对遵从（中证红利 vs 上证红利）**：
  - `000922` 严格映射为“中证红利”（`secid: 1.000922`，回退基准点位 5518.95），盘中与离线实测点位处于 5400~5600 正常区间；
  - `000015` 独立映射为“上证红利”（`secid: 1.000015`，点位 3248.31）；
  - 全站代码全局扫描确认：零将 000015 偷换或映射为中证红利的现象，符合 Rule 16 Invariant。

### 1.2 侧边栏设置 Popover 弹窗交互审查
- **3~15 只展示数量滑块**：
  - `st.slider("走廊展示数量", min_value=3, max_value=15, value=cur_limit, step=1)`，初始值绑定 `st.session_state.sb_corridor_display_limit`；
  - 滑块数值变动时，实时触发持久化落盘并驱动卡片列表切片 `[:display_limit]`。
- **三模检索与排序保持**：
  - `_fmt_option` 格式化为 `f"{sec_tag}{c_name} ({k}) [{pinyin_str}]"`，完整支持拼音缩写（如 `zzhl`）、代码（`000922`）与中文名称多模检索；
  - `avail_options` 构建时优先将当前选中的 `sb_selected_corridor_indices` 保持在前，杜绝排序乱序或乱跳。
- **任意 6 位代码验证与接入**：
  - 前端输入框 `st.text_input` 设 `max_chars=6`，前端校验 `len(clean_code) == 6 and clean_code.isdigit()`；
  - 后端接入 `validate_and_fetch_code(clean_code)` 实施东财 Push2 实时接口探测，失败自动回退本地 DuckDB `v_etfs`；
  - 校验成功后通过 `insert(0, clean_code)` 置顶自选走廊并自动持久化，调用 `st.rerun()` 即时刷新。

### 1.3 自选配置持久化与冷启动防御 (`custom_watchlist.json`)
- **冷启动自愈**：
  - 当 `data/cache/custom_watchlist.json` 不存在时，`load_custom_watchlist()` 自动生成默认 6 只核心指数（含 000922 中证红利）并落盘，返回有效字典；
  - 当文件内容损坏（非法 JSON）时，使用 `try...except` 优雅降级返回默认结构，杜绝崩溃白屏。
- **双向兼容性映射**：
  - 自动对齐 `selected_codes` ↔ `selected_symbols` 与 `display_limit` ↔ `display_count`，保障老版本或外部调用数据兼容。
- **原子级防损写入**：
  - `save_custom_watchlist()` 采用临时文件写入 + `replace()` 原子重命名机制，彻底杜绝并发写半截文件损坏风险。

### 1.4 UI 细节修复审查
- **Primary 按钮白色文字穿透**：
  - CSS 声明为：
    ```css
    button[kind="primary"],
    button[kind="primary"] *,
    button[kind="primary"] p,
    button[kind="primary"] span {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    ```
    所有子元素及段落/文字节点均强制 `#ffffff !important`，深色与浅色模式下对比度清晰。
- **Tab 1 步骤一文案去重**：
  - 在卡片区以 `safe_markdown_html` 统一呈现【定权模型、资产锚点、权益中枢、回撤上限】四合一紧凑卡片；
  - 移除下方 caption 中重复出现的“资产锚点”和“权益上限”字符串，保留收益预期与投资画像提示，同屏文本零重复。

---

## 2. Adversarial & Edge-Case Findings

### [Minor] Finding 1: `validate_and_fetch_code` 对短数字字符串的 `zfill(6)` 自动补零机制
- **What**: 在 `data_loader.py` 中，`validate_and_fetch_code` 内部采用 `c = str(code_str).strip().zfill(6)`。若直接传入少于 6 位的纯数字（例如 `"123"`），会被自动左侧补零为 `"000123"`。
- **Where**: `AGY2_FundAdvisory/data_loader.py:1231`
- **Assessment**:
  - 在前端 GUI 中，`app_gui.py:1462` 拥有显式的门禁校验：`if len(clean_code) == 6 and clean_code.isdigit():`，因此在界面交互层面用户无法直接提交少于 6 位的代码，不会产生非预期行为。
  - 在金融终端（如 Wind/同花顺）中，输入短代码自动补零（如 16 -> 000016）属于普遍存在的容错设计。
- **Suggestion**: 行为安全，无需修改；在文档或接口注释中注明该补零行为即可。

### [Informational] Finding 2: 并发写缓存安全防御
- **What**: 多进程或热重载时若同时写入 `custom_watchlist.json`，是否可能出现文件写锁竞争？
- **Where**: `AGY2_FundAdvisory/data_loader.py:1216-1219`
- **Verification**: `save_custom_watchlist` 使用了 `tmp_file.replace(CUSTOM_WATCHLIST_FILE)`，在 Windows NTFS 文件系统下 `Path.replace()` 具备原子替换属性，有效抵御了写半截损坏。

---

## 3. Verified Claims

1. **裁判文件哈希基线完好**：
   - 运行 `py -3 scripts/verify_referee_hashes.py` -> **PASS (4/4 完好无损)**。
2. **Milestone 1 核心与回归测试全绿**：
   - 运行 `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py` -> **PASS (6 passed)**。
   - 运行 `py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py tests/test_infra.py` -> **PASS (38 passed)**。
3. **独立对抗脚本全面通过**：
   - 运行 `py -3 scripts/verify_m1_reviewer_r8_m1_2.py` -> **PASS (All 5 Test Suites Passed)**。
4. **实时行情与离线收盘点位真实验收**：
   - 000922 中证红利实时点位为 5495.89，涨跌幅 -1.70%，MA20 为 5418.11，偏离 +1.44%，点位符合 5000~6500 区间，无 0.00% 假平盘。

---

## 4. Coverage Gaps

- **外部行情接口断网场景**：已通过 Mock 抛出 `URLError` / `TimeoutError` 进行离线回退验证，测试套件已完整覆盖本地 Parquet 与 DuckDB 双轨回退路径。
- 无未探索的高风险代码盲区。

---

## 5. Unverified Items

- 无未验证项。所有需求均已完成独立实操与自动化代码核验。
