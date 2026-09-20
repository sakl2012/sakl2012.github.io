/**
 * 5-Zone 階梯防脆弱策略 (ABC 三倉全自動最佳化版) - Google Apps Script 自動監控與 Email 警報
 * 主力：Binance Vision (免 451 封鎖) | 備援：OKX / Bybit | 具備防崩潰與自動切換機制
 * 最新架構：升級為 5-Zone 階梯狀態機 (Zone 0 深熊底 ~ Zone 4 牛頂逃頂)
 * 資金配比：A 20% / B 55% / C 25%，C 倉四星輪動 (AAVE/SUI/LINK/NEAR/PAXG)
 */

const YOUR_EMAIL = "sakl19930909@gmail.com"; // 您的信箱

function checkZoneAndAlert() {
  try {
    // 1. 取得市場資料（自動走 主力 -> 備援 機制）
    const currentPrice = getCurrentPrice();
    const ma200 = getYesterdayMA200();
    const sma72Price = get72hSMA();
    
    if (!ma200 || !currentPrice || !sma72Price) {
      Logger.log("⚠️ 所有交易所 API 均未能成功回傳數據，本輪略過並靜默等待下次觸發。");
      return;
    }
    
    // 2. 計算比值
    const ratio = currentPrice / ma200;
    const ratioSma72 = sma72Price / ma200; 
    
    // 3. 讀取之前的 Zone 狀態 (預設為 2)
    const props = PropertiesService.getScriptProperties();
    let currentZone = parseInt(props.getProperty("CURRENT_ZONE"));
    if (isNaN(currentZone)) currentZone = 2;
    let newZone = currentZone;
    
    // 4. 狀態機邏輯 (5-Zone 階梯防脆弱狀態機，含 72h SMA 平滑防插針)
    if (currentZone === 0) {
      // 在極限深熊底，若 72h SMA 回升突破 0.82 則脫離深熊進入初熊防守
      if (ratioSma72 > 0.82) newZone = 1;
    }
    else if (currentZone === 1) {
      // 初熊防禦期：若持續下破 0.78 則進入 Zone 0 深熊抄底；若反彈突破 1.02 則回歸 Zone 2
      if (ratioSma72 < 0.78) newZone = 0;
      else if (ratioSma72 > 1.02) newZone = 2;
    } 
    else if (currentZone === 2) {
      // 牛市巡航期：若 72h SMA 跌破 0.98 進入 Zone 1 防守；若比值突破 1.25 進入 Zone 3
      if (ratioSma72 < 0.98) newZone = 1;
      else if (ratio > 1.25) newZone = 3;
    } 
    else if (currentZone === 3) {
      // 過熱警戒期：若回跌低於 1.15 回降 Zone 2；若破 1.40 進入 Zone 4 逃頂
      if (ratio < 1.15) newZone = 2;
      else if (ratio > 1.40) newZone = 4;
    } 
    else if (currentZone === 4) {
      // 極限逃頂期：回跌低於 1.30 回降 Zone 3
      if (ratio < 1.30) newZone = 3;
    }
    
    Logger.log(`目前價格: ${currentPrice.toFixed(2)}, MA200: ${ma200.toFixed(2)}`);
    Logger.log(`當前比值: ${ratio.toFixed(3)}, 72h SMA比值: ${ratioSma72.toFixed(3)}`);
    Logger.log(`原 Zone: ${currentZone} -> 新 Zone: ${newZone}`);
    
    // 5. 判斷是否切換並發送 Email
    if (newZone !== currentZone) {
      const allocationText = getAllocationConfig(newZone);
      const zoneNames = {
        0: "深熊大底 (頂級抄底模式)",
        1: "初熊防禦 (防刀緩衝模式)",
        2: "牛市巡航 (健康起飛模式)",
        3: "過熱警戒 (階梯獲利模式)",
        4: "極度貪婪/逃頂 (避險保命模式)"
      };
      
      const subject = `🚨 5-Zone 策略狀態切換：Zone ${newZone} (${zoneNames[newZone]})`;
      const body = `
自動監控機器人發現市場狀態改變！

🔹 新狀態：Zone ${newZone} (${zoneNames[newZone]})
🔹 舊狀態：Zone ${currentZone} (${zoneNames[currentZone]})

📊 當前市場數據：
- BTC 價格：$${currentPrice.toFixed(2)}
- 1D MA200：$${ma200.toFixed(2)}
- 即時乖離比值：${ratio.toFixed(3)}
- 72小時 SMA 乖離：${ratioSma72.toFixed(3)}

==================================================
🎯 建議三倉最新配置目標 (宏觀分配: A 20% / B 55% / C 25%)：
==================================================
${allocationText}
==================================================

請立即登入幣安 App，在「智能持倉」中依上述比例調整目標權重！
      `;
      
      MailApp.sendEmail(YOUR_EMAIL, subject, body);
      Logger.log("Email 已發送！");
      
      props.setProperty("CURRENT_ZONE", newZone.toString());
    }
  } catch (err) {
    Logger.log("全域捕捉異常（已攔截防止報警信）: " + err.toString());
  }
}

// ==========================================================
// === 取得對應 Zone 的持倉配置文字 (3大核心 + 6大Alpha 三幣全天候版) ===
// ==========================================================
function getAllocationConfig(zone) {
  if (zone === 0) {
    return `【Zone 0: 深熊大底】(極限雙抄底進攻模式 - 5年全週期最佳化認證)
👉 👑 核心 1 (20% 資金): BTC 65% | QQQB 25% | PAXG 10% (偏差2%)
👉 🏛️ 核心 2 (20% 資金): ETH 65% | QQQB 25% | PAXG 10% (偏差2%)
👉 🤖 核心 3 (10% 資金): TAO 65% | QQQB 25% | PAXG 10% (偏差2%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 35% | QQQB 35% | PAXG 30% (全天候靜態 35/35/30，偏差2%)`;
  }
  else if (zone === 1) {
    return `【Zone 1: 初牛修復】(防震盪過渡模式 - 均勢動態累積)
👉 👑 核心 1 (20% 資金): BTC 50% | QQQB 30% | PAXG 20% (偏差2%)
👉 🏛️ 核心 2 (20% 資金): ETH 50% | QQQB 30% | PAXG 20% (偏差2%)
👉 🤖 核心 3 (10% 資金): TAO 50% | QQQB 30% | PAXG 20% (偏差2%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 35% | QQQB 35% | PAXG 30% (全天候靜態 35/35/30，偏差2%)`;
  } 
  else if (zone === 2) {
    return `【Zone 2: 牛市巡航】(穩健主升浪模式 - 現正運行 ⭐)
👉 👑 核心 1 (20% 資金): BTC 45% | QQQB 35% | PAXG 20% (偏差2%)
👉 🏛️ 核心 2 (20% 資金): ETH 40% | QQQB 35% | PAXG 25% (偏差2%)
👉 🤖 核心 3 (10% 資金): TAO 35% | QQQB 35% | PAXG 30% (偏差2%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 35% | QQQB 35% | PAXG 30% (全天候靜態 35/35/30，偏差2%)`;
  } 
  else if (zone === 3) {
    return `【Zone 3: 過熱警戒】(高位鎖利模式 - 大幅沉澱美股與黃金)
👉 👑 核心 1 (20% 資金): BTC 30% | QQQB 35% | PAXG 35% (偏差2%)
👉 🏛️ 核心 2 (20% 資金): ETH 25% | QQQB 35% | PAXG 40% (偏差2%)
👉 🤖 核心 3 (10% 資金): TAO 20% | QQQB 40% | PAXG 40% (偏差2%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 35% | QQQB 35% | PAXG 30% (全天候靜態 35/35/30，偏差2%)`;
  } 
  else if (zone === 4) {
    return `【Zone 4: 極度貪婪/逃頂】(終極避險逃頂模式 - 物理金條封存)
👉 👑 核心 1 (20% 資金): BTC 5% | SPYB 30% | PAXG 65% (偏差2%)
👉 🏛️ 核心 2 (20% 資金): ETH 5% | SPYB 30% | PAXG 65% (偏差2%)
👉 🤖 核心 3 (10% 資金): TAO 5% | SPYB 25% | PAXG 70% (偏差2%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 35% | SPYB 35% | PAXG 30% (全天候靜態 35/35/30，偏差2%)`;
  } 
  else {
    return `尚未定義此 Zone 的持倉配置。`;
  }
}

// ==========================================
// === 核心安全 Fetch 工具 (防崩潰封裝) ===
// ==========================================

function safeFetchJson(url) {
  try {
    const res = UrlFetchApp.fetch(url, {
      muteHttpExceptions: true,
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
    });
    
    const statusCode = res.getResponseCode();
    if (statusCode === 200) {
      return JSON.parse(res.getContentText());
    } else {
      return null;
    }
  } catch (e) {
    return null;
  }
}

// ==========================================
// === 取得即時價格 (6級頂級容災：OKX -> Bybit -> Gate.io -> KuCoin -> Binance -> Coinbase) ===
// ==========================================

function getCurrentPrice() {
  // 1. OKX
  try {
    const oData = safeFetchJson("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT");
    if (oData && oData.data && oData.data.length > 0) return parseFloat(oData.data[0].last);
  } catch (e) {}

  // 2. Bybit
  try {
    const bybitData = safeFetchJson("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT");
    if (bybitData && bybitData.result && bybitData.result.list && bybitData.result.list.length > 0) return parseFloat(bybitData.result.list[0].lastPrice);
  } catch (e) {}

  // 3. Gate.io
  try {
    const gateData = safeFetchJson("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT");
    if (gateData && gateData.length > 0 && gateData[0].last) return parseFloat(gateData[0].last);
  } catch (e) {}

  // 4. KuCoin
  try {
    const kuData = safeFetchJson("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT");
    if (kuData && kuData.data && kuData.data.price) return parseFloat(kuData.data.price);
  } catch (e) {}

  // 5. Binance api1 / api3
  try {
    const bData = safeFetchJson("https://api1.binance.com/api/v3/ticker/price?symbol=BTCUSDT") || safeFetchJson("https://api3.binance.com/api/v3/ticker/price?symbol=BTCUSDT");
    if (bData && bData.price) return parseFloat(bData.price);
  } catch (e) {}

  // 6. Coinbase Exchange
  try {
    const cbData = safeFetchJson("https://api.exchange.coinbase.com/products/BTC-USD/ticker");
    if (cbData && cbData.price) return parseFloat(cbData.price);
  } catch (e) {}

  return null;
}

// ==========================================
// === 取得 200 日線 MA (4級容災：OKX -> Bybit -> Gate.io -> Binance) ===
// ==========================================

function getYesterdayMA200() {
  // 1. OKX
  try {
    const oData = safeFetchJson("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1Dutc&limit=201");
    if (oData && oData.data && oData.data.length >= 200) {
      let sum = 0;
      const len = Math.min(200, oData.data.length);
      for (let i = 0; i < len; i++) sum += parseFloat(oData.data[i][4]);
      return sum / len;
    }
  } catch (e) {}

  // 2. Bybit
  try {
    const bybitData = safeFetchJson("https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=D&limit=200");
    if (bybitData && bybitData.result && bybitData.result.list && bybitData.result.list.length >= 200) {
      let sum = 0;
      for (let i = 0; i < 200; i++) sum += parseFloat(bybitData.result.list[i][4]);
      return sum / 200;
    }
  } catch (e) {}

  // 3. Gate.io
  try {
    const gateData = safeFetchJson("https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=BTC_USDT&interval=1d&limit=200");
    if (gateData && gateData.length >= 200) {
      let sum = 0;
      for (let i = 0; i < 200; i++) sum += parseFloat(gateData[i][2]);
      return sum / 200;
    }
  } catch (e) {}

  // 4. Binance api1
  try {
    const bData = safeFetchJson("https://api1.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=200");
    if (bData && Array.isArray(bData) && bData.length >= 200) {
      let sum = 0;
      for (let i = 0; i < 200; i++) sum += parseFloat(bData[i][4]);
      return sum / 200;
    }
  } catch (e) {}

  return null;
}

// ==========================================
// === 取得 72 小時 SMA (4級容災：OKX -> Bybit -> Gate.io -> Binance) ===
// ==========================================

function get72hSMA() {
  // 1. OKX
  try {
    const oData = safeFetchJson("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=72");
    if (oData && oData.data && oData.data.length >= 72) {
      let sum = 0;
      for (let i = 0; i < 72; i++) sum += parseFloat(oData.data[i][4]);
      return sum / 72;
    }
  } catch (e) {}

  // 2. Bybit
  try {
    const bybitData = safeFetchJson("https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=60&limit=72");
    if (bybitData && bybitData.result && bybitData.result.list && bybitData.result.list.length >= 72) {
      let sum = 0;
      for (let i = 0; i < 72; i++) sum += parseFloat(bybitData.result.list[i][4]);
      return sum / 72;
    }
  } catch (e) {}

  // 3. Gate.io
  try {
    const gateData = safeFetchJson("https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=BTC_USDT&interval=1h&limit=72");
    if (gateData && gateData.length >= 72) {
      let sum = 0;
      for (let i = 0; i < 72; i++) sum += parseFloat(gateData[i][2]);
      return sum / 72;
    }
  } catch (e) {}

  // 4. Binance api1
  try {
    const bData = safeFetchJson("https://api1.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=72");
    if (bData && Array.isArray(bData) && bData.length >= 72) {
      let sum = 0;
      for (let i = 0; i < 72; i++) sum += parseFloat(bData[i][4]);
      return sum / 72;
    }
  } catch (e) {}

  return null;
}

// ==========================================================
// === 補漲智能持倉換幣 / 止盈輪動監控 (PENDLE, LINK, LTC, ICP 四大波段標的) ===
// ==========================================================
//
// 📌【日線級別 (Daily) 波段持倉操盤核心原則 (Swing Trading SOP)】
// ------------------------------------------------------------------------------------------
// 1. 級別定義與心態管理：
//    • 本模組完全錨定「日線級別 (Daily)」，持倉週期預期為 1～3 週，追求 12%～25% 的波段主升浪。
//    • 嚴禁受盤中「15 分鐘 / 5 分鐘」的短線小雜訊干擾（例如盤中微跌 2% 只是日線的微小下影線）。
//    • 只要日線收盤沒有跌破 slFloor（防守底線），一律抱牢等待補漲，絕不輕易被洗下車！
//
// 2. 觸發警報執行紀律 (接獲 Email 提醒後的 SOP)：
//    • 【觸發 tpTarget 止盈】：代表已抵達日線強阻力平台，該幣波段性價比已吃滿。
//      立即打開幣安 App 終止該機器人並市價平倉現貨，將利潤全數鎖定，並換入 nextRotate 推薦的低位 Alpha！
//    • 【觸發 slFloor 止損】：代表日線關鍵均線或大底破位，趨勢走弱。
//      立即檢查盤面，評估手動關閉停損，避免資金陷入漫長套牢。
//
// 3. 四大標的最新日線結構與點位計算依據 (2026-09 最新 K 線驗證)：
//    • PENDLE (成本 $2.570):
//      - 結構：MA20($2.17) > MA50($1.77) > MA200($1.51) 全多頭發散，突破看漲旗形。
//      - tpTarget: $3.15 (+22.6%) -> 半年籌碼套牢平台（5~6月密集阻力區）。
//      - slFloor:  $2.20 (-14.4%) -> 貼合 MA20 動態均線防守位。
//    • LINK (成本 $12.291):
//      - 結構：站穩 MA20($11.77) 上方完成回踩確認，大箱體極致縮量蓄勢。
//      - tpTarget: $14.50 (+18.0%) -> 週線級別大箱體天花板與阻力密集區。
//      - slFloor:  $10.80 (-12.1%) -> 近 30 日低點 ($10.61) 上方防守頸線。
//    • LTC (成本 $57.780):
//      - 結構：MA50 向上金叉 MA200 完成牛熊轉換，下方 $50~$52 為歷史多重鐵底。
//      - tpTarget: $65.00 (+12.5%) -> 半年線下降趨勢線終極壓制位。
//      - slFloor:  $52.00 (-10.0%) -> 歷史多重底極限防線。
//    • ICP (成本 $2.761):
//      - 結構：剛站上 MA200($2.44) 與 MA20($2.70)，日線二次探底回踩完成。
//      - tpTarget: $3.25 (+17.7%) -> 2026 上半年四重大頂頸線密集壓制區。
//      - slFloor:  $2.45 (-11.3%) -> 貼合 200 日均線 ($2.44) 硬底。
// ------------------------------------------------------------------------------------------

function getSingleTokenPrice(sym, okxId) {
  // 1. Bybit
  try {
    const bybitData = safeFetchJson(`https://api.bybit.com/v5/market/tickers?category=spot&symbol=${sym}USDT`);
    if (bybitData && bybitData.result && bybitData.result.list && bybitData.result.list.length > 0) return parseFloat(bybitData.result.list[0].lastPrice);
  } catch (e) {}

  // 2. Gate.io
  try {
    const gateData = safeFetchJson(`https://api.gateio.ws/api/v4/spot/tickers?currency_pair=${sym}_USDT`);
    if (gateData && gateData.length > 0 && gateData[0].last) return parseFloat(gateData[0].last);
  } catch (e) {}

  // 3. KuCoin
  try {
    const kuData = safeFetchJson(`https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=${sym}-USDT`);
    if (kuData && kuData.data && kuData.data.price) return parseFloat(kuData.data.price);
  } catch (e) {}

  // 4. Binance api1
  try {
    const fbData = safeFetchJson(`https://api1.binance.com/api/v3/ticker/price?symbol=${sym}USDT`);
    if (fbData && fbData.price) return parseFloat(fbData.price);
  } catch (e) {}

  return null;
}

function checkCoinRotationAlert() {
  try {
    const targets = {
      PENDLEUSDT: { sym: "PENDLE", name: "Pendle",            okxId: "PENDLE-USDT", entryPrice: 2.57,  tpTarget: 3.15, slFloor: 2.20, nextRotate: "AAVE 或 UNI" },
      LINKUSDT:   { sym: "LINK",   name: "Chainlink",         okxId: "LINK-USDT",   entryPrice: 12.291,tpTarget: 14.50,slFloor: 10.80,nextRotate: "AAVE 或 NEAR" },
      LTCUSDT:    { sym: "LTC",    name: "Litecoin",          okxId: "LTC-USDT",    entryPrice: 57.78, tpTarget: 65.00, slFloor: 52.00, nextRotate: "AAVE 或 LINK" },
      ICPUSDT:    { sym: "ICP",    name: "Internet Computer", okxId: "ICP-USDT",    entryPrice: 2.761, tpTarget: 3.25, slFloor: 2.45, nextRotate: "UNI 或 ONDO" }
    };

    // 1. 批次取得 OKX 全現貨現價
    const priceMap = {};
    try {
      const okxData = safeFetchJson("https://www.okx.com/api/v5/market/tickers?instType=SPOT");
      if (okxData && okxData.data) {
        for (let d of okxData.data) {
          priceMap[d.instId] = parseFloat(d.last);
        }
      }
    } catch (e) {}

    const props = PropertiesService.getScriptProperties();
    const now = new Date().getTime();
    const logArr = [];

    for (let bKey in targets) {
      const info = targets[bKey];
      let curPrice = priceMap[info.okxId];

      // 若 OKX 未取到，自動走 Bybit -> Gate.io -> KuCoin -> Binance 4層備援
      if (!curPrice) {
        curPrice = getSingleTokenPrice(info.sym, info.okxId);
      }

      if (!curPrice) continue;
      
      const entry = info.entryPrice || curPrice;
      const pnlPct = ((curPrice - entry) / entry) * 100;
      const pnlSign = pnlPct >= 0 ? '+' : '';
      const pnlStr = ` (${pnlSign}${pnlPct.toFixed(2)}%)`;
      
      logArr.push(`${info.sym}: $${curPrice}${pnlStr}`);

      const lastAlertKey = `LAST_ALERT_${info.sym}`;
      const lastAlertTime = parseInt(props.getProperty(lastAlertKey) || "0");
      const COOLDOWN_MS = 12 * 60 * 60 * 1000; // 同一幣種 12 小時冷卻

      if (now - lastAlertTime < COOLDOWN_MS) continue;

      // 1. 觸發補漲達成 ➔ 獲利了結換幣信號
      if (curPrice >= info.tpTarget) {
        const subject = `🎯【智能持倉換幣提醒】${info.sym} 補漲目標已達成 ($${curPrice}${pnlStr})！建議獲利了結換倉！`;
        const body = `
哈囉！您設定的補漲智能持倉出現了【獲利了結 / 換幣輪動】信號！

🔥 標的：${info.name} (${info.sym})
💰 建倉成本：$${entry.toFixed(4)}
📈 當前現價：$${curPrice.toFixed(4)}${pnlStr}
🎯 原定補漲目標位：$${info.tpTarget.toFixed(4)} (已達成突破！)
🛑 關鍵防守底線：$${info.slFloor.toFixed(4)}

==================================================
💡 建議操盤執行 SOP：
==================================================
1. 打開幣安 App ➔ 進入「智能持倉」機器人列表。
2. 找到【${info.sym} + QQQB + PAXG】機器人，點擊「終止並以市價平倉現貨」。
   - 此時該輪補漲波段利潤已全數鎖定（且一部分已自然沉澱在 QQQB/PAXG 中）。
3. 資金換倉下一位低位補漲標的：
   - 推薦接力換入：【${info.nextRotate}】！
   - 重新創建新的 3 幣機器人（例如：新幣 35% / QQQB 35% / PAXG 30%，偏差 2%）。
==================================================

祝 獲利滿滿，複利長青！
        `;
        MailApp.sendEmail(YOUR_EMAIL, subject, body);
        Logger.log(`Email 換幣提醒已發送: ${info.sym}`);
        props.setProperty(lastAlertKey, now.toString());
      }
      // 2. 觸發破位跌破強支撐 ➔ 防守止損換幣信號
      else if (curPrice <= info.slFloor) {
        const subject = `⚠️【智能持倉破位警告】${info.sym} 跌破關鍵支撐 ($${curPrice}${pnlStr})！`;
        const body = `
注意！您設定的補漲標的已跌破防守頸線！

🚨 標的：${info.name} (${info.sym})
💰 建倉成本：$${entry.toFixed(4)}
📉 當前現價：$${curPrice.toFixed(4)}${pnlStr}
🛑 關鍵防守底線：$${info.slFloor.toFixed(4)} (已跌破)
🎯 原定補漲目標位：$${info.tpTarget.toFixed(4)}

建議立即檢查盤面，評估是否手動關閉該機器人以防資金被深套，或換入更強勢的 Alpha 龍頭。
        `;
        MailApp.sendEmail(YOUR_EMAIL, subject, body);
        Logger.log(`Email 破位提醒已發送: ${info.sym}`);
        props.setProperty(lastAlertKey, now.toString());
      }
    }

    if (logArr.length > 0) {
      Logger.log(`[換幣監控巡檢正常] 監控報價：${logArr.join(" | ")}`);
    } else {
      Logger.log("⚠️ 換幣輪動監控：無法獲取即時幣價。");
    }
  } catch (err) {
    Logger.log("換幣監控全域異常: " + err.toString());
  }
}

// 支援外部遠端載入器 (Remote Dynamic Loader)
if (typeof globalThis !== 'undefined') {
  globalThis.checkZoneAndAlert = checkZoneAndAlert;
  globalThis.checkCoinRotationAlert = checkCoinRotationAlert;
}


