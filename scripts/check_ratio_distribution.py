import json, os

with open('scripts/data_cache/BTCUSDT_1d.json') as f:
    btc = json.load(f)

# Calculate MA200 and ratio for every day from 2021 to 2026
dates = [row['date'] for row in btc]
prices = {row['date']: row['c'] for row in btc}

ma200 = {}
for i in range(199, len(dates)):
    window = [prices[dates[j]] for j in range(i-199, i+1)]
    ma200[dates[i]] = sum(window) / 200.0

ratios = {d: prices[d] / ma200[d] for d in ma200}
ratio_vals = list(ratios.values())

print('Historical Ratio Stats (2021-2026, %d days):' % len(ratio_vals))
print('Min ratio: %.3f (Deep Bear Bottom)' % min(ratio_vals))
print('Max ratio: %.3f (Peak Bull Top)' % max(ratio_vals))
print('Below 0.80: %d days (%.1f%%)' % (sum(1 for r in ratio_vals if r < 0.80), sum(1 for r in ratio_vals if r < 0.80)/len(ratio_vals)*100))
print('0.80 - 1.00: %d days (%.1f%%)' % (sum(1 for r in ratio_vals if 0.80 <= r < 1.00), sum(1 for r in ratio_vals if 0.80 <= r < 1.00)/len(ratio_vals)*100))
print('1.00 - 1.25: %d days (%.1f%%)' % (sum(1 for r in ratio_vals if 1.00 <= r < 1.25), sum(1 for r in ratio_vals if 1.00 <= r < 1.25)/len(ratio_vals)*100))
print('1.25 - 1.40: %d days (%.1f%%)' % (sum(1 for r in ratio_vals if 1.25 <= r < 1.40), sum(1 for r in ratio_vals if 1.25 <= r < 1.40)/len(ratio_vals)*100))
print('Above 1.40: %d days (%.1f%%)' % (sum(1 for r in ratio_vals if r >= 1.40), sum(1 for r in ratio_vals if r >= 1.40)/len(ratio_vals)*100))
