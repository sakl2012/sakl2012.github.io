import json, os, math
from datetime import datetime, timezone

# -------------------------------------------------------------
# 1. 加載真實小時級 K 線 (1h Klines)
# -------------------------------------------------------------
tokens = ['BTC', 'SOL', 'TAO', 'AAVE', 'LINK', 'NEAR', 'SUI', 'PAXG']
cache_1h = 'scripts/data_cache_1h'
data_1h = {}
for s in tokens:
    with open(os.path.join(cache_1h, f'{s}USDT_1h.json')) as f:
        data_1h[s] = json.load(f)

common_ts = set(x['t'] for x in data_1h['TAO'])
for s in tokens:
    common_ts = common_ts & set(x['t'] for x in data_1h[s])
sorted_ts = sorted(list(common_ts))

bars = {t: {} for t in sorted_ts}
for s in tokens:
    for bar in data_1h[s]:
        if bar['t'] in bars:
            bars[bar['t']][s] = bar

# -------------------------------------------------------------
# 2. 計算 BTC MA200 (每日 UTC 00:00 更新) 與 每小時 72h SMA
# -------------------------------------------------------------
with open('scripts/data_cache/BTCUSDT_1d.json') as f:
    btc_1d = json.load(f)
btc_1d_dict = {row['date']: row['c'] for row in btc_1d}
all_dates = sorted(list(btc_1d_dict.keys()))
daily_ma200 = {}
for i, d in enumerate(all_dates):
    if i >= 199:
        daily_ma200[d] = sum(btc_1d_dict[all_dates[j]] for j in range(i-199, i+1)) / 200.0

btc_closes = [bars[t]['BTC']['c'] for t in sorted_ts]
sma72_dict = {}
for i, t in enumerate(sorted_ts):
    if i >= 71:
        sma72_dict[t] = sum(btc_closes[i-71:i+1]) / 72.0
    else:
        sma72_dict[t] = sum(btc_closes[:i+1]) / float(i+1)

# -------------------------------------------------------------
# 3. 加載真實資金費率
# -------------------------------------------------------------
cache_funding = 'scripts/data_cache_funding'
funding_dict = {}
for s in ['BTC', 'SOL', 'AAVE', 'LINK', 'NEAR', 'SUI']:
    with open(os.path.join(cache_funding, f'{s}USDT_funding.json')) as f:
        f_list = json.load(f)
        funding_dict[s] = {row['t']: row['r'] for row in f_list}

def get_funding_income_or_cost(token, notional, t):
    # 每 8 小時結算一次
    if token in funding_dict and t in funding_dict[token]:
        return notional * funding_dict[token][t]
    return 0.0

# -------------------------------------------------------------
# 4. 動態非線性滑點 + Taker 摩擦手續費函數
# -------------------------------------------------------------
def get_friction_rate(token, bar):
    base_taker = 0.0010 # 0.10% Binance Taker
    volatility = (bar['h'] - bar['l']) / bar['l'] if bar['l'] > 0 else 0.005
    base_slip = 0.0005 # 0.05%
    if token in ['PAXG', 'TAO']:
        base_slip += 0.0005 # 深度保護 +0.05%
    if volatility > 0.015:
        # 單小時波幅大於 1.5% 時，非線性擴大衝擊滑點 (最高至 0.35%)
        impact = min(0.0030, (volatility - 0.015) * 0.15)
        base_slip += impact
    return base_taker + base_slip

# -------------------------------------------------------------
# 5. 策略配置定義
# -------------------------------------------------------------
rules_4zone = {
    1: {
        'A': {'BTC': 0.74, 'PAXG': 0.26},
        'B': {'SOL': 0.26, 'TAO': 0.29, 'PAXG': 0.45},
        'C': {'AAVE': 0.25, 'SUI': 0.20, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.25}
    },
    2: {
        'A': {'BTC': 0.58, 'PAXG': 0.42},
        'B': {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60},
        'C': {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30}
    },
    3: {
        'A': {'BTC': 0.37, 'PAXG': 0.63},
        'B': {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63},
        'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45}
    },
    4: {
        'A': {'BTC': 0.05, 'PAXG': 0.95},
        'B': {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80},
        'C': {'PAXG': 0.75, 'AAVE': 0.08, 'LINK': 0.07, 'SUI': 0.05, 'NEAR': 0.05}
    }
}

rules_5zone = {
    0: { # 極限深熊底 (<0.80) -> 全面抄底
        'A': {'BTC': 0.80, 'PAXG': 0.20},
        'B': {'SOL': 0.30, 'TAO': 0.35, 'PAXG': 0.35},
        'C': {'AAVE': 0.30, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15}
    },
    1: { # 初熊陰跌防守 (0.80 <= R < 1.00) -> 高黃金避險，不接飛刀
        'A': {'BTC': 0.40, 'PAXG': 0.60},
        'B': {'SOL': 0.15, 'TAO': 0.15, 'PAXG': 0.70},
        'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.10, 'NEAR': 0.10, 'PAXG': 0.50}
    },
    2: { # 牛市巡航 (1.00 <= R < 1.25)
        'A': {'BTC': 0.58, 'PAXG': 0.42},
        'B': {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60},
        'C': {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30}
    },
    3: { # 過熱警戒 (1.25 <= R < 1.40)
        'A': {'BTC': 0.37, 'PAXG': 0.63},
        'B': {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63},
        'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45}
    },
    4: { # 極度逃頂 (R >= 1.40)
        'A': {'BTC': 0.05, 'PAXG': 0.95},
        'B': {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80},
        'C': {'PAXG': 0.75, 'AAVE': 0.08, 'LINK': 0.07, 'SUI': 0.05, 'NEAR': 0.05}
    }
}

# -------------------------------------------------------------
# 6. 高保真小時級回測模擬引擎 (含 24h 執行冷卻 + 72h SMA 雙重濾波)
# -------------------------------------------------------------
def run_high_fidelity_simulation(zone_rules, get_zone_func, name, use_sma72=True, cooldown_hours=24):
    initial_cap = 10000.0
    cap_A = initial_cap * 0.20
    cap_B = initial_cap * 0.55
    cap_C = initial_cap * 0.25
    
    t0 = sorted_ts[0]
    d0_str = datetime.fromtimestamp(t0/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    ma0 = daily_ma200.get(d0_str, 50000.0)
    p0 = {s: bars[t0][s]['c'] for s in tokens}
    r0 = p0['BTC'] / ma0
    z0 = get_zone_func(r0, 2)
    
    holdings_A = {s: (cap_A * w) / p0[s] for s, w in zone_rules[z0]['A'].items()}
    holdings_B = {s: (cap_B * w) / p0[s] for s, w in zone_rules[z0]['B'].items()}
    holdings_C = {s: (cap_C * w) / p0[s] for s, w in zone_rules[z0]['C'].items()}
    
    curr_zone = z0
    last_switch_t = 0
    
    hourly_portfolio_values = []
    zone_switches = 0
    total_friction_fees = 0.0
    total_funding_income = 0.0
    
    # 記錄連鎖穿透次數 (即連續小時內觸發)
    consecutive_signals = 0
    pending_target_zone = None
    
    for i, t in enumerate(sorted_ts):
        p = {s: bars[t][s]['c'] for s in tokens}
        d_str = datetime.fromtimestamp(t/1000, tz=timezone.utc).strftime('%Y-%m-%d')
        ma = daily_ma200.get(d_str, daily_ma200.get('2024-04-11', 50000.0))
        
        # 實時比值 vs 72h SMA 比值
        r_realtime = p['BTC'] / ma
        r_sma72 = sma72_dict[t] / ma
        
        # 決定比值依據：若啟用 SMA72 濾波，需兩者共同確認（或採 SMA72 防插針）
        r_used = r_sma72 if use_sma72 else r_realtime
        target_z = get_zone_func(r_used, curr_zone)
        
        # 計算各倉即時價值
        val_A = sum(holdings_A[s] * p[s] for s in holdings_A)
        val_B = sum(holdings_B[s] * p[s] for s in holdings_B)
        val_C = sum(holdings_C[s] * p[s] for s in holdings_C)
        
        # 8 小時資金費率結算 (期現套利與永續合約對沖)
        # B 倉多單對沖部位收到/支付資金費
        for s in ['SOL', 'TAO']:
            if s in holdings_B:
                notional = holdings_B[s] * p[s]
                # B 倉有 50% 為期現 Delta-Neutral 套利對沖，空單收取費率
                f_rate = funding_dict.get(s, {}).get(t, 0.0)
                # 收益 = notional * 0.5 * f_rate
                funding_gain = notional * 0.5 * f_rate
                total_funding_income += funding_gain
                val_B += funding_gain
        
        current_total = val_A + val_B + val_C
        hourly_portfolio_values.append(current_total)
        
        # 檢查 Zone 切換 (加入真實實盤防插針確認機制：需持續 2 小時確認，且距離上次切換滿足冷卻)
        hours_since_last_switch = (t - last_switch_t) / (1000 * 3600)
        
        if target_z != curr_zone and hours_since_last_switch >= cooldown_hours:
            if pending_target_zone == target_z:
                consecutive_signals += 1
            else:
                pending_target_zone = target_z
                consecutive_signals = 1
                
            # 需至少連續 2 個小時確認此信號（嚴格杜絕瞬間插針）
            if consecutive_signals >= 2:
                curr_zone = target_z
                last_switch_t = t
                zone_switches += 1
                pending_target_zone = None
                consecutive_signals = 0
                
                # 執行真實調倉並扣除動態衝擊摩擦
                for sub, h_dict, cap_val in [('A', holdings_A, val_A), ('B', holdings_B, val_B), ('C', holdings_C, val_C)]:
                    tgt = zone_rules[curr_zone][sub]
                    all_sub_tokens = set(list(tgt.keys()) + list(h_dict.keys()))
                    sub_fee = 0.0
                    for s in all_sub_tokens:
                        curr_amt_val = h_dict.get(s, 0.0) * p[s]
                        tgt_amt_val = cap_val * tgt.get(s, 0.0)
                        diff_val = abs(tgt_amt_val - curr_amt_val)
                        if diff_val > 1.0: # 交易金額超過 $1
                            friction_rate = get_friction_rate(s, bars[t][s])
                            fee = diff_val * friction_rate
                            sub_fee += fee
                    
                    total_friction_fees += sub_fee
                    net_cap = cap_val - sub_fee
                    if sub == 'A': holdings_A = {s: (net_cap * w) / p[s] for s, w in tgt.items()}
                    elif sub == 'B': holdings_B = {s: (net_cap * w) / p[s] for s, w in tgt.items()}
                    elif sub == 'C': holdings_C = {s: (net_cap * w) / p[s] for s, w in tgt.items()}
        else:
            consecutive_signals = 0
            
            # 日內日常偏離度平衡 (僅在 UTC 00:00 每日結算一次，避免小時級過度調倉損耗)
            dt_obj = datetime.fromtimestamp(t/1000, tz=timezone.utc)
            if dt_obj.hour == 0:
                # 檢查 C 倉偏離 (10%)
                tgt_C = zone_rules[curr_zone]['C']
                weights_C = {s: (holdings_C[s] * p[s]) / val_C for s in holdings_C}
                dev_C = max(abs(weights_C[s] - tgt_C.get(s, 0.0)) for s in set(list(weights_C.keys()) + list(tgt_C.keys())))
                if dev_C >= 0.10:
                    c_fee = 0.0
                    for s in set(list(tgt_C.keys()) + list(holdings_C.keys())):
                        diff = abs(val_C * tgt_C.get(s, 0.0) - holdings_C.get(s, 0.0) * p[s])
                        if diff > 1.0:
                            f_rate = get_friction_rate(s, bars[t][s])
                            c_fee += diff * f_rate
                    total_friction_fees += c_fee
                    net_C = val_C - c_fee
                    holdings_C = {s: (net_C * w) / p[s] for s, w in tgt_C.items()}
                    
                # 檢查 B 倉偏離 (5%)
                tgt_B = zone_rules[curr_zone]['B']
                weights_B = {s: (holdings_B[s] * p[s]) / val_B for s in holdings_B}
                dev_B = max(abs(weights_B[s] - tgt_B.get(s, 0.0)) for s in set(list(weights_B.keys()) + list(tgt_B.keys())))
                if dev_B >= 0.05:
                    b_fee = 0.0
                    for s in set(list(tgt_B.keys()) + list(holdings_B.keys())):
                        diff = abs(val_B * tgt_B.get(s, 0.0) - holdings_B.get(s, 0.0) * p[s])
                        if diff > 1.0:
                            f_rate = get_friction_rate(s, bars[t][s])
                            b_fee += diff * f_rate
                    total_friction_fees += b_fee
                    net_B = val_B - b_fee
                    holdings_B = {s: (net_B * w) / p[s] for s, w in tgt_B.items()}

    # 指標統計
    total_ret = (hourly_portfolio_values[-1] / hourly_portfolio_values[0]) - 1.0
    total_hours = len(sorted_ts)
    total_days = total_hours / 24.0
    cagr = ((hourly_portfolio_values[-1] / hourly_portfolio_values[0]) ** (365.0 / total_days)) - 1.0
    
    # 計算最大回撤 (MDD) - 基于小時級真實極值點 (高頻穿透下最真實的心理承壓)
    peaks = [hourly_portfolio_values[0]]
    for v in hourly_portfolio_values[1:]:
        peaks.append(max(peaks[-1], v))
    dds = [(v - p) / p for v, p in zip(hourly_portfolio_values, peaks)]
    mdd = min(dds)
    
    # 日收益率序列 (轉日級計算標準 Sharpe)
    daily_sample_vals = [hourly_portfolio_values[i] for i in range(0, total_hours, 24)]
    d_rets = [(daily_sample_vals[i] / daily_sample_vals[i-1]) - 1.0 for i in range(1, len(daily_sample_vals))]
    mean_ret = sum(d_rets) / len(d_rets)
    std_ret = math.sqrt(sum((r - mean_ret)**2 for r in d_rets) / len(d_rets))
    sharpe = (mean_ret / std_ret) * math.sqrt(365) if std_ret > 0 else 0.0
    calmar = cagr / abs(mdd) if abs(mdd) > 0 else 0.0
    
    return {
        'name': name,
        'return': total_ret,
        'cagr': cagr,
        'mdd': mdd,
        'sharpe': sharpe,
        'calmar': calmar,
        'switches': zone_switches,
        'fees': total_friction_fees,
        'funding': total_funding_income
    }

# -------------------------------------------------------------
# 7. 狀態機判定邏輯
# -------------------------------------------------------------
def get_zone_4model(r, cur):
    if r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

def get_zone_4hysteresis(r, cur):
    if cur == 1:
        if r > 1.02: return 2
        return 1
    elif cur == 2:
        if r < 0.85: return 1
        elif r > 1.25: return 3
        return 2
    elif cur == 3:
        if r < 1.15: return 2
        elif r > 1.40: return 4
        return 3
    elif cur == 4:
        if r < 1.30: return 3
        return 4

def get_zone_5model(r, cur):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

print('\n==================== 啟動高保真極限回測 (21,107 根真實小時 K 線) ====================')
# 測試四種變體：
# 1. 經典 4-Zone (無 SMA72 濾波，裸小時 K 線直接觸發)
# 2. 經典 4-Zone + 72h SMA 防插針濾波
# 3. 遲滯 4-Zone + 72h SMA
# 4. 階梯 5-Zone + 72h SMA 防插針濾波 (Zone 1 防守期 + Zone 0 深熊底)

m1 = run_high_fidelity_simulation(rules_4zone, get_zone_4model, '1. 經典 4-Zone (裸小時K線/無濾波)', use_sma72=False, cooldown_hours=0)
m2 = run_high_fidelity_simulation(rules_4zone, get_zone_4model, '2. 經典 4-Zone (+72h SMA + 24h冷卻)', use_sma72=True, cooldown_hours=24)
m3 = run_high_fidelity_simulation(rules_4zone, get_zone_4hysteresis, '3. 遲滯 4-Zone (+72h SMA + 24h冷卻)', use_sma72=True, cooldown_hours=24)
m4 = run_high_fidelity_simulation(rules_5zone, get_zone_5model, '4. 階梯 5-Zone (+72h SMA + 24h冷卻)', use_sma72=True, cooldown_hours=24)

print('\n' + '='*105)
print('%-38s | %-8s | %-7s | %-8s | %-7s | %-7s | %-6s | %-8s | %-8s' % (
    '模型架構 (Model Configuration)', '總回報', 'CAGR', '小時MDD', 'Sharpe', 'Calmar', '切換數', '摩擦損耗', '資金費收入'
))
print('-'*105)
for res in [m1, m2, m3, m4]:
    print('%-38s | %+7.2f%% | %6.2f%% | %7.2f%% | %7.2f | %7.2f | %6d | $%7.1f | $%7.1f' % (
        res['name'], res['return']*100, res['cagr']*100, res['mdd']*100, res['sharpe'], res['calmar'], res['switches'], res['fees'], res['funding']
    ))
print('='*105)
