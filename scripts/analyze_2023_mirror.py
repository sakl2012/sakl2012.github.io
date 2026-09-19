import json
from datetime import datetime

with open('scripts/data_cache/feige_2years_posts.json', 'r', encoding='utf-8') as f:
    posts = json.load(f)

posts_2023 = [p for p in posts if p.get('year') == '2023']
print(f"Total 2023 posts: {len(posts_2023)}")

# Sort by engagement
posts_2023_sorted = sorted(posts_2023, key=lambda x: (x.get('views') or 0) + (x.get('likes') or 0)*100, reverse=True)

# Categorize 2023 posts
keywords = {
    'BTC_Bottom_Cycle': ['大底', '抄底', '熊转牛', '牛市', '熊市', '25000', '26000', '27000', '28000', '30000', '周期', '定投'],
    'Public_Chains': ['SOL', 'ETH', 'BNB', 'FTX', 'LUNA', '公链'],
    'Sector_Narratives': ['AI', '铭文', 'ORDI', 'Inscriptions', 'DeFi', 'DEX', 'ARB', 'OP'],
    'Mindset_Strategy': ['拿住', '割肉', '现货', '合约', '爆仓', '止损', '散户', '主力']
}

with open('scripts/data_cache/analysis_2023_insights.txt', 'w', encoding='utf-8') as out:
    out.write("=== 2023 飛哥熊轉牛經典貼文深度萃取 ===\n")
    for category, kws in keywords.items():
        matched = [p for p in posts_2023_sorted if any(k.lower() in (p.get('body') or '').lower() for k in kws)]
        out.write(f"\n=============================================\n")
        out.write(f"Category: {category} (Matched: {len(matched)} posts)\n")
        out.write(f"=============================================\n")
        for i, p in enumerate(matched[:6]):
            out.write(f"\n--- [{i+1}] ID: {p.get('id')} | Date: {p.get('date')} | Views: {p.get('views')} | Likes: {p.get('likes')} ---\n")
            out.write(f"Body:\n{p.get('body')}\n")
            if p.get('quote'):
                out.write(f"Quote: {p.get('quote')}\n")

print("2023 insights written to scripts/data_cache/analysis_2023_insights.txt")
