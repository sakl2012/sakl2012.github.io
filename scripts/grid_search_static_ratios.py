import json
import os
import math
import datetime
from simulate_user_exact_fleet import days_5y, simulate_bot

# 5 Alpha tokens from user's exact list
alpha_tokens = ['BNB', 'UNI', 'AAVE', 'LINK', 'NEAR']

def evaluate_static_ratio(w_c, w_q, w_p, threshold=0.02):
    # Equal weight 1000U each = 5000U total
    tot_nav = [0.0] * len(days_5y)
    
    for sym in alpha_tokens:
        nh, tr = simulate_bot(days_5y, sym, False, None, (w_c, w_q, w_p), initial_cap=1000.0)
        for i in range(len(days_5y)):
            tot_nav[i] += nh[i]
            
    initial = 5000.0
    final = tot_nav[-1]
    ret = (final - initial) / initial
    n_years = len(days_5y) / 365.25
    cagr = ((final / initial) ** (1.0 / n_years)) - 1.0
    
    peak = tot_nav[0]
    mdd = 0.0
    d_rets = []
    for j in range(1, len(tot_nav)):
        if tot_nav[j] > peak: peak = tot_nav[j]
        dd = (peak - tot_nav[j]) / peak
        if dd > mdd: mdd = dd
        d_rets.append(tot_nav[j] / tot_nav[j-1] - 1.0)
        
    mean_r = sum(d_rets) / len(d_rets)
    var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
    sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
    calmar = cagr / mdd if mdd > 0 else 0
    
    return {
        'wc': w_c, 'wq': w_q, 'wp': w_p,
        'final': final, 'ret': ret, 'cagr': cagr,
        'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar
    }

# Grid search all combinations step=0.05
all_results = []
for c in range(1, 17): # 5% to 80%
    wc = round(c * 0.05, 2)
    for q in range(1, 20 - c):
        wq = round(q * 0.05, 2)
        wp = round(1.0 - wc - wq, 2)
        if wp < 0.05: continue
        res = evaluate_static_ratio(wc, wq, wp, threshold=0.02)
        all_results.append(res)

# Sort by Sharpe, Return, and MDD
best_sharpe = sorted(all_results, key=lambda x: x['sharpe'], reverse=True)[0]
best_ret = sorted(all_results, key=lambda x: x['ret'], reverse=True)[0]
lowest_mdd = sorted(all_results, key=lambda x: x['mdd'])[0]

# Also test specific popular ratios:
r_33 = evaluate_static_ratio(0.3333, 0.3333, 0.3334, threshold=0.02)
r_40_30_30 = evaluate_static_ratio(0.40, 0.30, 0.30, threshold=0.02)
r_50_25_25 = evaluate_static_ratio(0.50, 0.25, 0.25, threshold=0.02)
r_25_50_25 = evaluate_static_ratio(0.25, 0.50, 0.25, threshold=0.02)
r_20_40_40 = evaluate_static_ratio(0.20, 0.40, 0.40, threshold=0.02)

print("=== GRID SEARCH: OPTIMAL STATIC RATIOS FOR ALPHA FLEET (5-YEAR 2021-2026) ===")
print("Tokens: BNB, UNI, AAVE, LINK, NEAR ($5,000 Initial Capital, Threshold=2%)\n")

print(f"{'Configuration':<25} | {'Ratio (Coin / QQQ / PAXG)':<26} | {'Final NAV':<12} | {'Total Ret':<10} | {'CAGR':<8} | {'MDD':<8} | {'Sharpe':<7}")
print("-" * 105)

configs = [
    ("Best Sharpe (Max Risk-Adj)", f"{best_sharpe['wc']*100:.0f}% / {best_sharpe['wq']*100:.0f}% / {best_sharpe['wp']*100:.0f}%", best_sharpe),
    ("Best Return (Max Profit)", f"{best_ret['wc']*100:.0f}% / {best_ret['wq']*100:.0f}% / {best_ret['wp']*100:.0f}%", best_ret),
    ("Lowest MDD (Max Defense)", f"{lowest_mdd['wc']*100:.0f}% / {lowest_mdd['wq']*100:.0f}% / {lowest_mdd['wp']*100:.0f}%", lowest_mdd),
    ("Classic Equal 1/3 (33%)", "33.3% / 33.3% / 33.3%", r_33),
    ("Growth Tilt (40/30/30)", "40.0% / 30.0% / 30.0%", r_40_30_30),
    ("Crypto Heavy (50/25/25)", "50.0% / 25.0% / 25.0%", r_50_25_25),
    ("Equity Heavy (25/50/25)", "25.0% / 50.0% / 25.0%", r_25_50_25),
    ("Dual Anchor (20/40/40)", "20.0% / 40.0% / 40.0%", r_20_40_40)
]

for title, ratio_str, r in configs:
    print(f"{title:<25} | {ratio_str:<26} | ${r['final']:>10.2f} | {r['ret']*100:>8.2f}% | {r['cagr']*100:>6.2f}% | {r['mdd']*100:>6.2f}% | {r['sharpe']:>7.3f}")
