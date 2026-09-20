import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

def load_data():
    with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
        btc_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'PAXGUSDT_1d.json'), 'r', encoding='utf-8') as f:
        paxg_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
        qqq_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'SPY_1d.json'), 'r', encoding='utf-8') as f:
        spy_raw = json.load(f)

    btc_by_date = {b['date']: b['c'] for b in btc_raw}
    paxg_by_date = {b['date']: b['c'] for b in paxg_raw}
    qqq_by_date = {b['date']: b['c'] for b in qqq_raw}
    spy_by_date = {b['date']: b['c'] for b in spy_raw}

    btc_dates_sorted = sorted(btc_raw, key=lambda x: x['date'])
    btc_ma200 = {}
    for i in range(len(btc_dates_sorted)):
        if i >= 199:
            window = btc_dates_sorted[i-199:i+1]
            btc_ma200[btc_dates_sorted[i]['date']] = sum(w['c'] for w in window) / 200.0

    start_dt = datetime.date(2021, 9, 20)
    end_dt = datetime.date(2026, 9, 18)
    
    aligned_days = []
    last_qqq = qqq_raw[0]['c']
    last_spy = spy_raw[0]['c']
    
    cur = start_dt
    while cur <= end_dt:
        d_str = cur.strftime('%Y-%m-%d')
        if d_str in qqq_by_date:
            last_qqq = qqq_by_date[d_str]
        if d_str in spy_by_date:
            last_spy = spy_by_date[d_str]
            
        if d_str in btc_by_date and d_str in paxg_by_date and d_str in btc_ma200:
            btc_p = btc_by_date[d_str]
            ma200 = btc_ma200[d_str]
            r = btc_p / ma200
            aligned_days.append({
                'date': d_str,
                'BTC': btc_p,
                'PAXG': paxg_by_date[d_str],
                'QQQ': last_qqq,
                'SPY': last_spy,
                'MA200': ma200,
                'R': r
            })
        cur += datetime.timedelta(days=1)
    return aligned_days

def get_zone(r):
    if r < 0.80:
        return 0
    elif r < 1.00:
        return 1
    elif r < 1.25:
        return 2
    elif r < 1.40:
        return 3
    else:
        return 4

def simulate(days, asset1, asset2, asset3, zone_weights, fee_rate=0.001, rebal_threshold=0.01):
    initial_capital = 10000.0
    nav = initial_capital
    
    first_day = days[0]
    z0 = get_zone(first_day['R'])
    target_w1, target_w2, target_w3 = zone_weights[z0]
    
    p1 = first_day[asset1]
    p2 = first_day[asset2]
    p3 = first_day[asset3]
    
    u1 = (nav * target_w1) / p1
    u2 = (nav * target_w2) / p2
    u3 = (nav * target_w3) / p3
    
    nav_history = [{'date': first_day['date'], 'nav': nav}]
    rebal_trades = 0
    cur_zone = z0
    
    for i in range(1, len(days)):
        d = days[i]
        p1 = d[asset1]
        p2 = d[asset2]
        p3 = d[asset3]
        
        val1 = u1 * p1
        val2 = u2 * p2
        val3 = u3 * p3
        nav = val1 + val2 + val3
        
        w1 = val1 / nav
        w2 = val2 / nav
        w3 = val3 / nav
        
        new_zone = get_zone(d['R'])
        zone_changed = (new_zone != cur_zone)
        cur_zone = new_zone
        
        target_w1, target_w2, target_w3 = zone_weights[cur_zone]
        max_drift = max(abs(w1 - target_w1), abs(w2 - target_w2), abs(w3 - target_w3))
        
        if zone_changed or max_drift >= rebal_threshold:
            tgt_val1 = nav * target_w1
            tgt_val2 = nav * target_w2
            tgt_val3 = nav * target_w3
            
            delta1 = abs(tgt_val1 - val1)
            delta2 = abs(tgt_val2 - val2)
            delta3 = abs(tgt_val3 - val3)
            
            trade_vol = (delta1 + delta2 + delta3) / 2.0
            fee = trade_vol * fee_rate
            nav -= fee
            
            u1 = (nav * target_w1) / p1
            u2 = (nav * target_w2) / p2
            u3 = (nav * target_w3) / p3
            rebal_trades += 1
            
        nav_history.append({'date': d['date'], 'nav': nav})
        
    total_ret = (nav - initial_capital) / initial_capital
    n_years = len(days) / 365.25
    cagr = ((nav / initial_capital) ** (1.0 / n_years)) - 1.0
    
    peak = nav_history[0]['nav']
    max_dd = 0.0
    daily_returns = []
    mdd_date = None
    
    # Also track 2022 bear market drawdown (2021-11-10 to 2022-12-31)
    peak_2022 = 0.0
    mdd_2022 = 0.0
    
    for j in range(1, len(nav_history)):
        cur_nav = nav_history[j]['nav']
        cur_date = nav_history[j]['date']
        
        if cur_nav > peak:
            peak = cur_nav
        dd = (peak - cur_nav) / peak
        if dd > max_dd:
            max_dd = dd
            mdd_date = cur_date
            
        if '2021-11-01' <= cur_date <= '2022-12-31':
            if cur_nav > peak_2022:
                peak_2022 = cur_nav
            dd_22 = (peak_2022 - cur_nav) / peak_2022 if peak_2022 > 0 else 0
            if dd_22 > mdd_2022:
                mdd_2022 = dd_22
                
        ret = (cur_nav / nav_history[j-1]['nav']) - 1.0
        daily_returns.append(ret)
        
    mean_ret = sum(daily_returns) / len(daily_returns)
    var = sum((r - mean_ret)**2 for r in daily_returns) / len(daily_returns)
    daily_vol = math.sqrt(var)
    ann_vol = daily_vol * math.sqrt(365.25)
    rf = 0.03
    sharpe = (cagr - rf) / ann_vol if ann_vol > 0 else 0.0
    calmar = cagr / max_dd if max_dd > 0 else 0.0
    
    return {
        'total_ret': total_ret,
        'cagr': cagr,
        'max_dd': max_dd,
        'mdd_2022': mdd_2022,
        'mdd_date': mdd_date,
        'sharpe': sharpe,
        'calmar': calmar,
        'ann_vol': ann_vol,
        'trades': rebal_trades,
        'final_nav': nav
    }

def pearson(x, y):
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((x[i] - mean_x)**2 for i in range(n))
    var_y = sum((y[i] - mean_y)**2 for i in range(n))
    return cov / math.sqrt(var_x * var_y)

def main():
    days = load_data()
    
    # Calculate daily log returns
    ret_btc = []
    ret_qqq = []
    ret_spy = []
    ret_paxg = []
    for i in range(1, len(days)):
        ret_btc.append(math.log(days[i]['BTC'] / days[i-1]['BTC']))
        ret_qqq.append(math.log(days[i]['QQQ'] / days[i-1]['QQQ']))
        ret_spy.append(math.log(days[i]['SPY'] / days[i-1]['SPY']))
        ret_paxg.append(math.log(days[i]['PAXG'] / days[i-1]['PAXG']))
        
    print("--- 5-Year Asset Correlations (Daily Returns 2021-2026) ---")
    print(f"Corr(QQQ, SPY):  {pearson(ret_qqq, ret_spy):.4f}")
    print(f"Corr(BTC, QQQ):  {pearson(ret_btc, ret_qqq):.4f}")
    print(f"Corr(BTC, SPY):  {pearson(ret_btc, ret_spy):.4f}")
    print(f"Corr(BTC, PAXG): {pearson(ret_btc, ret_paxg):.4f}")
    print(f"Corr(QQQ, PAXG): {pearson(ret_qqq, ret_paxg):.4f}")
    print(f"Corr(SPY, PAXG): {pearson(ret_spy, ret_paxg):.4f}")
    
    # 2022 Bear Market only correlation
    ret_btc_22, ret_qqq_22, ret_spy_22, ret_paxg_22 = [], [], [], []
    for i in range(1, len(days)):
        if '2022-01-01' <= days[i]['date'] <= '2022-12-31':
            ret_btc_22.append(math.log(days[i]['BTC'] / days[i-1]['BTC']))
            ret_qqq_22.append(math.log(days[i]['QQQ'] / days[i-1]['QQQ']))
            ret_spy_22.append(math.log(days[i]['SPY'] / days[i-1]['SPY']))
            ret_paxg_22.append(math.log(days[i]['PAXG'] / days[i-1]['PAXG']))
            
    print("\n--- 2022 Bear Market Crash Correlations (2022-01-01 ~ 2022-12-31) ---")
    print(f"Corr(QQQ, SPY):  {pearson(ret_qqq_22, ret_spy_22):.4f}")
    print(f"Corr(BTC, QQQ):  {pearson(ret_btc_22, ret_qqq_22):.4f}")
    print(f"Corr(BTC, PAXG): {pearson(ret_btc_22, ret_paxg_22):.4f}")
    print(f"Corr(QQQ, PAXG): {pearson(ret_qqq_22, ret_paxg_22):.4f}")
    
    # Zone weights (Standard Pareto Tri-Asset)
    # Zone 0: 65% Coin, 25% Asset2, 10% Asset3
    # Zone 1: 50% Coin, 30% Asset2, 20% Asset3
    # Zone 2: 45% Coin, 35% Asset2, 20% Asset3
    # Zone 3: 30% Coin, 35% Asset2, 35% Asset3
    # Zone 4:  5% Coin, 30% Asset2, 65% Asset3
    zone_weights_std = {
        0: (0.65, 0.25, 0.10),
        1: (0.50, 0.30, 0.20),
        2: (0.45, 0.35, 0.20),
        3: (0.30, 0.35, 0.35),
        4: (0.05, 0.30, 0.65)
    }
    
    res_gold = simulate(days, 'BTC', 'QQQ', 'PAXG', zone_weights_std)
    res_spy = simulate(days, 'BTC', 'QQQ', 'SPY', zone_weights_std)
    res_btc_spy_gold = simulate(days, 'BTC', 'SPY', 'PAXG', zone_weights_std)
    
    # Print comparison
    print("\n--- 5-Year Portfolio Simulation Results (2021-09-20 ~ 2026-09-18) ---")
    print(f"{'Metric':<20} | {'BTC+QQQ+PAXG (Gold)':<22} | {'BTC+QQQ+SPY (Double Equity)':<26} | {'BTC+SPY+PAXG (Broad+Gold)':<22}")
    print("-" * 95)
    print(f"{'Total Return':<20} | {res_gold['total_ret']*100:>19.2f}% | {res_spy['total_ret']*100:>23.2f}% | {res_btc_spy_gold['total_ret']*100:>19.2f}%")
    print(f"{'CAGR':<20} | {res_gold['cagr']*100:>19.2f}% | {res_spy['cagr']*100:>23.2f}% | {res_btc_spy_gold['cagr']*100:>19.2f}%")
    print(f"{'Max Drawdown (5Y)':<20} | {res_gold['max_dd']*100:>19.2f}% | {res_spy['max_dd']*100:>23.2f}% | {res_btc_spy_gold['max_dd']*100:>19.2f}%")
    print(f"{'MDD in 2022 Crash':<20} | {res_gold['mdd_2022']*100:>19.2f}% | {res_spy['mdd_2022']*100:>23.2f}% | {res_btc_spy_gold['mdd_2022']*100:>19.2f}%")
    print(f"{'Sharpe Ratio':<20} | {res_gold['sharpe']:>20.3f} | {res_spy['sharpe']:>24.3f} | {res_btc_spy_gold['sharpe']:>20.3f}")
    print(f"{'Calmar Ratio':<20} | {res_gold['calmar']:>20.3f} | {res_spy['calmar']:>24.3f} | {res_btc_spy_gold['calmar']:>20.3f}")
    print(f"{'Annual Volatility':<20} | {res_gold['ann_vol']*100:>19.2f}% | {res_spy['ann_vol']*100:>23.2f}% | {res_btc_spy_gold['ann_vol']*100:>19.2f}%")
    print(f"{'Rebalance Count':<20} | {res_gold['trades']:>20} | {res_spy['trades']:>24} | {res_btc_spy_gold['trades']:>20}")
    print(f"{'Final NAV ($10k)':<20} | ${res_gold['final_nav']:>19.2f} | ${res_spy['final_nav']:>23.2f} | ${res_btc_spy_gold['final_nav']:>19.2f}")

    # Output JSON summary for artifact
    out = {
        'correlations_5y': {
            'QQQ_SPY': pearson(ret_qqq, ret_spy),
            'BTC_QQQ': pearson(ret_btc, ret_qqq),
            'BTC_SPY': pearson(ret_btc, ret_spy),
            'BTC_PAXG': pearson(ret_btc, ret_paxg),
            'QQQ_PAXG': pearson(ret_qqq, ret_paxg),
            'SPY_PAXG': pearson(ret_spy, ret_paxg)
        },
        'correlations_2022': {
            'QQQ_SPY': pearson(ret_qqq_22, ret_spy_22),
            'BTC_QQQ': pearson(ret_btc_22, ret_qqq_22),
            'BTC_PAXG': pearson(ret_btc_22, ret_paxg_22),
            'QQQ_PAXG': pearson(ret_qqq_22, ret_paxg_22)
        },
        'res_gold': res_gold,
        'res_spy': res_spy,
        'res_btc_spy_gold': res_btc_spy_gold
    }
    with open(os.path.join(os.path.dirname(__file__), 'gold_vs_spy_comparison.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

if __name__ == '__main__':
    main()
