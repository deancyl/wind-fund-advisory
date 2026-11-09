import pandas as pd
import numpy as np

for p in [
    "data/processed/aligned_matrix_total_return.parquet",
    "data/aligned_matrix_total_return.parquet",
    "AGY2_FundAdvisory/data/aligned_matrix_total_return.parquet"
]:
    try:
        df = pd.read_parquet(p)
        print(f"Found {p}, shape: {df.shape}")
        print("Columns:", df.columns.tolist())
        target_cols = [c for c in ['H11009', 'H30269', '930609', 'H00922', 'H00300', 'AU9999', 'SPX_CNY'] if c in df.columns]
        print("Target cols present:", target_cols)
        print("Head:")
        print(df[['date'] + target_cols].head(3))
        print("Tail:")
        print(df[['date'] + target_cols].tail(3))
        
        # Check H11009 and H30269 CAGR
        n_days = len(df)
        for col in target_cols:
            s = df[col].astype(float).values
            cagr = (s[-1] / s[0]) ** (250.0 / n_days) - 1.0
            daily_diff = np.diff(s)
            zero_diff_count = np.sum(daily_diff == 0)
            print(f"{col}: start={s[0]:.2f}, end={s[-1]:.2f}, CAGR={cagr*100:.2f}%, zero_diffs={zero_diff_count}/{len(daily_diff)}")
        break
    except Exception as e:
        print(f"Failed {p}: {e}")
