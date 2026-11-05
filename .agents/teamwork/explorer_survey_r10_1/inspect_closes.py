import pandas as pd
from pathlib import Path

workspace = Path(r"d:\Google\Workspace\Wind")

p_h30269 = workspace / "data/processed/csindex_H30269.parquet"
df_h30269 = pd.read_parquet(p_h30269)
print("csindex_H30269 收盘 tail 5:")
print(df_h30269[['日期', '收盘', '涨跌幅', '滚动市盈率']].tail(5))

p_h00922 = workspace / "data/processed/csindex_H00922.parquet"
df_h00922 = pd.read_parquet(p_h00922)
print("csindex_H00922 收盘 tail 5:")
print(df_h00922[['日期', '收盘', '涨跌幅', '滚动市盈率']].tail(5))
