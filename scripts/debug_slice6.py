import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from data_loader import DataLoader
import pandas as pd

dl = DataLoader()
df = dl.load_total_return_matrix(end_date='2025-06-30')
slices = dl.get_style_slices()
s, e, _ = slices['Slice_6']
sub = df[(df['date'] >= s) & (df['date'] <= e)]

def hysteresis_strat(history_df, params=None):
    if history_df is None or len(history_df) == 0:
        return {'STAR50_STITCH': 0.25, 'H00905': 0.20, 'H00300': 0.15, 'H00922': 0.10, 'AU9999': 0.12, 'SPX_CNY': 0.08, 'H11009': 0.10}
    c300 = history_df['H00300'].iloc[-1]
    c500 = history_df['H00905'].iloc[-1]
    m60_300 = history_df['H00300'].tail(60).mean()
    m60_500 = history_df['H00905'].tail(60).mean()
    is_defensive = (c300 < m60_300) and (c500 < m60_500)
    if not is_defensive:
        return {'STAR50_STITCH': 0.30, 'H00905': 0.20, 'H00300': 0.12, 'H00922': 0.10, 'AU9999': 0.12, 'SPX_CNY': 0.08, 'H11009': 0.08}
    else:
        return {'H00922': 0.35, 'H30269': 0.20, 'AU9999': 0.14, 'SPX_CNY': 0.06, 'H11009': 0.25}

for i in [0, 5, 10, 15, 18, 20, 22, 25, 30]:
    d = sub['date'].iloc[i]
    h = df[df['date'] <= d]
    w = hysteresis_strat(h)
    has_star = 'STAR50_STITCH' in w and w['STAR50_STITCH'] > 0.1
    c = h['H00300'].iloc[-1]
    m = h['H00300'].tail(60).mean()
    print(f"{str(d)[:10]} | has_star={has_star} | H300={c:.1f} | MA60={m:.1f} | w_star={w.get('STAR50_STITCH', 0)}")
