import urllib.request
import urllib.parse
import json
import time
import os
from datetime import datetime

base_url = 'https://www.binance.com/bapi/composite/v2/friendly/pgc/content/queryUserProfilePageContentsWithFilter'
target_uid = 'W_LxuKCvfIc1GLolhxDeOg'

headers = {
    'authority': 'www.binance.com',
    'accept': '*/*',
    'accept-language': 'zh-TC,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'bnc-uuid': 'a785dc47-f2c3-4662-b66d-f78deb00145b',
    'clienttype': 'web',
    'content-type': 'application/json',
    'csrftoken': '73902908ec20bba1495fccc6f4567554',
    'device-info': 'eyJzY3JlZW5fcmVzb2x1dGlvbiI6IjE5MjAsMTA4MCIsImF2YWlsYWJsZV9zY3JlZW5fcmVzb2x1dGlvbiI6IjE5MjAsMTA0MCIsInN5c3RlbV92ZXJzaW9uIjoiV2luZG93cyAxMCIsImJyYW5kX21vZGVsIjoidW5rbm93biIsInN5c3RlbV9sYW5nIjoiZW4tVVMiLCJ0aW1lem9uZSI6IkdNVCswODowMCIsInRpbWV6b25lT2Zmc2V0IjotNDgwLCJ1c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzE1Mi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwibGlzdF9wbHVnaW4iOiJQREYgVmlld2VyLENocm9tZSBQREYgVmlld2VyLENocm9taXVtIFBERiBWaWV3ZXIsTWljcm9zb2Z0IEVkZ2UgUERGIFZpZXdlcixXZWJLaXQgYnVpbHQtaW4gUERGIiwiY2FudmFzX2NvZGUiOiIxZTUwOGZiYSIsIndlYmdsX3ZlbmRvciI6Ikdvb2dsZSBJbmMuIChJbnRlbCkiLCJ3ZWJnbF9yZW5kZXJlciI6IkFOR0xFIChJbnRlbCwgSW50ZWwoUikgSEQgR3JhcGhpY3MgNjIwICgweDAwMDA1OTE2KSBEaXJlY3QzRDExIHZzXzVfMCBwc181XzAsIEQzRDExKSIsImF1ZGlvIjoiMTI0LjA0MzQ3Nzc2Njk2NTIyIiwicGxhdGZvcm0iOiJXaW4zMiIsIndlYl90aW1lem9uZSI6IkFzaWEvVGFpcGVpIiwiZGV2aWNlX25hbWUiOiJDaHJvbWUgVjE1Mi4wLjAuMCAoV2luZG93cykiLCJmaW5nZXJwcmludCI6IjYzNTc2ZmM2ZTc2M2M2YmRhY2NlMTIxM2IwMTkxZDdmIiwiZGV2aWNlX2lkIjoiIiwicmVsYXRlZF9kZXZpY2VfaWRzIjoiIn0=',
    'fvideo-id': '33d0bf7ad64eaca8be5de1ea672be0bc9d3d859c',
    'lang': 'zh-TC',
    'referer': 'https://www.binance.com/zh-TC/square/profile/xg297174',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36',
    'cookie': 'bnc-uuid=a785dc47-f2c3-4662-b66d-f78deb00145b; BNC_FV_KEY=33d0bf7ad64eaca8be5de1ea672be0bc9d3d859c; BNC-Location=TW; theme=dark; lang=zh-TC'
}

data_file = 'scripts/data_cache/feige_2years_posts.json'

def fetch_batch(time_offset):
    params = {
        'targetSquareUid': target_uid,
        'timeOffset': time_offset,
        'filterType': 'ALL'
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('success'):
                    return data.get('data', {})
                else:
                    time.sleep(1 + attempt)
        except Exception as e:
            time.sleep(1 + attempt * 1.5)
    return None

def clean_post(item):
    t = item.get('firstReleaseTime') or item.get('createTime')
    dt_str = ''
    year_str = ''
    month_str = ''
    if t:
        try:
            dt = datetime.fromtimestamp(t / 1000)
            dt_str = dt.strftime('%Y-%m-%d %H:%M')
            year_str = dt.strftime('%Y')
            month_str = dt.strftime('%Y-%m')
        except Exception:
            pass
    
    pairs = []
    raw_pairs = item.get('tradingPairs') or item.get('coinPairList') or []
    for p in raw_pairs:
        if isinstance(p, dict):
            name = p.get('name') or p.get('pair') or p.get('symbol')
            rate = p.get('rate') or p.get('priceChangePercent') or ''
            if name:
                pairs.append({'name': str(name), 'rate': str(rate)})
        elif isinstance(p, str):
            pairs.append({'name': p, 'rate': ''})

    quote_text = ''
    qc = item.get('quoteContent')
    if isinstance(qc, dict):
        quote_text = qc.get('bodyTextOnly') or qc.get('body') or qc.get('title') or ''

    body = item.get('bodyTextOnly') or item.get('body') or ''

    return {
        'id': str(item.get('id', '')),
        'timestamp': t,
        'date': dt_str,
        'year': year_str,
        'month': month_str,
        'title': item.get('title') or '',
        'body': body.strip(),
        'quote': quote_text.strip(),
        'pairs': pairs,
        'views': item.get('viewCount') or 0,
        'likes': item.get('likeCount') or 0,
        'comments': item.get('commentCount') or 0,
        'shares': item.get('shareCount') or 0,
        'url': f"https://www.binance.com/zh-TC/square/post/{item.get('id')}"
    }

def main():
    print("=== 擴充爬取 2023 年歷史貼文 ===")
    all_posts = []
    seen_ids = set()

    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            all_posts = json.load(f)
        for p in all_posts:
            seen_ids.add(str(p.get('id')))
        print(f"現有貼文數量: {len(all_posts)}")
    
    # Find the earliest timestamp in existing dataset
    min_ts = min([p['timestamp'] for p in all_posts if p.get('timestamp')])
    print(f"從最遠點繼續回溯: {datetime.fromtimestamp(min_ts/1000)} (ts={min_ts})")

    current_offset = min_ts
    page = 0
    added_count = 0

    while True:
        page += 1
        data = fetch_batch(current_offset)
        if not data:
            print("無法獲取數據，結束。")
            break

        contents = data.get('contents') or []
        if not contents:
            print("本頁內容為空，已爬取至創號首篇貼文！")
            break

        new_in_batch = 0
        for raw in contents:
            cleaned = clean_post(raw)
            pid = cleaned['id']
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_posts.append(cleaned)
                new_in_batch += 1
                added_count += 1

        next_offset = data.get('timeOffset')
        t_sample = contents[0].get('firstReleaseTime') or contents[0].get('createTime')
        dt_str = datetime.fromtimestamp(t_sample/1000).strftime('%Y-%m-%d %H:%M') if t_sample else 'N/A'
        print(f"2023 擴展第 {page} 頁: 本批 {len(contents)} 篇 (新增 {new_in_batch}) | 日期: {dt_str} | 總計: {len(all_posts)}")

        if not next_offset or next_offset == current_offset:
            print("抵達最早分頁游標，爬取全部完成！")
            break

        current_offset = next_offset
        time.sleep(0.18)

    # Sort reverse chronological
    all_posts.sort(key=lambda x: x.get('timestamp') or 0, reverse=True)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\n==========================================")
    print(f"2023 年貼文擴充完成！新增了 {added_count} 篇貼文。")
    print(f"當前歷史數據庫總篇數: {len(all_posts)}")
    print(f"最遠貼文時間: {all_posts[-1].get('date')} (ID: {all_posts[-1].get('id')})")
    print(f"==========================================")

if __name__ == '__main__':
    main()
