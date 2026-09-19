import json
from collections import defaultdict

with open('scripts/data_cache/feige_2years_posts.json', 'r', encoding='utf-8') as f:
    posts = json.load(f)

# Search for posts where Feige discusses specific altcoins
# Specifically: SOL, UNI, HYPE, SUI, ARB, PENDLE, AAVE, LINK, NEAR, FET, VIRTUAL, ENA, DOGE, MKR, AVAX
candidates = [
    'SOL', 'UNI', 'HYPE', 'SUI', 'ARB', 'PENDLE', 'AAVE', 'LINK', 'NEAR', 'FET', 'VIRTUAL', 'ENA', 'DOGE', 'MKR', 'ONDO', 'RENDER'
]

stats = defaultdict(lambda: {'count': 0, 'views': 0, 'likes': 0, 'mentions_2026': 0, 'sample_quotes': []})

for p in posts:
    b = (p.get('body') or '') + ' ' + (p.get('title') or '') + ' ' + (p.get('quote') or '')
    year = p.get('year')
    for c in candidates:
        if c.lower() in b.lower():
            stats[c]['count'] += 1
            stats[c]['views'] += (p.get('views') or 0)
            stats[c]['likes'] += (p.get('likes') or 0)
            if year == '2026':
                stats[c]['mentions_2026'] += 1
            if len(stats[c]['sample_quotes']) < 3 and len(b) > 40:
                stats[c]['sample_quotes'].append({
                    'id': p.get('id'),
                    'date': p.get('date'),
                    'text': b[:200].replace('\n', ' ')
                })

with open('scripts/data_cache/feige_c_candidates_ranking.txt', 'w', encoding='utf-8') as out:
    out.write("=== Feige Candidate Coins Stats & Analysis ===\n\n")
    # Sort by 2026 mentions and total engagement
    sorted_coins = sorted(candidates, key=lambda c: stats[c]['mentions_2026'] * 10 + stats[c]['count'], reverse=True)
    for c in sorted_coins:
        s = stats[c]
        out.write(f"Coin: {c} | Total Mentions: {s['count']} | 2026 Mentions: {s['mentions_2026']} | Total Views: {s['views']:,} | Likes: {s['likes']:,}\n")
        for q in s['sample_quotes']:
            out.write(f"   [{q['date']}] {q['text']}...\n")
        out.write("\n")

print("Candidate analysis written to scripts/data_cache/feige_c_candidates_ranking.txt")
