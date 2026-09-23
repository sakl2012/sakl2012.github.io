/**
 * Triad 三元策略 (純現貨三幣 ＋ 雙壁避險全自動化版) - Google Apps Script 自動監控與 Email 警報
 * 主力：Binance Vision (免 451 封鎖) | 備援：OKX / Bybit / Gate.io / KuCoin / Coinbase | 具備防崩潰與自動切換機制
 * 最新架構：Triad 三元全天候狀態機 (Zone 0 深熊底 ~ Zone 4 逃頂鎖利 ~ Zone 5 熊市主跌防禦)
 * 資產配置：三大核心 50% (BTC 20% / ETH 20% / TAO 10%) ＋ 6 大菁英 Alpha 50% (各 8.33%)
 * 防禦機制：純現貨雙壁架構 (QQQB 35% + PAXG 60%~65%)，Zone 4 Alpha 率先清零、Zone 5 核心清零
 */

const YOUR_EMAIL = "sakl19930909@gmail.com"; // 您的信箱

// ==========================================
// === 統一主入口：一觸即發，全盤巡檢 ===
// ==========================================
// === 統一主入口：宏觀 6-Zone 狀態機巡檢 ===
// ==========================================
function main() {
  try {
    checkZoneAndAlert();
  } catch (e) {
    Logger.log("checkZoneAndAlert 異常: " + e);
  }
}

function runAllMonitors() {
  main();
}

function checkZoneAndAlert() {
  try {
    // 1. 取得市場資料（自動走 主力 -> 備援 機制）
    const currentPrice = getCurrentPrice();
    const ma200 = getYesterdayMA200();
    const sma72Price = get72hSMA();
    
    if (!ma200 || !currentPrice || !sma72Price) {
      Logger.log("⚠️ 所有交易所 API 均未能成功回傳 BTC 宏觀數據，本輪宏觀巡檢略過。");
      return;
    }
    
    // 2. 計算比值
    const ratio = currentPrice / ma200;
    const ratioSma72 = sma72Price / ma200; 
    
    // 3. 讀取之前的 Zone 與週期狀態 (預設為 2)
    const props = PropertiesService.getScriptProperties();
    let currentZone = parseInt(props.getProperty("CURRENT_ZONE"));
    if (isNaN(currentZone)) currentZone = 2;
    let newZone = currentZone;

    let hasReachedZone4 = props.getProperty("HAS_REACHED_ZONE4") === "true";
    let cyclePeakPrice = parseFloat(props.getProperty("CYCLE_PEAK_PRICE") || "0");
    if (isNaN(cyclePeakPrice)) cyclePeakPrice = 0;
    
    // 4. 狀態機邏輯 (6-Zone 閉環單向狀態機：嚴禁 Zone 4 倒退回 Zone 3/2/1)
    if (hasReachedZone4) {
      // 若價格創本輪週期新高，動態刷新週期大頂
      if (currentPrice > cyclePeakPrice) {
        cyclePeakPrice = currentPrice;
        props.setProperty("CYCLE_PEAK_PRICE", cyclePeakPrice.toString());
      }

      // 判斷是否跌穿深熊大底 (< 0.80)
      if (ratio < 0.80) {
        // 熊市跌透到底，正式交棒給 Zone 0 深熊大底，並重置本輪週期標記！
        hasReachedZone4 = false;
        cyclePeakPrice = 0;
        newZone = 0;
        props.setProperty("HAS_REACHED_ZONE4", "false");
        props.setProperty("CYCLE_PEAK_PRICE", "0");
      } 
      // 判斷是否自大頂回撤 ≥ 20%（技術性轉熊）或已處於 Zone 5
      else if ((cyclePeakPrice > 0 && currentPrice <= cyclePeakPrice * 0.80) || currentZone === 5) {
        newZone = 5; // 進入或死鎖在 Zone 5 熊市主跌防禦！
      } 
      // 否則（回撤未達 20%）：死鎖在 Zone 4！絕對禁止退回 Zone 3、Zone 2 或 Zone 1！
      else {
        newZone = 4;
      }
    } 
    // 尚未觸發過 Zone 4 時的正常牛市爬坡階梯 (Zone 0 -> 1 -> 2 -> 3 -> 4)
    else {
      if (ratio < 0.80) newZone = 0;
      else if (ratio < 1.00) newZone = 1;
      else if (ratio < 1.25) newZone = 2;
      else if (ratio < 1.40) newZone = 3;
      else {
        // 首次突破 1.40，正式進入 Zone 4 逃頂期！鎖定狀態機！
        hasReachedZone4 = true;
        cyclePeakPrice = currentPrice;
        newZone = 4;
        props.setProperty("HAS_REACHED_ZONE4", "true");
        props.setProperty("CYCLE_PEAK_PRICE", cyclePeakPrice.toString());
      }
    }
    
    Logger.log(`目前價格: ${currentPrice.toFixed(2)}, MA200: ${ma200.toFixed(2)}`);
    Logger.log(`當前比值: ${ratio.toFixed(3)}, 72h SMA比值: ${ratioSma72.toFixed(3)}`);
    Logger.log(`週期標記: hasReachedZone4=${hasReachedZone4}, cyclePeakPrice=${cyclePeakPrice}`);
    Logger.log(`原 Zone: ${currentZone} -> 新 Zone: ${newZone}`);
    
    // 5. 判斷是否切換並發送 Email
    if (newZone !== currentZone) {
      const allocationText = getAllocationConfig(newZone);
      const zoneNames = {
        0: "深熊大底 (頂級抄底模式 - 65%現貨/25%QQQB/10%PAXG)",
        1: "初牛修復 (均勢動態積累 - 50%現貨/30%QQQB/20%PAXG)",
        2: "牛市巡航 (穩健主升浪 - 45%現貨/35%QQQB/20%PAXG)",
        3: "過熱警戒 (階梯獲利鎖利 - 30%現貨/35%QQQB/35%PAXG)",
        4: "極度貪婪/逃頂鎖利 (Alpha率先清零，核心留5%底倉，QQQB 35%＋PAXG 60%~65%)",
        5: "熊市確認/主跌防禦 (全盤現貨100%清零，純現貨雙壁終極防禦)"
      };
      
      const subject = `🚨 Triad 三元策略狀態切換：Zone ${newZone} (${zoneNames[newZone]})`;
      const body = `
自動監控機器人發現市場狀態改變！

🔹 新狀態：Zone ${newZone} (${zoneNames[newZone]})
🔹 舊狀態：Zone ${currentZone} (${zoneNames[currentZone]})

📊 當前市場數據：
- BTC 價格：$${currentPrice.toFixed(2)}
- 1D MA200：$${ma200.toFixed(2)}
- 即時乖離比值：${ratio.toFixed(3)}
- 72小時 SMA 乖離：${ratioSma72.toFixed(3)}
- 週期大頂標記：${cyclePeakPrice > 0 ? '$' + cyclePeakPrice.toFixed(2) : '尚未觸發'}

==================================================
🎯 建議全盤 9 大機器人最新配置目標 (三大核心 50% + 6大Alpha 50%)：
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
    return `【Zone 4: 極度貪婪/逃頂鎖利】(逃頂鎖利模式 - Alpha 率先清零，核心留 5% 底倉防踏空)
👉 👑 核心 1 (20% 資金): BTC 5% | QQQB 35% | PAXG 60% (偏差2%，核心留 5% 底倉防踏空)
👉 🏛️ 核心 2 (20% 資金): ETH 5% | QQQB 35% | PAXG 60% (偏差2%)
👉 🤖 核心 3 (10% 資金): TAO 5% | QQQB 35% | PAXG 60% (偏差2%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 0% | QQQB 35% | PAXG 65% (山寨率先 100% 清零出清！轉入純現貨雙壁鎖利)
📌【特別紀律】：此階段已觸發單向逃頂死鎖，絕不因短期回踩退回 Zone 3！若自大頂回撤 ≥20% 則直接進入 Zone 5 熊市防禦。`;
  } 
  else if (zone === 5) {
    return `【Zone 5: 熊市確認/主跌防禦】(全盤清零雙壁避險模式 - 大頂回撤 ≥20% 轉熊)
👉 👑 核心 1 (20% 資金): BTC 0% | QQQB 35% | PAXG 65% (核心最後 5% 正式清零)
👉 🏛️ 核心 2 (20% 資金): ETH 0% | QQQB 35% | PAXG 65% (全額純現貨雙壁)
👉 🤖 核心 3 (10% 資金): TAO 0% | QQQB 35% | PAXG 65% (全額純現貨雙壁)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 0% | QQQB 35% | PAXG 65% (全盤 9 大組合全面現貨清零，純現貨雙壁終極防禦)
📌【特別紀律】：全盤 100% 現貨清零，由 QQQB 35% ＋ PAXG 65% 純現貨雙壁避險，死鎖直至跌透至 Zone 0 深熊抄底線 (BTC/MA200 < 0.80)！`;
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
// === 個幣微觀幣價追蹤退役說明 (全面轉向 Macro 6-Zone 宏觀狀態機) ===
// ==========================================================
// 📌 核心架構轉型：
// 1. 個幣微觀雜訊過濾：AAVE、ONDO、NEAR 等核心 Alpha 持倉均在幣安 App 內設定了
//    「35% 幣 + 35% QQQB + 30% PAXG」之智能持倉機器人，
//    並以 2% 比例閾值 7x24 全自動執行夏農再平衡（高拋低吸鎖定利潤至 QQQB/PAXG），
//    完全不需人工盯盤或微觀價格報警，徹底告別微觀情緒內耗。
// 2. 聚焦 Macro 6-Zone 宏觀狀態機：唯一決定大週期倉位勝負的是 BTC/MA200 比值之 Zone 切換（Zone 0 ~ Zone 5）。
//    只有當 BTC 突破 Zone 3 ($88,400+) 或觸發 Zone 4 逃頂 ($99,100+) 時才需調整整體配置。
// 3. 保留相容性空函式：維持舊版 GAS 觸發器（Triggers）相容性，防止觸發 ReferenceError。

function checkCoinRotationAlert() {
  Logger.log("ℹ️ 個幣微觀幣價追蹤已退役。全面聚焦 Macro 6-Zone 宏觀狀態機監控。");
}

function checkCandidateRadarAlert(priceMap) {
  Logger.log("ℹ️ 候補雷達已退役。全面聚焦 Macro 6-Zone 宏觀狀態機監控。");
}

function checkDogeRetestAlert(dogePrice) {
  Logger.log("ℹ️ DOGE 雷達已退役。全面聚焦 Macro 6-Zone 宏觀狀態機監控。");
}

// 支援外部遠端載入器 (Remote Dynamic Loader)
if (typeof globalThis !== 'undefined') {
  globalThis.main = main;
  globalThis.runAllMonitors = runAllMonitors;
  globalThis.autoMonitor = main;
  globalThis.checkZoneAndAlert = checkZoneAndAlert;
  globalThis.checkCoinRotationAlert = checkCoinRotationAlert;
  globalThis.checkCandidateRadarAlert = checkCandidateRadarAlert;
  globalThis.checkDogeRetestAlert = checkDogeRetestAlert;
}


