import json, os, math

# Load all potential candidates
tokens = ['BTC', 'SOL', 'TAO', 'AAVE', 'LINK', 'NEAR', 'PAXG', 'SUI', 'PENDLE', 'UNI', 'ENA']
cache_dir = 'scripts/data_cache'
data = {}
for s in tokens:
    with open(os.path.join(cache_dir, f'{s}USDT_1d.json')) as f:
        data[s] = {row['date']: row['c'] for row in json.load(f)}

# Find common dates for TAO, SUI, PENDLE, AAVE etc. (from 2024-04-11)
dates = sorted(list(set(data['BTC'].keys()) & set(data['TAO'].keys()) & set(data['SUI'].keys()) & set(data['PENDLE'].keys())))
print('Comprehensive Simulation Window: %d days (%s to %s)' % (len(dates), dates[0], dates[-1]))

def run_multi_token_c(c_config):
    initial_cap = 10000.0
    cap_A = initial_cap * 0.20
    cap_B = initial_cap * 0.55
    cap_C = initial_cap * 0.25
    
    ratios_A = {'BTC': 0.58, 'PAXG': 0.42}
    ratios_B = {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60}
    ratios_C = c_config
    
    d0 = dates[0]
    holdings_A = {s: (cap_A * w) / data[s][d0] for s, w in ratios_A.items()}
    holdings_B = {s: (cap_B * w) / data[s][d0] for s, w in ratios_B.items()}
    holdings_C = {s: (cap_C * w) / data[s][d0] for s, w in ratios_C.items()}
    
    daily_vals = []
    rebal_C = 0
    total_fee = 0.0
    
    for d in dates:
        p = {s: data[s][d] for s in data if d in data[s]}
        val_A = sum(holdings_A[s] * p[s] for s in holdings_A)
        val_B = sum(holdings_B[s] * p[s] for s in holdings_B)
        val_C = sum(holdings_C[s] * p[s] for s in holdings_C)
        daily_vals.append(val_A + val_B + val_C)
        
        # Check C rebalance 10%
        c_weights = {s: (holdings_C[s] * p[s]) / val_C for s in holdings_C}
        c_dev = max(abs(c_weights[s] - ratios_C[s]) for s in ratios_C)
        if c_dev >= 0.10:
            rebal_C += 1
            traded = sum(abs(val_C * ratios_C[s] - holdings_C[s] * p[s]) for s in ratios_C) / 2.0
            fee = traded * 0.0015
            total_fee += fee
            net = val_C - fee
            holdings_C = {s: (net * ratios_C[s]) / p[s] for s in ratios_C}
            
        # Check B rebalance 5%
        b_weights = {s: (holdings_B[s] * p[s]) / val_B for s in holdings_B}
        b_dev = max(abs(b_weights[s] - ratios_B[s]) for s in ratios_B)
        if b_dev >= 0.05:
            traded = sum(abs(val_B * ratios_B[s] - holdings_B[s] * p[s]) for s in ratios_B) / 2.0
            fee = traded * 0.0015
            total_fee += fee
            net = val_B - fee
            holdings_B = {s: (net * ratios_B[s]) / p[s] for s in ratios_B}

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
        'return': ret, 'cagr': cagr, 'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar, 'rebal_C': rebal_C, 'fees': total_fee
    }

universe_candidates = {
    '1. 基準 C 倉 (AAVE 38, NEAR 22, LINK 11, PAXG 29)': {
        'AAVE': 0.38, 'NEAR': 0.22, 'LINK': 0.11, 'PAXG': 0.29
    },
    '2. 飛哥全明星輪動 (AAVE 30, SUI 15, PENDLE 15, LINK 10, PAXG 30)': {
        'AAVE': 0.30, 'SUI': 0.15, 'PENDLE': 0.15, 'LINK': 0.10, 'PAXG': 0.30
    },
    '3. 新一代公鏈+DeFi (AAVE 30, SUI 15, NEAR 10, LINK 15, PAXG 30)': {
        'AAVE': 0.30, 'SUI': 0.15, 'NEAR': 0.10, 'LINK': 0.15, 'PAXG': 0.30
    },
    '4. 旗艦收益版 (AAVE 30, PENDLE 20, LINK 15, NEAR 10, PAXG 25)': {
        'AAVE': 0.30, 'PENDLE': 0.20, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.25
    },
    '5. 高防禦全明星 (AAVE 25, SUI 10, PENDLE 10, LINK 15, PAXG 40)': {
        'AAVE': 0.25, 'SUI': 0.10, 'PENDLE': 0.10, 'LINK': 0.15, 'PAXG': 0.40
    }
}

for name, cfg in universe_candidates.items():
    res = run_multi_token_c(cfg)
    print('%-55s | Ret: %+.2f%% | CAGR: %.2f%% | MDD: %.2f%% | Sharpe: %.2f | Calmar: %.2f | C-Rebal: %d' % (
        name, res['return']*100, res['cagr']*100, res['mdd']*100, res['sharpe'], res['calmar'], res['rebal_C']
    ))
