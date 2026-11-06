import pandas as pd
import numpy as np
from pathlib import Path

ws = Path(__file__).resolve().parent.parent.parent.parent
mat_p = ws / "data" / "processed" / "aligned_matrix_total_return.parquet"
df_mat = pd.read_parquet(mat_p)

print("Recent 20 days metrics from aligned_matrix_total_return:")
for col in ['H00300', 'H30269', 'H00922', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', 'H11009']:
    s = df_mat[col].dropna().values
    p_t = s[-1]
    ma20 = np.mean(s[-20:])
    bias20 = ((p_t - ma20) / ma20) * 100.0
    rets = np.diff(s[-21:]) / s[-21:-1]
    sigma_day = np.std(rets)
    sigma_day_pct = sigma_day * 100.0
    vol_ann = sigma_day * np.sqrt(250.0)
    print(f"  {col:15s}: p_t={p_t:.2f}, MA20={ma20:.2f}, Bias20={bias20:+.2f}%, sigma_day={sigma_day_pct:.2f}%, 1.5*sigma={1.5*sigma_day_pct:.2f}%, vol_ann={vol_ann:.2%}")
