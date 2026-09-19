import json, os, math, itertools
from datetime import datetime, timezone
import sys
sys.path.append('.')

from scripts.run_ultra_rigorous_backtest import (
    sorted_ts, bars, daily_ma200, sma72_dict, funding_dict, tokens, 
    get_friction_rate, run_high_fidelity_simulation
)

# 基準比值切換函數 (5-Zone)
def get_zone_5(r, cur):
    if r < 0.80: return 0
    elif r < 1.00: return 1
    elif r < 1.25: return 2
    elif r < 1.40: return 3
    else: return 4

# 候選資產配置網格
# 測試 Zone 1 (防守緩衝期 0.80 <= R < 1.00) 的黃金 vs 現貨比重
# 測試 Zone 0 (深熊大底 R < 0.80) 的抄底激進程度
# 測試 Zone 2/3/4 的平滑過渡

candidates_Zone1 = [
    # A: 保守防守 (PAXG 60%)
    {
        'desc': 'Z1: PAXG 60% (高防守緩衝)',
        'A': {'BTC': 0.40, 'PAXG': 0.60},
        'B': {'SOL': 0.15, 'TAO': 0.15, 'PAXG': 0.70},
        'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.10, 'NEAR': 0.10, 'PAXG': 0.50}
    },
    # B: 中度均衡 (PAXG 50%)
    {
        'desc': 'Z1: PAXG 50% (中度平衡緩衝)',
        'A': {'BTC': 0.50, 'PAXG': 0.50},
        'B': {'SOL': 0.18, 'TAO': 0.17, 'PAXG': 0.65},
        'C': {'AAVE': 0.20, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.40}
    },
    # C: 輕度防守 (PAXG 40%)
    {
        'desc': 'Z1: PAXG 40% (輕度防守)',
        'A': {'BTC': 0.55, 'PAXG': 0.45},
        'B': {'SOL': 0.22, 'TAO': 0.18, 'PAXG': 0.60},
        'C': {'AAVE': 0.25, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.35}
    }
]

candidates_Zone0 = [
    # A: 狂暴深熊抄底 (高彈性幣種)
    {
        'desc': 'Z0: 狂暴抄底 (PAXG 15~20%)',
        'A': {'BTC': 0.80, 'PAXG': 0.20},
        'B': {'SOL': 0.30, 'TAO': 0.35, 'PAXG': 0.35},
        'C': {'AAVE': 0.30, 'SUI': 0.25, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.15}
    },
    # B: 穩健深熊抄底 (PAXG 25~30%)
    {
        'desc': 'Z0: 穩健抄底 (PAXG 25~35%)',
        'A': {'BTC': 0.75, 'PAXG': 0.25},
        'B': {'SOL': 0.25, 'TAO': 0.30, 'PAXG': 0.45},
        'C': {'AAVE': 0.25, 'SUI': 0.20, 'LINK': 0.15, 'NEAR': 0.15, 'PAXG': 0.25}
    }
]

# 固定已驗證優異的 Zone 2, 3, 4
Z2 = {
    'A': {'BTC': 0.58, 'PAXG': 0.42},
    'B': {'SOL': 0.25, 'TAO': 0.15, 'PAXG': 0.60},
    'C': {'AAVE': 0.30, 'SUI': 0.15, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.30}
}
Z3 = {
    'A': {'BTC': 0.37, 'PAXG': 0.63},
    'B': {'SOL': 0.18, 'TAO': 0.19, 'PAXG': 0.63},
    'C': {'AAVE': 0.20, 'SUI': 0.10, 'LINK': 0.15, 'NEAR': 0.10, 'PAXG': 0.45}
}
Z4 = {
    'A': {'BTC': 0.05, 'PAXG': 0.95},
    'B': {'SOL': 0.07, 'TAO': 0.13, 'PAXG': 0.80},
    'C': {'PAXG': 0.75, 'AAVE': 0.08, 'LINK': 0.07, 'SUI': 0.05, 'NEAR': 0.05}
}

print('Starting Grid Search over 21,107 hourly bars...')
results = []
for z0_cand in candidates_Zone0:
    for z1_cand in candidates_Zone1:
        rules = {
            0: {'A': z0_cand['A'], 'B': z0_cand['B'], 'C': z0_cand['C']},
            1: {'A': z1_cand['A'], 'B': z1_cand['B'], 'C': z1_cand['C']},
            2: Z2,
            3: Z3,
            4: Z4
        }
        name = f"{z0_cand['desc']} + {z1_cand['desc']}"
        res = run_high_fidelity_simulation(rules, get_zone_5, name, use_sma72=True, cooldown_hours=24)
        results.append(res)
        print(f"Done: {name} -> Ret: {res['return']*100:+.2f}%, MDD: {res['mdd']*100:.2f}%, Calmar: {res['calmar']:.2f}")

results.sort(key=lambda x: x['calmar'], reverse=True)
print('\n' + '='*100)
print('5-Zone 參數組合網格優化排名 (按 Calmar 排序):')
print('='*100)
for i, r in enumerate(results):
    print(f"#{i+1}: {r['name']}")
    print(f"     總回報: {r['return']*100:+.2f}% | CAGR: {r['cagr']*100:.2f}% | 小時MDD: {r['mdd']*100:.2f}% | Sharpe: {r['sharpe']:.2f} | Calmar: {r['calmar']:.2f} | 摩擦損耗: ${r['fees']:.1f}")
