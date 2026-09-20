import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

def load_json(sym):
    with open(os.path.join(CACHE_DIR, sym), 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {x['date']: x['c'] for x in data if 'date' in x}

btc_map = load_json('BTCUSDT_1d.json')
eth_map = load_json('ETHUSDT_1d.json')
bnb_map = load_json('BNBUSDT_1d.json')
uni_map = load_json('UNIUSDT_1d.json')
aave_map = load_json('AAVEUSDT_1d.json')
link_map = load_json('LINKUSDT_1d.json')
near_map = load_json('NEARUSDT_1d.json')
paxg_map = load_json('PAXGUSDT_1d.json')
qqq_map = load_json('QQQ_1d.json')
tao_map = load_json('TAOUSDT_1d.json')
ondo_map = load_json('ONDOUSDT_1d.json')

with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_raw = json.load(f)
btc_dates = sorted(btc_raw, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_dates)):
    if i >= 199:
        w = btc_dates[i-199:i+1]
        btc_ma200[btc_dates[i]['date']] = sum(x['c'] for x in w) / 200.0

# 1. 5-Year Full Cycle (2021-09-20 to 2026-09-07) with user's EXACT 5-year tokens:
# Core: BTC (25%), ETH (25%) = 50%
# Alpha: BNB (10%), UNI (10%), AAVE (10%), LINK (10%), NEAR (10%) = 50% (STRICTLY NO SOL!)
dates_5y = sorted(list(set(btc_map.keys()) & set(eth_map.keys()) & set(bnb_map.keys()) & 
                       set(uni_map.keys()) & set(aave_map.keys()) & set(link_map.keys()) & 
                       set(near_map.keys()) & set(paxg_map.keys()) & set(btc_ma200.keys())))
start_5y = next(i for i, d in enumerate(dates_5y) if d >= '2021-09-20')
end_5y = next(i for i, d in enumerate(dates_5y) if d <= '2026-09-07' and i == len(dates_5y)-1 or (i < len(dates_5y)-1 and dates_5y[i+1] > '2026-09-07'))
dates_5y = dates_5y[start_5y:end_5y+1]

days_5y = []
last_qqq = qqq_map['2021-09-20']
for d in dates_5y:
    if d in qqq_map: last_qqq = qqq_map[d]
    days_5y.append({
        'date': d,
        'BTC': btc_map[d],
        'ETH': eth_map[d],
        'BNB': bnb_map[d],
        'UNI': uni_map[d],
        'AAVE': aave_map[d],
        'LINK': link_map[d],
        'NEAR': near_map[d],
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

def simulate_bot(days_list, coin_key, is_5z, zone_weights, static_weights=(0.3333, 0.3333, 0.3334), initial_cap=1000.0):
    nav = initial_cap
    z0 = get_zone(days_list[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zone_weights[z0] if is_5z else static_weights
    u_c = (nav * w_c) / days_list[0][coin_key]
    u_q = (nav * w_q) / days_list[0]['QQQ']
    u_p = (nav * w_p) / days_list[0]['PAXG']
    nav_history = [nav]
    trades = 0
    
    for i in range(1, len(days_list)):
        d = days_list[i]
        p_c, p_q, p_p = d[coin_key], d['QQQ'], d['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        cur_wc = val_c / nav
        cur_wq = val_q / nav
        cur_wp = val_p / nav
        
        if is_5z:
            new_z = get_zone(d['R'])
            zone_changed = (new_z != cur_z)
            cur_z = new_z
            tw_c, tw_q, tw_p = zone_weights[cur_z]
        else:
            zone_changed = False
            tw_c, tw_q, tw_p = static_weights
            
        drift = max(abs(cur_wc - tw_c), abs(cur_wq - tw_q), abs(cur_wp - tw_p))
        if zone_changed or drift >= 0.01:
            trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
            nav -= trade_vol * 0.001
            u_c = (nav * tw_c) / p_c
            u_q = (nav * tw_q) / p_q
            u_p = (nav * tw_p) / p_p
            trades += 1
        nav_history.append(nav)
    return nav_history, trades

# User Exact Weights
zw_core_btc = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.45, 0.35, 0.20), 3: (0.30, 0.35, 0.35), 4: (0.05, 0.30, 0.65)}
zw_core_eth = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.40, 0.35, 0.25), 3: (0.25, 0.35, 0.40), 4: (0.05, 0.30, 0.65)}
zw_alpha    = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)}

# Run 5-Year portfolio with user's exact tokens (NO SOL)
bots_5y = [
    ('BTC', 'Core 1 (BTC)', 2500.0, zw_core_btc),
    ('ETH', 'Core 2 (ETH)', 2500.0, zw_core_eth),
    ('BNB', 'Alpha 1 (BNB)', 1000.0, zw_alpha),
    ('UNI', 'Alpha 2 (UNI)', 1000.0, zw_alpha),
    ('AAVE', 'Alpha 3 (AAVE)', 1000.0, zw_alpha),
    ('LINK', 'Alpha 4 (LINK)', 1000.0, zw_alpha),
    ('NEAR', 'Alpha 5 (NEAR)', 1000.0, zw_alpha)
]

def run_portfolio_5y(is_5z, static_w=(0.3333, 0.3333, 0.3334)):
    tot_nav = [0.0] * len(days_5y)
    bot_details = {}
    tot_trades = 0
    for sym, label, cap, zw in bots_5y:
        nh, tr = simulate_bot(days_5y, sym, is_5z, zw, static_w, initial_cap=cap)
        tot_trades += tr
        bot_details[label] = {'initial': cap, 'final': nh[-1], 'ret': (nh[-1]-cap)/cap, 'trades': tr}
        for i in range(len(days_5y)):
            tot_nav[i] += nh[i]
            
    final = tot_nav[-1]
    ret = (final - 10000.0) / 10000.0
    n_years = len(days_5y) / 365.25
    cagr = ((final / 10000.0) ** (1.0 / n_years)) - 1.0
    peak = tot_nav[0]
    mdd = 0.0
    d_rets = []
    for j in range(1, len(tot_nav)):
        if tot_nav[j] > peak: peak = tot_nav[j]
        dd = (peak - tot_nav[j]) / peak
        if dd > mdd: mdd = dd
        d_rets.append(tot_nav[j] / tot_nav[j-1] - 1.0)
    mean_r = sum(d_rets) / len(d_rets)
    var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
    sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
    calmar = cagr / mdd if mdd > 0 else 0
    return {'final': final, 'ret': ret, 'cagr': cagr, 'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar, 'trades': tot_trades, 'bot_details': bot_details}

res_5z = run_portfolio_5y(True)
res_eq = run_portfolio_5y(False, (0.3333, 0.3333, 0.3334))
res_50 = run_portfolio_5y(False, (0.50, 0.25, 0.25))

print("=== USER'S EXACT PORTFOLIO (NO SOL): 5-YEAR FULL CYCLE RESULTS ===")
print(f"Core: BTC (2500U), ETH (2500U) | Alpha: BNB, UNI, AAVE, LINK, NEAR (each 1000U)")
print(f"Dates: {days_5y[0]['date']} ~ {days_5y[-1]['date']} ({len(days_5y)} days)")
print(f"\n{'Strategy':<22} | {'Final NAV ($10k)':<18} | {'Total Ret':<10} | {'CAGR':<8} | {'MDD':<8} | {'Sharpe':<6} | {'Calmar':<6}")
print("-" * 88)
for name, r in [('5-Zone Dynamic', res_5z), ('Static 1/3 (33/33/33)', res_eq), ('Static 50% (50/25/25)', res_50)]:
    print(f"{name:<22} | ${r['final']:>16.2f} | {r['ret']*100:>8.2f}% | {r['cagr']*100:>6.2f}% | {r['mdd']*100:>6.2f}% | {r['sharpe']:>6.3f} | {r['calmar']:>6.3f}")

print("\n--- PER-BOT DETAILS UNDER USER'S EXACT 5-YEAR TOKENS ---")
for k in res_5z['bot_details']:
    b5 = res_5z['bot_details'][k]
    be = res_eq['bot_details'][k]
    print(f"{k:<18} (Cap ${b5['initial']:.0f}): 5Z=${b5['final']:.2f} ({b5['ret']*100:+.1f}%) | Static 1/3=${be['final']:.2f} ({be['ret']*100:+.1f}%)")
