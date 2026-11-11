import pandas as pd
from pathlib import Path

root = Path("d:/Google/Workspace/Wind")
df_global = pd.read_parquet(root / "data/global/global_indices.parquet")

for code in ['IXIC', 'SPX', 'HSTECH', 'HSI']:
    sub = df_global[df_global['index_code'] == code].sort_values('date').copy()
    if len(sub) >= 20:
        c_cur = sub['close'].iloc[-1]
        c_20_ago = sub['close'].iloc[-20]
        ma20 = sub['close'].tail(20).mean()
        bias20 = (c_cur / ma20 - 1.0) * 100.0
        ret_cur = sub['daily_return'].iloc[-1]
        d_latest = sub['date'].iloc[-1]
        print(f"[{code}] date={d_latest}, close={c_cur:.2f}, ret={ret_cur:+.2f}%, ma20={ma20:.2f}, bias20={bias20:+.2f}%")
