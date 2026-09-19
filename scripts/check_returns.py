import json
with open('scripts/data_cache/ENAUSDT_1d.json') as f: ena = json.load(f)
with open('scripts/data_cache/AAVEUSDT_1d.json') as f: aave = json.load(f)
with open('scripts/data_cache/LINKUSDT_1d.json') as f: link = json.load(f)
with open('scripts/data_cache/NEARUSDT_1d.json') as f: near = json.load(f)

d0 = '2024-04-11'
def get_p(lst, d):
    for row in lst:
        if row['date'] == d: return row['c']
    return lst[-1]['c']

p_ena0, p_ena1 = get_p(ena, d0), ena[-1]['c']
p_aave0, p_aave1 = get_p(aave, d0), aave[-1]['c']
p_link0, p_link1 = get_p(link, d0), link[-1]['c']
p_near0, p_near1 = get_p(near, d0), near[-1]['c']

print('ENA: %.4f -> %.4f (%+.1f%%)' % (p_ena0, p_ena1, (p_ena1/p_ena0 - 1)*100))
print('AAVE: %.2f -> %.2f (%+.1f%%)' % (p_aave0, p_aave1, (p_aave1/p_aave0 - 1)*100))
print('LINK: %.2f -> %.2f (%+.1f%%)' % (p_link0, p_link1, (p_link1/p_link0 - 1)*100))
print('NEAR: %.2f -> %.2f (%+.1f%%)' % (p_near0, p_near1, (p_near1/p_near0 - 1)*100))
