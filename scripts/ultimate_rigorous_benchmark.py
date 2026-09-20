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
sol_map = load_json('SOLUSDT_1d.json')
aave_map = load_json('AAVEUSDT_1d.json')
link_map = load_json('LINKUSDT_1d.json')
near_map = load_json('NEARUSDT_1d.json')
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

# Build master daily timeline
all_dates = sorted(list(set(btc_map.keys()) & set(paxg_map.keys()) & set(btc_ma200.keys())))
start_idx = next(i for i, d in enumerate(all_dates) if d >= '2021-09-20')
all_dates = all_dates[start_idx:]

master_days = []
last_qqq = qqq_map['2021-09-20']

for i in range(len(all_dates)):
    d_str = all_dates[i]
    dt = datetime.datetime.strptime(d_str, '%Y-%m-%d').date()
    is_weekend = (dt.weekday() >= 5) # 5=Sat, 6=Sun
    
    # QQQ only updates on weekdays
    is_qqq_trading = (d_str in qqq_map and not is_weekend)
    if d_str in qqq_map:
        last_qqq = qqq_map[d_str]
        
    p_btc = btc_map[d_str]
    ma = btc_ma200[d_str]
    raw_r = p_btc / ma
    
    # Calculate 72h (3-day) SMA of R to prevent whipsaw
    if len(master_days) >= 2:
        r_sma72 = (raw_r + master_days[-1]['raw_r'] + master_days[-2]['raw_r']) / 3.0
    elif len(master_days) == 1:
        r_sma72 = (raw_r + master_days[-1]['raw_r']) / 2.0
    else:
        r_sma72 = raw_r
        
    master_days.append({
        'date': d_str,
        'dt': dt,
        'is_weekend': is_weekend,
        'is_qqq_trading': is_qqq_trading,
        'BTC': p_btc,
        'ETH': eth_map.get(d_str, p_btc),
        'BNB': bnb_map.get(d_str, p_btc),
        'SOL': sol_map.get(d_str, p_btc),
        'AAVE': aave_map.get(d_str, p_btc),
        'LINK': link_map.get(d_str, p_btc),
        'NEAR': near_map.get(d_str, p_btc),
        'PAXG': paxg_map[d_str],
        'QQQ': last_qqq,
        'raw_r': raw_r,
        'r_sma72': r_sma72
    })

def get_zone_from_r(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

def simulate_rigorous_bot(days, coin_key, is_5z, zone_weights, static_weights, initial_cap=1000.0):
    nav = initial_cap
    z0 = get_zone_from_r(days[0]['r_sma72'])
    cur_z = z0
    
    w_c, w_q, w_p = zone_weights[z0] if is_5z else static_weights
    u_c = (nav * w_c) / days[0][coin_key]
    u_q = (nav * w_q) / days[0]['QQQ']
    u_p = (nav * w_p) / days[0]['PAXG']
    
    nav_history = [nav]
    trades = 0
    fee_rate = 0.001 # 10 bps standard Binance spot fee
    slippage_zone = 0.0005 # 5 bps extra slippage on zone transition
    
    for i in range(1, len(days)):
        d = days[i]
        p_c = d[coin_key]
        p_q = d['QQQ']
        p_p = d['PAXG']
        
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        cur_wc = val_c / nav
        cur_wq = val_q / nav
        cur_wp = val_p / nav
        
        if is_5z:
            # 72h SMA determines zone to prevent whipsaw
            new_z = get_zone_from_r(d['r_sma72'])
            zone_changed = (new_z != cur_z)
            cur_z = new_z
            tw_c, tw_q, tw_p = zone_weights[cur_z]
        else:
            zone_changed = False
            tw_c, tw_q, tw_p = static_weights
            
        drift = max(abs(cur_wc - tw_c), abs(cur_wq - tw_q), abs(cur_wp - tw_p))
        
        # Rigorous Execution Rule:
        # If today is weekend/holiday and QQQ is closed:
        # QQQ cannot be traded. We can only rebalance between Coin and PAXG if drift between them is high!
        # When Monday arrives (QQQ trading open), full 3-asset rebalancing executes.
        if zone_changed or drift >= 0.01:
            if not d['is_qqq_trading']:
                # Weekend lock: rebalance only between Coin and PAXG if needed, keeping QQQ units fixed
                # Target ratio between Coin and PAXG: tw_c : tw_p
                target_ratio_cp = tw_c / (tw_c + tw_p) if (tw_c + tw_p) > 0 else 0.5
                avail_nav = val_c + val_p
                tgt_c = avail_nav * target_ratio_cp
                tgt_p = avail_nav * (1.0 - target_ratio_cp)
                
                drift_weekend = abs(val_c - tgt_c) / avail_nav if avail_nav > 0 else 0
                if drift_weekend >= 0.015: # slightly higher threshold on weekends
                    trade_vol = (abs(tgt_c - val_c) + abs(tgt_p - val_p)) / 2.0
                    fee = trade_vol * fee_rate
                    avail_nav -= fee
                    u_c = (avail_nav * target_ratio_cp) / p_c
                    u_p = (avail_nav * (1.0 - target_ratio_cp)) / p_p
                    nav = u_c * p_c + u_p * p_p + val_q
                    trades += 1
            else:
                # Normal weekday: full 3-way rebalance
                tgt_c = nav * tw_c
                tgt_q = nav * tw_q
                tgt_p = nav * tw_p
                
                trade_vol = (abs(tgt_c - val_c) + abs(tgt_q - val_q) + abs(tgt_p - val_p)) / 2.0
                fee = trade_vol * fee_rate
                if zone_changed:
                    fee += trade_vol * slippage_zone # apply zone slippage penalty
                nav -= fee
                
                u_c = (nav * tw_c) / p_c
                u_q = (nav * tw_q) / p_q
                u_p = (nav * tw_p) / p_p
                trades += 1
                
        nav_history.append(nav)
        
    tot_ret = (nav - initial_cap) / initial_cap
    n_years = len(days) / 365.25
    cagr = ((nav / initial_cap) ** (1.0 / n_years)) - 1.0 if nav > 0 else -1.0
    
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
        'final': nav,
        'tot_ret': tot_ret,
        'cagr': cagr,
        'mdd': mdd,
        'sharpe': sharpe,
        'calmar': calmar,
        'trades': trades,
        'nav_history': nav_history
    }

# Complete fleet definition
bot_definitions = [
    ('BTC', 'Core 1 (BTC)', 2500.0, {
        0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.45, 0.35, 0.20), 3: (0.30, 0.35, 0.35), 4: (0.05, 0.30, 0.65)
    }),
    ('ETH', 'Core 2 (ETH)', 2500.0, {
        0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.40, 0.35, 0.25), 3: (0.25, 0.35, 0.40), 4: (0.05, 0.30, 0.65)
    }),
    ('BNB', 'Alpha 1 (BNB)', 1000.0, {
        0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)
    }),
    ('AAVE', 'Alpha 2 (AAVE)', 1000.0, {
        0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)
    }),
    ('LINK', 'Alpha 3 (LINK)', 1000.0, {
        0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)
    }),
    ('NEAR', 'Alpha 4 (NEAR)', 1000.0, {
        0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)
    }),
    ('SOL', 'Alpha 5 (SOL)', 1000.0, {
        0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)
    })
]

def simulate_portfolio_scenario(start_date, end_date='2026-09-07'):
    scenario_days = [d for d in master_days if start_date <= d['date'] <= end_date]
    if len(scenario_days) < 30: return None
    
    # 1. 5-Zone Fleet
    nav_5z_tot = [0.0] * len(scenario_days)
    # 2. Static 1/3 Fleet (33.3% / 33.3% / 33.3%)
    nav_eq_tot = [0.0] * len(scenario_days)
    # 3. Static 50% Coin (50% / 25% / 25%)
    nav_50_tot = [0.0] * len(scenario_days)
    
    for ckey, label, cap, zw in bot_definitions:
        r_5z = simulate_rigorous_bot(scenario_days, ckey, True, zw, (0.3333, 0.3333, 0.3334), initial_cap=cap)
        r_eq = simulate_rigorous_bot(scenario_days, ckey, False, zw, (0.3333, 0.3333, 0.3334), initial_cap=cap)
        r_50 = simulate_rigorous_bot(scenario_days, ckey, False, zw, (0.50, 0.25, 0.25), initial_cap=cap)
        
        for k in range(len(scenario_days)):
            nav_5z_tot[k] += r_5z['nav_history'][k]
            nav_eq_tot[k] += r_eq['nav_history'][k]
            nav_50_tot[k] += r_50['nav_history'][k]
            
    def get_summary(history, initial=10000.0):
        final = history[-1]
        ret = (final - initial) / initial
        n_years = len(history) / 365.25
        cagr = ((final / initial) ** (1.0 / n_years)) - 1.0 if final > 0 else 0
        peak = history[0]
        mdd = 0.0
        d_rets = []
        for j in range(1, len(history)):
            if history[j] > peak: peak = history[j]
            dd = (peak - history[j]) / peak
            if dd > mdd: mdd = dd
            d_rets.append(history[j] / history[j-1] - 1.0)
        mean_r = sum(d_rets) / len(d_rets)
        var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
        ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
        sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
        calmar = cagr / mdd if mdd > 0 else 0
        return {'final': final, 'ret': ret, 'cagr': cagr, 'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar}
        
    return {
        'start_date': start_date,
        'days': len(scenario_days),
        '5Z': get_summary(nav_5z_tot),
        'Static_1_3': get_summary(nav_eq_tot),
        'Static_50': get_summary(nav_50_tot)
    }

scenarios = [
    ('2021-09-20', '全週期5年 (2021牛頂~2026)'),
    ('2022-11-21', '熊市大底起步 (FTX破產 16,000U~2026)'),
    ('2023-10-16', '初牛啟動起步 (BTC突破 28,000U~2026)'),
    ('2024-03-14', '高檔洗盤起步 (BTC創歷史新高 73,000U~2026)')
]

print("=== RIGOROUS MULTI-START BENCHMARK RESULTS (WEEKEND LOCK + 72H SMA + SLIPPAGE) ===")
for s_date, desc in scenarios:
    res = simulate_portfolio_scenario(s_date)
    print(f"\n[Scenario]: {desc} (Total {res['days']} days)")
    print(f"{'Strategy':<22} | {'Final NAV ($10k)':<18} | {'Total Ret':<10} | {'CAGR':<8} | {'MDD':<8} | {'Sharpe':<6} | {'Calmar':<6}")
    print("-" * 88)
    for k, name in [('5Z', '5-Zone Dynamic'), ('Static_1_3', 'Static 1/3 (33/33/33)'), ('Static_50', 'Static 50% (50/25/25)')]:
        s = res[k]
        print(f"{name:<22} | ${s['final']:>16.2f} | {s['ret']*100:>8.2f}% | {s['cagr']*100:>6.2f}% | {s['mdd']*100:>6.2f}% | {s['sharpe']:>6.3f} | {s['calmar']:>6.3f}")
