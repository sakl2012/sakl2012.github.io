import json, os, math, datetime
from analyze_core_alpha_ratio import days, get_zone

def sim(coin_key, is_5z, static_weights=(0.3333, 0.3333, 0.3334)):
    zone_weights = {
        0: (0.65, 0.25, 0.10),
        1: (0.50, 0.30, 0.20),
        2: (0.45, 0.35, 0.20),
        3: (0.30, 0.35, 0.35),
        4: (0.05, 0.30, 0.65)
    }
    initial = 10000.0
    nav = initial
    z0 = get_zone(days[0]['R'])
    cur_z = z0
    w_c, w_q, w_p = zone_weights[z0] if is_5z else static_weights
    u_c = (nav * w_c) / days[0][coin_key]
    u_q = (nav * w_q) / days[0]['QQQ']
    u_p = (nav * w_p) / days[0]['PAXG']
    nav_history = [nav]
    
    for i in range(1, len(days)):
        d = days[i]
        p_c, p_q, p_p = d[coin_key], d['QQQ'], d['PAXG']
        val_c = u_c * p_c
        val_q = u_q * p_q
        val_p = u_p * p_p
        nav = val_c + val_q + val_p
        
        if is_5z:
            new_z = get_zone(d['R'])
            drift = max(abs(val_c/nav - zone_weights[new_z][0]), abs(val_q/nav - zone_weights[new_z][1]), abs(val_p/nav - zone_weights[new_z][2]))
            if new_z != cur_z or drift >= 0.01:
                cur_z = new_z
                tw_c, tw_q, tw_p = zone_weights[cur_z]
                trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                nav -= trade_vol * 0.001
                u_c = (nav * tw_c) / p_c
                u_q = (nav * tw_q) / p_q
                u_p = (nav * tw_p) / p_p
        else:
            drift = max(abs(val_c/nav - static_weights[0]), abs(val_q/nav - static_weights[1]), abs(val_p/nav - static_weights[2]))
            if drift >= 0.01:
                tw_c, tw_q, tw_p = static_weights
                trade_vol = (abs(nav*tw_c - val_c) + abs(nav*tw_q - val_q) + abs(nav*tw_p - val_p)) / 2.0
                nav -= trade_vol * 0.001
                u_c = (nav * tw_c) / p_c
                u_q = (nav * tw_q) / p_q
                u_p = (nav * tw_p) / p_p
        nav_history.append(nav)
        
    tot_ret = (nav - initial) / initial
    peak = nav_history[0]
    mdd = 0.0
    for n in nav_history:
        if n > peak: peak = n
        dd = (peak - n) / peak
        if dd > mdd: mdd = dd
    return nav, tot_ret, mdd

for coin in ['BTC', 'ETH', 'BNB', 'SOL']:
    nav_5z, ret_5z, mdd_5z = sim(coin, is_5z=True)
    nav_st_eq, ret_st_eq, mdd_st_eq = sim(coin, is_5z=False, static_weights=(0.3333, 0.3333, 0.3334))
    nav_st_50, ret_st_50, mdd_st_50 = sim(coin, is_5z=False, static_weights=(0.50, 0.25, 0.25))
    print(f"=== {coin} ===")
    print(f"  5-Zone:     Final=${nav_5z:.2f}, Ret={ret_5z*100:+.2f}%, MDD={mdd_5z*100:.2f}%")
    print(f"  Static 1/3: Final=${nav_st_eq:.2f}, Ret={ret_st_eq*100:+.2f}%, MDD={mdd_st_eq*100:.2f}%")
    print(f"  Static 50%: Final=${nav_st_50:.2f}, Ret={ret_st_50*100:+.2f}%, MDD={mdd_st_50*100:.2f}%")
