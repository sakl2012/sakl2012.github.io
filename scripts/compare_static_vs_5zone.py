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

btc_map = {b['date']: b['c'] for b in btc_raw}
paxg_map = {b['date']: b['c'] for b in paxg_raw}
qqq_map = {b['date']: b['c'] for b in qqq_raw}

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
    if d in btc_map and d in paxg_map and d in btc_ma200:
        days.append({
            'date': d,
            'BTC': btc_map[d],
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

def simulate_static(w_c, w_q, w_p, fee_rate=0.001, rebal_threshold=0.01):
    initial = 10000.0
    nav = initial
    
    u_c = (nav * w_c) / days[0]['BTC']
    u_q = (nav * w_q) / days[0]['QQQ']
    u_p = (nav * w_p) / days[0]['PAXG']
    
    nav_history = [nav]
    trades = 0
    
    for i in range(1, len(days)):
        d = days[i]
        p_c, p_q, p_p = d['BTC'], d['QQQ'], d['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        drift = max(abs(val_c/nav - w_c), abs(val_q/nav - w_q), abs(val_p/nav - w_p))
        if drift >= rebal_threshold:
            trade_vol = (abs(nav*w_c - val_c) + abs(nav*w_q - val_q) + abs(nav*w_p - val_p)) / 2.0
            nav -= trade_vol * fee_rate
            u_c = (nav * w_c) / p_c
            u_q = (nav * w_q) / p_q
            u_p = (nav * w_p) / p_p
            trades += 1
        nav_history.append(nav)
        
    tot_ret = (nav - initial) / initial
    n_years = len(days) / 365.25
    cagr = ((nav / initial) ** (1.0 / n_years)) - 1.0
    
    peak = nav_history[0]
    mdd = 0.0
    d_rets = []
    for j in range(1, len(nav_history)):
        if nav_history[j] > peak: peak = nav_history[j]
        dd = (peak - nav_history[j]) / peak
        if dd > mdd: mdd = dd
        d_rets.append(nav_history[j] / nav_history[j-1] - 1.0)
        
    mean_r = sum(d_rets) / len(d_rets)
    var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
    sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
    calmar = cagr / mdd if mdd > 0 else 0
    
    return {
        'w_c': w_c, 'w_q': w_q, 'w_p': w_p,
        'tot_ret': tot_ret, 'final_nav': nav, 'cagr': cagr,
        'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar,
        'trades': trades
    }

def simulate_5zone():
    zone_weights = {
        0: (0.65, 0.25, 0.10),
        1: (0.50, 0.30, 0.20),
        2: (0.45, 0.35, 0.20),
        3: (0.30, 0.35, 0.35),
        4: (0.05, 0.30, 0.65)
    }
    initial = 10000.0
    nav = initial
    z0 = get_zone(days[0]['R'])
    w_c, w_q, w_p = zone_weights[z0]
    u_c = (nav * w_c) / days[0]['BTC']
    u_q = (nav * w_q) / days[0]['QQQ']
    u_p = (nav * w_p) / days[0]['PAXG']
    cur_z = z0
    nav_history = [nav]
    trades = 0
    
    for i in range(1, len(days)):
        d = days[i]
        p_c, p_q, p_p = d['BTC'], d['QQQ'], d['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
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
        nav_history.append(nav)
        
    tot_ret = (nav - initial) / initial
    n_years = len(days) / 365.25
    cagr = ((nav / initial) ** (1.0 / n_years)) - 1.0
    
    peak = nav_history[0]
    mdd = 0.0
    d_rets = []
    for j in range(1, len(nav_history)):
        if nav_history[j] > peak: peak = nav_history[j]
        dd = (peak - nav_history[j]) / peak
        if dd > mdd: mdd = dd
        d_rets.append(nav_history[j] / nav_history[j-1] - 1.0)
        
    mean_r = sum(d_rets) / len(d_rets)
    var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
    sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
    calmar = cagr / mdd if mdd > 0 else 0
    
    return {
        'tot_ret': tot_ret, 'final_nav': nav, 'cagr': cagr,
        'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar,
        'trades': trades
    }

# Grid search all static combinations (step = 0.05)
best_ret = None
best_sharpe = None
results = []

for c in range(0, 21):
    wc = c * 0.05
    for q in range(0, 21 - c):
        wq = q * 0.05
        wp = round(1.0 - wc - wq, 2)
        if wp < 0: continue
        res = simulate_static(wc, wq, wp)
        results.append(res)
        if best_ret is None or res['tot_ret'] > best_ret['tot_ret']:
            best_ret = res
        if best_sharpe is None or res['sharpe'] > best_sharpe['sharpe']:
            best_sharpe = res

# Also test common popular static allocations:
# 1. 1/3, 1/3, 1/3 (Equal weight)
res_equal = simulate_static(0.3333, 0.3333, 0.3334)
# 2. 50/25/25
res_50_25_25 = simulate_static(0.50, 0.25, 0.25)
# 3. 60/20/20
res_60_20_20 = simulate_static(0.60, 0.20, 0.20)
# 4. 40/30/30
res_40_30_30 = simulate_static(0.40, 0.30, 0.30)
# 5. 100% BTC Buy & Hold
res_btc_hodl = simulate_static(1.0, 0.0, 0.0)
# 6. 5-Zone
res_5z = simulate_5zone()

print("=== COMPARISON RESULTS ===")
print("5-Zone Dynamic:")
print(f"  Final: ${res_5z['final_nav']:.2f}, Ret: {res_5z['tot_ret']*100:.2f}%, CAGR: {res_5z['cagr']*100:.2f}%, MDD: {res_5z['mdd']*100:.2f}%, Sharpe: {res_5z['sharpe']:.3f}, Calmar: {res_5z['calmar']:.3f}")

print("\nBest Static (Highest Return):")
print(f"  Weights: BTC {best_ret['w_c']*100:.0f}% / QQQ {best_ret['w_q']*100:.0f}% / PAXG {best_ret['w_p']*100:.0f}%")
print(f"  Final: ${best_ret['final_nav']:.2f}, Ret: {best_ret['tot_ret']*100:.2f}%, CAGR: {best_ret['cagr']*100:.2f}%, MDD: {best_ret['mdd']*100:.2f}%, Sharpe: {best_ret['sharpe']:.3f}, Calmar: {best_ret['calmar']:.3f}")

print("\nBest Static (Highest Sharpe Ratio):")
print(f"  Weights: BTC {best_sharpe['w_c']*100:.0f}% / QQQ {best_sharpe['w_q']*100:.0f}% / PAXG {best_sharpe['w_p']*100:.0f}%")
print(f"  Final: ${best_sharpe['final_nav']:.2f}, Ret: {best_sharpe['tot_ret']*100:.2f}%, CAGR: {best_sharpe['cagr']*100:.2f}%, MDD: {best_sharpe['mdd']*100:.2f}%, Sharpe: {best_sharpe['sharpe']:.3f}, Calmar: {best_sharpe['calmar']:.3f}")

print("\nCommon Static - Equal Weight (33.3% / 33.3% / 33.3%):")
print(f"  Final: ${res_equal['final_nav']:.2f}, Ret: {res_equal['tot_ret']*100:.2f}%, CAGR: {res_equal['cagr']*100:.2f}%, MDD: {res_equal['mdd']*100:.2f}%, Sharpe: {res_equal['sharpe']:.3f}, Calmar: {res_equal['calmar']:.3f}")

print("\nCommon Static - 50% BTC / 25% QQQ / 25% PAXG:")
print(f"  Final: ${res_50_25_25['final_nav']:.2f}, Ret: {res_50_25_25['tot_ret']*100:.2f}%, CAGR: {res_50_25_25['cagr']*100:.2f}%, MDD: {res_50_25_25['mdd']*100:.2f}%, Sharpe: {res_50_25_25['sharpe']:.3f}, Calmar: {res_50_25_25['calmar']:.3f}")

print("\n100% BTC Buy & Hold:")
print(f"  Final: ${res_btc_hodl['final_nav']:.2f}, Ret: {res_btc_hodl['tot_ret']*100:.2f}%, CAGR: {res_btc_hodl['cagr']*100:.2f}%, MDD: {res_btc_hodl['mdd']*100:.2f}%, Sharpe: {res_btc_hodl['sharpe']:.3f}, Calmar: {res_btc_hodl['calmar']:.3f}")
