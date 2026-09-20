import urllib.request
import json
import time
import datetime

t_start = int(datetime.datetime(2023, 1, 1, 0, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&startTime={t_start}&limit=1000"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        d0 = datetime.datetime.fromtimestamp(data[0][0]/1000, datetime.timezone.utc)
        d1 = datetime.datetime.fromtimestamp(data[-1][0]/1000, datetime.timezone.utc)
        print(f"BTC 15m call success: {len(data)} bars ({d0} to {d1})")
except Exception as e:
    print("Error:", e)
