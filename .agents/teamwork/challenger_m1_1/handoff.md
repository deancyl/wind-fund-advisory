# Handoff Report: Milestone 1 Adversarial Challenge

**Agent**: Challenger M1-1 (Data Freshness, Latency & Fallback Stress Challenger)  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1`  
**Milestone**: M1 (Features 1-5 per `PROJECT.md` & `ORIGINAL_REQUEST.md`)  
**Verdict**: **REQUEST_CHANGES**  
**Timestamp**: 2026-11-04T10:31:00Z  

---

## 1. Observation

### 1.1 Baseline Referee Files & Physical Safety Redline
- **Referee SHA-256 Check**:
  Command executed: `powershell -Command "Get-FileHash tests/test_infra.py, AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, AGY2_FundAdvisory/tests/test_infra.py -Algorithm SHA256 | Format-Table -AutoSize"`
  Result:
  ```
  Algorithm Hash                                                             Path
  --------- ----                                                             ----
  SHA256    48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100 D:\Google\Workspace\Wind\tests\test_infra.py
  SHA256    76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py
  SHA256    88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py
  SHA256    A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957 D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md
  SHA256    B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py
  ```
  `git status --porcelain` showed 0 modifications on referee files. Physical safety redlines are 100% intact.

---

### 1.2 Adversarial Latency Benchmark: Finding on `FundPurchaseCacheManager`
Command executed: `py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py -v -s`

Verbatim benchmark log:
```
[Benchmark] FundPurchaseCacheManager Cold Start: Avg=113.49ms, Max=146.98ms, P95=132.44ms
FAILED
[Benchmark] FundPurchaseCacheManager Warm Query: 2.09 µs/query
PASSED
[Benchmark] FundMetadataManager Cached Read: Avg=0.19ms, Max=0.33ms, P99=0.33ms
PASSED
[Benchmark] FundMetadataManager Master Fallback: 8.25ms
PASSED
```

Verbatim failure traceback:
```python
___________________ TestColdStartAndLatencyBenchmarks.test_fund_purchase_cache_cold_start_under_50ms ___________________
    def test_fund_purchase_cache_cold_start_under_50ms(self):
        ...
        print(f"\n[Benchmark] FundPurchaseCacheManager Cold Start: Avg={avg_ms:.2f}ms, Max={max_ms:.2f}ms, P95={p95_ms:.2f}ms")
>       assert max_ms < 50.0, f"Cold start max time {max_ms:.2f}ms exceeded 50ms strict bound!"
E       AssertionError: Cold start max time 146.98ms exceeded 50ms strict bound!
E       assert np.float64(146.98190003400669) < 50.0

AGY2_FundAdvisory\tests\test_challenger_m1_adversarial.py:93: AssertionError
```

Code inspection of root cause in `AGY2_FundAdvisory/cache_manager.py`:
- Lines 476-491 in `FundPurchaseCacheManager._update_memory_cache`:
  ```python
  res_dict = {}
  for row in df.itertuples(index=False):
      code = getattr(row, "基金代码")
      p_st = getattr(row, "申购状态")
      r_st = getattr(row, "赎回状态")
      d_lim = float(getattr(row, "日累计限定金额"))
      is_limited = ("暂停" in p_st) or ("限" in p_st) or (d_lim < 1e8)
      norm_status = "暂停申购" if ("暂停" in p_st or "封闭" in p_st or d_lim <= 0) else ("限制大额" if (d_lim < 1e8 or "限" in p_st) else "开放申购")
      res_dict[code] = {
          "fund_code": code,
          "status": norm_status,
          "daily_limit": d_lim if norm_status != "暂停申购" else (d_lim if d_lim > 0 else 0.0),
          "is_limited": is_limited,
          "redemption_status": r_st
      }
  cls._MEMORY_DICT = res_dict
  ```
- `data/cache/fund_purchase.parquet` contains **27,964 rows**.
- `pd.read_parquet` took only ~5.09ms, but the pure Python `for row in df.itertuples(index=False):` with `getattr` and dictionary creations across 27,964 rows takes ~100-140ms.
- As a result, the cold-start call `FundPurchaseCacheManager.get_fund_quota("050025")` took **113.49ms (average)** and **146.98ms (maximum)**, directly failing the `< 50ms` requirement in `DISPATCH.md`.

---

### 1.3 Adversarial Network Disconnection & Fault Injection Verification
All 9 network fault injection test cases PASSED:
1. **EastMoney push2 Endpoint Mock Failures**:
   - `urllib.error.URLError` (DNS / Network unreachability) -> PASSED (Gracefully falls back to `data/cache/market_breadth.json`, returns valid dictionary, 0 crashes).
   - `TimeoutError` (Socket / Connection timeout) -> PASSED.
   - `ConnectionRefusedError` -> PASSED.
   - `urllib.error.HTTPError(502 Bad Gateway)` -> PASSED.
2. **EastMoney Push2 Failure With Cache Missing**:
   - Simulated network offline + missing cache file -> PASSED (Returns neutral safe structure: `turnover_str="-- 亿"`, `up_pct=50.0`, `sentiment_label="数据同步中"`, `source="cold_start_unready"` with 0 exceptions).
3. **EastMoney Push2 Corrupt & Empty Response**:
   - Malformed JSON `b"{malformed json content"` -> PASSED (Safely caught, falls back to disk cache).
   - Empty diff list `{"data": {"diff": []}}` -> PASSED (Safely handled without `IndexError`).
4. **AkShare & IndexValuationEngine Offline Simulation**:
   - `akshare.stock_index_pe_lg` and `stock_zh_index_value_csindex` mocked to raise Exception -> PASSED (IndexValuationEngine falls back to DuckDB `v_index_valuations` and local parquets, all 6 core indices returned).
   - AkShare failure AND DuckDB failure simultaneously -> PASSED (IndexValuationEngine falls back to historical baseline values, returning valid PE labels).
   - Dual-key indexing (`000300` and `1.000300`) verified intact.

---

### 1.4 Code Scan: Purge of Fake Constants and Dictionaries
- **`INDEX_PE_METAS` Scan**:
  - Ripgrep search across workspace revealed 0 instances of `INDEX_PE_METAS` in any Python source file (only present in `PROJECT.md` documentation and test assertions).
- **`3210` / `1780` Scan**:
  - Ripgrep and AST parsing confirmed 0 instances of `3210` or `1780` in `AGY2_FundAdvisory/data_loader.py` and `AGY2_FundAdvisory/app_gui.py`.
  - The only occurrences in the workspace are in `chips_market.py` (Kweichow Moutai stock price `1780.00`) and `money_flow.py` (sector index `3210.8`), which are completely unrelated to market breadth or turnover.
- **AST Parsing of `fetch_market_turnover_and_sentiment`**:
  - `ast.walk` verified that no `ast.Constant` node in `fetch_market_turnover_and_sentiment` contains `3210` or `1780`.

---

## 2. Logic Chain

1. **Premise 1 (Contract Requirement)**:
   Per `DISPATCH.md` item 1: "Write a stress script or test to measure `FundPurchaseCacheManager.get_fund_quota` cold start time. Is it strictly < 50ms?"
2. **Premise 2 (Empirical Measurement)**:
   In `test_challenger_m1_adversarial.py`, resetting memory cache (`FundPurchaseCacheManager._MEMORY_DICT = None`) and calling `get_fund_quota("050025")` across 10 independent trials yielded:
   - Average cold start time: **113.49ms**
   - Maximum cold start time: **146.98ms**
   - 95th percentile: **132.44ms**
3. **Premise 3 (Worker Test Gap)**:
   Worker Prod M1 in `test_m1_open_data_and_cache.py` line 101 only benchmarked `pd.read_parquet(FUND_PURCHASE_CACHE_PATH)` (which took 5.09ms), but did not benchmark `get_fund_quota` cold start. The bottleneck is the 27,964-row `itertuples` loop in `_update_memory_cache` in `cache_manager.py:476-491`.
4. **Deductive Conclusion**:
   Because 113.49ms > 50.0ms, the implementation does not satisfy the `< 50ms` cold-start SLA for `get_fund_quota`. Changes are required.

---

## 3. Caveats

- **Warm Performance**: Once warm, `FundPurchaseCacheManager.get_fund_quota` performs at 2.09 µs per query, which is exceptionally fast.
- **Parquet Read Speed**: The Parquet file itself loads in 5.09ms, confirming the disk format is well-optimized; the sole bottleneck is the in-memory dictionary transformation in pure Python.
- **Features 1, 2, 4, 5**: Features 1 (EastMoney real market breadth), 2 (IndexValuationEngine), 4 (FundMetadataManager 24h TTL cache & liquidation risk), and 5 (MarketScreener candidate pool restore) passed all adversarial challenge tests without issues.

---

## 4. Conclusion

- **Verdict**: **REQUEST_CHANGES**
- **Action Required for Worker Prod M1**:
  Optimize `FundPurchaseCacheManager._update_memory_cache` in `AGY2_FundAdvisory/cache_manager.py` to eliminate the slow `itertuples` loop over 27,964 rows so that cold start time of `FundPurchaseCacheManager.get_fund_quota` is strictly `< 50ms`.
  *Recommended Solution*:
  Instead of iterating 27,964 rows with Python `itertuples`, keep `_MEMORY_DF` indexed by `基金代码` (`df.set_index("基金代码", inplace=True)` takes ~1.0ms), and perform lazy on-demand lookup or vectorize dictionary generation (e.g. `to_dict('index')` or vectorized column operations).

---

## 5. Verification Method

To reproduce and verify the finding:
1. Run the empirical adversarial challenger test suite:
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py -v -s
   ```
2. Invalidation Condition:
   Once `_update_memory_cache` is optimized, `test_fund_purchase_cache_cold_start_under_50ms` will report `max_ms < 50.0` and PASS, allowing the verdict to transition to APPROVE.
