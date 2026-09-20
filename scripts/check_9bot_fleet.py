import json, os, math, datetime
from simulate_user_exact_fleet import btc_map, eth_map, bnb_map, uni_map, aave_map, link_map, near_map, paxg_map, qqq_map, tao_map, ondo_map, btc_ma200, get_zone, zw_core_btc, zw_core_eth, zw_alpha

zw_core_tao = {0: (0.65, 0.25, 0.10), 1: (0.50, 0.30, 0.20), 2: (0.35, 0.35, 0.30), 3: (0.20, 0.40, 0.40), 4: (0.05, 0.25, 0.70)}

# Common dates for all 9 tokens + BTC MA200
dates_9 = sorted(list(set(btc_map.keys()) & set(eth_map.keys()) & set(tao_map.keys()) &
                      set(bnb_map.keys()) & set(uni_map.keys()) & set(aave_map.keys()) &
                      set(link_map.keys()) & set(near_map.keys()) & set(ondo_map.keys()) &
                      set(paxg_map.keys()) & set(btc_ma200.keys())))

days_9 = []
last_qqq = qqq_map.get(dates_9[0], 450.0)
for d in dates_9:
    if d in qqq_map: last_qqq = qqq_map[d]
    days_9.append({
        'date': d,
        'BTC': btc_map[d], 'ETH': eth_map[d], 'TAO': tao_map[d],
        'BNB': bnb_map[d], 'UNI': uni_map[d], 'AAVE': aave_map[d],
        'LINK': link_map[d], 'NEAR': near_map[d], 'ONDO': ondo_map[d],
        'PAXG': paxg_map[d], 'QQQ': last_qqq,
        'R': btc_map[d] / btc_ma200[d]
    })

print(f"9-Token Exact Fleet: {len(days_9)} common days, {days_9[0]['date']} ~ {days_9[-1]['date']}")

# 3 Core (BTC 2000U, ETH 2000U, TAO 1000U = 5000U)
# 6 Alpha (BNB, UNI, AAVE, LINK, NEAR, ONDO each 833.33U = 5000U)
bots_9 = [
    ('BTC', 'Core 1 (BTC)', 2000.0, zw_core_btc),
    ('ETH', 'Core 2 (ETH)', 2000.0, zw_core_eth),
    ('TAO', 'Core 3 (TAO)', 1000.0, zw_core_tao),
    ('BNB', 'Alpha 1 (BNB)', 833.33, zw_alpha),
    ('UNI', 'Alpha 2 (UNI)', 833.33, zw_alpha),
    ('AAVE', 'Alpha 3 (AAVE)', 833.33, zw_alpha),
    ('LINK', 'Alpha 4 (LINK)', 833.33, zw_alpha),
    ('NEAR', 'Alpha 5 (NEAR)', 833.33, zw_alpha),
    ('ONDO', 'Alpha 6 (ONDO)', 833.33, zw_alpha)
]

from simulate_user_exact_fleet import simulate_bot

def run_9(is_5z, static_w=(0.3333, 0.3333, 0.3334)):
    tot_nav = [0.0] * len(days_9)
    bot_res = {}
    for sym, label, cap, zw in bots_9:
        nh, tr = simulate_bot(days_9, sym, is_5z, zw, static_w, initial_cap=cap)
        bot_res[label] = {'initial': cap, 'final': nh[-1], 'ret': (nh[-1]-cap)/cap}
        for i in range(len(days_9)):
            tot_nav[i] += nh[i]
    final = tot_nav[-1]
    ret = (final - 10000.0) / 10000.0
    peak = tot_nav[0]
    mdd = 0.0
    for n in tot_nav:
        if n > peak: peak = n
        dd = (peak - n) / peak
        if dd > mdd: mdd = dd
    return final, ret, mdd, bot_res

f_5z, r_5z, m_5z, b_5z = run_9(True)
f_eq, r_eq, m_eq, b_eq = run_9(False, (0.3333, 0.3333, 0.3334))
f_50, r_50, m_50, b_50 = run_9(False, (0.50, 0.25, 0.25))

print(f"\n5-Zone Dynamic:        Final=${f_5z:.2f}, Ret={r_5z*100:+.2f}%, MDD={m_5z*100:.2f}%")
print(f"Static 1/3 (33/33/33): Final=${f_eq:.2f}, Ret={r_eq*100:+.2f}%, MDD={m_eq*100:.2f}%")
print(f"Static 50% (50/25/25): Final=${f_50:.2f}, Ret={r_50*100:+.2f}%, MDD={m_50*100:.2f}%")
print("\nPer-Bot Breakdown for Exact 9-Bot Fleet:")
for k in b_5z:
    print(f"  {k:<18}: 5Z=${b_5z[k]['final']:.2f} ({b_5z[k]['ret']*100:+.1f}%) | Static 1/3=${b_eq[k]['final']:.2f} ({b_eq[k]['ret']*100:+.1f}%)")
