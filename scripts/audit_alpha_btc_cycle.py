import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

def load_token(fname):
    p = os.path.join(CACHE_DIR, fname)
    if not os.path.exists(p): return None
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {x['date']: x['c'] for x in data if 'date' in x}

btc_map = load_token('BTCUSDT_1d.json')
paxg_map = load_token('PAXGUSDT_1d.json')
qqq_map = load_token('QQQ_1d.json')

with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_raw = json.load(f)
btc_dates = sorted(btc_raw, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_dates)):
    if i >= 199:
        w = btc_dates[i-199:i+1]
        btc_ma200[btc_dates[i]['date']] = sum(x['c'] for x in w) / 200.0

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

def test_coin(coin_sym, fname, z_weights):
    coin_map = load_token(fname)
    if not coin_map: return None
    
    dates = sorted(list(set(coin_map.keys()) & set(btc_map.keys()) & set(paxg_map.keys()) & set(btc_ma200.keys())))
    if len(dates) < 200: return None
    
    days = []
    last_qqq = qqq_map.get(dates[0], 400.0)
    for d in dates:
        if d in qqq_map: last_qqq = qqq_map[d]
        days.append({
            'date': d,
            'p_c': coin_map[d],
            'p_b': btc_map[d],
            'p_q': last_qqq,
            'p_p': paxg_map[d],
            'r': btc_map[d] / btc_ma200[d]
        })
        
    def sim(is_5z, static_w=(0.3333, 0.3333, 0.3334)):
        nav = 10000.0
        z0 = get_zone(days[0]['r'])
        cur_z = z0
        w_c, w_q, w_p = z_weights[z0] if is_5z else static_w
        u_c = (nav * w_c) / days[0]['p_c']
        u_q = (nav * w_q) / days[0]['p_q']
        u_p = (nav * w_p) / days[0]['p_p']
        nav_hist = [nav]
        trades = 0
        
        for i in range(1, len(days)):
            d = days[i]
            p_c, p_q, p_p = d['p_c'], d['p_q'], d['p_p']
            val_c = u_c * p_c
            val_q = u_q * p_q
            val_p = u_p * p_p
            nav = val_c + val_q + val_p
            
            if is_5z:
                new_z = get_zone(d['r'])
                drift = max(abs(val_c/nav - z_weights[new_z][0]), abs(val_q/nav - z_weights[new_z][1]), abs(val_p/nav - z_weights[new_z][2]))
                if new_z != cur_z or drift >= 0.01:
                    cur_z = new_z
                    tw_c, tw_q, tw_p = z_weights[cur_z]
                    t_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                    nav -= t_vol * 0.001
                    u_c = (nav * tw_c) / p_c
                    u_q = (nav * tw_q) / p_q
                    u_p = (nav * tw_p) / p_p
                    trades += 1
            else:
                drift = max(abs(val_c/nav - static_w[0]), abs(val_q/nav - static_w[1]), abs(val_p/nav - static_w[2]))
                if drift >= 0.01:
                    tw_c, tw_q, tw_p = static_w
                    t_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                    nav -= t_vol * 0.001
                    u_c = (nav * tw_c) / p_c
                    u_q = (nav * tw_q) / p_q
                    u_p = (nav * tw_p) / p_p
                    trades += 1
            nav_hist.append(nav)
            
        tot_ret = (nav - 10000.0) / 10000.0
        peak = nav_hist[0]
        mdd = 0.0
        for n in nav_hist:
            if n > peak: peak = n
            dd = (peak - n) / peak
            if dd > mdd: mdd = dd
        return nav, tot_ret, mdd, trades

    nav_5z, ret_5z, mdd_5z, tr_5z = sim(True)
    nav_st, ret_st, mdd_st, tr_st = sim(False)
    
    # Calculate correlation of daily log returns between Coin and BTC
    ret_c = [math.log(days[i]['p_c'] / days[i-1]['p_c']) for i in range(1, len(days))]
    ret_b = [math.log(days[i]['p_b'] / days[i-1]['p_b']) for i in range(1, len(days))]
    mean_c = sum(ret_c) / len(ret_c)
    mean_b = sum(ret_b) / len(ret_b)
    cov = sum((ret_c[i] - mean_c) * (ret_b[i] - mean_b) for i in range(len(ret_c)))
    var_c = sum((r - mean_c)**2 for r in ret_c)
    var_b = sum((r - mean_b)**2 for r in ret_b)
    corr = cov / math.sqrt(var_c * var_b) if var_c > 0 and var_b > 0 else 0
    
    # Coin buy & hold return
    hodl_ret = (days[-1]['p_c'] - days[0]['p_c']) / days[0]['p_c']
    
    return {
        'sym': coin_sym,
        'days': len(days),
        'start_date': days[0]['date'],
        'end_date': days[-1]['date'],
        'corr_btc': corr,
        'hodl_ret': hodl_ret,
        'nav_5z': nav_5z,
        'ret_5z': ret_5z,
        'mdd_5z': mdd_5z,
        'nav_st': nav_st,
        'ret_st': ret_st,
        'mdd_st': mdd_st,
        'diff_pct': (ret_5z - ret_st) * 100
    }

# Alpha weights
weights_alpha = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.35, 0.35, 0.30),
    3: (0.20, 0.40, 0.40),
    4: (0.05, 0.25, 0.70)
}

weights_core_btc = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.45, 0.35, 0.20),
    3: (0.30, 0.35, 0.35),
    4: (0.05, 0.30, 0.65)
}

test_list = [
    ('BTC', 'BTCUSDT_1d.json', weights_core_btc),
    ('ETH', 'ETHUSDT_1d.json', weights_alpha),
    ('BNB', 'BNBUSDT_1d.json', weights_alpha),
    ('SOL', 'SOLUSDT_1d.json', weights_alpha),
    ('AAVE', 'AAVEUSDT_1d.json', weights_alpha),
    ('LINK', 'LINKUSDT_1d.json', weights_alpha),
    ('NEAR', 'NEARUSDT_1d.json', weights_alpha),
    ('UNI', 'UNIUSDT_1d.json', weights_alpha),
    ('TAO', 'TAOUSDT_1d.json', weights_alpha),
    ('PENDLE', 'PENDLEUSDT_1d.json', weights_alpha),
    ('FET', 'FETUSDT_1d.json', weights_alpha),
    ('SUI', 'SUIUSDT_1d.json', weights_alpha),
]

print(f"{'Coin':<8} | {'Days':<5} | {'Corr(BTC)':<9} | {'HODL Ret':<9} | {'5-Zone Ret':<10} | {'Static Ret':<10} | {'5Z vs Static':<12}")
print("-" * 80)
for sym, fname, w in test_list:
    res = test_coin(sym, fname, w)
    if res:
        print(f"{res['sym']:<8} | {res['days']:<5} | {res['corr_btc']:>8.3f}  | {res['hodl_ret']*100:>7.1f}%  | {res['ret_5z']*100:>8.1f}%  | {res['ret_st']*100:>8.1f}%  | {res['diff_pct']:>+10.1f}%")
