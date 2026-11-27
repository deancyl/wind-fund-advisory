# -*- coding: utf-8 -*-
"""
AGY2 每日公共市场数据包构建器 (scripts/build_daily_public_bundle.py)
==================================================================
供 GitHub Actions (`daily-market-data.yml`) 与本地一键演练使用：
  1. （非 --skip-network 模式）刷新全市场场外申购/限购规则表（保留原费率与基金类型列），
     执行湖仓原位清洗（清零锁定期/场内基/假海外）与东财批量增量日更；
  2. 严格按 PUBLIC_BUNDLE_WHITELIST（6 个 100% 纯公开市场文件，零用户隐私）打包：
     - `agy2-market-bundle-latest.tar.gz`（桌面/Python 端）
  3. 同步产出 Phase 4 纯本地轻内核二进制契约包：
     - `agy2-mobile-compact-v1.tar.gz`（`nav_f32.bin` little-endian float32 + `bundle_meta.json`）
  4. 生成含 SHA256 校验码与最新交易日的 `manifest.json`。
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
for p in (str(AGY2_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import runtime_paths
from remote_bundle_sync import (
    DEFAULT_BUNDLE_FILENAME,
    DEFAULT_MANIFEST_FILENAME,
    PUBLIC_BUNDLE_WHITELIST,
    compute_file_sha256,
)

MOBILE_COMPACT_FILENAME = "agy2-mobile-compact-v1.tar.gz"


def _safe_num(val: Any, default: float = 0.0) -> float:
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _refresh_trading_rules_preserving_fees(data_dir: Path) -> Dict[str, Any]:
    """
    联网刷新 fund_trading_rules.parquet，同时严格保留既有的 est_management_fee /
    est_custodian_fee / est_sales_service_fee / est_total_operating_fee 与 fund_type 列。
    """
    rules_path = data_dir / "master" / "fund_trading_rules.parquet"
    if not rules_path.exists():
        return {"status": "missing_existing_rules"}

    try:
        import akshare_compat

        df_old = pd.read_parquet(rules_path)
        df_new = akshare_compat.fund_purchase_em()
        if df_new is None or df_new.empty:
            return {"status": "upstream_empty_kept_existing"}

        col_map = {
            "基金代码": "symbol",
            "基金简称": "fund_name",
            "基金类型": "fund_type",
            "最新净值/万份收益": "nav",
            "申购状态": "purchase_status",
            "赎回状态": "redemption_status",
            "购买起点": "min_purchase_amount",
            "日累计限定金额": "daily_limit_amount",
            "手续费": "discount_purchase_fee_pct",
            "下一开放日": "next_open_date",
        }
        renamed = df_new.rename(columns={k: v for k, v in col_map.items() if k in df_new.columns}).copy()
        if "symbol" not in renamed.columns or "purchase_status" not in renamed.columns:
            return {"status": "unexpected_schema_kept_existing"}

        renamed["symbol"] = renamed["symbol"].astype(str).str.strip().str.zfill(6)
        renamed = renamed.drop_duplicates(subset=["symbol"], keep="first")

        # 合并保留既有费率与类型字段
        preserve_cols = [
            c for c in (
                "symbol",
                "wind_code",
                "fund_type",
                "est_management_fee",
                "est_custodian_fee",
                "est_sales_service_fee",
                "est_total_operating_fee",
            )
            if c in df_old.columns
        ]
        old_keep = df_old[preserve_cols].copy()
        old_keep["symbol"] = old_keep["symbol"].astype(str).str.strip().str.zfill(6)
        old_keep = old_keep.drop_duplicates(subset=["symbol"], keep="first")

        merged = renamed.merge(old_keep, on="symbol", how="left", suffixes=("", "_old"))
        if "fund_type_old" in merged.columns:
            if "fund_type" in merged.columns:
                merged["fund_type"] = merged["fund_type"].fillna(merged["fund_type_old"])
            else:
                merged["fund_type"] = merged["fund_type_old"]
            merged.drop(columns=["fund_type_old"], inplace=True)

        if "wind_code" not in merged.columns:
            merged["wind_code"] = merged["symbol"] + ".OF"
        else:
            merged["wind_code"] = merged["wind_code"].fillna(merged["symbol"] + ".OF")

        merged["daily_limit_amount"] = pd.to_numeric(merged.get("daily_limit_amount"), errors="coerce").fillna(1e10)
        merged["min_purchase_amount"] = pd.to_numeric(merged.get("min_purchase_amount"), errors="coerce").fillna(10.0)
        merged["nav"] = pd.to_numeric(merged.get("nav"), errors="coerce")
        merged["discount_purchase_fee_pct"] = pd.to_numeric(merged.get("discount_purchase_fee_pct"), errors="coerce").fillna(0.15)
        merged["purchase_status"] = merged["purchase_status"].astype(str).fillna("开放申购")
        merged["redemption_status"] = merged.get("redemption_status", pd.Series("开放赎回", index=merged.index)).astype(str).fillna("开放赎回")
        merged["is_purchase_allowed"] = ~merged["purchase_status"].str.contains("暂停|封闭|场内", na=False)
        merged["is_redemption_allowed"] = ~merged["redemption_status"].str.contains("暂停|封闭", na=False)
        merged["is_large_amount_limited"] = merged["daily_limit_amount"] < 1e6
        for fee_c, def_v in (
            ("est_management_fee", 0.5),
            ("est_custodian_fee", 0.1),
            ("est_sales_service_fee", 0.0),
            ("est_total_operating_fee", 0.6),
        ):
            if fee_c not in merged.columns:
                merged[fee_c] = def_v
            else:
                merged[fee_c] = pd.to_numeric(merged[fee_c], errors="coerce").fillna(def_v)
        merged["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tmp_path = rules_path.with_suffix(".parquet.tmp")
        merged.to_parquet(tmp_path, index=False)
        os.replace(tmp_path, rules_path)
        return {"status": "refreshed", "rows": int(len(merged))}
    except Exception as exc:
        print(f"[WARN] Trading rules refresh skipped (kept existing): {exc}", file=sys.stderr)
        return {"status": "error_kept_existing", "error": str(exc)}


def _build_mobile_compact_archive(data_dir: Path, out_tar: Path) -> Dict[str, Any]:
    """
    导出 Phase 4 跨平台轻内核紧凑数据包（零 Parquet 依赖）：
      - nav_f32.bin: row-major [n_dates, n_funds] IEEE-754 little-endian float32
      - bundle_meta.json: 完整日期轴 + 排序基金元数据
    """
    nav_path = data_dir / "processed" / "market_elite_nav_matrix.parquet"
    meta_path = data_dir / "processed" / "market_elite_meta.parquet"
    nav_df = pd.read_parquet(nav_path)
    meta_df = pd.read_parquet(meta_path)

    nav_df = nav_df.sort_index()
    meta_map: Dict[str, Dict[str, Any]] = {}
    for _, r in meta_df.iterrows():
        c = str(r.get("fund_code", "")).strip().zfill(6)
        meta_map[c] = r.to_dict()

    codes = sorted([str(c).strip().zfill(6) for c in nav_df.columns if str(c).strip().zfill(6) in meta_map])
    sub_nav = nav_df[codes]
    dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in sub_nav.index]
    arr_f32 = np.ascontiguousarray(sub_nav.to_numpy(dtype=np.float32), dtype="<f4")

    funds_list: List[Dict[str, Any]] = []
    for c in codes:
        m = meta_map[c]
        funds_list.append({
            "code": c,
            "name": str(m.get("fund_name", c)),
            "bucket_10": str(m.get("bucket_10", "")),
            "bucket_label": str(m.get("bucket_label", "")),
            "asset_class": str(m.get("asset_class", "equity")),
            "is_index_eligible": bool(m.get("is_index_eligible", False)),
            "est_total_operating_fee": round(_safe_num(m.get("est_total_operating_fee"), 0.6), 4),
            "daily_limit_amount": _safe_num(m.get("daily_limit_amount"), 1e10),
            "purchase_status": str(m.get("purchase_status", "开放申购")),
            "real_scale_yi": round(_safe_num(m.get("real_scale_yi"), 0.0), 2) or None,
        })

    meta_payload = {
        "schema_version": "1.0",
        "dtype": "float32_le",
        "layout": "row_major_dates_x_funds",
        "n_dates": int(len(dates)),
        "n_funds": int(len(codes)),
        "start_date": dates[0] if dates else "",
        "end_date": dates[-1] if dates else "",
        "dates": dates,
        "funds": funds_list,
    }

    with tempfile.TemporaryDirectory(prefix="agy2_mobile_") as td:
        td_p = Path(td)
        bin_p = td_p / "nav_f32.bin"
        meta_p = td_p / "bundle_meta.json"
        bin_p.write_bytes(arr_f32.tobytes(order="C"))
        meta_p.write_text(json.dumps(meta_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

        with tarfile.open(out_tar, "w:gz") as tf:
            tf.add(meta_p, arcname="bundle_meta.json")
            tf.add(bin_p, arcname="nav_f32.bin")

    return {
        "n_dates": int(len(dates)),
        "n_funds": int(len(codes)),
        "latest_trade_date": dates[-1] if dates else "",
        "nav_bin_bytes": int(arr_f32.nbytes),
    }


def build_daily_public_bundle(output_dir: Path, skip_network: bool = False) -> Dict[str, Any]:
    data_dir = runtime_paths.get_data_dir()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    network_report: Dict[str, Any] = {"skipped": bool(skip_network)}
    if not skip_network:
        from market_lakehouse import incremental_daily_sync, reclassify_and_clean_existing_lakehouse

        network_report["trading_rules"] = _refresh_trading_rules_preserving_fees(data_dir)
        network_report["reclassify"] = reclassify_and_clean_existing_lakehouse()
        network_report["lakehouse_sync"] = incremental_daily_sync(cooldown_minutes=0)

    # 校验白名单 6 个纯公开文件全部就绪
    missing: List[str] = []
    for rel in PUBLIC_BUNDLE_WHITELIST:
        p = data_dir / rel
        if not p.exists():
            missing.append(rel)
    if missing:
        raise FileNotFoundError(f"Missing required public bundle files: {missing}")

    # 1. 打包主公共数据包（严格白名单 6 文件，零用户隐私）
    bundle_tar = output_dir / DEFAULT_BUNDLE_FILENAME
    with tarfile.open(bundle_tar, "w:gz") as tf:
        for rel in sorted(PUBLIC_BUNDLE_WHITELIST):
            src = data_dir / rel
            tf.add(src, arcname=rel)

    # 2. 打包 Phase 4 跨平台轻内核 float32 紧凑包
    mobile_tar = output_dir / MOBILE_COMPACT_FILENAME
    compact_info = _build_mobile_compact_archive(data_dir, mobile_tar)

    # 3. 输出带 SHA256 的 manifest.json
    bundle_sha = compute_file_sha256(bundle_tar)
    mobile_sha = compute_file_sha256(mobile_tar)
    latest_date = compact_info["latest_trade_date"]
    st_file = data_dir / "processed" / "market_elite_sync_status.json"
    if st_file.exists():
        try:
            st_obj = json.loads(st_file.read_text(encoding="utf-8"))
            latest_date = str(st_obj.get("latest_date") or latest_date)[:10]
        except Exception:
            pass

    manifest = {
        "schema_version": "2.2.0",
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_trade_date": latest_date,
        "fund_count": compact_info["n_funds"],
        "trading_days": compact_info["n_dates"],
        "bundle_file": DEFAULT_BUNDLE_FILENAME,
        "sha256": bundle_sha,
        "bundle_size_bytes": int(bundle_tar.stat().st_size),
        "mobile_compact_file": MOBILE_COMPACT_FILENAME,
        "mobile_compact_sha256": mobile_sha,
        "mobile_compact_size_bytes": int(mobile_tar.stat().st_size),
        "files": sorted(PUBLIC_BUNDLE_WHITELIST),
        "network_report": network_report,
    }
    manifest_path = output_dir / DEFAULT_MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AGY2 daily public market data bundle & compact float32 package.")
    parser.add_argument("--output-dir", required=True, help="Directory to write tar.gz bundles and manifest.json")
    parser.add_argument("--skip-network", action="store_true", help="Skip live network refresh and package local public files only")
    args = parser.parse_args()

    manifest = build_daily_public_bundle(Path(args.output_dir), skip_network=bool(args.skip_network))
    print(
        f"[OK] Built public bundle ({manifest['bundle_size_bytes'] / 1024 / 1024:.2f} MB) & "
        f"mobile compact ({manifest['mobile_compact_size_bytes'] / 1024 / 1024:.2f} MB) | "
        f"funds={manifest['fund_count']} | latest_date={manifest['latest_trade_date']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
