import json
import os
import math
from simulate_user_exact_fleet import days_5y, bots_5y, simulate_bot

# Alpha tokens from user's exact list
alpha_tokens = ['BNB', 'UNI', 'AAVE', 'LINK', 'NEAR']

def evaluate_ratio(w_c, w_q, w_p, threshold=0.02):
    tot_nav = [0.0] * len(days_5y)
    bot_results = {}
    
    for sym in alpha_tokens:
        nh, tr = simulate_bot(days_5y, sym, False, None, (w_c, w_q, w_p), initial_cap=1000.0)
        bot_results[sym] = {'final': nh[-1], 'ret': (nh[-1]-1000.0)/1000.0, 'trades': tr}
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
        'mdd': mdd, 'sharpe': sharpe, 'calmar': calmar,
        'bot_results': bot_results
    }

# Also evaluate for BTC single bot
def evaluate_btc(w_c, w_q, w_p, threshold=0.02):
    nh, tr = simulate_bot(days_5y, 'BTC', False, None, (w_c, w_q, w_p), initial_cap=10000.0)
    initial = 10000.0
    final = nh[-1]
    ret = (final - initial) / initial
    n_years = len(days_5y) / 365.25
    cagr = ((final / initial) ** (1.0 / n_years)) - 1.0
    peak = nh[0]
    mdd = 0.0
    d_rets = []
    for j in range(1, len(nh)):
        if nh[j] > peak: peak = nh[j]
        dd = (peak - nh[j]) / peak
        if dd > mdd: mdd = dd
        d_rets.append(nh[j] / nh[j-1] - 1.0)
    mean_r = sum(d_rets) / len(d_rets)
    var_r = sum((r - mean_r)**2 for r in d_rets) / len(d_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(365.25)
    sharpe = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0
    return {'final': final, 'ret': ret, 'cagr': cagr, 'mdd': mdd, 'sharpe': sharpe, 'trades': tr}

# Test 35/35/30 vs 33/33/33 vs 20/40/40
r_35_35_30 = evaluate_ratio(0.35, 0.35, 0.30)
r_33_33_33 = evaluate_ratio(0.3333, 0.3333, 0.3334)
r_20_40_40 = evaluate_ratio(0.20, 0.40, 0.40)

btc_35 = evaluate_btc(0.35, 0.35, 0.30)
btc_33 = evaluate_btc(0.3333, 0.3333, 0.3334)
btc_20 = evaluate_btc(0.20, 0.40, 0.40)

# 5-Zone BTC for reference
from simulate_user_exact_fleet import zw_core_btc
nh_5z, tr_5z = simulate_bot(days_5y, 'BTC', True, zw_core_btc, None, initial_cap=10000.0)
btc_5z_ret = (nh_5z[-1] - 10000.0) / 10000.0

print("=== EVALUATION OF 35% Coin / 35% QQQ / 30% PAXG ===")
print("Alpha Fleet (BNB, UNI, AAVE, LINK, NEAR - $5,000 Initial, Threshold=2%):")
print(f"{'Configuration':<25} | {'Final NAV':<12} | {'Total Ret':<10} | {'CAGR':<8} | {'MDD':<8} | {'Sharpe':<7}")
print("-" * 80)
for name, r in [('35% / 35% / 30% (User Q)', r_35_35_30), 
                ('33.3% / 33.3% / 33.3% (Equal)', r_33_33_33), 
                ('20% / 40% / 40% (Dual Anchor)', r_20_40_40)]:
    print(f"{name:<25} | ${r['final']:>10.2f} | {r['ret']*100:>8.2f}% | {r['cagr']*100:>6.2f}% | {r['mdd']*100:>6.2f}% | {r['sharpe']:>7.3f}")

print("\nSingle Core 1 (BTC) Bot ($10,000 Initial, Threshold=2%):")
print(f"  35% / 35% / 30%: Final=${btc_35['final']:.2f} ({btc_35['ret']*100:+.2f}%), MDD={btc_35['mdd']*100:.2f}%, Sharpe={btc_35['sharpe']:.3f}, Trades={btc_35['trades']}")
print(f"  33% / 33% / 33%: Final=${btc_33['final']:.2f} ({btc_33['ret']*100:+.2f}%), MDD={btc_33['mdd']*100:.2f}%, Sharpe={btc_33['sharpe']:.3f}, Trades={btc_33['trades']}")
print(f"  5-Zone Dynamic:  Final=${nh_5z[-1]:.2f} ({btc_5z_ret*100:+.2f}%), Trades={tr_5z}")

print("\nPer-Token Breakdown for Alpha Fleet under 35% / 35% / 30%:")
for sym in alpha_tokens:
    b = r_35_35_30['bot_results'][sym]
    print(f"  {sym:<6}: Final=${b['final']:.2f} ({b['ret']*100:+.1f}%), Trades={b['trades']}")
