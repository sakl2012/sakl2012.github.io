import json
import os
import datetime
import urllib.request
import time

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_binance_klines_full(symbol, start_time_ms):
    all_bars = []
    cur_start = start_time_ms
    print(f"Fetching Binance daily klines for {symbol}...")
    while True:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&startTime={cur_start}&limit=1000"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching {symbol} at {cur_start}: {e}")
            break
            
        if not data:
            break
            
        for k in data:
            t = k[0]
            all_bars.append({
                't': t,
                'date': datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc).strftime('%Y-%m-%d'),
                'o': float(k[1]),
                'h': float(k[2]),
                'l': float(k[3]),
                'c': float(k[4]),
                'v': float(k[5])
            })
            
        if len(data) < 1000:
            break
        cur_start = data[-1][0] + 86400000
        time.sleep(0.1)
        
    unique_bars = {}
    for b in all_bars:
        unique_bars[b['t']] = b
    res = sorted(unique_bars.values(), key=lambda x: x['t'])
    if res:
        print(f"-> {symbol}: {len(res)} daily bars ({res[0]['date']} to {res[-1]['date']})")
        with open(os.path.join(CACHE_DIR, f"{symbol}_1d.json"), 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2)
    return res

# Fetch ONDOUSDT and UNIUSDT from 2020/2021
t_start = int(datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc).timestamp() * 1000)
fetch_binance_klines_full('ONDOUSDT', t_start)
fetch_binance_klines_full('UNIUSDT', t_start)
