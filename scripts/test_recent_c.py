import json, os, math

symbols = ['BTCUSDT', 'SOLUSDT', 'TAOUSDT', 'AAVEUSDT', 'LINKUSDT', 'NEARUSDT', 'PAXGUSDT', 'ENAUSDT']
cache_dir = 'scripts/data_cache'
data = {}
for s in symbols:
    with open(os.path.join(cache_dir, f'{s}_1d.json')) as f:
        data[s.replace('USDT','')] = {row['date']: row['c'] for row in json.load(f)}

# Filter to recent 1 year (from 2025-09-07) and recent 6 months (from 2026-03-07)
all_dates = sorted(list(set(data['BTC'].keys()) & set(data['TAO'].keys()) & set(data['ENA'].keys())))

def eval_window(start_d, candidate_cfgs):
    dates = [d for d in all_dates if d >= start_d]
    print('\n=== Evaluation Window: %s to %s (%d days) ===' % (dates[0], dates[-1], len(dates)))
    for name, cfg in candidate_cfgs.items():
        cap_C = 2500.0 # pure C-tier simulation
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
        print(' %-45s | Ret: %+.2f%% | CAGR: %.1f%% | MDD: %.1f%% | Sharpe: %.2f | Rebal: %d' % (
            name, ret*100, cagr*100, mdd*100, sharpe, rebal_count
        ))

candidates = {
    'A. 原版 C (AAVE 38, NEAR 22, LINK 11, PAXG 29)': {'AAVE': 0.38, 'NEAR': 0.22, 'LINK': 0.11, 'PAXG': 0.29},
    'B. 平衡輪動 (AAVE 35, LINK 15, NEAR 15, ENA 5, PAXG 30)': {'AAVE': 0.35, 'LINK': 0.15, 'NEAR': 0.15, 'ENA': 0.05, 'PAXG': 0.30},
    'C. DeFi/公鏈強化 (AAVE 40, LINK 15, NEAR 15, PAXG 30)': {'AAVE': 0.40, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.30},
    'D. 飛哥高彈性 (AAVE 30, LINK 15, NEAR 15, ENA 10, PAXG 30)': {'AAVE': 0.30, 'LINK': 0.15, 'NEAR': 0.15, 'ENA': 0.10, 'PAXG': 0.30},
}

eval_window('2025-09-07', candidates)
eval_window('2026-03-07', candidates)
