import urllib.request, json, os
from datetime import datetime, timezone

tokens_to_cache = ['SUIUSDT', 'PENDLEUSDT', 'UNIUSDT', 'RENDERUSDT', 'FETUSDT']
cache_dir = 'scripts/data_cache'
for sym in tokens_to_cache:
    url = f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=1d&limit=1000'
    raw = json.loads(urllib.request.urlopen(url).read())
    cleaned = []
    seen = set()
    for k in raw:
        t = k[0]
        if t in seen: continue
        seen.add(t)
        cleaned.append({
            't': t,
            'date': datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime('%Y-%m-%d'),
            'c': float(k[4]), 'h': float(k[2]), 'l': float(k[3]), 'o': float(k[1])
        })
    cleaned.sort(key=lambda x: x['t'])
    with open(os.path.join(cache_dir, f'{sym}_1d.json'), 'w', encoding='utf-8') as f:
        json.dump(cleaned, f)
    print('Cached %s: %d bars (%s to %s)' % (sym, len(cleaned), cleaned[0]['date'], cleaned[-1]['date']))
