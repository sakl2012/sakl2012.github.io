import json, os, math, datetime
from analyze_core_alpha_ratio import days, nav_btc, nav_eth, nav_bnb, nav_sol

# Let's inspect Bull Run (2023-01-01 to 2024-03-31)
idx_start = next(i for i, d in enumerate(days) if d['date'] >= '2023-01-01')
idx_end = next(i for i, d in enumerate(days) if d['date'] >= '2024-03-31')

ret_core_bull = 0.5 * (nav_btc[idx_end]/nav_btc[idx_start]) + 0.5 * (nav_eth[idx_end]/nav_eth[idx_start]) - 1.0
ret_alpha_bull = 0.5 * (nav_bnb[idx_end]/nav_bnb[idx_start]) + 0.5 * (nav_sol[idx_end]/nav_sol[idx_start]) - 1.0

print(f"2023-2024 Bull Run:")
print(f"Core Return:  {ret_core_bull*100:+.2f}%")
print(f"Alpha Return: {ret_alpha_bull*100:+.2f}%")
