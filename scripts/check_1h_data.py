import json, os

CACHE_1H = os.path.join(os.path.dirname(__file__), 'data_cache_1h')
with open(os.path.join(CACHE_1H, 'BTCUSDT_1h.json'), 'r', encoding='utf-8') as f:
    btc_1h = json.load(f)

print(f"BTC 1h bars: {len(btc_1h)}")
if btc_1h:
    print(f"Start: {btc_1h[0].get('date', btc_1h[0].get('t'))}, End: {btc_1h[-1].get('date', btc_1h[-1].get('t'))}")
    print(f"Sample bar: {btc_1h[0]}")
