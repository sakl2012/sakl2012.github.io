import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

def load_json(filename):
    with open(os.path.join(CACHE_DIR, filename), 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {x['date']: x['c'] for x in data if 'date' in x}

tao_map = load_json('TAOUSDT_1d.json')
btc_map = load_json('BTCUSDT_1d.json')
paxg_map = load_json('PAXGUSDT_1d.json')
qqq_map = load_json('QQQ_1d.json')

with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_raw = json.load(f)
btc_dates = sorted(btc_raw, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_dates)):
    if i >= 199:
        w = btc_dates[i-199:i+1]
        btc_ma200[btc_dates[i]['date']] = sum(x['c'] for x in w) / 200.0

common_dates = sorted(list(set(tao_map.keys()) & set(btc_map.keys()) & set(paxg_map.keys()) & set(btc_ma200.keys())))
print(f"TAO common dates: {len(common_dates)} days, from {common_dates[0]} to {common_dates[-1]}")

days = []
last_qqq = qqq_map[common_dates[0]] if common_dates[0] in qqq_map else 440.0
for d in common_dates:
    if d in qqq_map:
        last_qqq = qqq_map[d]
    days.append({
        'date': d,
        'TAO': tao_map[d],
        'BTC': btc_map[d],
        'PAXG': paxg_map[d],
        'QQQ': last_qqq,
        'R': btc_map[d] / btc_ma200[d]
    })

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

def sim_tao(is_5z, zone_weights, static_weights=(0.3333, 0.3333, 0.3334), initial=1000.0):
    nav = initial
    z0 = get_zone(days[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zone_weights[z0] if is_5z else static_weights
    u_c = (nav * w_c) / days[0]['TAO']
    u_q = (nav * w_q) / days[0]['QQQ']
    u_p = (nav * w_p) / days[0]['PAXG']
    nav_history = [nav]
    trades = 0
    
    for i in range(1, len(days)):
        d = days[i]
        p_c, p_q, p_p = d['TAO'], d['QQQ'], d['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        if is_5z:
            new_z = get_zone(d['R'])
            drift = max(abs(val_c/nav - zone_weights[new_z][0]), abs(val_q/nav - zone_weights[new_z][1]), abs(val_p/nav - zone_weights[new_z][2]))
            if new_z != cur_z or drift >= 0.01:
                cur_z = new_z
                tw_c, tw_q, tw_p = zone_weights[cur_z]
                trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                nav -= trade_vol * 0.001
                u_c = (nav * tw_c) / p_c
                u_q = (nav * tw_q) / p_q
                u_p = (nav * tw_p) / p_p
                trades += 1
        else:
            drift = max(abs(val_c/nav - static_weights[0]), abs(val_q/nav - static_weights[1]), abs(val_p/nav - static_weights[2]))
            if drift >= 0.01:
                tw_c, tw_q, tw_p = static_weights
                trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                nav -= trade_vol * 0.001
                u_c = (nav * tw_c) / p_c
                u_q = (nav * tw_q) / p_q
                u_p = (nav * tw_p) / p_p
                trades += 1
        nav_history.append(nav)
        
    tot_ret = (nav - initial) / initial
    peak = nav_history[0]
    mdd = 0.0
    for n in nav_history:
        if n > peak: peak = n
        dd = (peak - n) / peak
        if dd > mdd: mdd = dd
    return nav, tot_ret, mdd, trades

# Core 3 (TAO) Webpage Zone Weights:
weights_core_tao = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.35, 0.35, 0.30),
    3: (0.20, 0.40, 0.40),
    4: (0.05, 0.25, 0.70)
}

nav_5z, ret_5z, mdd_5z, tr_5z = sim_tao(True, weights_core_tao, initial=1000.0)
nav_eq, ret_eq, mdd_eq, tr_eq = sim_tao(False, weights_core_tao, static_weights=(0.3333, 0.3333, 0.3334), initial=1000.0)
nav_50, ret_50, mdd_50, tr_50 = sim_tao(False, weights_core_tao, static_weights=(0.50, 0.25, 0.25), initial=1000.0)

# Buy & hold TAO
tao_start = days[0]['TAO']
tao_end = days[-1]['TAO']
ret_hodl = (tao_end - tao_start) / tao_start
mdd_hodl = 0.0
peak_t = tao_start
for d in days:
    if d['TAO'] > peak_t: peak_t = d['TAO']
    dd = (peak_t - d['TAO']) / peak_t
    if dd > mdd_hodl: mdd_hodl = dd

print("=== TAO (Core 3: TAO + QQQ + PAXG) SIMULATION RESULTS ===")
print(f"Period: {days[0]['date']} ~ {days[-1]['date']} ({len(days)} days, since Binance listing)")
print(f"TAO Start Price: ${tao_start:.2f}, End Price: ${tao_end:.2f}")
print(f"\n1. 5-Zone (Webpage Core 3 settings):")
print(f"   Final: ${nav_5z:.2f} ({ret_5z*100:+.2f}%), MDD: {mdd_5z*100:.2f}%, Trades: {tr_5z}")
print(f"\n2. Static Equal Weight (33.3% TAO / 33.3% QQQ / 33.3% PAXG):")
print(f"   Final: ${nav_eq:.2f} ({ret_eq*100:+.2f}%), MDD: {mdd_eq*100:.2f}%, Trades: {tr_eq}")
print(f"\n3. Static 50% TAO (50% TAO / 25% QQQ / 25% PAXG):")
print(f"   Final: ${nav_50:.2f} ({ret_50*100:+.2f}%), MDD: {mdd_50*100:.2f}%, Trades: {tr_50}")
print(f"\n4. 100% TAO Buy & Hold (HODL):")
print(f"   Final: ${1000.0*(1+ret_hodl):.2f} ({ret_hodl*100:+.2f}%), MDD: {mdd_hodl*100:.2f}%")
