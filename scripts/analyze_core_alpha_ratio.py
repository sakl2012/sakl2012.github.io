import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'ETHUSDT_1d.json'), 'r', encoding='utf-8') as f:
    eth_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'BNBUSDT_1d.json'), 'r', encoding='utf-8') as f:
    bnb_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'SOLUSDT_1d.json'), 'r', encoding='utf-8') as f:
    sol_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'PAXGUSDT_1d.json'), 'r', encoding='utf-8') as f:
    paxg_raw = json.load(f)
with open(os.path.join(CACHE_DIR, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
    qqq_raw = json.load(f)

btc_map = {b['date']: b['c'] for b in btc_raw}
eth_map = {b['date']: b['c'] for b in eth_raw}
bnb_map = {b['date']: b['c'] for b in bnb_raw}
sol_map = {b['date']: b['c'] for b in sol_raw}
paxg_map = {b['date']: b['c'] for b in paxg_raw}
qqq_map = {b['date']: b['c'] for b in qqq_raw}

# BTC MA200
btc_dates = sorted(btc_raw, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_dates)):
    if i >= 199:
        w = btc_dates[i-199:i+1]
        btc_ma200[btc_dates[i]['date']] = sum(x['c'] for x in w) / 200.0

start_dt = datetime.date(2021, 9, 20)
end_dt = datetime.date(2026, 9, 18)

days = []
cur = start_dt
last_qqq = qqq_raw[0]['c']
while cur <= end_dt:
    d = cur.strftime('%Y-%m-%d')
    if d in qqq_map:
        last_qqq = qqq_map[d]
    if d in btc_map and d in eth_map and d in bnb_map and d in sol_map and d in paxg_map and d in btc_ma200:
        days.append({
            'date': d,
            'BTC': btc_map[d],
            'ETH': eth_map[d],
            'BNB': bnb_map[d],
            'SOL': sol_map[d],
            'PAXG': paxg_map[d],
            'QQQ': last_qqq,
            'R': btc_map[d] / btc_ma200[d]
        })
    cur += datetime.timedelta(days=1)

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

def sim_single_bot(coin_key, zone_weights):
    initial = 10000.0
    nav = initial
    z0 = get_zone(days[0]['R'])
    w_c, w_q, w_p = zone_weights[z0]
    u_c = (nav * w_c) / days[0][coin_key]
    u_q = (nav * w_q) / days[0]['QQQ']
    u_p = (nav * w_p) / days[0]['PAXG']
    cur_z = z0
    
    daily_navs = [nav]
    for i in range(1, len(days)):
        d = days[i]
        p_c, p_q, p_p = d[coin_key], d['QQQ'], d['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        new_z = get_zone(d['R'])
        drift = max(abs(val_c/nav - zone_weights[new_z][0]), abs(val_q/nav - zone_weights[new_z][1]), abs(val_p/nav - zone_weights[new_z][2]))
        if new_z != cur_z or drift >= 0.01:
            cur_z = new_z
            tw_c, tw_q, tw_p = zone_weights[cur_z]
            # Fee
            trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
            nav -= trade_vol * 0.001
            u_c = (nav * tw_c) / p_c
            u_q = (nav * tw_q) / p_q
            u_p = (nav * tw_p) / p_p
        daily_navs.append(nav)
    return daily_navs

# Zone configs:
# Core BTC weights
weights_core_btc = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.45, 0.35, 0.20),
    3: (0.30, 0.35, 0.35),
    4: (0.05, 0.30, 0.65)
}
# Core ETH weights
weights_core_eth = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.40, 0.35, 0.25),
    3: (0.25, 0.35, 0.40),
    4: (0.05, 0.30, 0.65)
}
# Alpha weights (BNB, SOL etc)
weights_alpha = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.35, 0.35, 0.30),
    3: (0.20, 0.40, 0.40),
    4: (0.05, 0.25, 0.70)
}

nav_btc = sim_single_bot('BTC', weights_core_btc)
nav_eth = sim_single_bot('ETH', weights_core_eth)
nav_bnb = sim_single_bot('BNB', weights_alpha)
nav_sol = sim_single_bot('SOL', weights_alpha)

# Define Core basket (50% BTC + 50% ETH)
# Define Alpha basket (50% BNB + 50% SOL)
# Test different allocations:
allocations = [
    ("100% 主力 (純BTC+ETH)", 1.0, 0.0),
    ("70% 主力 + 30% Alpha (防守穩健型)", 0.7, 0.3),
    ("50% 主力 + 50% Alpha (標準平衡型 - 官方預設)", 0.5, 0.5),
    ("30% 主力 + 70% Alpha (進取爆發型)", 0.3, 0.7),
    ("100% Alpha (全山寨藍籌艦隊)", 0.0, 1.0)
]

print("--- 5-Year Performance under Different Core vs Alpha Capital Allocations ---")
print(f"{'配置架構':<30} | {'5年總報酬':<10} | {'CAGR':<8} | {'MDD':<8} | {'夏普比率':<8} | {'卡瑪比率':<8}")
print("-" * 80)

for name, w_core, w_alpha in allocations:
    portfolio_nav = []
    for i in range(len(days)):
        core_val = 0.5 * (nav_btc[i]/nav_btc[0]) + 0.5 * (nav_eth[i]/nav_eth[0])
        alpha_val = 0.5 * (nav_bnb[i]/nav_bnb[0]) + 0.5 * (nav_sol[i]/nav_sol[0])
        tot = (w_core * core_val + w_alpha * alpha_val) * 10000.0
        portfolio_nav.append(tot)
        
    tot_ret = (portfolio_nav[-1] - portfolio_nav[0]) / portfolio_nav[0]
    n_years = len(days) / 365.25
    cagr = ((portfolio_nav[-1] / portfolio_nav[0]) ** (1.0 / n_years)) - 1.0
    
    # MDD
    peak = portfolio_nav[0]
    mdd = 0.0
    d_rets = []
    for j in range(1, len(portfolio_nav)):
        if portfolio_nav[j] > peak: peak = portfolio_nav[j]
        dd = (peak - portfolio_nav[j]) / peak
        if dd > mdd: mdd = dd
        d_rets.append(portfolio_nav[j] / portfolio_nav[j-1] - 1.0)
        
    mean_r = sum(d_rets) / len(d_rets)
    var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
    sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
    calmar = cagr / mdd if mdd > 0 else 0
    
    print(f"{name:<30} | {tot_ret*100:>9.2f}% | {cagr*100:>7.2f}% | {mdd*100:>7.2f}% | {sharpe:>8.3f} | {calmar:>8.3f}")
