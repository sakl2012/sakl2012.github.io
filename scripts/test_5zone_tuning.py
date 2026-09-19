import json, os, math
from datetime import datetime, timezone
from scripts.run_ultra_rigorous_backtest import (
    sorted_ts, bars, daily_ma200, sma72_dict, funding_dict, tokens, 
    get_friction_rate, run_high_fidelity_simulation
)

# 測試不同門檻的 5-Zone
# 變體 A: 0.80 為深熊門檻
rules_5zone_A = {
    0: {'A': {'BTC': 0.80, 'PAXG': 0.20}, 'B': {'SOL': 0.30, 'TAO': 0.35, 'PAXG': 0.35}, 'C': {'AAVE': 0.30, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15}},
    1: {'A': {'BTC': 0.40, 'PAXG': 0.60}, 'B': {'SOL': 0.15, 'TAO': 0.15, 'PAXG': 0.70}, 'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.10, 'NEAR': 0.10, 'PAXG': 0.50}},
    2: {'A': {'BTC': 0.58, 'PAXG': 0.42}, 'B': {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60}, 'C': {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30}},
    3: {'A': {'BTC': 0.37, 'PAXG': 0.63}, 'B': {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63}, 'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45}},
    4: {'A': {'BTC': 0.05, 'PAXG': 0.95}, 'B': {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80}, 'C': {'PAXG': 0.75, 'AAVE': 0.08, 'LINK': 0.07, 'SUI': 0.05, 'NEAR': 0.05}}
}

# 變體 B: 0.85 為深熊門檻 (讓更多時間在 Zone 0 享有反彈紅利，同時保留 0.85-1.00 的防守)
def get_zone_5_thresh85(r, cur):
    if r < 0.85: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

# 變體 C: 階梯 5-Zone + 遲滯冷卻 (Zone 1 回彈到 1.02 才進 Zone 2，Zone 0 反彈到 0.88 才回 Zone 1)
def get_zone_5_hysteresis(r, cur):
    if cur == 0:
        if r > 0.85: return 1
        return 0
    elif cur == 1:
        if r < 0.78: return 0
        elif r > 1.02: return 2
        return 1
    elif cur == 2:
        if r < 0.98: return 1
        elif r > 1.27: return 3
        return 2
    elif cur == 3:
        if r < 1.22: return 2
        elif r > 1.42: return 4
        return 3
    elif cur == 4:
        if r < 1.36: return 3
        return 4

mA = run_high_fidelity_simulation(rules_5zone_A, get_zone_5_thresh85, '5-Zone (Thresh 0.85 / 1.00)', use_sma72=True, cooldown_hours=24)
mB = run_high_fidelity_simulation(rules_5zone_A, get_zone_5_hysteresis, '5-Zone (+Hysteresis 防反覆橫跳)', use_sma72=True, cooldown_hours=24)

print('Variant A (Thresh 0.85): Return %+.2f%% | CAGR %.2f%% | MDD %.2f%% | Sharpe %.2f | Calmar %.2f | Switches %d | Fees $%.1f' % (
    mA['return']*100, mA['cagr']*100, mA['mdd']*100, mA['sharpe'], mA['calmar'], mA['switches'], mA['fees']
))
print('Variant B (Hysteresis):  Return %+.2f%% | CAGR %.2f%% | MDD %.2f%% | Sharpe %.2f | Calmar %.2f | Switches %d | Fees $%.1f' % (
    mB['return']*100, mB['cagr']*100, mB['mdd']*100, mB['sharpe'], mB['calmar'], mB['switches'], mB['fees']
))
