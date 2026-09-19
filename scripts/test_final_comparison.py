import json, os, math

# Load all 8 key tokens
tokens = ['BTC', 'SOL', 'TAO', 'AAVE', 'LINK', 'NEAR', 'SUI', 'PAXG']
cache_dir = 'scripts/data_cache'
data = {}
for s in tokens:
    with open(os.path.join(cache_dir, f'{s}USDT_1d.json')) as f:
        data[s] = {row['date']: row['c'] for row in json.load(f)}

dates = sorted(list(set(data['BTC'].keys()) & set(data['TAO'].keys()) & set(data['SUI'].keys())))

# Test multi-zone full strategy for both C-tier variants across 880 days
def evaluate_full_4zone_strategy(c_configs_4zones, c_thresh=0.10):
    initial_cap = 10000.0
    cap_A = initial_cap * 0.20
    cap_B = initial_cap * 0.55
    cap_C = initial_cap * 0.25
    
    # Standard 4-zone A and B configs
    zone_rules = {
        1: {
            'A': {'BTC': 0.74, 'PAXG': 0.26},
            'B': {'SOL': 0.26, 'TAO': 0.29, 'PAXG': 0.45},
            'C': c_configs_4zones[1]
        },
        2: {
            'A': {'BTC': 0.58, 'PAXG': 0.42},
            'B': {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60},
            'C': c_configs_4zones[2]
        },
        3: {
            'A': {'BTC': 0.37, 'PAXG': 0.63},
            'B': {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63},
            'C': c_configs_4zones[3]
        },
        4: {
            'A': {'BTC': 0.05, 'PAXG': 0.95},
            'B': {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80},
            'C': c_configs_4zones[4]
        }
    }
    
    # Calculate BTC MA200
    all_btc = sorted(list(data['BTC'].keys()))
    btc_ma = {}
    for i, d in enumerate(all_btc):
        if i >= 199:
            btc_ma[d] = sum(data['BTC'][all_btc[j]] for j in range(i-199, i+1)) / 200.0
            
    # Init
    d0 = dates[0]
    r0 = data['BTC'][d0] / btc_ma[d0]
    z0 = 1 if r0 < 1.00 else (2 if r0 < 1.25 else (3 if r0 < 1.50 else 4))
    
    holdings_A = {s: (cap_A * w) / data[s][d0] for s, w in zone_rules[z0]['A'].items()}
    holdings_B = {s: (cap_B * w) / data[s][d0] for s, w in zone_rules[z0]['B'].items()}
    holdings_C = {s: (cap_C * w) / data[s][d0] for s, w in zone_rules[z0]['C'].items()}
    
    curr_zone = z0
    daily_vals = []
    total_rebal_c = 0
    total_fees = 0.0
    
    for d in dates:
        p = {s: data[s][d] for s in tokens}
        r = p['BTC'] / btc_ma[d]
        target_z = 1 if r < 1.00 else (2 if r < 1.25 else (3 if r < 1.50 else 4))
        
        val_A = sum(holdings_A[s] * p[s] for s in holdings_A)
        val_B = sum(holdings_B[s] * p[s] for s in holdings_B)
        val_C = sum(holdings_C[s] * p[s] for s in holdings_C)
        daily_vals.append(val_A + val_B + val_C)
        
        if target_z != curr_zone:
            curr_zone = target_z
            # Zone shift rebalance
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
            # Check C threshold rebalance
            tgt_C = zone_rules[curr_zone]['C']
            weights_C = {s: (holdings_C[s] * p[s]) / val_C for s in holdings_C}
            dev = max(abs(weights_C[s] - tgt_C.get(s, 0.0)) for s in set(list(weights_C.keys()) + list(tgt_C.keys())))
            if dev >= c_thresh:
                total_rebal_c += 1
                traded = sum(abs(val_C * tgt_C.get(s, 0.0) - holdings_C.get(s, 0.0) * p[s]) for s in set(list(tgt_C.keys()) + list(holdings_C.keys()))) / 2.0
                fee = traded * 0.0015
                total_fees += fee
                net = val_C - fee
                holdings_C = {s: (net * w) / p[s] for s, w in tgt_C.items()}
                
            # Check B threshold rebalance (5%)
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
        'return': ret, 'cagr': cagr, 'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar, 'rebal_C': total_rebal_c, 'fees': total_fees
    }

# Compare Candidate 1: DeFi重磅 (AAVE 40, LINK 20, NEAR 10, PAXG 30)
c_deficenter = {
    1: {'AAVE': 0.35, 'LINK': 0.25, 'NEAR': 0.15, 'PAXG': 0.25},
    2: {'AAVE': 0.40, 'LINK': 0.20, 'NEAR': 0.10, 'PAXG': 0.30},
    3: {'AAVE': 0.25, 'LINK': 0.25, 'NEAR': 0.10, 'PAXG': 0.40},
    4: {'AAVE': 0.10, 'LINK': 0.10, 'NEAR': 0.05, 'PAXG': 0.75}
}

# Compare Candidate 2: 四星全板塊輪動 (AAVE 30, SUI 15, LINK 15, NEAR 10, PAXG 30)
c_allstars = {
    1: {'AAVE': 0.25, 'SUI': 0.20, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.25},
    2: {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30},
    3: {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45},
    4: {'AAVE': 0.08, 'SUI': 0.05, 'LINK': 0.07, 'NEAR': 0.05, 'PAXG': 0.75}
}

res_defi = evaluate_full_4zone_strategy(c_deficenter)
res_stars = evaluate_full_4zone_strategy(c_allstars)

print('=== 全週期 4-Zone 動態切換實盤模擬 ===')
print('方案 A (DeFi雙核心 3幣): Ret: %+.2f%% | CAGR: %.2f%% | MDD: %.2f%% | Sharpe: %.2f | Calmar: %.2f | Fees: $%.1f' % (
    res_defi['return']*100, res_defi['cagr']*100, res_defi['mdd']*100, res_defi['sharpe'], res_defi['calmar'], res_defi['fees']
))
print('方案 B (四星全輪動 4幣): Ret: %+.2f%% | CAGR: %.2f%% | MDD: %.2f%% | Sharpe: %.2f | Calmar: %.2f | Fees: $%.1f' % (
    res_stars['return']*100, res_stars['cagr']*100, res_stars['mdd']*100, res_stars['sharpe'], res_stars['calmar'], res_stars['fees']
))
