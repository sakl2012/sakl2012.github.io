import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'PAXGUSDT_1d.json'), 'r', encoding='utf-8') as f:
    paxg_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
    qqq_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'SPY_1d.json'), 'r', encoding='utf-8') as f:
    spy_raw = json.load(f)

btc_map = {b['date']: b['c'] for b in btc_raw}
paxg_map = {b['date']: b['c'] for b in paxg_raw}
qqq_map = {b['date']: b['c'] for b in qqq_raw}
spy_map = {b['date']: b['c'] for b in spy_raw}

dates = sorted(list(set(btc_map.keys()) & set(paxg_map.keys())))

def pearson(x, y):
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((x[i] - mean_x)**2 for i in range(n))
    var_y = sum((y[i] - mean_y)**2 for i in range(n))
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / math.sqrt(var_x * var_y)

# Group by calendar year
years = ['2022', '2023', '2024', '2025', '2026']

print("Yearly Returns and Daily Return Correlations:")
for yr in years:
    yr_dates = [d for d in dates if d.startswith(yr)]
    if len(yr_dates) < 10:
        continue
    
    # Calculate returns over the year
    p_btc_start = btc_map[yr_dates[0]]
    p_btc_end = btc_map[yr_dates[-1]]
    btc_ret = (p_btc_end - p_btc_start) / p_btc_start
    
    p_paxg_start = paxg_map[yr_dates[0]]
    p_paxg_end = paxg_map[yr_dates[-1]]
    paxg_ret = (p_paxg_end - p_paxg_start) / p_paxg_start
    
    # Daily returns
    d_btc = []
    d_paxg = []
    for i in range(1, len(yr_dates)):
        d_btc.append(math.log(btc_map[yr_dates[i]] / btc_map[yr_dates[i-1]]))
        d_paxg.append(math.log(paxg_map[yr_dates[i]] / paxg_map[yr_dates[i-1]]))
        
    corr_daily = pearson(d_btc, d_paxg)
    
    # 30-day rolling price correlation or level trend
    print(f"Year {yr}: BTC Ret: {btc_ret*100:+6.2f}%, PAXG Ret: {paxg_ret*100:+6.2f}%, Daily Log-Return Corr: {corr_daily:.4f}")

# Look specifically at last 365 days (2025-09 to 2026-09)
last_365 = dates[-365:]
d_btc_365 = [math.log(btc_map[last_365[i]] / btc_map[last_365[i-1]]) for i in range(1, len(last_365))]
d_paxg_365 = [math.log(paxg_map[last_365[i]] / paxg_map[last_365[i-1]]) for i in range(1, len(last_365))]
corr_365 = pearson(d_btc_365, d_paxg_365)
btc_ret_365 = (btc_map[last_365[-1]] - btc_map[last_365[0]]) / btc_map[last_365[0]]
paxg_ret_365 = (paxg_map[last_365[-1]] - paxg_map[last_365[0]]) / paxg_map[last_365[0]]
print(f"\nPast 12 Months ({last_365[0]} ~ {last_365[-1]}):")
print(f"BTC Return: {btc_ret_365*100:+.2f}%, PAXG Return: {paxg_ret_365*100:+.2f}%")
print(f"Daily Return Correlation: {corr_365:.4f}")

# Let's also check August 2024 crash
aug_dates = [d for d in dates if '2024-07-28' <= d <= '2024-08-10']
if aug_dates:
    print(f"\nAug 2024 Yen Carry Trade Crash:")
    for d in aug_dates:
        print(f"  {d}: BTC={btc_map[d]:.1f}, PAXG={paxg_map[d]:.1f}")
