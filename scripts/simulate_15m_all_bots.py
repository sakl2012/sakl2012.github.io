import json
import os
import math
import datetime

CACHE_15M = os.path.join(os.path.dirname(__file__), 'data_cache_15m')
CACHE_1D = os.path.join(os.path.dirname(__file__), 'data_cache')

def load_15m(sym):
    path = os.path.join(CACHE_15M, f"{sym}_15m.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load daily QQQ and BTC for MA200
with open(os.path.join(CACHE_1D, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
    qqq_1d = json.load(f)
with open(os.path.join(CACHE_1D, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_1d = json.load(f)

qqq_by_date = {x['date']: x['c'] for x in qqq_1d}
btc_1d_sorted = sorted(btc_1d, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_1d_sorted)):
    if i >= 199:
        w = btc_1d_sorted[i-199:i+1]
        btc_ma200[btc_1d_sorted[i]['date']] = sum(x['c'] for x in w) / 200.0

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

# Zone weights definition
zw_btc  = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.45, 0.35, 0.20), 3: (0.30, 0.35, 0.35), 4: (0.05, 0.30, 0.65)}
zw_eth  = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.40, 0.35, 0.25), 3: (0.25, 0.35, 0.40), 4: (0.05, 0.30, 0.65)}
zw_tao  = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)}
zw_alpha= {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)}

fleet_specs = [
    ('BTCUSDT', 'Core 1 (BTC)', 2000.0, zw_btc),
    ('ETHUSDT', 'Core 2 (ETH)', 2000.0, zw_eth),
    ('TAOUSDT', 'Core 3 (TAO)', 1000.0, zw_tao),
    ('BNBUSDT', 'Alpha 1 (BNB)', 833.33, zw_alpha),
    ('UNIUSDT', 'Alpha 2 (UNI)', 833.33, zw_alpha),
    ('AAVEUSDT', 'Alpha 3 (AAVE)', 833.33, zw_alpha),
    ('LINKUSDT', 'Alpha 4 (LINK)', 833.33, zw_alpha),
    ('NEARUSDT', 'Alpha 5 (NEAR)', 833.33, zw_alpha),
    ('ONDOUSDT', 'Alpha 6 (ONDO)', 833.33, zw_alpha)
]

def simulate_single_bot_15m(bars, is_5z, zone_weights, static_weights, threshold=0.02, initial_cap=1000.0):
    nav = initial_cap
    z0 = get_zone(bars[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zone_weights[z0] if is_5z else static_weights
    u_c = (nav * w_c) / bars[0]['c']
    u_q = (nav * w_q) / bars[0]['qqq']
    u_p = (nav * w_p) / bars[0]['paxg']
    
    trades = 0
    fees = 0.0
    nav_hist = [nav]
    
    for i in range(1, len(bars)):
        b = bars[i]
        p_c = b['c']
        p_q = b['qqq']
        p_p = b['paxg']
        
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
            tw_c, tw_q, tw_p = zone_weights[cur_z]
        else:
            zone_changed = False
            tw_c, tw_q, tw_p = static_weights
            
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
            
        nav_hist.append(nav)
        
    ret = (nav - initial_cap) / initial_cap
    peak = nav_hist[0]
    mdd = 0.0
    for n in nav_hist:
        if n > peak: peak = n
        dd = (peak - n) / peak
        if dd > mdd: mdd = dd
    return nav, ret, mdd, trades, fees

def run_all_bots():
    print("Loading 15m master data...")
    btc_bars = load_15m('BTCUSDT')
    paxg_bars = load_15m('PAXGUSDT')
    
    if not btc_bars or not paxg_bars:
        print("BTC or PAXG 15m data not ready yet!")
        return
        
    paxg_map = {b['t']: b['c'] for b in paxg_bars}
    
    # Calculate R ratio for each BTC 15m bar
    # 72h SMA = 72 * 4 = 288 15m bars
    btc_master = {}
    r_window = []
    
    # Sort BTC bars
    btc_sorted = sorted(btc_bars, key=lambda x: x['t'])
    last_qqq = 265.0 # Jan 2023 QQQ
    
    for b in btc_sorted:
        t = b['t']
        d_str = b['date']
        day_str = d_str.split(' ')[0]
        
        # Weekend QQQ fixed (forward-fill)
        if day_str in qqq_by_date:
            last_qqq = qqq_by_date[day_str]
            
        ma = btc_ma200.get(day_str, 28000.0)
        raw_r = b['c'] / ma
        r_window.append(raw_r)
        if len(r_window) > 288:
            r_window.pop(0)
        r_sma72 = sum(r_window) / len(r_window)
        
        if t in paxg_map:
            btc_master[t] = {
                't': t,
                'date': d_str,
                'day': day_str,
                'c_btc': b['c'],
                'paxg': paxg_map[t],
                'qqq': last_qqq,
                'R': r_sma72
            }
            
    print(f"Built master BTC timeline: {len(btc_master)} bars")
    
    # Now simulate each bot
    all_bot_results = []
    
    print("\n" + "="*110)
    print("=== USER FLEET: 15-MINUTE K-LINE RIGOROUS SIMULATION (2023-01-01 TO PRESENT) ===")
    print("Condition: QQQ weekend forward-fill, new coins start 1 month after listing, threshold=2%")
    print("="*110)
    
    for sym, label, initial_cap, zw in fleet_specs:
        raw_bars = load_15m(sym)
        if not raw_bars:
            print(f"Skipping {sym}: data not found")
            continue
            
        sorted_bars = sorted(raw_bars, key=lambda x: x['t'])
        first_t = sorted_bars[0]['t']
        first_dt = datetime.datetime.fromtimestamp(first_t/1000, datetime.timezone.utc)
        
        # Rule: "沒有發行的幣，從發行後一個月開始比較"
        # If token was listed after 2023-01-01, add 30 days (1 month)
        if first_dt.date() > datetime.date(2023, 1, 1):
            start_t = first_t + (30 * 86400 * 1000) # 30 days later
            start_dt = datetime.datetime.fromtimestamp(start_t/1000, datetime.timezone.utc)
            start_note = f"Listed {first_dt.strftime('%Y-%m-%d')} (+1m Buffer -> Started {start_dt.strftime('%Y-%m-%d')})"
        else:
            start_t = first_t
            start_dt = first_dt
            start_note = f"Full Period (Started {start_dt.strftime('%Y-%m-%d')})"
            
        # Filter bars starting from start_t and align with btc_master
        bot_bars = []
        for b in sorted_bars:
            t = b['t']
            if t >= start_t and t in btc_master:
                bot_bars.append({
                    't': t,
                    'date': b['date'],
                    'c': b['c'],
                    'paxg': btc_master[t]['paxg'],
                    'qqq': btc_master[t]['qqq'],
                    'R': btc_master[t]['R']
                })
                
        if len(bot_bars) < 100:
            print(f"Insufficient bars for {sym}")
            continue
            
        # Run 4 Strategies:
        # 1. 5-Zone Dynamic
        n_5z, r_5z, m_5z, t_5z, f_5z = simulate_single_bot_15m(bot_bars, True, zw, None, threshold=0.02, initial_cap=initial_cap)
        # 2. Static Equal 1/3 (33.3% / 33.3% / 33.3%)
        n_eq, r_eq, m_eq, t_eq, f_eq = simulate_single_bot_15m(bot_bars, False, zw, (0.3333, 0.3333, 0.3334), threshold=0.02, initial_cap=initial_cap)
        # 3. Static Dual Anchor (20% / 40% / 40%)
        n_20, r_20, m_20, t_20, f_20 = simulate_single_bot_15m(bot_bars, False, zw, (0.20, 0.40, 0.40), threshold=0.02, initial_cap=initial_cap)
        # 4. Static 35/35/30
        n_35, r_35, m_35, t_35, f_35 = simulate_single_bot_15m(bot_bars, False, zw, (0.35, 0.35, 0.30), threshold=0.02, initial_cap=initial_cap)
        
        all_bot_results.append({
            'sym': sym, 'label': label, 'cap': initial_cap,
            'start_note': start_note, 'bars': len(bot_bars),
            '5Z': (n_5z, r_5z, m_5z, t_5z),
            'Eq': (n_eq, r_eq, m_eq, t_eq),
            'Dual': (n_20, r_20, m_20, t_20),
            'S35': (n_35, r_35, m_35, t_35)
        })
        
        print(f"\n[{label}] ({sym}) - Initial Cap: ${initial_cap:.2f} U | {start_note} | Bars: {len(bot_bars)}")
        print(f"{'Strategy':<22} | {'Final NAV':<14} | {'Return':<9} | {'MDD':<8} | {'Trades':<8}")
        print("-" * 70)
        print(f"{'5-Zone Dynamic':<22} | ${n_5z:>11.2f} U | {r_5z*100:>7.2f}% | {m_5z*100:>6.2f}% | {t_5z:>6}")
        print(f"{'Static 1/3 (33/33/33)':<22} | ${n_eq:>11.2f} U | {r_eq*100:>7.2f}% | {m_eq*100:>6.2f}% | {t_eq:>6}")
        print(f"{'Static Dual (20/40/40)':<22} | ${n_20:>11.2f} U | {r_20*100:>7.2f}% | {m_20*100:>6.2f}% | {t_20:>6}")
        print(f"{'Static 35/35/30':<22} | ${n_35:>11.2f} U | {r_35*100:>7.2f}% | {m_35*100:>6.2f}% | {t_35:>6}")

    # Output summary JSON
    with open(os.path.join(os.path.dirname(__file__), 'sim_15m_results.json'), 'w', encoding='utf-8') as fp:
        json.dump(all_bot_results, fp, indent=2)

if __name__ == '__main__':
    run_all_bots()
