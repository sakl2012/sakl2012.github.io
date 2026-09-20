import json
import os
import math
import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

def load_data():
    """Load and harmonize historical daily prices from 2021-09-20 to 2026-09-18."""
    with open(os.path.join(CACHE_DIR, 'BTCUSDT_1d.json'), 'r', encoding='utf-8') as f:
        btc_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'ETHUSDT_1d.json'), 'r', encoding='utf-8') as f:
        eth_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'PAXGUSDT_1d.json'), 'r', encoding='utf-8') as f:
        paxg_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'BNBUSDT_1d.json'), 'r', encoding='utf-8') as f:
        bnb_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'SOLUSDT_1d.json'), 'r', encoding='utf-8') as f:
        sol_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'QQQ_1d.json'), 'r', encoding='utf-8') as f:
        qqq_raw = json.load(f)
    with open(os.path.join(CACHE_DIR, 'SPY_1d.json'), 'r', encoding='utf-8') as f:
        spy_raw = json.load(f)

    # Index by date
    btc_by_date = {b['date']: b['c'] for b in btc_raw}
    eth_by_date = {b['date']: b['c'] for b in eth_raw}
    paxg_by_date = {b['date']: b['c'] for b in paxg_raw}
    bnb_by_date = {b['date']: b['c'] for b in bnb_raw}
    sol_by_date = {b['date']: b['c'] for b in sol_raw}
    qqq_by_date = {b['date']: b['c'] for b in qqq_raw}
    spy_by_date = {b['date']: b['c'] for b in spy_raw}

    # Precalculate 200MA for BTC for every date
    # Sort all btc dates
    btc_dates_sorted = sorted(btc_raw, key=lambda x: x['date'])
    btc_ma200 = {}
    for i in range(len(btc_dates_sorted)):
        if i >= 199:
            window = btc_dates_sorted[i-199:i+1]
            btc_ma200[btc_dates_sorted[i]['date']] = sum(w['c'] for w in window) / 200.0

    # Backtest dates: exactly 5 years from 2021-09-20 to 2026-09-18
    # We use all calendar days from 2021-09-20 to 2026-09-18
    start_dt = datetime.date(2021, 9, 20)
    end_dt = datetime.date(2026, 9, 18)
    
    aligned_days = []
    last_qqq = None
    last_spy = None
    
    cur = start_dt
    while cur <= end_dt:
        d_str = cur.strftime('%Y-%m-%d')
        
        # Forward fill equity
        if d_str in qqq_by_date:
            last_qqq = qqq_by_date[d_str]
        if d_str in spy_by_date:
            last_spy = spy_by_date[d_str]
            
        if d_str in btc_by_date and d_str in paxg_by_date and d_str in btc_ma200:
            if last_qqq is None:
                # Find closest prior qqq
                last_qqq = qqq_raw[0]['c']
            if last_spy is None:
                last_spy = spy_raw[0]['c']
                
            btc_p = btc_by_date[d_str]
            ma200 = btc_ma200[d_str]
            r = btc_p / ma200
            
            aligned_days.append({
                'date': d_str,
                'BTC': btc_p,
                'ETH': eth_by_date.get(d_str, eth_raw[0]['c']),
                'BNB': bnb_by_date.get(d_str, bnb_raw[0]['c']),
                'SOL': sol_by_date.get(d_str, sol_raw[0]['c']),
                'PAXG': paxg_by_date[d_str],
                'QQQ': last_qqq,
                'SPY': last_spy,
                'MA200': ma200,
                'R': r
            })
            
        cur += datetime.timedelta(days=1)

    print(f"Harmonized {len(aligned_days)} trading days from {aligned_days[0]['date']} to {aligned_days[-1]['date']}")
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

def simulate_portfolio(days, coin_key, equity_key, zone_weights, fee_rate=0.001, rebal_threshold=0.01):
    """
    Simulate a 3-asset dynamic rebalance portfolio.
    zone_weights: dict mapping zone_id (0..4) -> (w_coin, w_equity, w_paxg)
    """
    initial_capital = 10000.0
    nav = initial_capital
    
    # Initialize holdings at day 0
    first_day = days[0]
    z0 = get_zone(first_day['R'])
    target_wc, target_we, target_wp = zone_weights[z0]
    
    p_coin = first_day[coin_key]
    p_eq = first_day[equity_key]
    p_paxg = first_day['PAXG']
    
    u_c = (nav * target_wc) / p_coin
    u_e = (nav * target_we) / p_eq
    u_p = (nav * target_wp) / p_paxg
    
    nav_history = [nav]
    rebal_trades = 0
    cur_zone = z0
    
    for i in range(1, len(days)):
        d = days[i]
        p_coin = d[coin_key]
        p_eq = d[equity_key]
        p_paxg = d['PAXG']
        
        val_c = u_c * p_coin
        val_e = u_e * p_eq
        val_p = u_p * p_paxg
        nav = val_c + val_e + val_p
        
        w_c = val_c / nav
        w_e = val_e / nav
        w_p = val_p / nav
        
        new_zone = get_zone(d['R'])
        zone_changed = (new_zone != cur_zone)
        cur_zone = new_zone
        
        target_wc, target_we, target_wp = zone_weights[cur_zone]
        
        # Check drift
        max_drift = max(abs(w_c - target_wc), abs(w_e - target_we), abs(w_p - target_wp))
        
        if zone_changed or max_drift >= rebal_threshold:
            # Rebalance
            tgt_val_c = nav * target_wc
            tgt_val_e = nav * target_we
            tgt_val_p = nav * target_wp
            
            delta_c = abs(tgt_val_c - val_c)
            delta_e = abs(tgt_val_e - val_e)
            delta_p = abs(tgt_val_p - val_p)
            
            trade_vol = (delta_c + delta_e + delta_p) / 2.0
            fee = trade_vol * fee_rate
            nav -= fee
            
            u_c = (nav * target_wc) / p_coin
            u_e = (nav * target_we) / p_eq
            u_p = (nav * target_wp) / p_paxg
            rebal_trades += 1
            
        nav_history.append(nav)
        
    # Calculate performance metrics
    total_ret = (nav - initial_capital) / initial_capital
    n_days = len(days)
    n_years = n_days / 365.25
    cagr = ((nav / initial_capital) ** (1.0 / n_years)) - 1.0
    
    # MDD
    peak = nav_history[0]
    max_dd = 0.0
    daily_returns = []
    for j in range(1, len(nav_history)):
        if nav_history[j] > peak:
            peak = nav_history[j]
        dd = (peak - nav_history[j]) / peak
        if dd > max_dd:
            max_dd = dd
        ret = (nav_history[j] / nav_history[j-1]) - 1.0
        daily_returns.append(ret)
        
    # Annualized Volatility & Sharpe
    mean_ret = sum(daily_returns) / len(daily_returns)
    var = sum((r - mean_ret)**2 for r in daily_returns) / len(daily_returns)
    daily_vol = math.sqrt(var)
    ann_vol = daily_vol * math.sqrt(365.25)
    rf = 0.03 # 3% risk-free
    sharpe = (cagr - rf) / ann_vol if ann_vol > 0 else 0.0
    
    # Calmar ratio
    calmar = cagr / max_dd if max_dd > 0 else 0.0
    
    # Sortino ratio
    downside_var = sum((min(0.0, r))**2 for r in daily_returns) / len(daily_returns)
    downside_vol = math.sqrt(downside_var) * math.sqrt(365.25)
    sortino = (cagr - rf) / downside_vol if downside_vol > 0 else 0.0
    
    return {
        'initial_capital': initial_capital,
        'final_nav': nav,
        'total_ret': total_ret,
        'cagr': cagr,
        'mdd': max_dd,
        'ann_vol': ann_vol,
        'sharpe': sharpe,
        'calmar': calmar,
        'sortino': sortino,
        'rebal_trades': rebal_trades,
        'nav_history': nav_history
    }

def simulate_buy_and_hold(days, asset_key):
    p0 = days[0][asset_key]
    nav_history = []
    initial_capital = 10000.0
    for d in days:
        nav = initial_capital * (d[asset_key] / p0)
        nav_history.append(nav)
    
    final_nav = nav_history[-1]
    total_ret = (final_nav - initial_capital) / initial_capital
    n_years = len(days) / 365.25
    cagr = ((final_nav / initial_capital) ** (1.0 / n_years)) - 1.0
    
    peak = nav_history[0]
    max_dd = 0.0
    daily_returns = []
    for j in range(1, len(nav_history)):
        if nav_history[j] > peak:
            peak = nav_history[j]
        dd = (peak - nav_history[j]) / peak
        if dd > max_dd:
            max_dd = dd
        ret = (nav_history[j] / nav_history[j-1]) - 1.0
        daily_returns.append(ret)
        
    mean_ret = sum(daily_returns) / len(daily_returns)
    var = sum((r - mean_ret)**2 for r in daily_returns) / len(daily_returns)
    ann_vol = math.sqrt(var) * math.sqrt(365.25)
    rf = 0.03
    sharpe = (cagr - rf) / ann_vol if ann_vol > 0 else 0.0
    calmar = cagr / max_dd if max_dd > 0 else 0.0
    
    return {
        'asset': asset_key,
        'total_ret': total_ret,
        'cagr': cagr,
        'mdd': max_dd,
        'ann_vol': ann_vol,
        'sharpe': sharpe,
        'calmar': calmar,
        'final_nav': final_nav
    }

def run_grid_search(days, coin_key='BTC', equity_key='QQQ'):
    print(f"\n=======================================================")
    print(f"RUNNING 5-YEAR GRID SEARCH FOR {coin_key} + {equity_key} + PAXG")
    print(f"=======================================================")
    
    # Candidate weights for each zone (w_coin, w_equity, w_paxg)
    # Zone 0 (Deep Bear: R < 0.80)
    cand_z0 = [
        (0.70, 0.20, 0.10),
        (0.75, 0.20, 0.05),
        (0.80, 0.15, 0.05),
        (0.65, 0.25, 0.10)
    ]
    # Zone 1 (Early Bull Recovery: 0.80 <= R < 1.00)
    cand_z1 = [
        (0.55, 0.25, 0.20),
        (0.60, 0.25, 0.15),
        (0.50, 0.30, 0.20),
        (0.65, 0.20, 0.15)
    ]
    # Zone 2 (Active Cruise: 1.00 <= R < 1.25)
    cand_z2 = [
        (0.40, 0.35, 0.25),
        (0.45, 0.35, 0.20),
        (0.40, 0.40, 0.20),
        (0.50, 0.30, 0.20)
    ]
    # Zone 3 (Overheat Alert: 1.25 <= R < 1.40)
    cand_z3 = [
        (0.25, 0.35, 0.40),
        (0.30, 0.35, 0.35),
        (0.20, 0.40, 0.40),
        (0.25, 0.40, 0.35)
    ]
    # Zone 4 (Extreme Greed Escape: R >= 1.40)
    cand_z4 = [
        (0.05, 0.30, 0.65),
        (0.05, 0.25, 0.70),
        (0.10, 0.30, 0.60),
        (0.00, 0.30, 0.70)
    ]
    
    best_calmar = -1.0
    best_config = None
    best_res = None
    min_mdd = 999.0
    min_mdd_config = None
    min_mdd_res = None
    all_results = []
    
    total_combinations = len(cand_z0) * len(cand_z1) * len(cand_z2) * len(cand_z3) * len(cand_z4)
    print(f"Total parameter combinations to evaluate: {total_combinations}")
    
    for w0 in cand_z0:
        for w1 in cand_z1:
            for w2 in cand_z2:
                for w3 in cand_z3:
                    for w4 in cand_z4:
                        zw = {0: w0, 1: w1, 2: w2, 3: w3, 4: w4}
                        res = simulate_portfolio(days, coin_key, equity_key, zw)
                        
                        item = {
                            'config': zw,
                            'cagr': res['cagr'],
                            'mdd': res['mdd'],
                            'calmar': res['calmar'],
                            'sharpe': res['sharpe'],
                            'total_ret': res['total_ret'],
                            'trades': res['rebal_trades'],
                            'res': res
                        }
                        all_results.append(item)
                        
                        if res['calmar'] > best_calmar:
                            best_calmar = res['calmar']
                            best_config = zw
                            best_res = res
                            
                        if res['mdd'] < min_mdd:
                            min_mdd = res['mdd']
                            min_mdd_config = zw
                            min_mdd_res = res

    # Sort all by Calmar ratio descending
    all_results.sort(key=lambda x: x['calmar'], reverse=True)
    
    print("\nTop 5 Parameter Configurations by Calmar:")
    for idx, r in enumerate(all_results[:5]):
        cfg = r['config']
        print(f"\nRank #{idx+1} | Calmar: {r['calmar']:.3f} | Sharpe: {r['sharpe']:.3f} | CAGR: {r['cagr']*100:.2f}% | MDD: {r['mdd']*100:.2f}% | Ret: {r['total_ret']*100:.1f}% | Trades: {r['trades']}")
        for z in range(5):
            print(f"  Zone {z}: {coin_key} {int(cfg[z][0]*100)}% / {equity_key} {int(cfg[z][1]*100)}% / PAXG {int(cfg[z][2]*100)}%")
            
    return best_config, best_res, all_results

def main():
    days = load_data()
    
    # 1. Inspect Zone distribution across the 5 years
    zone_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for d in days:
        z = get_zone(d['R'])
        zone_counts[z] += 1
    print("\n=======================================================")
    print("5-YEAR MARKET REGIME (ZONE) DISTRIBUTION (1825 Days):")
    print("=======================================================")
    print(f"Zone 0 (Deep Bear, R < 0.80):       {zone_counts[0]:4d} days ({zone_counts[0]/len(days)*100:5.1f}%)")
    print(f"Zone 1 (Early Bull, 0.80<=R<1.00):  {zone_counts[1]:4d} days ({zone_counts[1]/len(days)*100:5.1f}%)")
    print(f"Zone 2 (Active Cruise, 1.00<=R<1.25): {zone_counts[2]:4d} days ({zone_counts[2]/len(days)*100:5.1f}%)")
    print(f"Zone 3 (Overheat, 1.25<=R<1.40):    {zone_counts[3]:4d} days ({zone_counts[3]/len(days)*100:5.1f}%)")
    print(f"Zone 4 (Greed/Top, R >= 1.40):      {zone_counts[4]:4d} days ({zone_counts[4]/len(days)*100:5.1f}%)")
    
    print("\n=======================================================")
    print("5-YEAR BENCHMARKS (2021-09-20 to 2026-09-18, 5.0 Years)")
    print("=======================================================")
    for a in ['BTC', 'ETH', 'BNB', 'SOL', 'QQQ', 'SPY', 'PAXG']:
        bm = simulate_buy_and_hold(days, a)
        print(f"Buy & Hold {a:4s}: Total Ret: {bm['total_ret']*100:+7.2f}% | CAGR: {bm['cagr']*100:6.2f}% | MDD: {bm['mdd']*100:6.2f}% | Sharpe: {bm['sharpe']:5.2f} | Calmar: {bm['calmar']:5.2f}")

    # Evaluate Current Website Configuration
    # Current Website Ratios for BTC:
    # Z0: 75/20/5, Z1: 60/25/15, Z2: 45/35/20, Z3: 30/35/35, Z4: 5/30/65
    cur_web_btc = {
        0: (0.75, 0.20, 0.05),
        1: (0.60, 0.25, 0.15),
        2: (0.45, 0.35, 0.20),
        3: (0.30, 0.35, 0.35),
        4: (0.05, 0.30, 0.65)
    }
    cur_res_btc = simulate_portfolio(days, 'BTC', 'QQQ', cur_web_btc)
    print("\n=======================================================")
    print("CURRENT WEBSITE STRATEGY (BTC + QQQ + PAXG):")
    print(f"Total Ret: {cur_res_btc['total_ret']*100:+.2f}% | CAGR: {cur_res_btc['cagr']*100:.2f}% | MDD: {cur_res_btc['mdd']*100:.2f}% | Sharpe: {cur_res_btc['sharpe']:.2f} | Calmar: {cur_res_btc['calmar']:.2f} | Trades: {cur_res_btc['rebal_trades']}")
    print("=======================================================")

    # Run Grid Search for Core 1 (BTC)
    best_btc_cfg, best_btc_res, btc_all = run_grid_search(days, 'BTC', 'QQQ')
    
    # Run Grid Search for Core 2 (ETH)
    best_eth_cfg, best_eth_res, eth_all = run_grid_search(days, 'ETH', 'QQQ')

    # Run Grid Search for BNB (Long-cycle Alpha benchmark)
    best_bnb_cfg, best_bnb_res, bnb_all = run_grid_search(days, 'BNB', 'QQQ')

    # Save summary report
    summary = {
        'start_date': days[0]['date'],
        'end_date': days[-1]['date'],
        'total_days': len(days),
        'best_btc': {
            'config': best_btc_cfg,
            'metrics': {k: v for k, v in best_btc_res.items() if k != 'nav_history'}
        },
        'best_eth': {
            'config': best_eth_cfg,
            'metrics': {k: v for k, v in best_eth_res.items() if k != 'nav_history'}
        },
        'best_bnb': {
            'config': best_bnb_cfg,
            'metrics': {k: v for k, v in best_bnb_res.items() if k != 'nav_history'}
        },
        'current_web_btc': {
            'config': cur_web_btc,
            'metrics': {k: v for k, v in cur_res_btc.items() if k != 'nav_history'}
        }
    }
    
    report_path = os.path.join(os.path.dirname(__file__), '5year_optimization_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nOptimization results saved to {report_path}")

if __name__ == '__main__':
    main()
