import json, os, math, datetime

CACHE_1H = os.path.join(os.path.dirname(__file__), 'data_cache_1h')
CACHE_1D = os.path.join(os.path.dirname(__file__), 'data_cache')

with open(os.path.join(CACHE_1H, 'BTCUSDT_1h.json'), 'r', encoding='utf-8') as f:
    btc_1h = json.load(f)
with open(os.path.join(CACHE_1H, 'PAXGUSDT_1h.json'), 'r', encoding='utf-8') as f:
    paxg_1h = json.load(f)
with open(os.path.join(CACHE_1D, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
    qqq_1d = json.load(f)
with open(os.path.join(CACHE_1D, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_1d = json.load(f)

# Calculate daily MA200
btc_dates = sorted(btc_1d, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_dates)):
    if i >= 199:
        w = btc_dates[i-199:i+1]
        btc_ma200[btc_dates[i]['date']] = sum(x['c'] for x in w) / 200.0

qqq_by_date = {x['date']: x['c'] for x in qqq_1d}
paxg_1h_map = {x['date']: x['c'] for x in paxg_1h}

# Build common 1h dataset
common_1h = []
last_qqq = 440.0

for b in btc_1h:
    d_str = b['date'] # 'YYYY-MM-DD HH:MM'
    day_str = d_str.split(' ')[0]
    if day_str in qqq_by_date:
        last_qqq = qqq_by_date[day_str]
    if d_str in paxg_1h_map and day_str in btc_ma200:
        p_btc = b['c']
        p_paxg = paxg_1h_map[d_str]
        ma = btc_ma200[day_str]
        common_1h.append({
            'date': d_str,
            'day': day_str,
            'BTC': p_btc,
            'PAXG': p_paxg,
            'QQQ': last_qqq,
            'R': p_btc / ma
        })

print(f"Loaded {len(common_1h)} common 1h bars from {common_1h[0]['date']} to {common_1h[-1]['date']}")

# Also extract common 1D bars for exact same time range
daily_bars = []
seen_days = set()
for bar in common_1h:
    day = bar['day']
    # keep the last hour of each day as the daily close
    if day not in seen_days:
        seen_days.add(day)

# group by day, take last bar
day_groups = {}
for bar in common_1h:
    day_groups.setdefault(bar['day'], []).append(bar)

daily_bars = [day_groups[d][-1] for d in sorted(day_groups.keys())]
print(f"Derived {len(daily_bars)} daily bars for the exact same period")

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

zw_btc = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.45, 0.35, 0.20), 3: (0.30, 0.35, 0.35), 4: (0.05, 0.30, 0.65)}

def run_sim(bars, is_5z, threshold=0.01):
    nav = 10000.0
    z0 = get_zone(bars[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zw_btc[z0] if is_5z else (0.3333, 0.3333, 0.3334)
    u_c = (nav * w_c) / bars[0]['BTC']
    u_q = (nav * w_q) / bars[0]['QQQ']
    u_p = (nav * w_p) / bars[0]['PAXG']
    trades = 0
    fees = 0.0
    
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
            trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
            fee = trade_vol * 0.001
            nav -= fee
            fees += fee
            u_c = (nav * tw_c) / p_c
            u_q = (nav * tw_q) / p_q
            u_p = (nav * tw_p) / p_p
            trades += 1
            
    return nav, (nav - 10000.0) / 10000.0, trades, fees

print("\n=== RESOLUTION COMPARISON: 1D (Daily) vs. 1H (Hourly) ===")
print("Same Period (2024-04-11 ~ 2026-09-07, ~2.5 Years, $10,000 Initial Capital)")

for th_pct, th in [('1%', 0.01), ('2%', 0.02), ('5%', 0.05)]:
    nav_1d_5z, ret_1d_5z, tr_1d_5z, fee_1d_5z = run_sim(daily_bars, True, th)
    nav_1h_5z, ret_1h_5z, tr_1h_5z, fee_1h_5z = run_sim(common_1h, True, th)
    
    nav_1d_eq, ret_1d_eq, tr_1d_eq, fee_1d_eq = run_sim(daily_bars, False, th)
    nav_1h_eq, ret_1h_eq, tr_1h_eq, fee_1h_eq = run_sim(common_1h, False, th)
    
    print(f"\n--- Threshold: {th_pct} ---")
    print(f"5-Zone (1D Daily):  Final=${nav_1d_5z:.2f} ({ret_1d_5z*100:+.2f}%), Trades={tr_1d_5z}, Fees=${fee_1d_5z:.2f}")
    print(f"5-Zone (1H Hourly): Final=${nav_1h_5z:.2f} ({ret_1h_5z*100:+.2f}%), Trades={tr_1h_5z}, Fees=${fee_1h_5z:.2f}")
    print(f"Static (1D Daily):  Final=${nav_1d_eq:.2f} ({ret_1d_eq*100:+.2f}%), Trades={tr_1d_eq}, Fees=${fee_1d_eq:.2f}")
    print(f"Static (1H Hourly): Final=${nav_1h_eq:.2f} ({ret_1h_eq*100:+.2f}%), Trades={tr_1h_eq}, Fees=${fee_1h_eq:.2f}")
