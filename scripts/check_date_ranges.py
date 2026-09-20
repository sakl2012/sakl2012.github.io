import json, os

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')
files = [f for f in os.listdir(CACHE_DIR) if f.endswith('_1d.json')]

for f in sorted(files):
    with open(os.path.join(CACHE_DIR, f), 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    dates = [x['date'] for x in data if 'date' in x]
    if dates:
        print(f"{f:<18}: {len(dates)} days, {dates[0]} ~ {dates[-1]}")
