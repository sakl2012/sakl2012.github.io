import json

with open('scripts/data_cache/feige_2years_posts.json', 'r', encoding='utf-8') as f:
    posts = json.load(f)

target_posts = [p for p in posts if p.get('year') == '2023' and p.get('month') in ['2023-08', '2023-09', '2023-10', '2023-11', '2023-12']]

key_posts = []
for p in target_posts:
    body = p.get('body', '')
    if any(k in body for k in ['25000', '26000', '28000', '30000', '减半', '大底', '洗盘', '蓄势', '牛市', '踏空']):
        key_posts.append(p)

key_posts.sort(key=lambda x: (x.get('views') or 0) + (x.get('likes') or 0)*50, reverse=True)

with open('scripts/data_cache/2023_key_quotes.txt', 'w', encoding='utf-8') as f:
    f.write(f"Found {len(key_posts)} key late-2023 transition posts.\n\n")
    for i, p in enumerate(key_posts[:15]):
        f.write(f"=== [{i+1}] Date: {p.get('date')} | ID: {p.get('id')} | Views: {p.get('views')} ===\n")
        f.write(f"Title: {p.get('title')}\n")
        f.write(f"Body:\n{p.get('body')}\n\n")

print("Key quotes written to scripts/data_cache/2023_key_quotes.txt")
