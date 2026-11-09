import os
import pandas as pd

# Let's inspect csindex_H30269.parquet and see the returns year by year
df = pd.read_parquet("data/processed/csindex_H30269.parquet")
df['year'] = pd.to_datetime(df['日期']).dt.year
for yr, grp in df.groupby('year'):
    s0 = grp['收盘'].iloc[0]
    s1 = grp['收盘'].iloc[-1]
    ret = (s1 / s0 - 1.0) * 100.0
    print(f"H30269 Year {yr}: start={s0:.2f}, end={s1:.2f}, ret={ret:+.2f}%")

df_h922 = pd.read_parquet("data/processed/csindex_H00922.parquet")
df_h922['year'] = pd.to_datetime(df_h922['日期']).dt.year
for yr, grp in df_h922.groupby('year'):
    s0 = grp['收盘'].iloc[0]
    s1 = grp['收盘'].iloc[-1]
    ret = (s1 / s0 - 1.0) * 100.0
    print(f"H00922 Year {yr}: start={s0:.2f}, end={s1:.2f}, ret={ret:+.2f}%")
