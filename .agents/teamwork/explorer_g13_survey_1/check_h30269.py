import pandas as pd

df = pd.read_parquet("data/processed/csindex_H30269.parquet")
print(df[['日期', '指数代码', '指数中文全称', '收盘']].head(5))
print(df[['日期', '指数代码', '指数中文全称', '收盘']].tail(5))

c0 = df['收盘'].iloc[0]
c1 = df['收盘'].iloc[-1]
cagr = (c1 / c0) ** (250.0 / len(df)) - 1.0
print(f"H30269: c0={c0}, c1={c1}, CAGR={cagr*100:.2f}%")
