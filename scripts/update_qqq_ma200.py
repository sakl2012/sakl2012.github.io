#!/usr/bin/env python3
"""
Fetch latest QQQ daily chart from Yahoo Finance and update qqq_ma200.json.
Runs daily in GitHub Actions or locally.
"""
import urllib.request
import json
import datetime
import os
import sys

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_json = os.path.join(repo_root, 'qqq_ma200.json')

    url = "https://query1.finance.yahoo.com/v8/finance/chart/QQQ?interval=1d&range=2y"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to fetch Yahoo Finance QQQ: {e}", file=sys.stderr)
        sys.exit(1)

    quotes = data['chart']['result'][0]
    ts = quotes['timestamp']
    indicators = quotes['indicators']['quote'][0]
    closes = indicators['close']

    valid = []
    for t, c in zip(ts, closes):
        if c is not None:
            dt = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')
            valid.append({'t': t, 'd': dt, 'c': round(c, 2)})

    if len(valid) < 200:
        print(f"Error: valid trading days ({len(valid)}) < 200", file=sys.stderr)
        sys.exit(1)

    recent = valid[-250:]
    last_200 = [x['c'] for x in recent[-200:]]
    ma200 = round(sum(last_200) / 200, 2)
    latest = recent[-1]
    ratio = round(latest['c'] / ma200, 4)

    payload = {
        "symbol": "QQQ",
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "latest_date": latest['d'],
        "latest_close": latest['c'],
        "ma200": ma200,
        "ratio": ratio,
        "status": "BULL_CRUISE" if ratio >= 1.00 else "BEAR_DEFENSE",
        "status_text": "多頭巡航 (安全)" if ratio >= 1.00 else "破位預警 (防禦)",
        "history_200": last_200
    }

    with open(target_json, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated {target_json}")
    print(f"Date: {latest['d']} | Close: {latest['c']} | MA200: {ma200} | Ratio: {ratio}")

if __name__ == '__main__':
    main()
