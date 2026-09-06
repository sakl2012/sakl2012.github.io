#!/usr/bin/env python3
"""
4-Zone Strategy - Automated D-Tier Sniper Audit Script
Powered by Google Gemini AI & GitHub Actions (24/7 Automation)
"""

import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

def get_tw_time():
    tz_tw = timezone(timedelta(hours=8))
    now = datetime.now(tz_tw)
    return now.strftime('%Y-%m-%d %H:%M')

def query_gemini(api_key, prompt):
    models = ['gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-pro-latest']
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 800
            }
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                parts = data['candidates'][0]['content']['parts']
                text = "".join([p.get('text', '') for p in parts if 'text' in p])
                if text:
                    return text.strip()
        except Exception as e:
            print(f"Error querying {model}: {e}")
            continue
    return None

def fetch_market_context():
    # Fetch live BTC and top tickers for context
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ENAUSDT%22,%22TAOUSDT%22,%22AAVEUSDT%22,%22LINKUSDT%22%5D"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            summary = ", ".join([f"{item['symbol'].replace('USDT','')}: ${float(item['lastPrice']):.3f} ({float(item['priceChangePercent']):+.1f}%)" for item in data])
            return summary
    except Exception as e:
        print(f"Failed to fetch market context: {e}")
        return "BTC: $76700, ENA: $0.168, TAO: $216, AAVE: $126, LINK: $11"

def build_audit_prompt(market_context, tw_time):
    return f"""
你是「4-Zone 動態防禦三倉策略系統」的 D 倉（飛哥獵手現貨狙擊）專屬 AI 審計大腦。

【背景與持倉現況】
- 宏觀策略：A 倉 (BTC/PAXG 20%)、B 倉 (SOL/TAO/PAXG 60%)、C 倉 (AAVE/NEAR/LINK/PAXG 20%) 已經由幣安智能持倉全自動運行。
- D 倉（機動獵手 95% PAXG + 5% 現貨伏擊槽）：專門追隨幣安廣場「K線人生飞哥」推薦的現貨標的。
- 飛哥近期關注與常態觀點板塊：
  1. 主流輪動：BTC/ETH 回踩防守做多；DeFi 龍頭 (AAVE, LINK)
  2. AI Agent 賽道主線：TAO, VIRTUAL
  3. 短線/定投關注名單：ENA (回踩0.13~0.15)、GIGGLE (震盪洗盤)、ZRO, LIT, PUMP, HYPE, TRUMP
  4. 垃圾幣/微盤/已暴漲：USELESS (翻倍慶祝)、PONS (鏈上微盤)
- 即時市場數據：{market_context}
- 當前審計時間（台灣時間 UTC+8）：{tw_time}

【D 倉四大硬核審計標準】
1. 實時歷史 K 線對齊：暴漲後才發文吹噓的一律判定【不追/略過】。
2. 時間戳與走勢檢驗：翻倍/炫耀文一律視為【停利清倉信號】而非進場點。
3. 只做首推真龍頭：二線補漲替代品一律判定【略過】。
4. 幣安現貨深度過濾：非幣安現貨或鏈上土狗微盤一律【略過】。
5. 若已在 A/B/C 倉（如 TAO, AAVE, LINK, SOL）：判定為【已在 ABC 倉自動配置，D 倉不重複追高】。

請直接輸出 HTML 代碼片段（包裹在 `<div ...>` 中），格式務必嚴格遵循以下 HTML 結構，直接輸出可嵌入 index.html 的 HTML，不要包含任何 markdown codeblock 標籤：

<div style="font-size: 12px; color: #64748b; line-height: 1.6; background: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 12px;">
    <strong>📡 最新爬文審計判定 ({tw_time})：</strong><br>
    • <strong>$LINK / $AAVE / $ETH (主流輪動)</strong>：LINK/AAVE 已在 C 倉配置 (49%) ➔ <span style="color:#2563eb; font-weight:700;">D 倉不重複追高，智能持倉自動吃肉</span><br>
    • <strong>$TAO / $VIRTUAL (AI Agent主線)</strong>：TAO 已在 B 倉配置 (15%) ➔ <span style="color:#2563eb; font-weight:700;">坐享主升浪</span><br>
    • <strong>$ENA</strong>：現價 <span id="d-live-ena" style="font-weight:700; color:#0f172a;">$0.168</span> 震盪，待解鎖回踩 $0.13~$0.15 ➔ <span style="color:#d97706; font-weight:700;">5% 伏擊槽持續鎖定中</span><br>
    • <strong>$ZRO / $LIT / $PUMP</strong>：近期點名追蹤標的 ➔ <span style="color:#d97706; font-weight:700;">未有起漲前首發信號前保持觀望</span><br>
    • <strong>$USELESS / $PONS</strong>：暴漲慶祝文 / 微盤 ➔ <span style="color:#dc2626; font-weight:700;">嚴格略過</span>
</div>
"""

def main():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        return

    tw_time = get_tw_time()
    market_context = fetch_market_context()
    print(f"[{tw_time}] Starting D-Tier Sniper automated audit...")
    print(f"Market context: {market_context}")

    prompt = build_audit_prompt(market_context, tw_time)
    audit_html = query_gemini(api_key, prompt)

    if not audit_html:
        print("Failed to get response from Gemini API.")
        return

    # Clean markdown if present
    audit_html = re.sub(r'^```html\s*', '', audit_html, flags=re.MULTILINE)
    audit_html = re.sub(r'^```\s*$', '', audit_html, flags=re.MULTILINE).strip()

    index_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
    if not os.path.exists(index_path):
        index_path = 'index.html'

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'<!-- D_TIER_AUDIT_START -->.*?<!-- D_TIER_AUDIT_END -->'
    replacement = f'<!-- D_TIER_AUDIT_START -->\n                    {audit_html}\n                    <!-- D_TIER_AUDIT_END -->'

    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully updated index.html with new D-tier audit assessment!")
    else:
        print("Could not find D_TIER_AUDIT_START / D_TIER_AUDIT_END markers in index.html.")

if __name__ == '__main__':
    main()
