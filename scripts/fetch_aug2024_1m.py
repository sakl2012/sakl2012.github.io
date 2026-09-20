import urllib.request, json, time, datetime, os

CACHE_1M = os.path.join(os.path.dirname(__file__), 'data_cache_1m')
os.makedirs(CACHE_1M, exist_ok=True)

def fetch_historical_1m(symbol, start_dt, end_dt):
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    cur = start_ms
    all_bars = []
    print(f"Fetching 1m bars for {symbol} from {start_dt} to {end_dt}...")
    
    while cur < end_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={cur}&endTime={end_ms}&limit=1000"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
            continue
            
        if not data: break
        for k in data:
            all_bars.append({
                't': k[0],
                'date': datetime.datetime.fromtimestamp(k[0] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'),
                'c': float(k[4])
            })
        if len(data) < 1000: break
        cur = data[-1][0] + 60000
        time.sleep(0.05)
        
    print(f"-> {symbol}: {len(all_bars)} bars")
    with open(os.path.join(CACHE_1M, f"{symbol}_aug2024_1m.json"), 'w', encoding='utf-8') as f:
        json.dump(all_bars, f, indent=2)
    return all_bars

t_start = datetime.datetime(2024, 8, 3, 0, 0, tzinfo=datetime.timezone.utc)
t_end = datetime.datetime(2024, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
fetch_historical_1m('BTCUSDT', t_start, t_end)
fetch_historical_1m('PAXGUSDT', t_start, t_end)
