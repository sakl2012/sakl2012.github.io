import json, os, math

# Load all 8 tokens
tokens = ['BTC', 'SOL', 'TAO', 'AAVE', 'LINK', 'NEAR', 'SUI', 'PAXG']
cache_dir = 'scripts/data_cache'
data = {}
for s in tokens:
    with open(os.path.join(cache_dir, f'{s}USDT_1d.json')) as f:
        data[s] = {row['date']: row['c'] for row in json.load(f)}

dates = sorted(list(set(data['BTC'].keys()) & set(data['TAO'].keys()) & set(data['SUI'].keys())))

# Calculate BTC MA200
all_btc = sorted(list(data['BTC'].keys()))
btc_ma = {}
for i, d in enumerate(all_btc):
    if i >= 199:
        btc_ma[d] = sum(data['BTC'][all_btc[j]] for j in range(i-199, i+1)) / 200.0

# -------------------------------------------------------------
# Simulation Engine
# -------------------------------------------------------------
def run_model_simulation(zone_rules, get_zone_func, name):
    initial_cap = 10000.0
    cap_A = initial_cap * 0.20
    cap_B = initial_cap * 0.55
    cap_C = initial_cap * 0.25
    
    d0 = dates[0]
    r0 = data['BTC'][d0] / btc_ma[d0]
    z0 = get_zone_func(r0, 2)
    
    holdings_A = {s: (cap_A * w) / data[s][d0] for s, w in zone_rules[z0]['A'].items()}
    holdings_B = {s: (cap_B * w) / data[s][d0] for s, w in zone_rules[z0]['B'].items()}
    holdings_C = {s: (cap_C * w) / data[s][d0] for s, w in zone_rules[z0]['C'].items()}
    
    curr_zone = z0
    daily_vals = []
    total_rebal_c = 0
    zone_switches = 0
    total_fees = 0.0
    
    for d in dates:
        p = {s: data[s][d] for s in tokens}
        r = p['BTC'] / btc_ma[d]
        target_z = get_zone_func(r, curr_zone)
        
        val_A = sum(holdings_A[s] * p[s] for s in holdings_A)
        val_B = sum(holdings_B[s] * p[s] for s in holdings_B)
        val_C = sum(holdings_C[s] * p[s] for s in holdings_C)
        daily_vals.append(val_A + val_B + val_C)
        
        if target_z != curr_zone:
            curr_zone = target_z
            zone_switches += 1
            for sub, h_dict, cap_val in [('A', holdings_A, val_A), ('B', holdings_B, val_B), ('C', holdings_C, val_C)]:
                tgt = zone_rules[curr_zone][sub]
                traded = sum(abs(cap_val * tgt.get(s, 0.0) - h_dict.get(s, 0.0) * p[s]) for s in set(list(tgt.keys()) + list(h_dict.keys()))) / 2.0
                fee = traded * 0.0015
                total_fees += fee
                net = cap_val - fee
                if sub == 'A': holdings_A = {s: (net * w) / p[s] for s, w in tgt.items()}
                elif sub == 'B': holdings_B = {s: (net * w) / p[s] for s, w in tgt.items()}
                elif sub == 'C': holdings_C = {s: (net * w) / p[s] for s, w in tgt.items()}
        else:
            # Check C threshold (10%)
            tgt_C = zone_rules[curr_zone]['C']
            weights_C = {s: (holdings_C[s] * p[s]) / val_C for s in holdings_C}
            dev = max(abs(weights_C[s] - tgt_C.get(s, 0.0)) for s in set(list(weights_C.keys()) + list(tgt_C.keys())))
            if dev >= 0.10:
                total_rebal_c += 1
                traded = sum(abs(val_C * tgt_C.get(s, 0.0) - holdings_C.get(s, 0.0) * p[s]) for s in set(list(tgt_C.keys()) + list(holdings_C.keys()))) / 2.0
                fee = traded * 0.0015
                total_fees += fee
                net = val_C - fee
                holdings_C = {s: (net * w) / p[s] for s, w in tgt_C.items()}
                
            # Check B threshold (5%)
            tgt_B = zone_rules[curr_zone]['B']
            weights_B = {s: (holdings_B[s] * p[s]) / val_B for s in holdings_B}
            dev_B = max(abs(weights_B[s] - tgt_B.get(s, 0.0)) for s in set(list(weights_B.keys()) + list(tgt_B.keys())))
            if dev_B >= 0.05:
                traded = sum(abs(val_B * tgt_B.get(s, 0.0) - holdings_B.get(s, 0.0) * p[s]) for s in set(list(tgt_B.keys()) + list(holdings_B.keys()))) / 2.0
                fee = traded * 0.0015
                total_fees += fee
                net = val_B - fee
                holdings_B = {s: (net * w) / p[s] for s, w in tgt_B.items()}

    ret = (daily_vals[-1] / daily_vals[0]) - 1.0
    cagr = ((daily_vals[-1] / daily_vals[0]) ** (365.0 / len(dates))) - 1.0
    peaks = [daily_vals[0]]
    for v in daily_vals[1:]: peaks.append(max(peaks[-1], v))
    dds = [(v - p) / p for v, p in zip(daily_vals, peaks)]
    mdd = min(dds)
    d_rets = [(daily_vals[i] / daily_vals[i-1]) - 1.0 for i in range(1, len(daily_vals))]
    mean_ret = sum(d_rets) / len(d_rets)
    std_ret = math.sqrt(sum((r - mean_ret)**2 for r in d_rets) / len(d_rets))
    sharpe = (mean_ret / std_ret) * math.sqrt(365) if std_ret > 0 else 0.0
    calmar = cagr / abs(mdd) if abs(mdd) > 0 else 0.0
    return {
        'name': name, 'return': ret, 'cagr': cagr, 'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar, 'zone_switches': zone_switches, 'fees': total_fees
    }

# -------------------------------------------------------------
# Model 1: 現行經典 4-Zone (Zone 1: <1.00, Zone 2: 1.00-1.25, Zone 3: 1.25-1.40, Zone 4: >1.40)
# -------------------------------------------------------------
rules_4zone = {
    1: {
        'A': {'BTC': 0.74, 'PAXG': 0.26},
        'B': {'SOL': 0.26, 'TAO': 0.29, 'PAXG': 0.45},
        'C': {'AAVE': 0.25, 'SUI': 0.20, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.25}
    },
    2: {
        'A': {'BTC': 0.58, 'PAXG': 0.42},
        'B': {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60},
        'C': {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30}
    },
    3: {
        'A': {'BTC': 0.37, 'PAXG': 0.63},
        'B': {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63},
        'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45}
    },
    4: {
        'A': {'BTC': 0.05, 'PAXG': 0.95},
        'B': {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80},
        'C': {'PAXG': 0.75, 'AAVE': 0.08, 'LINK': 0.07, 'SUI': 0.05, 'NEAR': 0.05}
    }
}
def get_zone_4model(r, cur):
    if r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

# -------------------------------------------------------------
# Model 2: 遲滯保護 4-Zone (Hysteresis - 跌破 0.85 才算熊底，回彈 1.02 才回牛)
# -------------------------------------------------------------
def get_zone_4hysteresis(r, cur):
    if cur == 1:
        if r > 1.02: return 2
        return 1
    elif cur == 2:
        if r < 0.85: return 1 # 延後抄底，避免 0.95 接飛刀
        elif r > 1.25: return 3
        return 2
    elif cur == 3:
        if r < 1.15: return 2
        elif r > 1.40: return 4
        return 3
    elif cur == 4:
        if r < 1.30: return 3
        return 4

# -------------------------------------------------------------
# Model 3: 5-Zone 狀態機 (引入 Zone 1 陰跌防守期 0.80-1.00，Zone 0 才是極限熊底 <0.80)
# -------------------------------------------------------------
rules_5zone = {
    0: { # 極限深熊抄底 (比值 < 0.80)
        'A': {'BTC': 0.80, 'PAXG': 0.20},
        'B': {'SOL': 0.30, 'TAO': 0.35, 'PAXG': 0.35},
        'C': {'AAVE': 0.30, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15}
    },
    1: { # 破位陰跌/防守觀察 (0.80 <= 比值 < 1.00) -> 高黃金防禦，絕不輕易接半山腰飛刀！
        'A': {'BTC': 0.40, 'PAXG': 0.60},
        'B': {'SOL': 0.15, 'TAO': 0.15, 'PAXG': 0.70},
        'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.10, 'NEAR': 0.10, 'PAXG': 0.50}
    },
    2: { # 牛市巡航 (1.00 <= 比值 < 1.25)
        'A': {'BTC': 0.58, 'PAXG': 0.42},
        'B': {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60},
        'C': {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30}
    },
    3: { # 過熱警戒 (1.25 <= 比值 < 1.40)
        'A': {'BTC': 0.37, 'PAXG': 0.63},
        'B': {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63},
        'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45}
    },
    4: { # 極度逃頂 (比值 >= 1.40)
        'A': {'BTC': 0.05, 'PAXG': 0.95},
        'B': {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80},
        'C': {'PAXG': 0.75, 'AAVE': 0.08, 'LINK': 0.07, 'SUI': 0.05, 'NEAR': 0.05}
    }
}
def get_zone_5model(r, cur):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

res1 = run_model_simulation(rules_4zone, get_zone_4model, 'Model 1: 經典 4-Zone (<1.00 直接抄底)')
res2 = run_model_simulation(rules_4zone, get_zone_4hysteresis, 'Model 2: 防假摔遲滯 4-Zone (<0.85 延後抄底)')
res3 = run_model_simulation(rules_5zone, get_zone_5model, 'Model 3: 階梯 5-Zone (0.80~1.00陰跌高防禦, <0.80極致熊底)')

print('\n==================== 實盤量化模擬結果 (2024-2026, 880 天) ====================')
for res in [res1, res2, res3]:
    print('%-38s | 總回報: %+.2f%% | CAGR: %.2f%% | MDD: %.2f%% | Sharpe: %.2f | Calmar: %.2f | 切倉次數: %d | 摩擦手續費: $%.1f' % (
        res['name'], res['return']*100, res['cagr']*100, res['mdd']*100, res['sharpe'], res['calmar'], res['zone_switches'], res['fees']
    ))
