import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

def load_token(sym):
    with open(os.path.join(CACHE_DIR, sym), 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {x['date']: x['c'] for x in data if 'date' in x}

btc_map = load_token('BTCUSDT_1d.json')
eth_map = load_token('ETHUSDT_1d.json')
bnb_map = load_token('BNBUSDT_1d.json')
sol_map = load_token('SOLUSDT_1d.json')
aave_map = load_token('AAVEUSDT_1d.json')
link_map = load_token('LINKUSDT_1d.json')
near_map = load_token('NEARUSDT_1d.json')
paxg_map = load_token('PAXGUSDT_1d.json')
qqq_map = load_token('QQQ_1d.json')

# Calculate BTC MA200
with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
    btc_raw = json.load(f)
btc_dates = sorted(btc_raw, key=lambda x: x['date'])
btc_ma200 = {}
for i in range(len(btc_dates)):
    if i >= 199:
        w = btc_dates[i-199:i+1]
        btc_ma200[btc_dates[i]['date']] = sum(x['c'] for x in w) / 200.0

start_dt = datetime.date(2021, 9, 20)
end_dt = datetime.date(2026, 9, 7) # common end date for AAVE/LINK/NEAR

days = []
cur = start_dt
last_qqq = qqq_map['2021-09-20']

while cur <= end_dt:
    d = cur.strftime('%Y-%m-%d')
    if d in qqq_map:
        last_qqq = qqq_map[d]
    if (d in btc_map and d in eth_map and d in bnb_map and d in sol_map and 
        d in aave_map and d in link_map and d in near_map and d in paxg_map and d in btc_ma200):
        days.append({
            'date': d,
            'BTC': btc_map[d],
            'ETH': eth_map[d],
            'BNB': bnb_map[d],
            'SOL': sol_map[d],
            'AAVE': aave_map[d],
            'LINK': link_map[d],
            'NEAR': near_map[d],
            'PAXG': paxg_map[d],
            'QQQ': last_qqq,
            'R': btc_map[d] / btc_ma200[d]
        })
    cur += datetime.timedelta(days=1)

print(f"Loaded {len(days)} common days from {days[0]['date']} to {days[-1]['date']}")

def get_zone(r):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

def simulate_bot(coin_key, is_5z, zone_weights, static_weights=(0.3333, 0.3333, 0.3334), initial_cap=1000.0):
    nav = initial_cap
    z0 = get_zone(days[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zone_weights[z0] if is_5z else static_weights
    u_c = (nav * w_c) / days[0][coin_key]
    u_q = (nav * w_q) / days[0]['QQQ']
    u_p = (nav * w_p) / days[0]['PAXG']
    nav_history = [nav]
    trades = 0
    
    for i in range(1, len(days)):
        d = days[i]
        p_c, p_q, p_p = d[coin_key], d['QQQ'], d['PAXG']
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
    return nav_history, trades

# Webpage Zone Weights:
# Core 1 (BTC)
weights_core_btc = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.45, 0.35, 0.20),
    3: (0.30, 0.35, 0.35),
    4: (0.05, 0.30, 0.65)
}
# Core 2 (ETH)
weights_core_eth = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.40, 0.35, 0.25),
    3: (0.25, 0.35, 0.40),
    4: (0.05, 0.30, 0.65)
}
# Alpha Fleet
weights_alpha = {
    0: (0.65, 0.25, 0.10),
    1: (0.50, 0.30, 0.20),
    2: (0.35, 0.35, 0.30),
    3: (0.20, 0.40, 0.40),
    4: (0.05, 0.25, 0.70)
}

# Entire Portfolio Setup: Initial Capital = 10,000 U
# 50% Core (BTC 2500 U, ETH 2500 U)
# 50% Alpha (BNB 1000 U, AAVE 1000 U, LINK 1000 U, NEAR 1000 U, SOL 1000 U)
bot_configs = [
    ('BTC', 'Core 1 (BTC)', 2500.0, weights_core_btc),
    ('ETH', 'Core 2 (ETH)', 2500.0, weights_core_eth),
    ('BNB', 'Alpha 1 (BNB)', 1000.0, weights_alpha),
    ('AAVE', 'Alpha 2 (AAVE)', 1000.0, weights_alpha),
    ('LINK', 'Alpha 3 (LINK)', 1000.0, weights_alpha),
    ('NEAR', 'Alpha 4 (NEAR)', 1000.0, weights_alpha),
    ('SOL', 'Alpha 5 (SOL)', 1000.0, weights_alpha)
]

def run_fleet(is_5z, static_weights=(0.3333, 0.3333, 0.3334)):
    total_nav_history = [0.0] * len(days)
    bot_results = {}
    tot_trades = 0
    
    for coin_key, label, cap, z_weights in bot_configs:
        nav_hist, tr = simulate_bot(coin_key, is_5z, z_weights, static_weights, initial_cap=cap)
        tot_trades += tr
        bot_results[label] = {
            'initial': cap,
            'final': nav_hist[-1],
            'return': (nav_hist[-1] - cap) / cap,
            'trades': tr
        }
        for i in range(len(days)):
            total_nav_history[i] += nav_hist[i]
            
    # Calculate overall portfolio metrics
    initial = 10000.0
    final = total_nav_history[-1]
    tot_ret = (final - initial) / initial
    n_years = len(days) / 365.25
    cagr = ((final / initial) ** (1.0 / n_years)) - 1.0
    
    peak = total_nav_history[0]
    mdd = 0.0
    d_rets = []
    for j in range(1, len(total_nav_history)):
        if total_nav_history[j] > peak: peak = total_nav_history[j]
        dd = (peak - total_nav_history[j]) / peak
        if dd > mdd: mdd = dd
        d_rets.append(total_nav_history[j] / total_nav_history[j-1] - 1.0)
        
    mean_r = sum(d_rets) / len(d_rets)
    var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
    sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
    calmar = cagr / mdd if mdd > 0 else 0
    
    return {
        'initial': initial,
        'final': final,
        'tot_ret': tot_ret,
        'cagr': cagr,
        'mdd': mdd,
        'sharpe': sharpe,
        'calmar': calmar,
        'trades': tot_trades,
        'bot_results': bot_results
    }

res_full_5z = run_fleet(is_5z=True)
res_full_eq = run_fleet(is_5z=False, static_weights=(0.3333, 0.3333, 0.3334))
res_full_50 = run_fleet(is_5z=False, static_weights=(0.50, 0.25, 0.25))

print("=== COMPLETE WEBPAGE PORTFOLIO (10,000 U) SIMULATION RESULTS ===")
print(f"Period: {days[0]['date']} ~ {days[-1]['date']} ({len(days)} days, ~5 full years)")
print("\n1. 5-Zone Full Fleet (3 Core + Alpha Fleet with Webpage Monotonic Curve):")
print(f"  Final Balance: ${res_full_5z['final']:.2f}")
print(f"  Total Return:  {res_full_5z['tot_ret']*100:+.2f}%")
print(f"  CAGR:          {res_full_5z['cagr']*100:.2f}%")
print(f"  Max Drawdown:  {res_full_5z['mdd']*100:.2f}%")
print(f"  Sharpe Ratio:  {res_full_5z['sharpe']:.3f}")
print(f"  Total Trades:  {res_full_5z['trades']}")

print("\n2. Static Equal Weight Full Fleet (All bots fixed at 33.3% Coin / 33.3% QQQ / 33.3% PAXG):")
print(f"  Final Balance: ${res_full_eq['final']:.2f}")
print(f"  Total Return:  {res_full_eq['tot_ret']*100:+.2f}%")
print(f"  CAGR:          {res_full_eq['cagr']*100:.2f}%")
print(f"  Max Drawdown:  {res_full_eq['mdd']*100:.2f}%")
print(f"  Sharpe Ratio:  {res_full_eq['sharpe']:.3f}")
print(f"  Total Trades:  {res_full_eq['trades']}")

print("\n3. Static 50% Coin Full Fleet (All bots fixed at 50% Coin / 25% QQQ / 25% PAXG):")
print(f"  Final Balance: ${res_full_50['final']:.2f}")
print(f"  Total Return:  {res_full_50['tot_ret']*100:+.2f}%")
print(f"  CAGR:          {res_full_50['cagr']*100:.2f}%")
print(f"  Max Drawdown:  {res_full_50['mdd']*100:.2f}%")
print(f"  Sharpe Ratio:  {res_full_50['sharpe']:.3f}")
print(f"  Total Trades:  {res_full_50['trades']}")

print("\n=== PER-BOT BREAKDOWN UNDER 5-ZONE vs STATIC 1/3 ===")
for k in res_full_5z['bot_results']:
    b_5z = res_full_5z['bot_results'][k]
    b_eq = res_full_eq['bot_results'][k]
    print(f"{k:<18} (Initial ${b_5z['initial']:.0f}):")
    print(f"   5-Zone:     Final=${b_5z['final']:.2f} ({b_5z['return']*100:+.1f}%), Trades={b_5z['trades']}")
    print(f"   Static 1/3: Final=${b_eq['final']:.2f} ({b_eq['return']*100:+.1f}%), Trades={b_eq['trades']}")
