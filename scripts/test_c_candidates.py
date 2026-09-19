import json, os, math

symbols = ['BTCUSDT', 'SOLUSDT', 'TAOUSDT', 'AAVEUSDT', 'LINKUSDT', 'NEARUSDT', 'PAXGUSDT', 'ENAUSDT']
cache_dir = 'scripts/data_cache'
data = {}
for s in symbols:
    with open(os.path.join(cache_dir, f'{s}_1d.json')) as f:
        data[s.replace('USDT','')] = {row['date']: row['c'] for row in json.load(f)}

dates = sorted(list(set(data['BTC'].keys()) & set(data['TAO'].keys()) & set(data['ENA'].keys())))

def run_portfolio_sim(c_config_zone2, c_threshold=0.10, c_weight=0.25, a_weight=0.20, b_weight=0.55):
    initial_cap = 10000.0
    cap_A = initial_cap * a_weight
    cap_B = initial_cap * b_weight
    cap_C = initial_cap * c_weight
    
    ratios_A = {'BTC': 0.58, 'PAXG': 0.42}
    ratios_B = {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60}
    ratios_C = c_config_zone2
    
    d0 = dates[0]
    holdings_A = {s: (cap_A * w) / data[s][d0] for s, w in ratios_A.items()}
    holdings_B = {s: (cap_B * w) / data[s][d0] for s, w in ratios_B.items()}
    holdings_C = {s: (cap_C * w) / data[s][d0] for s, w in ratios_C.items()}
    
    daily_vals = []
    rebal_count = 0
    total_fee = 0.0
    
    for d in dates:
        p = {s: data[s][d] for s in ['BTC', 'SOL', 'TAO', 'AAVE', 'LINK', 'NEAR', 'PAXG', 'ENA'] if d in data[s]}
        val_A = sum(holdings_A[s] * p[s] for s in holdings_A)
        val_B = sum(holdings_B[s] * p[s] for s in holdings_B)
        val_C = sum(holdings_C[s] * p[s] for s in holdings_C)
        total_val = val_A + val_B + val_C
        daily_vals.append(total_val)
        
        # Check C rebalance
        c_weights = {s: (holdings_C[s] * p[s]) / val_C for s in holdings_C}
        c_dev = max(abs(c_weights[s] - ratios_C.get(s, 0.0)) for s in set(list(c_weights.keys()) + list(ratios_C.keys())))
        if c_dev >= c_threshold:
            rebal_count += 1
            old_alloc = {s: holdings_C[s] * p[s] for s in holdings_C}
            target_alloc = {s: val_C * ratios_C[s] for s in ratios_C}
            traded_vol = sum(abs(target_alloc[s] - old_alloc.get(s, 0.0)) for s in ratios_C) / 2.0
            fee = traded_vol * 0.0015
            total_fee += fee
            net_val_C = val_C - fee
            holdings_C = {s: (net_val_C * ratios_C[s]) / p[s] for s in ratios_C}
            
        # Check B rebalance (5% threshold)
        b_weights = {s: (holdings_B[s] * p[s]) / val_B for s in holdings_B}
        b_dev = max(abs(b_weights[s] - ratios_B.get(s, 0.0)) for s in set(list(b_weights.keys()) + list(ratios_B.keys())))
        if b_dev >= 0.05:
            old_alloc_b = {s: holdings_B[s] * p[s] for s in holdings_B}
            target_alloc_b = {s: val_B * ratios_B[s] for s in ratios_B}
            traded_vol_b = sum(abs(target_alloc_b[s] - old_alloc_b.get(s, 0.0)) for s in ratios_B) / 2.0
            fee_b = traded_vol_b * 0.0015
            total_fee += fee_b
            net_val_B = val_B - fee_b
            holdings_B = {s: (net_val_B * ratios_B[s]) / p[s] for s in ratios_B}

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
        'return': ret,
        'cagr': cagr,
        'mdd': mdd,
        'sharpe': sharpe,
        'calmar': calmar,
        'rebalances_C': rebal_count,
        'fees': total_fee,
        'final_val': daily_vals[-1]
    }

candidates = {
    '1. 原版 C (AAVE 38%, NEAR 22%, LINK 11%, PAXG 29%)': {
        'AAVE': 0.38, 'NEAR': 0.22, 'LINK': 0.11, 'PAXG': 0.29
    },
    '2. 飛哥高彈性 (AAVE 30%, NEAR 20%, LINK 15%, ENA 10%, PAXG 25%)': {
        'AAVE': 0.30, 'NEAR': 0.20, 'LINK': 0.15, 'ENA': 0.10, 'PAXG': 0.25
    },
    '3. 飛哥平衡型 (AAVE 32%, NEAR 18%, LINK 12%, ENA 8%, PAXG 30%)': {
        'AAVE': 0.32, 'NEAR': 0.18, 'LINK': 0.12, 'ENA': 0.08, 'PAXG': 0.30
    },
    '4. 飛哥激進型 (AAVE 25%, NEAR 20%, LINK 20%, ENA 15%, PAXG 20%)': {
        'AAVE': 0.25, 'NEAR': 0.20, 'LINK': 0.20, 'ENA': 0.15, 'PAXG': 0.20
    },
    '5. 高防禦型 (AAVE 30%, NEAR 15%, LINK 10%, ENA 5%, PAXG 40%)': {
        'AAVE': 0.30, 'NEAR': 0.15, 'LINK': 0.10, 'ENA': 0.05, 'PAXG': 0.40
    }
}

print('Backtest window: %d days (%s to %s)' % (len(dates), dates[0], dates[-1]))
for name, cfg in candidates.items():
    res = run_portfolio_sim(cfg, c_threshold=0.10)
    print('%s\n   Total Return: %+.2f%% | CAGR: %.2f%% | MDD: %.2f%% | Sharpe: %.2f | Calmar: %.2f | C-Rebal: %d | Fees: $%.1f' % (
        name, res['return']*100, res['cagr']*100, res['mdd']*100, res['sharpe'], res['calmar'], res['rebalances_C'], res['fees']
    ))
