import urllib.request, json, os, time
from datetime import datetime, timezone

symbols = ['PENDLEUSDT', 'UNIUSDT']
cache_dir = 'scripts/data_cache_funding'
os.makedirs(cache_dir, exist_ok=True)

start_ts = 1712793600000 
end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)

for sym in symbols:
    filepath = os.path.join(cache_dir, f'{sym}_funding.json')
    if os.path.exists(filepath):
        try:
            with open(filepath) as f:
                existing = json.load(f)
            if len(existing) > 2000:
                print(f'Using cached {sym} funding: {len(existing)} records')
                continue
        except:
            pass
            
    print(f'Fetching {sym} funding rate...')
    curr = start_ts
    all_records = []
    seen = set()
    while curr < end_ts:
        url = f'https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&startTime={curr}&limit=1000'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                batch = json.loads(resp.read().decode('utf-8'))
                if not batch: break
                for k in batch:
                    t = k['fundingTime']
                    if t in seen: continue
                    seen.add(t)
                    all_records.append({
                        't': t,
                        'date': datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M'),
                        'r': float(k['fundingRate'])
                    })
                last_t = batch[-1]['fundingTime']
                if last_t <= curr: break
                curr = last_t + 1
                if len(batch) < 1000: break
                time.sleep(0.04)
        except Exception as e:
            print(f'Error fetching funding {sym}: {e}')
            break
            
    all_records.sort(key=lambda x: x['t'])
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(all_records, f)
    print(f'Saved {sym} funding: {len(all_records)} records')
