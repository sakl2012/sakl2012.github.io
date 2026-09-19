import json, os, math
from datetime import datetime, timezone

# -------------------------------------------------------------
# 1. 加載所有關聯代幣 (含 PENDLE 與 UNI)
# -------------------------------------------------------------
tokens = ['BTC', 'SOL', 'TAO', 'AAVE', 'LINK', 'NEAR', 'SUI', 'PAXG', 'PENDLE', 'UNI']
cache_1h = 'scripts/data_cache_1h'
data_1h = {}
for s in tokens:
    with open(os.path.join(cache_1h, f'{s}USDT_1h.json')) as f:
        data_1h[s] = json.load(f)

common_ts = set(x['t'] for x in data_1h['TAO'])
for s in tokens:
    common_ts = common_ts & set(x['t'] for x in data_1h[s])
sorted_ts = sorted(list(common_ts))

bars = {t: {} for t in sorted_ts}
for s in tokens:
    for bar in data_1h[s]:
        if bar['t'] in bars:
            bars[bar['t']][s] = bar

# -------------------------------------------------------------
# 2. 計算 BTC MA200 與 72h SMA
# -------------------------------------------------------------
with open('scripts/data_cache/BTCUSDT_1d.json') as f:
    btc_1d = json.load(f)
btc_1d_dict = {row['date']: row['c'] for row in btc_1d}
all_dates = sorted(list(btc_1d_dict.keys()))
daily_ma200 = {}
for i, d in enumerate(all_dates):
    if i >= 199:
        daily_ma200[d] = sum(btc_1d_dict[all_dates[j]] for j in range(i-199, i+1)) / 200.0

btc_closes = [bars[t]['BTC']['c'] for t in sorted_ts]
sma72_dict = {}
for i, t in enumerate(sorted_ts):
    if i >= 71:
        sma72_dict[t] = sum(btc_closes[i-71:i+1]) / 72.0
    else:
        sma72_dict[t] = sum(btc_closes[:i+1]) / float(i+1)

# -------------------------------------------------------------
# 3. 加載真實資金費率
# -------------------------------------------------------------
cache_funding = 'scripts/data_cache_funding'
funding_dict = {}
for s in ['BTC', 'SOL', 'AAVE', 'LINK', 'NEAR', 'SUI', 'PENDLE', 'UNI']:
    filepath = os.path.join(cache_funding, f'{s}USDT_funding.json')
    if os.path.exists(filepath):
        with open(filepath) as f:
            funding_dict[s] = {row['t']: row['r'] for row in json.load(f)}

# -------------------------------------------------------------
# 4. 動態非線性滑點 + Taker 手續費
# -------------------------------------------------------------
def get_friction_rate(token, bar):
    base_taker = 0.0010
    volatility = (bar['h'] - bar['l']) / bar['l'] if bar['l'] > 0 else 0.005
    base_slip = 0.0005
    if token in ['PAXG', 'TAO', 'PENDLE']:
        base_slip += 0.0005
    if volatility > 0.015:
        impact = min(0.0030, (volatility - 0.015) * 0.15)
        base_slip += impact
    return base_taker + base_slip

# -------------------------------------------------------------
# 5. 高保真回測引擎 (含 24h 冷卻 + 72h SMA + 連續2小時確認)
# -------------------------------------------------------------
def run_simulation(zone_rules, name):
    initial_cap = 10000.0
    cap_A = initial_cap * 0.20
    cap_B = initial_cap * 0.55
    cap_C = initial_cap * 0.25
    
    t0 = sorted_ts[0]
    d0_str = datetime.fromtimestamp(t0/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    ma0 = daily_ma200.get(d0_str, 50000.0)
    p0 = {s: bars[t0][s]['c'] for s in tokens}
    r0 = p0['BTC'] / ma0
    
    def get_zone(r):
        if r < 0.80: return 0
        elif r < 1.00: return 1
        elif r < 1.25: return 2
        elif r < 1.40: return 3
        else: return 4

    z0 = get_zone(r0)
    holdings_A = {s: (cap_A * w) / p0[s] for s, w in zone_rules[z0]['A'].items()}
    holdings_B = {s: (cap_B * w) / p0[s] for s, w in zone_rules[z0]['B'].items()}
    holdings_C = {s: (cap_C * w) / p0[s] for s, w in zone_rules[z0]['C'].items()}
    
    curr_zone = z0
    last_switch_t = 0
    hourly_portfolio_values = []
    zone_switches = 0
    total_friction_fees = 0.0
    total_funding_income = 0.0
    
    consecutive_signals = 0
    pending_target_zone = None
    
    for i, t in enumerate(sorted_ts):
        p = {s: bars[t][s]['c'] for s in tokens}
        d_str = datetime.fromtimestamp(t/1000, tz=timezone.utc).strftime('%Y-%m-%d')
        ma = daily_ma200.get(d_str, daily_ma200.get('2024-04-11', 50000.0))
        
        r_sma72 = sma72_dict[t] / ma
        target_z = get_zone(r_sma72)
        
        val_A = sum(holdings_A[s] * p[s] for s in holdings_A)
        val_B = sum(holdings_B[s] * p[s] for s in holdings_B)
        val_C = sum(holdings_C[s] * p[s] for s in holdings_C)
        
        # B 倉 50% Delta-Neutral 套利對沖收取費率
        for s in ['SOL', 'TAO']:
            if s in holdings_B:
                notional = holdings_B[s] * p[s]
                f_rate = funding_dict.get(s, {}).get(t, 0.0)
                gain = notional * 0.5 * f_rate
                total_funding_income += gain
                val_B += gain
        
        current_total = val_A + val_B + val_C
        hourly_portfolio_values.append(current_total)
        
        hours_since_last_switch = (t - last_switch_t) / (1000 * 3600)
        
        if target_z != curr_zone and hours_since_last_switch >= 24:
            if pending_target_zone == target_z:
                consecutive_signals += 1
            else:
                pending_target_zone = target_z
                consecutive_signals = 1
                
            if consecutive_signals >= 2:
                curr_zone = target_z
                last_switch_t = t
                zone_switches += 1
                pending_target_zone = None
                consecutive_signals = 0
                
                for sub, h_dict, cap_val in [('A', holdings_A, val_A), ('B', holdings_B, val_B), ('C', holdings_C, val_C)]:
                    tgt = zone_rules[curr_zone][sub]
                    all_sub_tokens = set(list(tgt.keys()) + list(h_dict.keys()))
                    sub_fee = 0.0
                    for s in all_sub_tokens:
                        curr_amt_val = h_dict.get(s, 0.0) * p[s]
                        tgt_amt_val = cap_val * tgt.get(s, 0.0)
                        diff_val = abs(tgt_amt_val - curr_amt_val)
                        if diff_val > 1.0:
                            f_rate = get_friction_rate(s, bars[t][s])
                            sub_fee += diff_val * f_rate
                    
                    total_friction_fees += sub_fee
                    net_cap = cap_val - sub_fee
                    if sub == 'A': holdings_A = {s: (net_cap * w) / p[s] for s, w in tgt.items()}
                    elif sub == 'B': holdings_B = {s: (net_cap * w) / p[s] for s, w in tgt.items()}
                    elif sub == 'C': holdings_C = {s: (net_cap * w) / p[s] for s, w in tgt.items()}
        else:
            consecutive_signals = 0
            
            # 日常 00:00 偏離度平衡
            dt_obj = datetime.fromtimestamp(t/1000, tz=timezone.utc)
            if dt_obj.hour == 0:
                tgt_C = zone_rules[curr_zone]['C']
                weights_C = {s: (holdings_C[s] * p[s]) / val_C for s in holdings_C}
                dev_C = max(abs(weights_C[s] - tgt_C.get(s, 0.0)) for s in set(list(weights_C.keys()) + list(tgt_C.keys())))
                if dev_C >= 0.10:
                    c_fee = sum(abs(val_C * tgt_C.get(s, 0.0) - holdings_C.get(s, 0.0) * p[s]) * get_friction_rate(s, bars[t][s]) for s in set(list(tgt_C.keys()) + list(holdings_C.keys()))) / 2.0
                    total_friction_fees += c_fee
                    net_C = val_C - c_fee
                    holdings_C = {s: (net_C * w) / p[s] for s, w in tgt_C.items()}
                    
                tgt_B = zone_rules[curr_zone]['B']
                weights_B = {s: (holdings_B[s] * p[s]) / val_B for s in holdings_B}
                dev_B = max(abs(weights_B[s] - tgt_B.get(s, 0.0)) for s in set(list(weights_B.keys()) + list(tgt_B.keys())))
                if dev_B >= 0.05:
                    b_fee = sum(abs(val_B * tgt_B.get(s, 0.0) - holdings_B.get(s, 0.0) * p[s]) * get_friction_rate(s, bars[t][s]) for s in set(list(tgt_B.keys()) + list(holdings_B.keys()))) / 2.0
                    total_friction_fees += b_fee
                    net_B = val_B - b_fee
                    holdings_B = {s: (net_B * w) / p[s] for s, w in tgt_B.items()}

    total_ret = (hourly_portfolio_values[-1] / hourly_portfolio_values[0]) - 1.0
    total_hours = len(sorted_ts)
    total_days = total_hours / 24.0
    cagr = ((hourly_portfolio_values[-1] / hourly_portfolio_values[0]) ** (365.0 / total_days)) - 1.0
    
    peaks = [hourly_portfolio_values[0]]
    for v in hourly_portfolio_values[1:]: peaks.append(max(peaks[-1], v))
    dds = [(v - p) / p for v, p in zip(hourly_portfolio_values, peaks)]
    mdd = min(dds)
    
    daily_vals = [hourly_portfolio_values[i] for i in range(0, total_hours, 24)]
    d_rets = [(daily_vals[i] / daily_vals[i-1]) - 1.0 for i in range(1, len(daily_vals))]
    mean_ret = sum(d_rets) / len(d_rets)
    std_ret = math.sqrt(sum((r - mean_ret)**2 for r in d_rets) / len(d_rets))
    sharpe = (mean_ret / std_ret) * math.sqrt(365) if std_ret > 0 else 0.0
    calmar = cagr / abs(mdd) if abs(mdd) > 0 else 0.0
    
    return {
        'name': name, 'return': total_ret, 'cagr': cagr, 'mdd': mdd, 
        'sharpe': sharpe, 'calmar': calmar, 'switches': zone_switches, 'fees': total_friction_fees
    }

# -------------------------------------------------------------
# 6. 定義四種 C 倉競爭模型
# -------------------------------------------------------------
# A/B 倉共用 5-Zone 經典最優配置
A_r = {
    0: {'BTC': 0.80, 'PAXG': 0.20},
    1: {'BTC': 0.50, 'PAXG': 0.50},
    2: {'BTC': 0.58, 'PAXG': 0.42},
    3: {'BTC': 0.37, 'PAXG': 0.63},
    4: {'BTC': 0.05, 'PAXG': 0.95}
}
B_r = {
    0: {'SOL': 0.30, 'TAO': 0.35, 'PAXG': 0.35},
    1: {'SOL': 0.18, 'TAO': 0.17, 'PAXG': 0.65},
    2: {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60},
    3: {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63},
    4: {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80}
}

# 基準模型: 現行四星 C 倉 (AAVE 30, SUI 15, LINK 15, NEAR 10, PAXG 30)
C_base = {
    0: {'AAVE': 0.30, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15},
    1: {'AAVE': 0.20, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.40},
    2: {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30},
    3: {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45},
    4: {'PAXG': 0.75, 'AAVE': 0.08, 'LINK': 0.07, 'SUI': 0.05, 'NEAR': 0.05}
}

# 競選模型 1: 納入 PENDLE (AAVE 15, PENDLE 15, SUI 15, LINK 15, NEAR 10, PAXG 30)
C_pendle = {
    0: {'AAVE': 0.15, 'PENDLE': 0.15, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15},
    1: {'AAVE': 0.10, 'PENDLE': 0.10, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.40},
    2: {'AAVE': 0.15, 'PENDLE': 0.15, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30},
    3: {'AAVE': 0.10, 'PENDLE': 0.10, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45},
    4: {'PAXG': 0.75, 'AAVE': 0.05, 'PENDLE': 0.05, 'LINK': 0.05, 'SUI': 0.05, 'NEAR': 0.05}
}

# 競選模型 2: 納入 UNI (AAVE 15, UNI 15, SUI 15, LINK 15, NEAR 10, PAXG 30)
C_uni = {
    0: {'AAVE': 0.15, 'UNI': 0.15, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15},
    1: {'AAVE': 0.10, 'UNI': 0.10, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.40},
    2: {'AAVE': 0.15, 'UNI': 0.15, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30},
    3: {'AAVE': 0.10, 'UNI': 0.10, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45},
    4: {'PAXG': 0.75, 'AAVE': 0.05, 'UNI': 0.05, 'LINK': 0.05, 'SUI': 0.05, 'NEAR': 0.05}
}

# 競選模型 3: 六星全明星 (AAVE 10, PENDLE 10, UNI 10, SUI 15, LINK 15, NEAR 10, PAXG 30)
C_allstar = {
    0: {'AAVE': 0.10, 'PENDLE': 0.10, 'UNI': 0.10, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15},
    1: {'AAVE': 0.07, 'PENDLE': 0.07, 'UNI': 0.06, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.40},
    2: {'AAVE': 0.10, 'PENDLE': 0.10, 'UNI': 0.10, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30},
    3: {'AAVE': 0.07, 'PENDLE': 0.07, 'UNI': 0.06, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45},
    4: {'PAXG': 0.75, 'AAVE': 0.04, 'PENDLE': 0.04, 'UNI': 0.04, 'LINK': 0.05, 'SUI': 0.04, 'NEAR': 0.04}
}

def make_rules(c_dict):
    return {z: {'A': A_r[z], 'B': B_r[z], 'C': c_dict[z]} for z in range(5)}

print('Executing ultra-rigorous 21,107h simulation for C-Tier variants...')
res_base = run_simulation(make_rules(C_base), '1. 現行四星基準 (AAVE+SUI+LINK+NEAR+PAXG)')
res_pendle = run_simulation(make_rules(C_pendle), '2. 納入 PENDLE (+PENDLE 利率衍生品)')
res_uni = run_simulation(make_rules(C_uni), '3. 納入 UNI (+UNI 現貨交易所分紅)')
res_all = run_simulation(make_rules(C_allstar), '4. 六星全明星 (+PENDLE + UNI 雙引擎)')

all_res = [res_base, res_pendle, res_uni, res_all]
all_res.sort(key=lambda x: x['calmar'], reverse=True)

print('\n' + '='*105)
print('%-42s | %-8s | %-7s | %-8s | %-7s | %-7s | %-8s' % (
    'C 倉架構模型 (C-Tier Model)', '總回報', 'CAGR', '小時MDD', 'Sharpe', 'Calmar', '手續費磨損'
))
print('-'*105)
for r in all_res:
    print('%-42s | %+7.2f%% | %6.2f%% | %7.2f%% | %7.2f | %7.2f | $%7.1f' % (
        r['name'], r['return']*100, r['cagr']*100, r['mdd']*100, r['sharpe'], r['calmar'], r['fees']
    ))
print('='*105)
