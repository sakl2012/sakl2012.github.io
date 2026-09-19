import json

with open('scripts/data_cache/feige_2years_posts.json', 'r', encoding='utf-8') as f:
    posts = json.load(f)

print(f"Total posts analyzed: {len(posts)}")

topics = {
    "Macro_Cycle": ["熊转牛", "2023", "加息", "降息", "5.7万", "15万", "20万", "大牛市", "周期"],
    "L1_PublicChains": ["SOL", "SUI", "SEI", "TIA", "二线公链", "公链"],
    "AI_Sector": ["TAO", "NEAR", "VIRTUAL", "FET", "AI Agent", "人工智能"],
    "DeFi_DEX": ["UNI", "ARB", "HYPE", "LIT", "ASTER", "ENA", "PENDLE", "Robinhood"],
    "Trading_Philosophy": ["跑得快", "分批", "定投", "手续费", "返佣", "滚仓"]
}

results = {}

for cat, kws in topics.items():
    matched = []
    for p in posts:
        text = (p.get('body') or '') + ' ' + (p.get('title') or '') + ' ' + (p.get('quote') or '')
        if any(k.lower() in text.lower() for k in kws):
            matched.append(p)
    matched_sorted = sorted(matched, key=lambda x: (x.get('views') or 0) + (x.get('likes') or 0)*100, reverse=True)
    results[cat] = matched_sorted

with open('scripts/data_cache/sector_analysis_summary.txt', 'w', encoding='utf-8') as out:
    for cat, items in results.items():
        out.write(f"\n=========================================\n")
        out.write(f"Category: {cat} (Total {len(items)} posts)\n")
        out.write(f"=========================================\n")
        for i, p in enumerate(items[:5]):
            out.write(f"\n--- [{i+1}] ID: {p.get('id')} | Date: {p.get('date')} | Views: {p.get('views')} | Likes: {p.get('likes')} ---\n")
            if p.get('title'):
                out.write(f"Title: {p.get('title')}\n")
            out.write(f"Body: {p.get('body')[:400]}...\n")
            if p.get('quote'):
                out.write(f"Quote: {p.get('quote')[:200]}...\n")

print("Analysis written to scripts/data_cache/sector_analysis_summary.txt")
