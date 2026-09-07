#!/usr/bin/env python3
"""
Rigorous Historical Backtester & Parameter Optimization Engine
For 4-Zone Dynamic Portfolio Strategy on Binance
"""

import os
import json
import time
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

DATA_CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
os.makedirs(DATA_CACHE_DIR, exist_ok=True)

SYMBOLS = ["BTCUSDT", "SOLUSDT", "TAOUSDT", "AAVEUSDT", "LINKUSDT", "NEARUSDT", "PAXGUSDT"]

ZONE_CONFIGS = {
    1: {
        "name": "Zone 1 (Bear Bottom)",
        "A": {"BTC": 0.74, "PAXG": 0.26},
        "B": {"SOL": 0.26, "TAO": 0.29, "PAXG": 0.45},
        "C": {"AAVE": 0.36, "LINK": 0.25, "NEAR": 0.11, "PAXG": 0.27}
    },
    2: {
        "name": "Zone 2 (Bull Cruise)",
        "A": {"BTC": 0.58, "PAXG": 0.42},
        "B": {"SOL": 0.25, "TAO": 0.15, "PAXG": 0.60},
        "C": {"AAVE": 0.38, "NEAR": 0.22, "LINK": 0.11, "PAXG": 0.29}
    },
    3: {
        "name": "Zone 3 (Overheat Alert)",
        "A": {"BTC": 0.37, "PAXG": 0.63},
        "B": {"SOL": 0.18, "TAO": 0.19, "PAXG": 0.63},
        "C": {"LINK": 0.44, "NEAR": 0.08, "AAVE": 0.00, "PAXG": 0.48}
    },
    4: {
        "name": "Zone 4 (Greed/Top-Escape)",
        "A": {"BTC": 0.05, "PAXG": 0.95},
        "B": {"SOL": 0.07, "TAO": 0.13, "PAXG": 0.80},
        "C": {"PAXG": 0.66, "NEAR": 0.21, "LINK": 0.08, "AAVE": 0.05}
    }
}

def fetch_binance_klines(symbol, interval="1d", start_year=2021):
    cache_file = os.path.join(DATA_CACHE_DIR, f"{symbol}_{interval}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if len(data) > 300:
                    print(f"Loaded {symbol} from cache ({len(data)} bars).")
                    return data
        except Exception:
            pass

    print(f"Fetching {symbol} ({interval}) from Binance API...")
    all_klines = []
    start_time = int(datetime(start_year, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)

    curr_start = start_time
    while curr_start < end_time:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={curr_start}&limit=1000"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
                if not batch:
                    break
                all_klines.extend(batch)
                last_time = batch[-1][0]
                if last_time <= curr_start:
                    break
                curr_start = last_time + 1
                if len(batch) < 1000:
                    break
                time.sleep(0.1)
        except Exception as e:
            print(f"Error fetching {symbol} at {curr_start}: {e}")
            time.sleep(1)
            break

    # Parse klines into clean list of [timestamp, open, high, low, close]
    cleaned = []
    seen = set()
    for k in all_klines:
        t = k[0]
        if t in seen:
            continue
        seen.add(t)
        cleaned.append({
            "t": t,
            "date": datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
            "c": float(k[4]),
            "h": float(k[2]),
            "l": float(k[3]),
            "o": float(k[1])
        })

    cleaned.sort(key=lambda x: x["t"])
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cleaned, f)
    print(f"Saved {symbol}: {len(cleaned)} bars ({cleaned[0]['date']} to {cleaned[-1]['date']}).")
    return cleaned

def prepare_dataset():
    raw_data = {}
    for sym in SYMBOLS:
        raw_data[sym] = fetch_binance_klines(sym)

    # Align dates
    date_to_prices = {}
    for sym, klines in raw_data.items():
        base_sym = sym.replace("USDT", "")
        for k in klines:
            d = k["date"]
            if d not in date_to_prices:
                date_to_prices[d] = {}
            date_to_prices[d][base_sym] = k["c"]

    sorted_dates = sorted(date_to_prices.keys())

    # Precalculate BTC MA200 for each date
    btc_series = []
    btc_klines = {k["date"]: k["c"] for k in raw_data["BTCUSDT"]}
    for d in sorted_dates:
        if d in btc_klines:
            btc_series.append(btc_klines[d])
        else:
            btc_series.append(btc_series[-1] if btc_series else 30000.0)

    dataset = []
    for i, d in enumerate(sorted_dates):
        prices = date_to_prices[d]
        if i >= 200:
            ma200 = sum(btc_series[i-199:i+1]) / 200.0
        else:
            ma200 = sum(btc_series[:i+1]) / (i + 1)
        btc_p = prices.get("BTC", btc_series[i])
        ratio = btc_p / ma200 if ma200 > 0 else 1.0

        dataset.append({
            "date": d,
            "prices": prices,
            "btc_price": btc_p,
            "ma200": ma200,
            "ratio": ratio
        })

    return dataset

def run_simulation(
    dataset,
    start_date="2024-04-12", # TAO Binance Listing date for 100% full asset overlap
    threshold_A=0.05,
    threshold_B=0.05,
    threshold_C=0.10,
    fee_rate=0.0010,       # 0.10% Binance spot taker fee
    slippage_rate=0.0005,  # 0.05% slippage
    b_paxg_override=None,
    zone_upper_bounds=(1.00, 1.25, 1.40),
    periodic_days=None     # If set (e.g. 7 or 30), use calendar rebalancing instead of deviation
):
    total_friction = fee_rate + slippage_rate
    initial_capital = 10000.0

    # Start slice
    sim_data = [row for row in dataset if row["date"] >= start_date]
    if not sim_data:
        return None

    # Sub-portfolio capital allocations (A: 20%, B: 60%, C: 20%)
    cap_A = initial_capital * 0.20
    cap_B = initial_capital * 0.60
    cap_C = initial_capital * 0.20

    # Hold token quantities: {symbol: qty}
    first_prices = sim_data[0]["prices"]

    def init_sub_holdings(target_ratios, sub_cap):
        holdings = {}
        for sym, weight in target_ratios.items():
            p = first_prices.get(sym, 1.0)
            holdings[sym] = (sub_cap * weight) / p
        return holdings

    # Get initial zone
    init_ratio = sim_data[0]["ratio"]
    z1_max, z2_max, z3_max = zone_upper_bounds
    if init_ratio < z1_max:
        init_zone = 1
    elif init_ratio < z2_max:
        init_zone = 2
    elif init_ratio < z3_max:
        init_zone = 3
    else:
        init_zone = 4

    config = ZONE_CONFIGS[init_zone]
    ratios_A = dict(config["A"])
    ratios_B = dict(config["B"])
    ratios_C = dict(config["C"])

    if b_paxg_override is not None:
        # adjust B ratios to custom PAXG
        old_paxg = ratios_B["PAXG"]
        ratios_B["PAXG"] = b_paxg_override
        rem_weight = 1.0 - b_paxg_override
        old_rem = 1.0 - old_paxg
        for s in ["SOL", "TAO"]:
            if s in ratios_B:
                ratios_B[s] = (ratios_B[s] / old_rem) * rem_weight

    holdings_A = init_sub_holdings(ratios_A, cap_A)
    holdings_B = init_sub_holdings(ratios_B, cap_B)
    holdings_C = init_sub_holdings(ratios_C, cap_C)

    portfolio_values = []
    rebalance_events = 0
    zone_switch_events = 0
    total_fee_cost = 0.0

    current_zone = init_zone
    days_since_rebal = 0

    for day_idx, row in enumerate(sim_data):
        prices = row["prices"]
        ratio = row["ratio"]

        # 1. Update Zone dynamically based on BTC / MA200
        if ratio < z1_max:
            target_zone = 1
        elif ratio < z2_max:
            target_zone = 2
        elif ratio < z3_max:
            target_zone = 3
        else:
            target_zone = 4

        zone_changed = (target_zone != current_zone)
        if zone_changed:
            current_zone = target_zone
            zone_switch_events += 1
            config = ZONE_CONFIGS[current_zone]
            ratios_A = dict(config["A"])
            ratios_B = dict(config["B"])
            ratios_C = dict(config["C"])
            if b_paxg_override is not None:
                old_paxg = ratios_B["PAXG"]
                ratios_B["PAXG"] = b_paxg_override
                rem_weight = 1.0 - b_paxg_override
                old_rem = 1.0 - old_paxg
                for s in ["SOL", "TAO"]:
                    if s in ratios_B:
                        ratios_B[s] = (ratios_B[s] / old_rem) * rem_weight

        # 2. Compute current sub-portfolio values
        def eval_sub(holdings):
            val = 0.0
            asset_vals = {}
            for sym, qty in holdings.items():
                p = prices.get(sym, 1.0)
                v = qty * p
                asset_vals[sym] = v
                val += v
            return val, asset_vals

        val_A, vals_A = eval_sub(holdings_A)
        val_B, vals_B = eval_sub(holdings_B)
        val_C, vals_C = eval_sub(holdings_C)

        total_val = val_A + val_B + val_C
        portfolio_values.append({
            "date": row["date"],
            "val": total_val,
            "btc_price": row["btc_price"],
            "zone": current_zone
        })

        # 3. Check Rebalance Trigger for each sub-portfolio
        days_since_rebal += 1

        def check_and_rebalance(sub_val, asset_vals, target_ratios, threshold, holdings):
            nonlocal rebalance_events, total_fee_cost
            if sub_val <= 0:
                return holdings

            do_rebal = False
            if periodic_days is not None:
                if days_since_rebal >= periodic_days:
                    do_rebal = True
            elif zone_changed:
                do_rebal = True
            else:
                # Check absolute weight deviation
                for sym, target_w in target_ratios.items():
                    curr_w = asset_vals.get(sym, 0.0) / sub_val
                    if abs(curr_w - target_w) >= threshold:
                        do_rebal = True
                        break

            if do_rebal:
                rebalance_events += 1
                new_holdings = {}
                traded_vol = 0.0
                for sym, target_w in target_ratios.items():
                    curr_val = asset_vals.get(sym, 0.0)
                    desired_val = sub_val * target_w
                    turnover = abs(desired_val - curr_val)
                    traded_vol += turnover

                cost = traded_vol * total_friction
                total_fee_cost += cost
                net_sub_val = max(0.0, sub_val - cost)

                for sym, target_w in target_ratios.items():
                    p = prices.get(sym, 1.0)
                    new_holdings[sym] = (net_sub_val * target_w) / p
                return new_holdings
            return holdings

        holdings_A = check_and_rebalance(val_A, vals_A, ratios_A, threshold_A, holdings_A)
        holdings_B = check_and_rebalance(val_B, vals_B, ratios_B, threshold_B, holdings_B)
        holdings_C = check_and_rebalance(val_C, vals_C, ratios_C, threshold_C, holdings_C)

        if zone_changed or (periodic_days and days_since_rebal >= periodic_days):
            days_since_rebal = 0

    # Performance metrics
    start_v = portfolio_values[0]["val"]
    end_v = portfolio_values[-1]["val"]
    total_return = (end_v - start_v) / start_v

    days = len(portfolio_values)
    years = days / 365.25
    cagr = math.pow(end_v / start_v, 1.0 / years) - 1.0 if (years > 0 and end_v > 0) else 0.0

    # Max Drawdown
    peak = start_v
    max_dd = 0.0
    daily_returns = []
    for i in range(1, len(portfolio_values)):
        v = portfolio_values[i]["val"]
        prev_v = portfolio_values[i-1]["val"]
        ret = (v - prev_v) / prev_v
        daily_returns.append(ret)
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        if dd > max_dd:
            max_dd = dd

    # Sharpe Ratio (rf = 4%)
    rf_daily = 0.04 / 365.25
    excess_returns = [r - rf_daily for r in daily_returns]
    avg_excess = sum(excess_returns) / len(excess_returns) if excess_returns else 0.0
    var = sum((r - avg_excess - rf_daily)**2 for r in daily_returns) / len(daily_returns) if daily_returns else 0.0
    std = math.sqrt(var) if var > 0 else 0.0001
    sharpe = (avg_excess / std) * math.sqrt(365.25)

    # Calmar Ratio
    calmar = cagr / max_dd if max_dd > 0 else 0.0

    return {
        "start_date": sim_data[0]["date"],
        "end_date": sim_data[-1]["date"],
        "days": days,
        "total_return_pct": total_return * 100.0,
        "cagr_pct": cagr * 100.0,
        "max_drawdown_pct": max_dd * 100.0,
        "sharpe_ratio": sharpe,
        "calmar_ratio": calmar,
        "rebalance_count": rebalance_events,
        "zone_switch_count": zone_switch_events,
        "total_fee_usd": total_fee_cost,
        "end_value": end_v,
        "curve": [(p["date"], round(p["val"], 1)) for p in portfolio_values[::5]] # sample for plotting
    }

def run_benchmarks(dataset, start_date="2024-04-12"):
    sim_data = [row for row in dataset if row["date"] >= start_date]
    p0 = sim_data[0]["prices"]
    pn = sim_data[-1]["prices"]
    days = len(sim_data)
    years = days / 365.25

    def calc_stats(daily_series):
        s0 = daily_series[0]
        sn = daily_series[-1]
        tot = (sn - s0) / s0
        cagr = math.pow(sn / s0, 1.0 / years) - 1.0 if years > 0 else 0.0
        peak = s0
        mdd = 0.0
        daily_ret = []
        for i in range(1, len(daily_series)):
            v = daily_series[i]
            prev = daily_series[i-1]
            daily_ret.append((v - prev) / prev)
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > mdd:
                mdd = dd
        rf_daily = 0.04 / 365.25
        excess = [r - rf_daily for r in daily_ret]
        avg_ex = sum(excess) / len(excess) if excess else 0.0
        var = sum((r - avg_ex - rf_daily)**2 for r in daily_ret) / len(daily_ret) if daily_ret else 0.0
        std = math.sqrt(var) if var > 0 else 0.0001
        sharpe = (avg_ex / std) * math.sqrt(365.25)
        calmar = cagr / mdd if mdd > 0 else 0.0
        return {
            "total_return_pct": tot * 100.0,
            "cagr_pct": cagr * 100.0,
            "max_drawdown_pct": mdd * 100.0,
            "sharpe_ratio": sharpe,
            "calmar_ratio": calmar
        }

    btc_series = [r["btc_price"] for r in sim_data]
    btc_stats = calc_stats(btc_series)

    sol_series = [r["prices"].get("SOL", 100.0) for r in sim_data]
    sol_stats = calc_stats(sol_series)

    # Equal Weight HODL
    eq_series = []
    for r in sim_data:
        val = 0.0
        for s in ["BTC", "SOL", "TAO", "AAVE", "LINK", "NEAR", "PAXG"]:
            init_p = p0.get(s, 1.0)
            curr_p = r["prices"].get(s, init_p)
            val += (10000.0 / 7.0) * (curr_p / init_p)
        eq_series.append(val)
    eq_stats = calc_stats(eq_series)

    return {
        "BTC_HODL": btc_stats,
        "SOL_HODL": sol_stats,
        "EQUAL_WEIGHT": eq_stats
    }

def main():
    print("================================================================")
    print("4-Zone Strategy - Rigorous Historical Simulation & Parameter Sweep")
    print("================================================================")

    dataset = prepare_dataset()
    print(f"Total historical days available: {len(dataset)} ({dataset[0]['date']} to {dataset[-1]['date']})")

    # 1. Benchmark: Full Overlap Period (2024-04-12 to Present)
    print("\n--- Running Benchmarks (2024-04-12 to Present) ---")
    benchmarks = run_benchmarks(dataset, start_date="2024-04-12")
    for name, b in benchmarks.items():
        print(f"[{name:12s}] Return: {b['total_return_pct']:+6.1f}% | CAGR: {b['cagr_pct']:+5.1f}% | MDD: -{b['max_drawdown_pct']:4.1f}% | Sharpe: {b['sharpe_ratio']:4.2f} | Calmar: {b['calmar_ratio']:4.2f}")

    # 2. Baseline Test: Current Strategy Settings (5% / 5% / 10%)
    print("\n--- Baseline: Current 4-Zone Strategy Parameters ---")
    current_res = run_simulation(dataset, start_date="2024-04-12", threshold_A=0.05, threshold_B=0.05, threshold_C=0.10)
    print(f"[CURRENT 5/5/10] Return: {current_res['total_return_pct']:+6.1f}% | CAGR: {current_res['cagr_pct']:+5.1f}% | MDD: -{current_res['max_drawdown_pct']:4.1f}% | Sharpe: {current_res['sharpe_ratio']:4.2f} | Calmar: {current_res['calmar_ratio']:4.2f}")
    print(f"                 Total Rebalances: {current_res['rebalance_count']} | Friction Fees: ${current_res['total_fee_usd']:.1f} | Zone Switches: {current_res['zone_switch_count']}")

    # 3. Parameter Sweep 1: Rebalance Thresholds
    print("\n--- Parameter Sweep 1: Rebalance Threshold Sensitivity ---")
    threshold_candidates = [
        ("Tight 2%", 0.02, 0.02, 0.05),
        ("Active 3%", 0.03, 0.03, 0.07),
        ("Current 5%", 0.05, 0.05, 0.10),
        ("Relaxed 7%", 0.07, 0.07, 0.12),
        ("Loose 10%", 0.10, 0.10, 0.15),
        ("Very Loose 15%", 0.15, 0.15, 0.20),
    ]
    sweep_results = []
    for label, tA, tB, tC in threshold_candidates:
        r = run_simulation(dataset, start_date="2024-04-12", threshold_A=tA, threshold_B=tB, threshold_C=tC)
        sweep_results.append((label, r))
        print(f"[{label:14s}] Return: {r['total_return_pct']:+6.1f}% | CAGR: {r['cagr_pct']:+5.1f}% | MDD: -{r['max_drawdown_pct']:4.1f}% | Sharpe: {r['sharpe_ratio']:4.2f} | Calmar: {r['calmar_ratio']:4.2f} | Rebal: {r['rebalance_count']:3d} | Fees: ${r['total_fee_usd']:5.1f}")

    # 4. Periodic Calendar Rebalance vs Threshold Rebalance
    print("\n--- Comparison: Calendar Periodic Rebalancing vs Deviation Threshold ---")
    cal_candidates = [
        ("Calendar 7 Days", 7),
        ("Calendar 14 Days", 14),
        ("Calendar 30 Days", 30)
    ]
    for label, days in cal_candidates:
        r = run_simulation(dataset, start_date="2024-04-12", periodic_days=days)
        print(f"[{label:16s}] Return: {r['total_return_pct']:+6.1f}% | CAGR: {r['cagr_pct']:+5.1f}% | MDD: -{r['max_drawdown_pct']:4.1f}% | Sharpe: {r['sharpe_ratio']:4.2f} | Calmar: {r['calmar_ratio']:4.2f} | Rebal: {r['rebalance_count']:3d} | Fees: ${r['total_fee_usd']:5.1f}")

    # 5. Parameter Sweep 2: PAXG Gold Allocation in B-Tier (Satellite 60%)
    print("\n--- Parameter Sweep 2: B-Tier Gold (PAXG) Anchor Sensitivity ---")
    paxg_candidates = [0.40, 0.50, 0.60, 0.70]
    paxg_results = []
    for p_gold in paxg_candidates:
        r = run_simulation(dataset, start_date="2024-04-12", b_paxg_override=p_gold)
        paxg_results.append((p_gold, r))
        print(f"[PAXG {int(p_gold*100)}% in B] Return: {r['total_return_pct']:+6.1f}% | CAGR: {r['cagr_pct']:+5.1f}% | MDD: -{r['max_drawdown_pct']:4.1f}% | Sharpe: {r['sharpe_ratio']:4.2f} | Calmar: {r['calmar_ratio']:4.2f} | End Val: ${r['end_value']:,.0f}")

    # 6. Parameter Sweep 3: Zone 2 Upper Ratio Threshold (1.20 vs 1.25 vs 1.30)
    print("\n--- Parameter Sweep 3: Zone 2 Transition Sensitivity ---")
    zone_candidates = [
        ("Zone 2 [1.00 ~ 1.20]", (1.00, 1.20, 1.40)),
        ("Zone 2 [1.00 ~ 1.25] (Curr)", (1.00, 1.25, 1.40)),
        ("Zone 2 [1.00 ~ 1.30]", (1.00, 1.30, 1.45))
    ]
    for label, z_bounds in zone_candidates:
        r = run_simulation(dataset, start_date="2024-04-12", zone_upper_bounds=z_bounds)
        print(f"[{label:26s}] Return: {r['total_return_pct']:+6.1f}% | CAGR: {r['cagr_pct']:+5.1f}% | MDD: -{r['max_drawdown_pct']:4.1f}% | Sharpe: {r['sharpe_ratio']:4.2f} | Calmar: {r['calmar_ratio']:4.2f}")

    # 7. Long 5-Year Macro Backtest (2021-01-01 to Present)
    print("\n--- 5-Year Macro Stress Test (2021 to Present) ---")
    long_res = run_simulation(dataset, start_date="2021-01-01")
    long_bench = run_benchmarks(dataset, start_date="2021-01-01")
    print(f"[5Y Strategy 4-Zone] Return: {long_res['total_return_pct']:+6.1f}% | CAGR: {long_res['cagr_pct']:+5.1f}% | MDD: -{long_res['max_drawdown_pct']:4.1f}% | Sharpe: {long_res['sharpe_ratio']:4.2f} | Calmar: {long_res['calmar_ratio']:4.2f}")
    print(f"[5Y BTC Buy & Hold ] Return: {long_bench['BTC_HODL']['total_return_pct']:+6.1f}% | CAGR: {long_bench['BTC_HODL']['cagr_pct']:+5.1f}% | MDD: -{long_bench['BTC_HODL']['max_drawdown_pct']:4.1f}% | Sharpe: {long_bench['BTC_HODL']['sharpe_ratio']:4.2f} | Calmar: {long_bench['BTC_HODL']['calmar_ratio']:4.2f}")
    print(f"[5Y Equal Weight HODL] Return: {long_bench['EQUAL_WEIGHT']['total_return_pct']:+6.1f}% | CAGR: {long_bench['EQUAL_WEIGHT']['cagr_pct']:+5.1f}% | MDD: -{long_bench['EQUAL_WEIGHT']['max_drawdown_pct']:4.1f}% | Sharpe: {long_bench['EQUAL_WEIGHT']['sharpe_ratio']:4.2f} | Calmar: {long_bench['EQUAL_WEIGHT']['calmar_ratio']:4.2f}")

    # Output full summary JSON for reporting
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmarks": benchmarks,
        "current_strategy": current_res,
        "sweep_thresholds": {label: r for label, r in sweep_results},
        "sweep_paxg": {f"{int(p*100)}%": r for p, r in paxg_results},
        "long_term_5y": {
            "strategy": long_res,
            "btc": long_bench["BTC_HODL"],
            "equal_weight": long_bench["EQUAL_WEIGHT"]
        }
    }

    out_file = os.path.join(os.path.dirname(__file__), "backtest_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nSaved comprehensive backtest report data to: {out_file}")

if __name__ == "__main__":
    main()
