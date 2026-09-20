import urllib.request
import json
import time
import datetime
import os

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache_1m')
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_1m_bars(symbol, total_bars=15000):
    """Fetch recent total_bars 1m bars from Binance."""
    print(f"Fetching {total_bars} 1-minute bars for {symbol} from Binance...")
    all_bars = []
    # Binance klines returns up to 1000 bars per call.
    # To get recent 15,000 bars: we can start from (now - 15000 mins)
    end_time_ms = int(time.time() * 1000)
    start_time_ms = end_time_ms - (total_bars * 60 * 1000)
    cur_start = start_time_ms
    
    while cur_start < end_time_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={cur_start}&limit=1000"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching {symbol} at {cur_start}: {e}")
            time.sleep(1)
            continue
            
        if not data:
            break
            
        for k in data:
            all_bars.append({
                't': k[0],
                'date': datetime.datetime.fromtimestamp(k[0] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'),
                'o': float(k[1]),
                'h': float(k[2]),
                'l': float(k[3]),
                'c': float(k[4]),
                'v': float(k[5])
            })
            
        if len(data) < 1000:
            break
        cur_start = data[-1][0] + 60000
        time.sleep(0.05)
        
    unique = {b['t']: b for b in all_bars}
    res = sorted(unique.values(), key=lambda x: x['t'])
    print(f"-> {symbol}: fetched {len(res)} 1m bars ({res[0]['date']} to {res[-1]['date']})")
    
    out_file = os.path.join(CACHE_DIR, f"{symbol}_1m.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=2)
    return res

if __name__ == '__main__':
    fetch_1m_bars('BTCUSDT', total_bars=20000)
    fetch_1m_bars('PAXGUSDT', total_bars=20000)
