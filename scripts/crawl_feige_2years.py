import urllib.request
import urllib.parse
import json
import time
import os
import sys
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

# 2 years back from 2026-09-19: target timestamp 2024-09-01 00:00:00 UTC = ~1725148800000
TARGET_TIMESTAMP = 1725148800000

output_dir = os.path.join(os.path.dirname(__file__), 'data_cache')
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, 'feige_2years_posts.json')

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
                    print(f"API returned error: {data.get('message')}, retrying...")
                    time.sleep(1 + attempt)
        except Exception as e:
            print(f"Network error on offset {time_offset} (attempt {attempt+1}): {e}")
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
    
    # Extract trading pairs
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

    # Extract quoted text
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
    print(f"=== 啟動飛哥 2 年歷史貼文全量爬蟲 ===")
    print(f"目標起始點: 當前最新")
    print(f"目標截止點: 2024年9月 (ts <= {TARGET_TIMESTAMP})")
    print(f"存檔路徑: {output_file}\n")

    all_posts = []
    seen_ids = set()

    # Load existing if available for resumption
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                for p in existing:
                    pid = str(p.get('id'))
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_posts.append(p)
            print(f"成功加載既有存檔: {len(all_posts)} 篇貼文。")
        except Exception as e:
            print(f"讀取既有存檔失敗: {e}")

    current_offset = int(time.time() * 1000)
    # If resuming, find lowest timestamp in existing
    if all_posts:
        min_ts = min([p['timestamp'] for p in all_posts if p.get('timestamp')])
        print(f"從既有存檔最早時間戳繼續翻頁: {datetime.fromtimestamp(min_ts/1000)} (ts={min_ts})")
        current_offset = min_ts

    page = 0
    total_added = 0

    while True:
        page += 1
        data = fetch_batch(current_offset)
        if not data:
            print(f"無法取得 offset {current_offset} 的數據，結束翻頁。")
            break

        contents = data.get('contents', [])
        if not contents:
            print(f"頁面為空，已爬取到底部。")
            break

        new_count = 0
        min_batch_ts = None
        for raw in contents:
            cleaned = clean_post(raw)
            pid = cleaned['id']
            ts = cleaned['timestamp']
            if ts:
                if min_batch_ts is None or ts < min_batch_ts:
                    min_batch_ts = ts

            if pid not in seen_ids:
                seen_ids.add(pid)
                all_posts.append(cleaned)
                new_count += 1
                total_added += 1

        next_offset = data.get('timeOffset')

        # Progress log
        latest_date = contents[0].get('firstReleaseTime') or contents[0].get('createTime')
        dt_sample = datetime.fromtimestamp(latest_date/1000).strftime('%Y-%m-%d %H:%M') if latest_date else 'N/A'
        print(f"第 {page} 頁: 本批 {len(contents)} 篇 (新增 {new_count}) | 當前進度日期: {dt_sample} | 累計總數: {len(all_posts)}")

        # Check if reached target
        if min_batch_ts and min_batch_ts <= TARGET_TIMESTAMP:
            print(f"\n已成功達到 2 年前目標時間 ({datetime.fromtimestamp(min_batch_ts/1000)})，爬取完成！")
            break

        if not next_offset or next_offset == current_offset:
            print("沒有更多歷史分頁游標，爬取完畢。")
            break

        current_offset = next_offset

        # Save checkpoint every 25 pages (500 posts)
        if page % 25 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_posts, f, ensure_ascii=False, indent=2)
            print(f"  --> [進度存檔] 已持久化保存 {len(all_posts)} 篇貼文。")

        # Politeness delay
        time.sleep(0.18)

    # Final sort and save
    all_posts.sort(key=lambda x: x.get('timestamp') or 0, reverse=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\n==========================================")
    print(f"爬蟲任務圓滿完成！")
    print(f"總共收集: {len(all_posts)} 篇歷史貼文")
    if all_posts:
        print(f"最新貼文時間: {all_posts[0].get('date')} (ID: {all_posts[0].get('id')})")
        print(f"最遠貼文時間: {all_posts[-1].get('date')} (ID: {all_posts[-1].get('id')})")
    print(f"檔案已儲存至: {output_file}")
    print(f"==========================================")

if __name__ == '__main__':
    main()
