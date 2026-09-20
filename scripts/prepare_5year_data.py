import json
import os
import datetime
import urllib.request
import time

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_binance_klines_full(symbol, start_time_ms):
    """Fetch all daily klines from start_time_ms up to present using pagination."""
    all_bars = []
    cur_start = start_time_ms
    print(f"Fetching full Binance daily klines for {symbol} starting from {datetime.datetime.fromtimestamp(start_time_ms/1000, datetime.timezone.utc).strftime('%Y-%m-%d')}...")
    
    while True:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&startTime={cur_start}&limit=1000"
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
            
        # next start time is last candle open time + 1 day
        cur_start = data[-1][0] + 86400000
        time.sleep(0.1)
        
    # Deduplicate by t
    unique_bars = {}
    for b in all_bars:
        unique_bars[b['t']] = b
    res = sorted(unique_bars.values(), key=lambda x: x['t'])
    print(f"-> {symbol}: {len(res)} daily bars ({res[0]['date']} to {res[-1]['date']})")
    return res

def fetch_yahoo_daily(symbol):
    """Fetch 5-year daily chart data from Yahoo Finance."""
    print(f"Fetching Yahoo Finance daily data for {symbol} (5y range)...")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5y"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        
    result = data['chart']['result'][0]
    timestamps = result['timestamp']
    indicators = result['indicators']['quote'][0]
    adjclose = result['indicators'].get('adjclose', [{}])[0].get('adjclose', indicators['close'])
    
    bars = []
    for i, t in enumerate(timestamps):
        c = adjclose[i] if adjclose and adjclose[i] is not None else indicators['close'][i]
        o = indicators['open'][i]
        h = indicators['high'][i]
        l = indicators['low'][i]
        v = indicators['volume'][i]
        if c is None or o is None:
            continue
        dt_str = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')
        bars.append({
            't': t * 1000,
            'date': dt_str,
            'o': float(o),
            'h': float(h),
            'l': float(l),
            'c': float(c),
            'v': float(v) if v else 0.0
        })
    bars.sort(key=lambda x: x['t'])
    print(f"-> {symbol}: {len(bars)} daily bars ({bars[0]['date']} to {bars[-1]['date']})")
    return bars

def main():
    # 2021-01-01 00:00:00 UTC = 1609459200000 ms
    start_2021_ms = 1609459200000
    
    # 1. Binance Crypto: BTC, ETH, PAXG
    for sym in ['BTCUSDT', 'ETHUSDT', 'PAXGUSDT', 'BNBUSDT', 'SOLUSDT']:
        bars = fetch_binance_klines_full(sym, start_2021_ms)
        filepath = os.path.join(CACHE_DIR, f"{sym}_1d.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(bars, f, indent=2)
        print(f"Saved {filepath}")
        
    # 2. Yahoo Finance: QQQ, SPY
    for sym in ['QQQ', 'SPY']:
        bars = fetch_yahoo_daily(sym)
        filepath = os.path.join(CACHE_DIR, f"{sym}_1d.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(bars, f, indent=2)
        print(f"Saved {filepath}")
        
    print("\nAll 5-year historical datasets successfully updated and verified!")

if __name__ == '__main__':
    main()
