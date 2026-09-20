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

def simulate_single_bot_15m(bars, is_5z, zone_weights, static_weights, threshold=0.01, initial_cap=1000.0):
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

def run_comparison():
    btc_bars = load_15m('BTCUSDT')
    paxg_bars = load_15m('PAXGUSDT')
    paxg_map = {b['t']: b['c'] for b in paxg_bars}
    
    btc_master = {}
    r_window = []
    btc_sorted = sorted(btc_bars, key=lambda x: x['t'])
    last_qqq = 265.0
    
    for b in btc_sorted:
        t = b['t']
        d_str = b['date']
        day_str = d_str.split(' ')[0]
        
        if day_str in qqq_by_date:
            last_qqq = qqq_by_date[day_str]
            
        ma = btc_ma200.get(day_str, b['c'])
        r_raw = b['c'] / ma if ma > 0 else 1.0
        
        r_window.append(r_raw)
        if len(r_window) > 288:
            r_window.pop(0)
        r_sma = sum(r_window) / len(r_window)
        
        if t in paxg_map:
            btc_master[t] = {
                'qqq': last_qqq,
                'paxg': paxg_map[t],
                'R': r_sma
            }
            
    results = []
    
    for sym, label, initial_cap, zw in fleet_specs:
        bars = load_15m(sym)
        sorted_bars = sorted(bars, key=lambda x: x['t'])
        first_t = sorted_bars[0]['t']
        first_dt = datetime.datetime.fromtimestamp(first_t / 1000, tz=datetime.timezone.utc)
        
        if first_dt.year > 2023 or (first_dt.year == 2023 and first_dt.month > 1):
            start_dt = first_dt + datetime.timedelta(days=30)
            start_t = int(start_dt.timestamp() * 1000)
            start_note = f"Listed {first_dt.strftime('%Y-%m-%d')} (+1m Buffer -> Started {start_dt.strftime('%Y-%m-%d')})"
        else:
            start_dt = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
            start_t = int(start_dt.timestamp() * 1000)
            start_note = f"Full Period (Started {start_dt.strftime('%Y-%m-%d')})"
            
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
                
        # 1% simulations
        n_5z_1, r_5z_1, m_5z_1, t_5z_1, f_5z_1 = simulate_single_bot_15m(bot_bars, True, zw, None, threshold=0.01, initial_cap=initial_cap)
        n_eq_1, r_eq_1, m_eq_1, t_eq_1, f_eq_1 = simulate_single_bot_15m(bot_bars, False, zw, (0.3333, 0.3333, 0.3334), threshold=0.01, initial_cap=initial_cap)
        n_35_1, r_35_1, m_35_1, t_35_1, f_35_1 = simulate_single_bot_15m(bot_bars, False, zw, (0.35, 0.35, 0.30), threshold=0.01, initial_cap=initial_cap)

        # 2% simulations
        n_5z_2, r_5z_2, m_5z_2, t_5z_2, f_5z_2 = simulate_single_bot_15m(bot_bars, True, zw, None, threshold=0.02, initial_cap=initial_cap)
        n_eq_2, r_eq_2, m_eq_2, t_eq_2, f_eq_2 = simulate_single_bot_15m(bot_bars, False, zw, (0.3333, 0.3333, 0.3334), threshold=0.02, initial_cap=initial_cap)
        n_35_2, r_35_2, m_35_2, t_35_2, f_35_2 = simulate_single_bot_15m(bot_bars, False, zw, (0.35, 0.35, 0.30), threshold=0.02, initial_cap=initial_cap)
        
        results.append({
            'sym': sym, 'label': label, 'cap': initial_cap, 'start_note': start_note,
            '5Z_1': (n_5z_1, r_5z_1, m_5z_1, t_5z_1, f_5z_1),
            '5Z_2': (n_5z_2, r_5z_2, m_5z_2, t_5z_2, f_5z_2),
            'Eq_1': (n_eq_1, r_eq_1, m_eq_1, t_eq_1, f_eq_1),
            'Eq_2': (n_eq_2, r_eq_2, m_eq_2, t_eq_2, f_eq_2),
            'S35_1': (n_35_1, r_35_1, m_35_1, t_35_1, f_35_1),
            'S35_2': (n_35_2, r_35_2, m_35_2, t_35_2, f_35_2)
        })

    with open(os.path.join(os.path.dirname(__file__), 'sim_1pct_vs_2pct_results.json'), 'w', encoding='utf-8') as fp:
        json.dump(results, fp, indent=2)

if __name__ == '__main__':
    run_comparison()
