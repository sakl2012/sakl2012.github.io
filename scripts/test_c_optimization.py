import json, os, math

symbols = ['BTCUSDT', 'SOLUSDT', 'TAOUSDT', 'AAVEUSDT', 'LINKUSDT', 'NEARUSDT', 'PAXGUSDT']
cache_dir = 'scripts/data_cache'
data = {}
for s in symbols:
    with open(os.path.join(cache_dir, f'{s}_1d.json')) as f:
        data[s.replace('USDT','')] = {row['date']: row['c'] for row in json.load(f)}

all_dates = sorted(list(set(data['BTC'].keys()) & set(data['TAO'].keys())))

# Test different C allocations without ENA to find the optimal frontier
c_proposals = {
    'C1 (原版: AAVE 38, NEAR 22, LINK 11, PAXG 29)': {'AAVE': 0.38, 'NEAR': 0.22, 'LINK': 0.11, 'PAXG': 0.29},
    'C2 (DeFi重磅: AAVE 40, LINK 20, NEAR 10, PAXG 30)': {'AAVE': 0.40, 'LINK': 0.20, 'NEAR': 0.10, 'PAXG': 0.30},
    'C3 (均衡輪動: AAVE 35, LINK 20, NEAR 15, PAXG 30)': {'AAVE': 0.35, 'LINK': 0.20, 'NEAR': 0.15, 'PAXG': 0.30},
    'C4 (高成長公鏈: AAVE 30, LINK 15, NEAR 25, PAXG 30)': {'AAVE': 0.30, 'LINK': 0.15, 'NEAR': 0.25, 'PAXG': 0.30},
    'C5 (極致防禦: AAVE 30, LINK 15, NEAR 15, PAXG 40)': {'AAVE': 0.30, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.40}
}

for name, cfg in c_proposals.items():
    dates = all_dates
    cap_C = 2500.0
    d0 = dates[0]
    holdings = {s: (cap_C * w) / data[s][d0] for s, w in cfg.items()}
    daily_vals = []
    rebal_count = 0
    fees = 0.0
    for d in dates:
        p = {s: data[s][d] for s in cfg}
        val = sum(holdings[s] * p[s] for s in holdings)
        daily_vals.append(val)
        weights = {s: (holdings[s] * p[s]) / val for s in holdings}
        dev = max(abs(weights[s] - cfg[s]) for s in cfg)
        if dev >= 0.10:
            rebal_count += 1
            traded = sum(abs(val * cfg[s] - holdings[s] * p[s]) for s in cfg) / 2.0
            fee = traded * 0.0015
            fees += fee
            net_val = val - fee
            holdings = {s: (net_val * cfg[s]) / p[s] for s in cfg}
    
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
    print('%-50s | 2.5y Ret: %+.2f%% | CAGR: %.2f%% | MDD: %.2f%% | Sharpe: %.2f | Calmar: %.2f | Rebal: %d' % (
        name, ret*100, cagr*100, mdd*100, sharpe, calmar, rebal_count
    ))
