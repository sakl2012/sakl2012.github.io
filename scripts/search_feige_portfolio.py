import json

with open('scripts/data_cache/feige_2years_posts.json', 'r', encoding='utf-8') as f:
    posts = json.load(f)

matches = []
for p in posts:
    b = (p.get('body') or '') + ' ' + (p.get('title') or '')
    if ('BTC' in b and 'ETH' in b) and any(k in b for k in ['仓位', '配置', '比例', '黄金', 'TAO']):
        matches.append(p)

matches.sort(key=lambda x: (x.get('views') or 0) + (x.get('likes') or 0)*50, reverse=True)

with open('scripts/data_cache/feige_portfolio_quotes.txt', 'w', encoding='utf-8') as f:
    f.write(f"Found {len(matches)} matching allocation posts.\n\n")
    for i, p in enumerate(matches[:10]):
        f.write(f"=== [{i+1}] Date: {p.get('date')} | ID: {p.get('id')} | Views: {p.get('views')} ===\n")
        f.write(f"{p.get('body')}\n\n")

print("Portfolio quotes written to scripts/data_cache/feige_portfolio_quotes.txt")
