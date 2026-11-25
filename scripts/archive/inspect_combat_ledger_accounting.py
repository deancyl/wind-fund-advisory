import json
from pathlib import Path

p = Path("data/ledgers/combat_29_funds.json")
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)

neg = [h["floating_pnl"] for h in d["holdings"] if h["floating_pnl"] < 0]
pos = [h["floating_pnl"] for h in d["holdings"] if h["floating_pnl"] > 0]
cost_of_neg = [h["cost_basis"] for h in d["holdings"] if h["floating_pnl"] < 0]

print("Sum neg pnl:", round(sum(neg), 2))
print("Sum pos pnl:", round(sum(pos), 2))
print("Net pnl:", round(sum(neg) + sum(pos), 2))
print("Deep loss (100032, 011613, 161725):", round(-332.54 - 428.48 - 175.76, 2))
print("Deep loss + 005827 + 002351:", round(-332.54 - 428.48 - 175.76 - 23.86 - 48.89, 2))
