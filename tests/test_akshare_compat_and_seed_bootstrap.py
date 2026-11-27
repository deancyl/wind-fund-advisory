# -*- coding: utf-8 -*-
"""
回归测试：AkShare 1.18~1.20.70+ 双版本兼容层、Docker 空挂载卷种子自举、
无私有中间 Parquet 矩阵重建、HEAD / 与 /api/v1/overview 容灾降级。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
AGY_DIR = ROOT / "AGY2_FundAdvisory"
if str(AGY_DIR) not in sys.path:
    sys.path.insert(0, str(AGY_DIR))

import akshare_compat
import runtime_paths


class _StrictAkShare12070:
    """模拟 AkShare 1.20.70：访问 7 个旧名直接抛 AttributeError，仅暴露新版接口。"""

    __version__ = "1.20.70"
    _REMOVED_OLD = {
        "stock_zh_index_hist_csindex": "index_hist_csindex",
        "stock_zh_index_value_csindex": "index_value_csindex",
        "stock_zh_index_daily_em": "index_zh_daily_em",
        "stock_zh_index_spot_em": "index_zh_spot_em",
        "tool_trade_date_hist_sina": "calendar_trade_date_hist_sina",
        "bond_zh_us_rate": "bond_zh_us_yield_em",
        "fund_open_fund_daily_em": "fund_open_nav_em",
    }

    def __getattr__(self, name: str):
        if name in self._REMOVED_OLD:
            raise AttributeError(
                f"{name} 已在 1.20.44 更名为 {self._REMOVED_OLD[name]}，请改用 ak.{self._REMOVED_OLD[name]}"
            )
        raise AttributeError(name)

    def index_hist_csindex(self, symbol: str = "H00300", start_date: str = "20240101", end_date: str = "20240110"):
        return pd.DataFrame({"日期": ["2024-01-02", "2024-01-03"], "收盘": [4000.0, 4020.0], "symbol": [symbol, symbol]})

    def index_value_csindex(self, symbol: str = "000922"):
        return pd.DataFrame({"日期": ["2024-01-02"], "市盈率1": [7.5], "symbol": [symbol]})

    def index_zh_daily_em(self, symbol: str = "sh000688", start_date: str = "20240101", end_date: str = "20240110"):
        return pd.DataFrame({"date": ["2024-01-02", "2024-01-03"], "close": [850.0, 860.0]})

    def index_zh_spot_em(self, symbol: str = "沪深重要指数"):
        return pd.DataFrame({"代码": ["000300"], "名称": ["沪深300"], "涨跌幅": [0.5], "symbol": [symbol]})

    def calendar_trade_date_hist_sina(self):
        return pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03"]})

    def bond_zh_us_yield_em(self, start_date: str = "19901219"):
        return pd.DataFrame({"日期": ["2024-01-02"], "中国国债收益率10年": [2.5], "美国国债收益率10年": [4.0]})

    def fund_open_fund_info_em(self, symbol: str = "002351", indicator: str = "单位净值走势"):
        return pd.DataFrame({"净值日期": ["2023-12-29", "2024-01-02", "2024-01-03"], "单位净值": [1.50, 1.51, 1.52]})


class _StrictAkShare11864:
    """模拟 AkShare 1.18.64：仅暴露旧版接口名 + fund_open_fund_info_em。"""

    __version__ = "1.18.64"

    def stock_zh_index_hist_csindex(self, symbol: str = "H00300", start_date: str = "20240101", end_date: str = "20240110"):
        return pd.DataFrame({"日期": ["2024-01-02"], "收盘": [4000.0]})

    def stock_zh_index_value_csindex(self, symbol: str = "000922"):
        return pd.DataFrame({"日期": ["2024-01-02"], "市盈率1": [7.2]})

    def stock_zh_index_daily_em(self, symbol: str = "sh000688", start_date: str = "20240101", end_date: str = "20240110"):
        return pd.DataFrame({"date": ["2024-01-02"], "close": [850.0]})

    def stock_zh_index_spot_em(self, symbol: str = "上证系列指数"):
        return pd.DataFrame({"代码": ["000300"], "涨跌幅": [0.4]})

    def tool_trade_date_hist_sina(self):
        return pd.DataFrame({"trade_date": ["2024-01-02"]})

    def bond_zh_us_rate(self, start_date: str = "19901219"):
        return pd.DataFrame({"日期": ["2024-01-02"], "中国国债收益率10年": [2.5]})

    def fund_open_fund_info_em(self, symbol: str = "002351", indicator: str = "单位净值走势"):
        return pd.DataFrame({"净值日期": ["2024-01-02", "2024-01-03"], "单位净值": [1.51, 1.52]})


def test_no_direct_legacy_akshare_calls_outside_compat():
    """静态门禁：禁止 AGY2_FundAdvisory 内（除 akshare_compat.py 外）直接调用 7 个在 1.20.41~45 废弃的旧接口。"""
    legacy_pat = re.compile(
        r"\bak\.(stock_zh_index_hist_csindex|stock_zh_index_value_csindex|stock_zh_index_daily_em"
        r"|stock_zh_index_spot_em|tool_trade_date_hist_sina|bond_zh_us_rate|fund_open_fund_daily_em)\b"
    )
    offenders = []
    for pyf in sorted(AGY_DIR.glob("*.py")):
        if pyf.name == "akshare_compat.py":
            continue
        text = pyf.read_text(encoding="utf-8", errors="ignore")
        for m in legacy_pat.finditer(text):
            offenders.append(f"{pyf.name}:{m.group(0)}")
    assert offenders == [], f"发现未走 akshare_compat 的旧版 AkShare 调用: {offenders}"


@pytest.mark.parametrize("fake_ak", [_StrictAkShare12070(), _StrictAkShare11864()])
def test_akshare_compat_works_on_both_118_and_12070(fake_ak):
    assert not akshare_compat.index_hist_csindex("H00300", "20240101", "20240110", ak_module=fake_ak).empty
    assert not akshare_compat.index_value_csindex("000922", ak_module=fake_ak).empty
    assert not akshare_compat.index_daily_em("sh000688", "20240101", "20240110", ak_module=fake_ak).empty
    df_spot = akshare_compat.index_spot_em("沪深重要指数", ak_module=fake_ak)
    assert "000300" in set(df_spot["代码"].astype(str))
    assert not akshare_compat.trade_date_hist_sina(ak_module=fake_ak).empty
    assert not akshare_compat.bond_zh_us_yield(ak_module=fake_ak).empty
    df_nav = akshare_compat.open_fund_nav_history("002351", start_date="2024-01-02", ak_module=fake_ak)
    assert len(df_nav) == 2
    assert str(df_nav["净值日期"].iloc[0]) == "2024-01-02"


def test_seed_bootstrap_on_empty_docker_data_volume(tmp_path, monkeypatch):
    """模拟 Docker 挂载空白 ./data:/app/data 且镜像内置 AGY2_SEED_DIR=/app/seed_data，验证 7 个种子自动补齐且不碰用户账本。"""
    empty_data = tmp_path / "mounted_empty_data"
    (empty_data / "ledgers").mkdir(parents=True, exist_ok=True)
    user_ledger = empty_data / "ledgers" / "my_private.json"
    user_ledger.write_text(json.dumps({"owner": "private_user", "cash": 12345}), encoding="utf-8")

    monkeypatch.setenv("AGY2_DATA_DIR", str(empty_data))
    monkeypatch.setenv("AGY2_SEED_DIR", str(ROOT / "data"))

    report1 = runtime_paths.bootstrap_public_seeds()
    assert len(report1["copied"]) == len(runtime_paths.PUBLIC_SEED_FILES)
    assert report1["missing_sources"] == []
    # 用户私密账本原封不动
    assert json.loads(user_ledger.read_text(encoding="utf-8"))["cash"] == 12345

    # 幂等性验证：二次调用零复制
    report2 = runtime_paths.bootstrap_public_seeds()
    assert report2["copied"] == []
    assert len(report2["skipped_existing"]) == len(runtime_paths.PUBLIC_SEED_FILES)

    # market_lakehouse 应动态读取新自举的湖仓数据，不再返回 0 只
    import market_lakehouse

    st = market_lakehouse.get_lakehouse_status()
    assert st.get("status") == "ready"
    assert int(st.get("elite_fund_count", 0)) >= 200
    nav_df, meta_df, _ = market_lakehouse.load_elite_lakehouse()
    assert nav_df is not None and len(nav_df.columns) >= 200
    assert meta_df is not None and len(meta_df) >= 200


def test_build_matrix_from_source_without_private_intermediate_parquets(tmp_path, monkeypatch):
    """极端场景：空数据目录 + 无种子 + 无 5 个私有中间 Parquet，验证 _build_matrix_from_source 用公开 AkShare 顺利重建矩阵。"""
    bare_dir = tmp_path / "bare_data"
    bare_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGY2_DATA_DIR", str(bare_dir))
    monkeypatch.delenv("AGY2_SEED_DIR", raising=False)

    # 让 resolve_data_file 仅看 bare_dir（彻底屏蔽真实仓库 data/，模拟彻底空卷）
    monkeypatch.setattr(runtime_paths, "resolve_data_file", lambda fn: bare_dir / str(fn).replace("\\", "/").lstrip("/").removeprefix("data/"))

    dates = pd.bdate_range("2024-01-02", "2024-03-29")
    n = len(dates)
    d_str = [d.strftime("%Y-%m-%d") for d in dates]

    monkeypatch.setattr(
        akshare_compat,
        "index_hist_csindex",
        lambda symbol, start_date="20240101", end_date="20240331", ak_module=None: pd.DataFrame(
            {"日期": d_str, "收盘": np.linspace(1000.0, 1050.0, n)}
        ),
    )
    monkeypatch.setattr(
        akshare_compat,
        "index_daily_em",
        lambda symbol, start_date=None, end_date=None, ak_module=None: pd.DataFrame(
            {"date": d_str, "close": np.linspace(800.0, 880.0, n) if "688" in symbol else np.linspace(1800.0, 1900.0, n)}
        ),
    )
    monkeypatch.setattr(
        akshare_compat,
        "spot_hist_sge",
        lambda symbol="Au99.99", ak_module=None: pd.DataFrame({"date": d_str, "close": np.linspace(480.0, 520.0, n)}),
    )
    monkeypatch.setattr(
        akshare_compat,
        "etf_hist_em",
        lambda symbol="513500", start_date="20240101", end_date="20240331", adjust="qfq", ak_module=None: pd.DataFrame(
            {"日期": d_str, "收盘": np.linspace(1.50, 1.65, n)}
        ),
    )

    from data_loader import DataLoader

    out_pq = bare_dir / "processed" / "aligned_matrix_total_return.parquet"
    dl = DataLoader(cache_file=out_pq)
    df = dl._build_matrix_from_source(start_date="2024-01-02", end_date="2024-03-29")

    required_cols = {
        "date", "H00300", "H00905", "H00852", "H00922", "H30269",
        "930609", "H11009", "STAR50_STITCH", "AU9999", "SPX_CNY",
        "BENCHMARK_30_70", "BENCHMARK_50_50",
    }
    assert required_cols.issubset(set(df.columns))
    assert len(df) >= 55
    for col in required_cols - {"date"}:
        assert df[col].isna().sum() == 0, f"列 {col} 存在 NaN"
        assert (df[col] > 0).all(), f"列 {col} 存在非正值"
    assert out_pq.exists()


def test_api_head_root_and_overview_graceful_degradation(monkeypatch):
    """验证 HEAD / 返回 200（零 405 日志刷屏），且极端异常时 /api/v1/overview 优雅降级为 200 DEGRADED。"""
    import api_server
    from fastapi.testclient import TestClient

    client = TestClient(api_server.app)
    r_head = client.head("/")
    assert r_head.status_code == 200

    # 模拟极端断网+无基线快照异常
    monkeypatch.setattr(
        api_server.StrategyBridge,
        "get_latest_market_snapshot",
        classmethod(lambda cls, **kwargs: (_ for _ in ()).throw(RuntimeError("simulated missing baseline"))),
    )
    r_ov = client.get("/api/v1/overview?force=true")
    assert r_ov.status_code == 200
    body = r_ov.json()
    assert body["market_verdict"]["regime"] == "DEGRADED"
    assert body["market_verdict"]["degraded"] is True
    assert "simulated missing baseline" in body["market_verdict"]["detail_explanation"]
    assert "sh000300" in body["indices"]
