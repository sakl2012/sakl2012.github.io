import json, os

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')

tokens = {
    'BNB': 'BNBUSDT_1d.json',
    'LINK': 'LINKUSDT_1d.json',
    'AAVE': 'AAVEUSDT_1d.json',
    'UNI': 'UNIUSDT_1d.json',
    'NEAR': 'NEARUSDT_1d.json',
    'SOL': 'SOLUSDT_1d.json',
    'TAO': 'TAOUSDT_1d.json'
}

for name, fname in tokens.items():
    p = os.path.join(CACHE_DIR, fname)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            d = json.load(f)
        dates = [x['date'] for x in d if 'date' in x]
        print(f"{name:<6}: Earliest cached = {dates[0]}, Total days = {len(dates)}")
