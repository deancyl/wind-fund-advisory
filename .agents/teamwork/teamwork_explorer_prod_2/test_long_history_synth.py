import pandas as pd
import numpy as np
from pathlib import Path

# Load local indices
hs300 = pd.read_parquet("data/processed/indices/000300.SH.parquet")[['date', 'close']].rename(columns={'close': 'H00300'})
zz500 = pd.read_parquet("data/processed/indices/000905.SH.parquet")[['date', 'close']].rename(columns={'close': 'H00905'})
div = pd.read_parquet("data/processed/indices/000015.SH.parquet")[['date', 'close']].rename(columns={'close': 'H00922'})
bond = pd.read_parquet("data/processed/indices/CBA00101.CS.parquet")[['date', 'close']].rename(columns={'close': '930609'})
gold = pd.read_parquet("data/processed/indices/AU9999.SGE.parquet")[['date', 'close']].rename(columns={'close': 'AU9999'})

for df in [hs300, zz500, div, bond, gold]:
    df['date'] = pd.to_datetime(df['date'])

m = hs300.merge(zz500, on='date', how='inner')
m = m.merge(div, on='date', how='inner')
m = m.merge(bond, on='date', how='inner')
m = m.merge(gold, on='date', how='inner')
m = m.sort_values('date').reset_index(drop=True)

print("Synthesized 2005+ multi-asset index overlap:")
print("Shape:", m.shape)
print("Range:", m['date'].min(), "to", m['date'].max())
print(m.head(2))
