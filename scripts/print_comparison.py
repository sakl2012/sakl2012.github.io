import json

with open('scripts/sim_1pct_vs_2pct_results.json', 'r') as f:
    res = json.load(f)

tot_5z_1, tot_5z_2 = 0, 0
tot_eq_1, tot_eq_2 = 0, 0
tot_s35_1, tot_s35_2 = 0, 0
fees_5z_1, fees_5z_2 = 0, 0
fees_eq_1, fees_eq_2 = 0, 0
fees_s35_1, fees_s35_2 = 0, 0
trades_5z_1, trades_5z_2 = 0, 0
trades_eq_1, trades_eq_2 = 0, 0
trades_s35_1, trades_s35_2 = 0, 0

print(f"{'Bot':<15} | {'Strat':<12} | {'1% NAV':<11} | {'2% NAV':<11} | {'Diff':<10} | {'Trades 1%/2%':<14} | {'Fees 1%/2%':<14}")
print('-'*90)

for r in res:
    lbl = r['label']
    for strat, k1, k2 in [('5-Zone', '5Z_1', '5Z_2'), ('Static 1/3', 'Eq_1', 'Eq_2'), ('Static 35/35', 'S35_1', 'S35_2')]:
        n1, ret1, m1, t1, f1 = r[k1]
        n2, ret2, m2, t2, f2 = r[k2]
        diff = n1 - n2
        print(f"{lbl:<15} | {strat:<12} | ${n1:>9.2f} | ${n2:>9.2f} | ${diff:>+8.2f} | {t1:>5} / {t2:<5} | ${f1:>4.1f} / ${f2:<4.1f}")
        if strat == '5-Zone':
            tot_5z_1 += n1
            tot_5z_2 += n2
            fees_5z_1 += f1
            fees_5z_2 += f2
            trades_5z_1 += t1
            trades_5z_2 += t2
        elif strat == 'Static 1/3':
            tot_eq_1 += n1
            tot_eq_2 += n2
            fees_eq_1 += f1
            fees_eq_2 += f2
            trades_eq_1 += t1
            trades_eq_2 += t2
        else:
            tot_s35_1 += n1
            tot_s35_2 += n2
            fees_s35_1 += f1
            fees_s35_2 += f2
            trades_s35_1 += t1
            trades_s35_2 += t2
    print('-'*90)

print('\n=== TOTAL PORTFOLIO SUMMARY (10,000 U Initial) ===')
print(f"5-Zone Dynamic    :")
print(f"  1% -> NAV: ${tot_5z_1:,.2f} U (+{(tot_5z_1-10000)/100:.2f}%) | Trades: {trades_5z_1} | Fees: ${fees_5z_1:.2f} U")
print(f"  2% -> NAV: ${tot_5z_2:,.2f} U (+{(tot_5z_2-10000)/100:.2f}%) | Trades: {trades_5z_2} | Fees: ${fees_5z_2:.2f} U")
print(f"  Difference: ${tot_5z_1 - tot_5z_2:+,.2f} U\n")

print(f"Static 1/3 (33%)  :")
print(f"  1% -> NAV: ${tot_eq_1:,.2f} U (+{(tot_eq_1-10000)/100:.2f}%) | Trades: {trades_eq_1} | Fees: ${fees_eq_1:.2f} U")
print(f"  2% -> NAV: ${tot_eq_2:,.2f} U (+{(tot_eq_2-10000)/100:.2f}%) | Trades: {trades_eq_2} | Fees: ${fees_eq_2:.2f} U")
print(f"  Difference: ${tot_eq_1 - tot_eq_2:+,.2f} U\n")

print(f"Static 35/35/30   :")
print(f"  1% -> NAV: ${tot_s35_1:,.2f} U (+{(tot_s35_1-10000)/100:.2f}%) | Trades: {trades_s35_1} | Fees: ${fees_s35_1:.2f} U")
print(f"  2% -> NAV: ${tot_s35_2:,.2f} U (+{(tot_s35_2-10000)/100:.2f}%) | Trades: {trades_s35_2} | Fees: ${fees_s35_2:.2f} U")
print(f"  Difference: ${tot_s35_1 - tot_s35_2:+,.2f} U")
