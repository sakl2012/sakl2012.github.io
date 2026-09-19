import urllib.request, json, os, time
from datetime import datetime, timezone

symbols = ['PENDLEUSDT', 'UNIUSDT']
cache_dir = 'scripts/data_cache_1h'
os.makedirs(cache_dir, exist_ok=True)

start_ts = 1712793600000 
end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)

for sym in symbols:
    filepath = os.path.join(cache_dir, f'{sym}_1h.json')
    if os.path.exists(filepath):
        try:
            with open(filepath) as f:
                existing = json.load(f)
            if len(existing) > 15000:
                print(f'Using cached {sym}: {len(existing)} bars')
                continue
        except:
            pass
            
    print(f'Fetching {sym} 1h klines from Binance...')
    curr = start_ts
    all_bars = []
    seen = set()
    while curr < end_ts:
        url = f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&startTime={curr}&limit=1000'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                batch = json.loads(resp.read().decode('utf-8'))
                if not batch: break
                for k in batch:
                    t = k[0]
                    if t in seen: continue
                    seen.add(t)
                    all_bars.append({
                        't': t,
                        'date': datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M'),
                        'o': float(k[1]), 'h': float(k[2]), 'l': float(k[3]), 'c': float(k[4]), 'v': float(k[5])
                    })
                last_t = batch[-1][0]
                if last_t <= curr: break
                curr = last_t + 1
                if len(batch) < 1000: break
                time.sleep(0.04)
        except Exception as e:
            print(f'Error fetching {sym} at {curr}: {e}')
            time.sleep(1)
            break
            
    all_bars.sort(key=lambda x: x['t'])
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(all_bars, f)
    print(f'Saved {sym}: {len(all_bars)} bars ({all_bars[0]["date"]} to {all_bars[-1]["date"]})')
