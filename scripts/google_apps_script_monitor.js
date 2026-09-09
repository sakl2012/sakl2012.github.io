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
// === 取得對應 Zone 的持倉配置文字 (ABC 五星全賽道輪動版) ===
// ==========================================================
function getAllocationConfig(zone) {
  if (zone === 0) {
    return `【Zone 0: 深熊大底】(極限抄底進攻模式 - 釋放黃金儲備)
👉 🅰️ 持倉 A (Core 20% | 偏差5%): BTC 80% | PAXG 20%
👉 🅱️ 持倉 B (Sat 55% | 偏差5%): SOL 30% | TAO 35% | PAXG 35%
👉 🅲 持倉 C (Alpha 25% | 偏差10%): AAVE 15% | UNI 15% | SUI 25% | LINK 15% | NEAR 15% | PAXG 15%`;
  }
  else if (zone === 1) {
    return `【Zone 1: 初熊防禦】(防刀緩衝期 - 提高黃金避險不接飛刀)
👉 🅰️ 持倉 A (Core 20% | 偏差5%): BTC 50% | PAXG 50%
👉 🅱️ 持倉 B (Sat 55% | 偏差5%): SOL 18% | TAO 17% | PAXG 65%
👉 🅲 持倉 C (Alpha 25% | 偏差10%): AAVE 10% | UNI 10% | SUI 15% | LINK 15% | NEAR 10% | PAXG 40%`;
  } 
  else if (zone === 2) {
    return `【Zone 2: 牛市巡航】(穩健起飛模式 - 現正運行 ⭐)
👉 🅰️ 持倉 A (Core 20% | 偏差5%): BTC 58% | PAXG 42%
👉 🅱️ 持倉 B (Sat 55% | 偏差5%): SOL 25% | TAO 15% | PAXG 60%
👉 🅲 持倉 C (Alpha 25% | 偏差10%): AAVE 15% | UNI 15% | SUI 15% | LINK 15% | NEAR 10% | PAXG 30%`;
  } 
  else if (zone === 3) {
    return `【Zone 3: 過熱警戒】(分批鎖利換金模式)
👉 🅰️ 持倉 A (Core 20% | 偏差5%): BTC 37% | PAXG 63%
👉 🅱️ 持倉 B (Sat 55% | 偏差5%): SOL 18% | TAO 19% | PAXG 63%
👉 🅲 持倉 C (Alpha 25% | 偏差10%): PAXG 45% | AAVE 10% | UNI 10% | SUI 10% | LINK 15% | NEAR 10%`;
  } 
  else if (zone === 4) {
    return `【Zone 4: 極度貪婪/逃頂】(全面避險保命模式)
👉 🅰️ 持倉 A (Core 20% | 偏差5%): BTC 5% | PAXG 95%
👉 🅱️ 持倉 B (Sat 55% | 偏差5%): SOL 7% | TAO 13% | PAXG 80%
👉 🅲 持倉 C (Alpha 25% | 偏差10%): PAXG 75% | AAVE 5% | UNI 5% | LINK 5% | SUI 5% | NEAR 5%`;
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
      headers: { "User-Agent": "Mozilla/5.0" }
    });
    
    const statusCode = res.getResponseCode();
    if (statusCode === 200) {
      return JSON.parse(res.getContentText());
    } else {
      Logger.log(`API [${url.split('?')[0]}] 回傳異常 HTTP ${statusCode}`);
      return null;
    }
  } catch (e) {
    Logger.log(`網路連線失敗 [${url.split('?')[0]}]: ${e.toString()}`);
    return null;
  }
}

// ==========================================
// === 取得即時價格 (Binance Vision -> OKX -> Bybit) ===
// ==========================================

function getCurrentPrice() {
  const binanceUrl = "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT";
  const bData = safeFetchJson(binanceUrl);
  if (bData && bData.price) return parseFloat(bData.price);

  Logger.log("⚠️ 幣安即時價格獲取失敗，切換至備援源 (OKX)...");
  const okxUrl = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT";
  const oData = safeFetchJson(okxUrl);
  if (oData && oData.data && oData.data.length > 0) return parseFloat(oData.data[0].last);

  Logger.log("⚠️ OKX 獲取失敗，切換至備援源 (Bybit)...");
  const bybitUrl = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT";
  const bybitData = safeFetchJson(bybitUrl);
  if (bybitData && bybitData.result && bybitData.result.list && bybitData.result.list.length > 0) return parseFloat(bybitData.result.list[0].lastPrice);

  return null;
}

// ==========================================
// === 取得 200 日線 MA (Binance Vision -> OKX) ===
// ==========================================

function getYesterdayMA200() {
  const binanceUrl = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=201";
  const bData = safeFetchJson(binanceUrl);
  if (bData && Array.isArray(bData) && bData.length >= 201) {
    let sum = 0;
    for (let i = 0; i < 200; i++) sum += parseFloat(bData[i][4]);
    return sum / 200;
  }

  Logger.log("⚠️ 幣安 MA200 獲取失敗，切換至備援源 (OKX)...");
  const okxUrl = "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1Dutc&limit=201";
  const oData = safeFetchJson(okxUrl);
  if (oData && oData.data && oData.data.length >= 201) {
    let sum = 0;
    for (let i = 1; i <= 200; i++) sum += parseFloat(oData.data[i][4]);
    return sum / 200;
  }

  return null;
}

// ==========================================
// === 取得 72 小時 SMA (Binance Vision -> OKX) ===
// ==========================================

function get72hSMA() {
  const binanceUrl = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=72";
  const bData = safeFetchJson(binanceUrl);
  if (bData && Array.isArray(bData) && bData.length >= 72) {
    let sum = 0;
    for (let i = 0; i < 72; i++) sum += parseFloat(bData[i][4]);
    return sum / 72;
  }

  Logger.log("⚠️ 幣安 72h SMA 獲取失敗，切換至備援源 (OKX)...");
  const okxUrl = "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=72";
  const oData = safeFetchJson(okxUrl);
  if (oData && oData.data && oData.data.length >= 72) {
    let sum = 0;
    for (let i = 0; i < 72; i++) sum += parseFloat(oData.data[i][4]);
    return sum / 72;
  }

  return null;
}
