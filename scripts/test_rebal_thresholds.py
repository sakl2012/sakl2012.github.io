import json
import os
import math
import datetime
from simulate_user_exact_fleet import days_5y, bots_5y, get_zone, simulate_bot

# We will test thresholds from 0.005 to 0.10
thresholds = [0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07, 0.10]

def simulate_bot_with_thresh(days_list, coin_key, is_5z, zone_weights, static_weights, threshold, initial_cap=1000.0):
    nav = initial_cap
    z0 = get_zone(days_list[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zone_weights[z0] if is_5z else static_weights
    u_c = (nav * w_c) / days_list[0][coin_key]
    u_q = (nav * w_q) / days_list[0]['QQQ']
    u_p = (nav * w_p) / days_list[0]['PAXG']
    nav_history = [nav]
    trades = 0
    total_fee_paid = 0.0
    
    for i in range(1, len(days_list)):
        d = days_list[i]
        p_c, p_q, p_p = d[coin_key], d['QQQ'], d['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        cur_wc = val_c / nav
        cur_wq = val_q / nav
        cur_wp = val_p / nav
        
        if is_5z:
            new_z = get_zone(d['R'])
            zone_changed = (new_z != cur_z)
            cur_z = new_z
            tw_c, tw_q, tw_p = zone_weights[cur_z]
        else:
            zone_changed = False
            tw_c, tw_q, tw_p = static_weights
            
        drift = max(abs(cur_wc - tw_c), abs(cur_wq - tw_q), abs(cur_wp - tw_p))
        if zone_changed or drift >= threshold:
            trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
            fee = trade_vol * 0.001
            nav -= fee
            total_fee_paid += fee
            u_c = (nav * tw_c) / p_c
            u_q = (nav * tw_q) / p_q
            u_p = (nav * tw_p) / p_p
            trades += 1
        nav_history.append(nav)
    return nav_history, trades, total_fee_paid

def run_fleet_thresh(is_5z, threshold, static_w=(0.3333, 0.3333, 0.3334)):
    tot_nav = [0.0] * len(days_5y)
    tot_trades = 0
    tot_fees = 0.0
    
    for sym, label, cap, zw in bots_5y:
        nh, tr, fee = simulate_bot_with_thresh(days_5y, sym, is_5z, zw, static_w, threshold, initial_cap=cap)
        tot_trades += tr
        tot_fees += fee
        for i in range(len(days_5y)):
            tot_nav[i] += nh[i]
            
    final = tot_nav[-1]
    ret = (final - 10000.0) / 10000.0
    n_years = len(days_5y) / 365.25
    cagr = ((final / 10000.0) ** (1.0 / n_years)) - 1.0
    
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
        'threshold': threshold,
        'final': final,
        'ret': ret,
        'cagr': cagr,
        'mdd': mdd,
        'sharpe': sharpe,
        'calmar': calmar,
        'trades': tot_trades,
        'fees': tot_fees
    }

print("=== SENSITIVITY TEST: REBALANCING THRESHOLDS (0.5% ~ 10%) ===")
print("User's Exact 5-Year Fleet (BTC, ETH, BNB, UNI, AAVE, LINK, NEAR - $10k Initial)\n")

print("--- 1. 5-Zone Dynamic Strategy Under Different Thresholds ---")
print(f"{'Threshold':<10} | {'Final NAV':<12} | {'Total Ret':<10} | {'CAGR':<8} | {'MDD':<8} | {'Sharpe':<7} | {'Trades':<8} | {'Fees Paid':<10}")
print("-" * 88)
results_5z = []
for th in thresholds:
    r = run_fleet_thresh(True, th)
    results_5z.append(r)
    print(f"{th*100:>5.1f}%     | ${r['final']:>10.2f} | {r['ret']*100:>8.2f}% | {r['cagr']*100:>6.2f}% | {r['mdd']*100:>6.2f}% | {r['sharpe']:>7.3f} | {r['trades']:>6}   | ${r['fees']:>8.2f}")

print("\n--- 2. Static Equal Weight (33/33/33) Under Different Thresholds ---")
print(f"{'Threshold':<10} | {'Final NAV':<12} | {'Total Ret':<10} | {'CAGR':<8} | {'MDD':<8} | {'Sharpe':<7} | {'Trades':<8} | {'Fees Paid':<10}")
print("-" * 88)
results_eq = []
for th in thresholds:
    r = run_fleet_thresh(False, th, (0.3333, 0.3333, 0.3334))
    results_eq.append(r)
    print(f"{th*100:>5.1f}%     | ${r['final']:>10.2f} | {r['ret']*100:>8.2f}% | {r['cagr']*100:>6.2f}% | {r['mdd']*100:>6.2f}% | {r['sharpe']:>7.3f} | {r['trades']:>6}   | ${r['fees']:>8.2f}")

# Also test single BTC bot sensitivity
print("\n--- 3. Single Core 1 (BTC) Bot Under Different Thresholds ($10k Initial) ---")
print(f"{'Threshold':<10} | {'5Z Final':<12} | {'5Z Trades':<10} | {'Static Final':<14} | {'Static Trades':<14}")
print("-" * 75)
for th in thresholds:
    zw_btc = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.45, 0.35, 0.20), 3: (0.30, 0.35, 0.35), 4: (0.05, 0.30, 0.65)}
    n_5z, t_5z, _ = simulate_bot_with_thresh(days_5y, 'BTC', True, zw_btc, (0.3333, 0.3333, 0.3334), th, 10000.0)
    n_eq, t_eq, _ = simulate_bot_with_thresh(days_5y, 'BTC', False, zw_btc, (0.3333, 0.3333, 0.3334), th, 10000.0)
    print(f"{th*100:>5.1f}%     | ${n_5z[-1]:>10.2f} | {t_5z:>8}   | ${n_eq[-1]:>12.2f} | {t_eq:>12}")
