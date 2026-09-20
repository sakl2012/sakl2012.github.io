import urllib.request, json, time, datetime

t_aug5 = int(datetime.datetime(2024, 8, 4, 0, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&startTime={t_aug5}&limit=10"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"Binance 1m from Aug 2024 available: {len(data)} bars, first: {datetime.datetime.fromtimestamp(data[0][0]/1000, datetime.timezone.utc)}")
except Exception as e:
    print("Error:", e)
