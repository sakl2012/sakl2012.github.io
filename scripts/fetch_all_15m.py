import urllib.request
import json
import time
import datetime
import os
import sys

CACHE_15M = os.path.join(os.path.dirname(__file__), 'data_cache_15m')
os.makedirs(CACHE_15M, exist_ok=True)

symbols = [
    'BTCUSDT',
    'ETHUSDT',
    'PAXGUSDT',
    'BNBUSDT',
    'UNIUSDT',
    'AAVEUSDT',
    'LINKUSDT',
    'NEARUSDT',
    'TAOUSDT',
    'ONDOUSDT'
]

def fetch_symbol_15m(symbol, start_dt, end_dt):
    out_file = os.path.join(CACHE_15M, f"{symbol}_15m.json")
    # Check if already cached
    if os.path.exists(out_file):
        with open(out_file, 'r', encoding='utf-8') as f:
            try:
                cached = json.load(f)
                if len(cached) > 1000:
                    d_end = datetime.datetime.fromtimestamp(cached[-1]['t']/1000, datetime.timezone.utc)
                    if d_end.date() >= datetime.date(2026, 9, 1):
                        print(f"[{symbol}] already cached: {len(cached)} bars ({cached[0]['date']} to {cached[-1]['date']})")
                        return cached
            except Exception:
                pass

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    cur = start_ms
    all_bars = []
    print(f"[{symbol}] Fetching 15m bars from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}...")
    
    retry_count = 0
    while cur < end_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&startTime={cur}&endTime={end_ms}&limit=1000"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            retry_count = 0
        except Exception as e:
            retry_count += 1
            if retry_count > 5:
                print(f"[{symbol}] Failed after 5 retries at {cur}: {e}")
                break
            time.sleep(1)
            continue
            
        if not data:
            break
            
        for k in data:
            all_bars.append({
                't': k[0],
                'date': datetime.datetime.fromtimestamp(k[0] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'),
                'c': float(k[4])
            })
            
        if len(data) < 1000:
            break
            
        cur = data[-1][0] + (15 * 60 * 1000)
        time.sleep(0.04) # safe rate limit
        
    unique = {b['t']: b for b in all_bars}
    res = sorted(unique.values(), key=lambda x: x['t'])
    if res:
        print(f"-> [{symbol}] Success: {len(res)} bars ({res[0]['date']} to {res[-1]['date']})")
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(res, f)
    return res

if __name__ == '__main__':
    start_dt = datetime.datetime(2023, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 9, 20, 8, 0, tzinfo=datetime.timezone.utc)
    for sym in symbols:
        fetch_symbol_15m(sym, start_dt, end_dt)
