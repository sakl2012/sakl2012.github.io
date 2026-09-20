import json
import os
import math
import datetime

CACHE_1M = os.path.join(os.path.dirname(__file__), 'data_cache_1m')
CACHE_1D = os.path.join(os.path.dirname(__file__), 'data_cache')

with open(os.path.join(CACHE_1M, 'BTCUSDT_1m.json'), 'r', encoding='utf-8') as f:
    btc_1m = json.load(f)
with open(os.path.join(CACHE_1M, 'PAXGUSDT_1m.json'), 'r', encoding='utf-8') as f:
    paxg_1m = json.load(f)
with open(os.path.join(CACHE_1D, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_1d = json.load(f)
with open(os.path.join(CACHE_1D, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
    qqq_1d = json.load(f)

# Calculate MA200 from 1D data
btc_1d_sorted = sorted(btc_1d, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_1d_sorted)):
    if i >= 199:
        w = btc_1d_sorted[i-199:i+1]
        btc_ma200[btc_1d_sorted[i]['date']] = sum(x['c'] for x in w) / 200.0

qqq_map = {x['date']: x['c'] for x in qqq_1d}
paxg_map = {x['t']: x['c'] for x in paxg_1m}

# Build common 1m dataset
bars_1m = []
last_qqq = 500.0 # recent QQQ price

for b in btc_1m:
    t = b['t']
    d_str = b['date'] # YYYY-MM-DD HH:MM
    day_str = d_str.split(' ')[0]
    
    if day_str in qqq_map:
        last_qqq = qqq_map[day_str]
    elif not last_qqq:
        last_qqq = 500.0
        
    if t in paxg_map:
        p_btc = b['c']
        p_paxg = paxg_map[t]
        ma = btc_ma200.get(day_str, btc_1d_sorted[-1]['c']) # fallback to latest MA
        bars_1m.append({
            't': t,
            'date': d_str,
            'day': day_str,
            'BTC': p_btc,
            'PAXG': p_paxg,
            'QQQ': last_qqq,
            'R': p_btc / ma
        })

print(f"Loaded {len(bars_1m)} common 1-minute bars from {bars_1m[0]['date']} to {bars_1m[-1]['date']}")
print(f"BTC start: ${bars_1m[0]['BTC']:.2f}, end: ${bars_1m[-1]['BTC']:.2f}")
print(f"PAXG start: ${bars_1m[0]['PAXG']:.2f}, end: ${bars_1m[-1]['PAXG']:.2f}")

# Also build 1-hour downsampled bars from these exact 1m bars
bars_1h = []
seen_hours = set()
for b in bars_1m:
    # YYYY-MM-DD HH
    h_str = b['date'][:13]
    if h_str not in seen_hours:
        seen_hours.add(h_str)
        bars_1h.append(b)
print(f"Downsampled to {len(bars_1h)} 1-hour bars for comparison")

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

zw_btc = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.45, 0.35, 0.20), 3: (0.30, 0.35, 0.35), 4: (0.05, 0.30, 0.65)}

def run_simulation(bars, is_5z, threshold, cooldown_mins=0):
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
        
        # Check if rebalance condition met
        if zone_changed or drift >= threshold:
            if (i - last_trade_idx) >= cooldown_mins:
                trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                fee = trade_vol * 0.001
                nav -= fee
                fees += fee
                u_c = (nav * tw_c) / p_c
                u_q = (nav * tw_q) / p_q
                u_p = (nav * tw_p) / p_p
                trades += 1
                last_trade_idx = i
                
    ret = (nav - initial) / initial
    return nav, ret, trades, fees

print("\n=== 1-MINUTE (1m) HIGH-FREQUENCY SIMULATION RESULTS ===")
print(f"Data: {len(bars_1m)} real consecutive 1-minute bars (~14 Days, 2026-09-06 to 2026-09-20)")
print("Initial Capital: $10,000.00 U\n")

print(f"{'Resolution':<12} | {'Strategy':<16} | {'Threshold':<10} | {'Final NAV':<12} | {'Return':<8} | {'Trades':<8} | {'Fees Paid':<10}")
print("-" * 88)

for res_name, bar_set in [('1-Minute (1m)', bars_1m), ('1-Hour (1h)', bars_1h)]:
    for strat_name, is_5z in [('5-Zone Dynamic', True), ('Static (33/33/33)', False)]:
        for th_label, th in [('1%', 0.01), ('2%', 0.02), ('5%', 0.05)]:
            nav, ret, tr, fee = run_simulation(bar_set, is_5z, th)
            print(f"{res_name:<12} | {strat_name:<16} | {th_label:<10} | ${nav:>10.2f} | {ret*100:>6.2f}% | {tr:>6}   | ${fee:>8.2f}")
    print("-" * 88)

# Now test the "Over-Trading Churn" effect:
# If threshold is 0.5% on 1-minute vs with a 15-minute cooldown (like Binance bot)
print("\n=== TESTING COOLDOWN & MICROSTRUCTURE EFFECT ON 1-MINUTE (1m) BARS ===")
print("Threshold = 1.0%")
for cd in [0, 5, 15, 60]:
    n, r, t, f = run_simulation(bars_1m, True, 0.01, cooldown_mins=cd)
    print(f"5-Zone 1m (Cooldown={cd:>2} mins): Final=${n:.2f} ({r*100:+.2f}%), Trades={t:>4}, Fees=${f:.2f}")

for cd in [0, 5, 15, 60]:
    n, r, t, f = run_simulation(bars_1m, False, 0.01, cooldown_mins=cd)
    print(f"Static 1m (Cooldown={cd:>2} mins): Final=${n:.2f} ({r*100:+.2f}%), Trades={t:>4}, Fees=${f:.2f}")
