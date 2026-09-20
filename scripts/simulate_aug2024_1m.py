import json, os, math, datetime

CACHE_1M = os.path.join(os.path.dirname(__file__), 'data_cache_1m')
CACHE_1D = os.path.join(os.path.dirname(__file__), 'data_cache')

with open(os.path.join(CACHE_1M, 'BTCUSDT_aug2024_1m.json'), 'r', encoding='utf-8') as f:
    btc_1m = json.load(f)
with open(os.path.join(CACHE_1M, 'PAXGUSDT_aug2024_1m.json'), 'r', encoding='utf-8') as f:
    paxg_1m = json.load(f)
with open(os.path.join(CACHE_1D, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
    qqq_1d = json.load(f)
with open(os.path.join(CACHE_1D, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_1d = json.load(f)

# Precalculate 1D MA200 for August 2024
btc_1d_sorted = sorted(btc_1d, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_1d_sorted)):
    if i >= 199:
        w = btc_1d_sorted[i-199:i+1]
        btc_ma200[btc_1d_sorted[i]['date']] = sum(x['c'] for x in w) / 200.0

qqq_by_date = {x['date']: x['c'] for x in qqq_1d}
paxg_map = {x['t']: x['c'] for x in paxg_1m}

bars_1m = []
last_qqq = 445.0 # QQQ price in early August 2024

for b in btc_1m:
    t = b['t']
    d_str = b['date'] # YYYY-MM-DD HH:MM
    day_str = d_str.split(' ')[0]
    if day_str in qqq_by_date:
        last_qqq = qqq_by_date[day_str]
    if t in paxg_map and day_str in btc_ma200:
        p_btc = b['c']
        p_paxg = paxg_map[t]
        ma = btc_ma200[day_str]
        bars_1m.append({
            't': t,
            'date': d_str,
            'day': day_str,
            'BTC': p_btc,
            'PAXG': p_paxg,
            'QQQ': last_qqq,
            'R': p_btc / ma
        })

print(f"Loaded {len(bars_1m)} common 1m bars from {bars_1m[0]['date']} to {bars_1m[-1]['date']}")
print(f"BTC Crash: High=${max(b['BTC'] for b in bars_1m):.1f}, Low=${min(b['BTC'] for b in bars_1m):.1f} (Drop of {(min(b['BTC'] for b in bars_1m)/max(b['BTC'] for b in bars_1m)-1)*100:.1f}%)")

# Downsample to 1H and 1D
seen_h = set()
bars_1h = []
for b in bars_1m:
    h_str = b['date'][:13]
    if h_str not in seen_h:
        seen_h.add(h_str)
        bars_1h.append(b)

seen_d = set()
bars_1d = []
for b in bars_1m:
    day = b['day']
    if day not in seen_d:
        seen_d.add(day)
day_groups = {}
for b in bars_1m: day_groups.setdefault(b['day'], []).append(b)
bars_1d = [day_groups[d][-1] for d in sorted(day_groups.keys())]

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

zw_btc = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.45, 0.35, 0.20), 3: (0.30, 0.35, 0.35), 4: (0.05, 0.30, 0.65)}

def run_sim(bars, is_5z, threshold, cooldown=0):
    initial = 10000.0
    nav = initial
    z0 = get_zone(bars[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zw_btc[z0] if is_5z else (0.3333, 0.3333, 0.3334)
    u_c = (nav * w_c) / bars[0]['BTC']
    u_q = (nav * w_q) / bars[0]['QQQ']
    u_p = (nav * w_p) / bars[0]['PAXG']
    trades = 0
    fees = 0.0
    nav_hist = [nav]
    last_trade_idx = -9999
    
    for i in range(1, len(bars)):
        b = bars[i]
        p_c, p_q, p_p = b['BTC'], b['QQQ'], b['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        cur_wc = val_c / nav
        cur_wq = val_q / nav
        cur_wp = val_p / nav
        
        if is_5z:
            new_z = get_zone(b['R'])
            zone_changed = (new_z != cur_z)
            cur_z = new_z
            tw_c, tw_q, tw_p = zw_btc[cur_z]
        else:
            zone_changed = False
            tw_c, tw_q, tw_p = (0.3333, 0.3333, 0.3334)
            
        drift = max(abs(cur_wc - tw_c), abs(cur_wq - tw_q), abs(cur_wp - tw_p))
        if zone_changed or drift >= threshold:
            if (i - last_trade_idx) >= cooldown:
                trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                fee = trade_vol * 0.001
                nav -= fee
                fees += fee
                u_c = (nav * tw_c) / p_c
                u_q = (nav * tw_q) / p_q
                u_p = (nav * tw_p) / p_p
                trades += 1
                last_trade_idx = i
        nav_hist.append(nav)
        
    ret = (nav - initial) / initial
    peak = nav_hist[0]
    mdd = 0.0
    for n in nav_hist:
        if n > peak: peak = n
        dd = (peak - n) / peak
        if dd > mdd: mdd = dd
    return nav, ret, mdd, trades, fees

# BTC buy & hold
ret_hodl = (bars_1m[-1]['BTC'] - bars_1m[0]['BTC']) / bars_1m[0]['BTC']
mdd_hodl = (max(b['BTC'] for b in bars_1m) - min(b['BTC'] for b in bars_1m)) / max(b['BTC'] for b in bars_1m)

print("\n=== AUGUST 5 2024 CRASH (10,081 ONE-MINUTE BARS TEST) ===")
print(f"BTC HODL: Final Ret = {ret_hodl*100:+.2f}%, Max Crash Depth = -{mdd_hodl*100:.2f}%\n")

print(f"{'Resolution':<12} | {'Strategy':<16} | {'Thresh':<8} | {'Final NAV ($10k)':<16} | {'Return':<8} | {'MDD':<8} | {'Trades':<8} | {'Fees':<8}")
print("-" * 92)

for r_name, b_set in [('1-Minute (1m)', bars_1m), ('1-Hour (1h)', bars_1h), ('1-Day (1d)', bars_1d)]:
    for s_name, is_5z in [('5-Zone Dynamic', True), ('Static (33/33/33)', False)]:
        for th_l, th in [('1%', 0.01), ('2%', 0.02), ('5%', 0.05)]:
            nav, ret, mdd, tr, fee = run_sim(b_set, is_5z, th)
            print(f"{r_name:<12} | {s_name:<16} | {th_l:<8} | ${nav:>14.2f} | {ret*100:>6.2f}% | {mdd*100:>6.2f}% | {tr:>6}   | ${fee:>6.2f}")
    print("-" * 92)
