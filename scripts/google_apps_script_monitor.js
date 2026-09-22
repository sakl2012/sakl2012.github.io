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
function main() {
  try {
    checkZoneAndAlert();
  } catch (e) {
    Logger.log("checkZoneAndAlert 異常: " + e);
  }
  try {
    checkCoinRotationAlert();
  } catch (e) {
    Logger.log("checkCoinRotationAlert 異常: " + e);
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
      Logger.log("⚠️ 所有交易所 API 均未能成功回傳 BTC 宏觀數據，本輪宏觀略過，但繼續執行持倉與候補雷達巡檢。");
      checkCoinRotationAlert();
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

    // 強制串聯調用現貨輪動與候補突破雷達（確保單一雲端觸發器全盤覆蓋）
    try {
      checkCoinRotationAlert();
    } catch (e) {
      Logger.log("串聯調用 checkCoinRotationAlert 異常: " + e.toString());
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
// 3. 四大標的最新日線/4小時結構與嚴格止損點位依據 (2026-09 最新 K 線突破防禦驗證)：
//    • 嚴格止損核心精神：鎖定右側主升浪起漲頸線（S/R Flip），絕不承受深幅回撤！
//      一旦跌破起漲點即判定為假突破（Bull Trap），果斷離場以維持極高盈虧比（R:R > 3.6:1）。
//
//    • ONDO (成本 $0.4530):
//      - 結構：放量突破 $0.45 頸線，受惠 DTCC 接入全美 85% 共同基金清算之頂級 RWA 敘事。
//      - tpTarget: $0.550 (+21.4%) -> 2026 前高密集阻力平台。
//      - slFloor:  $0.435 (-3.97%) -> 4H 突破起漲頸線（盈虧比 5.39:1，假突破證偽底線）。
//    • LINK (成本 $12.291):
//      - 結構：4H 底部階梯式墊高，站穩 $12.50 平台衝擊 $13.00 整數大關。
//      - tpTarget: $14.50 (+18.0%) -> 週線級別大箱體天花板與阻力密集區。
//      - slFloor:  $12.35 (+0.5%)   -> 移動保本保護止損（Break-Even），覆蓋手續費鎖死零本金風險！
//    • AAVE (成本 $137.16):
//      - 結構：飛哥 9/21 觀察名單第 1 名「代幣經濟學 3.0」爆拉，起漲腳在 $138.59。
//      - tpTarget: $165.00 (+20.3%) -> 2026 日線密集阻力天花板。
//      - slFloor:  $138.00 (+0.6%)  -> 移動保本保護止損（Break-Even），錨定起漲腳徹底保本！
//    • APT (換倉成本 $0.7830，替換原 ICP):
//      - 結構：Aptos 主網 9/18 推出 Confidential APT (ZK 隱私交易)，9/12 代幣解鎖拋壓消化完畢，4H 沿均線上攻。
//      - tpTarget: $0.950 (+21.3%) -> 日線大箱體天花板與週線強阻力平台。
//      - slFloor:  $0.745 (-4.85%) -> 4H 突破平台起漲頸線（防守底線，假突破證偽）。
//    • DOGE (回踩企穩與放量突破重點監控標的):
//      - 結構：9/21 巨量 2.46 億顆大陽線拉升 16.5%，突破 $0.0950 頸線衝擊 $0.1019 小前高阻力。
//      - 回踩支撐區：$0.0950 ~ $0.0975 (頂底轉換支撐帶，企穩確認買點)。
//      - 企穩確認線：$0.0980 (回踩測試後反彈站上，確認主力護盤成功)。
//      - 突破確認線：$0.1025 (若不深踩直接放量突破小前高，確認主升浪加速)。
//      - 證偽底線 (slFloor)：$0.0925 (9/21 放量大陽線實體起漲腳，跌破即假突破離場)。
//      - tpTarget: $0.1200 (+25.0%，盈虧比 R:R = 6.86:1 >= 3:1)。
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
      RENDERUSDT: { sym: "RENDER", name: "Render",           okxId: "RENDER-USDT", entryPrice: 1.816,  tpTarget: 2.350, slFloor: 1.720, nextRotate: "NEAR 或 FET" },
      LINKUSDT:   { sym: "LINK",   name: "Chainlink",         okxId: "LINK-USDT",   entryPrice: 12.291, tpTarget: 14.50, slFloor: 12.35, nextRotate: "NEAR 或 DOGE" },
      AAVEUSDT:   { sym: "AAVE",   name: "Aave",              okxId: "AAVE-USDT",   entryPrice: 137.16, tpTarget: 165.00, slFloor: 138.00, nextRotate: "FET 或 TAO" },
      SUIUSDT:    { sym: "SUI",    name: "Sui Network",       okxId: "SUI-USDT",    entryPrice: 1.0195, tpTarget: 1.450, slFloor: 0.965, nextRotate: "NEAR 或 DOGE" }
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
      // 2. 觸發跌破防守底線 ➔ 移動利潤保護 / 止損換幣信號
      else if (curPrice <= info.slFloor) {
        const isProfitLock = info.slFloor > entry;
        const subject = isProfitLock
          ? `🛡️【智能持倉移動止損觸發】${info.sym} 回踩觸及利潤保護底 ($${curPrice}${pnlStr})！`
          : `⚠️【智能持倉破位警告】${info.sym} 跌破關鍵支撐 ($${curPrice}${pnlStr})！`;
        const body = `
${isProfitLock ? '提醒您！您設定的標的觸及了【移動利潤保護底線（Trailing Stop）】！此時依然保持獲利！' : '注意！您設定的補漲標的已跌破防守頸線！'}

🚨 標的：${info.name} (${info.sym})
💰 建倉成本：$${entry.toFixed(4)}
📉 當前現價：$${curPrice.toFixed(4)}${pnlStr}
🛑 移動防守底線：$${info.slFloor.toFixed(4)} (已觸及)
🎯 原定補漲目標位：$${info.tpTarget.toFixed(4)}

==================================================
💡 建議操盤執行 SOP：
==================================================
${isProfitLock 
  ? `1. 打開幣安 App ➔ 進入「智能持倉」機器人列表。
2. 找到【${info.sym} + QQQB + PAXG】機器人，點擊「終止並以市價平倉現貨」。
   - 此時波段獲利已成功落袋保護（+10% 左右）。
3. 資金換入低位蓄勢標的：
   - 推薦接力換入：【${info.nextRotate}】！` 
  : `建議立即檢查盤面，評估是否手動關閉該機器人以防資金被深套，或換入更強勢的 Alpha 龍頭。`}
==================================================
        `;
        MailApp.sendEmail(YOUR_EMAIL, subject, body);
        Logger.log(`Email 防守提醒已發送: ${info.sym}`);
        props.setProperty(lastAlertKey, now.toString());
      }
    }

    if (logArr.length > 0) {
      Logger.log(`[換幣監控巡檢正常] 監控報價：${logArr.join(" | ")}`);
    } else {
      Logger.log("⚠️ 換幣輪動監控：無法獲取即時幣價。");
    }

    // 連帶自動執行候補幣 (DOGE, UNI, NEAR) 突破與回踩雷達即時審計
    checkCandidateRadarAlert(priceMap);

  } catch (err) {
    Logger.log("換幣監控全域異常: " + err.toString());
  }
}

// ==========================================================
// === 候補幣突破與回踩雷達監控模組 (Candidate Radar: DOGE / UNI / NEAR) ===
// ==========================================================
// 📌【候補名單量化位階推導 (2026-09 4H/1D 實盤審計)】
// 1. DOGE: 阻力突破線 $0.1025 / 目標 $0.1180 | 回踩支撐 $0.0950~$0.0975 / 企穩確認 $0.0980 | 證偽底 $0.0925
// 2. UNI:  阻力突破線 $9.50 / 目標 $11.50   | 回踩支撐 $8.60~$8.90 / 企穩確認 $9.00   | 證偽底 $8.55 (4H頸線)
// 3. NEAR: 阻力突破線 $4.60 / 目標 $5.80    | 回踩支撐 $4.15~$4.25 / 企穩確認 $4.30   | 證偽底 $3.95 (4H結構底)
// ----------------------------------------------------------

function checkCandidateRadarAlert(priceMap) {
  try {
    const props = PropertiesService.getScriptProperties();
    const now = new Date().getTime();

    const candidates = {
      DOGE: {
        sym: "DOGE",
        name: "Dogecoin",
        okxId: "DOGE-USDT",
        resistanceCeiling: 0.1025,
        tpTarget: 0.1180,
        retestHigh: 0.0975,
        retestLow: 0.0950,
        reboundConfirm: 0.0980,
        invalidationFloor: 0.0925,
        setupDesc: "頂底轉換回踩支撐或放量衝破 0.1025 前高加速",
        slDesc: "9/21 放量大陽線起漲腳",
        rrRatio: "6.8:1"
      },
      FET: {
        sym: "FET",
        name: "Artificial Superintelligence",
        okxId: "FET-USDT",
        resistanceCeiling: 0.220,
        tpTarget: 0.280,
        retestHigh: 0.200,
        retestLow: 0.190,
        reboundConfirm: 0.205,
        invalidationFloor: 0.180,
        setupDesc: "AI 聯盟日線大底放量突破回踩確認",
        slDesc: "日線突破平台支撐底 (-5.3%)",
        rrRatio: "5.2:1"
      },
      NEAR: {
        sym: "NEAR",
        name: "NEAR Protocol",
        okxId: "NEAR-USDT",
        resistanceCeiling: 4.60,
        tpTarget: 5.80,
        retestHigh: 4.25,
        retestLow: 4.15,
        reboundConfirm: 4.30,
        invalidationFloor: 3.95,
        setupDesc: "AI 代理 + 鏈抽象 + 量子安全頂級 L1",
        slDesc: "4H 結構支撐起漲腳 (-5.5%)",
        rrRatio: "5.8:1"
      }
    };

    for (let cKey in candidates) {
      const info = candidates[cKey];
      let curPrice = priceMap ? priceMap[info.okxId] : null;
      if (!curPrice) {
        curPrice = getSingleTokenPrice(info.sym, info.okxId);
      }
      if (!curPrice) {
        Logger.log(`⚠️ ${info.sym} 雷達監控：無法獲取即時幣價。`);
        continue;
      }

      const stateKey = `${info.sym}_RADAR_STATE`;
      const minPriceKey = `${info.sym}_MIN_RETEST_PRICE`;
      const lastAlertKey = `LAST_ALERT_${info.sym}_RADAR`;
      
      let state = props.getProperty(stateKey) || "MONITORING";
      let minRetestPrice = parseFloat(props.getProperty(minPriceKey) || "999999");
      const lastAlertTime = parseInt(props.getProperty(lastAlertKey) || "0");
      const COOLDOWN_MS = 4 * 60 * 60 * 1000; // 4 小時提醒冷卻

      let shouldAlert = false;
      let subject = "";
      let body = "";

      // 1. 假突破證偽 / 破位止損 (跌破起漲腳 invalidationFloor)
      if (curPrice <= info.invalidationFloor) {
        if (state !== "FAILED_BREAKDOWN" && (now - lastAlertTime > COOLDOWN_MS || state !== "FAILED_BREAKDOWN")) {
          state = "FAILED_BREAKDOWN";
          shouldAlert = true;
          subject = `⚠️【${info.sym} 支撐破位警報】跌破防守頸線 $${curPrice.toFixed(4)}！假突破證偽！`;
          body = `
注意！候補標的 ${info.name} (${info.sym}) 跌破了關鍵防守底線 $${info.invalidationFloor.toFixed(4)}！

📉 當前現價：$${curPrice.toFixed(4)}
🛑 證偽底線：$${info.invalidationFloor.toFixed(4)} (已跌破)
📌 技術判定：${info.slDesc} 失守，判定為「假突破（Bull Trap）」。

==================================================
💡 嚴格風控 SOP：
==================================================
1. 嚴禁在此時左側抄底接飛刀！
2. 保持現有持倉或觀望，絕不盲目換入 ${info.sym}。
3. 等待市場重新在下方尋求大底支撐。
==================================================
          `;
        }
      }
      // 2. 價格進入回踩支撐觀察區 (retestLow ~ retestHigh)
      else if (curPrice >= info.retestLow && curPrice <= info.retestHigh) {
        if (curPrice < minRetestPrice) {
          minRetestPrice = curPrice;
          props.setProperty(minPriceKey, minRetestPrice.toString());
        }
        if (state !== "IN_RETEST_ZONE" && (now - lastAlertTime > COOLDOWN_MS || state === "MONITORING")) {
          state = "IN_RETEST_ZONE";
          shouldAlert = true;
          subject = `🎯【${info.sym} 回踩關鍵支撐區】現價 $${curPrice.toFixed(4)} 抵達買點觀察帶 ($${info.retestLow.toFixed(4)}~$${info.retestHigh.toFixed(4)})！`;
          body = `
${info.name} (${info.sym}) 價格已回踩至頂底轉換關鍵支撐帶！

📍 當前現價：$${curPrice.toFixed(4)}
🛡️ 回踩支撐區間：$${info.retestLow.toFixed(4)} ~ $${info.retestHigh.toFixed(4)}
🛑 嚴格止損底線：$${info.invalidationFloor.toFixed(4)} (單筆試錯風險控制在 -5% 以內)
🎯 波段止盈目標：$${info.tpTarget.toFixed(4)} (${info.tpDesc}，盈虧比 R:R = ${info.rrRatio})
🔥 核心敘事定位：${info.setupDesc}

==================================================
💡 操盤 SOP：
==================================================
1. 密切觀察此區間是否出現縮量拒跌、或 1H/4H 長下影線。
2. 一旦反彈重新站上 $${info.reboundConfirm.toFixed(4)}，系統將立即發送「回踩成功」換倉確認信！
==================================================
          `;
        }
      }
      // 3. 回踩成功確認！(曾進入回踩區測試後，強勢反彈站上 reboundConfirm)
      else if (state === "IN_RETEST_ZONE" && curPrice >= info.reboundConfirm) {
        state = "RETEST_SUCCESS";
        shouldAlert = true;
        subject = `🚀【${info.sym} 回踩企穩確認】支撐驗證有效，反彈站上 $${curPrice.toFixed(4)}！右側買點確立！`;
        body = `
賀報！${info.name} (${info.sym}) 頂底轉換回踩測試圓滿成功，右側買點確立！

📈 當前現價：$${curPrice.toFixed(4)}
🛡️ 驗證回踩低點：$${minRetestPrice < 900000 ? minRetestPrice.toFixed(4) : info.retestLow.toFixed(4)} (完美守住支撐)
🛑 嚴格止損底線：$${info.invalidationFloor.toFixed(4)} (鎖定起漲腳)
🎯 波段止盈目標：$${info.tpTarget.toFixed(4)} (${info.tpDesc})
⚖️ 盈虧比審計：R:R = ${info.rrRatio} (符合頂級不對稱風控要求)

==================================================
💡 操盤執行 SOP：
==================================================
1. ${info.sym} 右側企穩信號正式確立！
2. 若您計劃將輪動組合換入 ${info.sym}：
   - 可在幣安 App 創建【${info.sym} 35% + QQQB 35% + PAXG 30%】智能持倉機器人；
   - 止損點堅決設於 $${info.invalidationFloor.toFixed(4)}，嚴禁凹單。
==================================================
        `;
      }
      // 4. 強勢放量直破關鍵阻力 (resistanceCeiling)
      else if (curPrice >= info.resistanceCeiling) {
        if (now - lastAlertTime > COOLDOWN_MS || state !== "BREAKOUT_DIRECT") {
          state = "BREAKOUT_DIRECT";
          shouldAlert = true;
          subject = `🔥【${info.sym} 放量突破關鍵阻力】現價 $${curPrice.toFixed(4)} 衝破阻力！主升浪加速！`;
          body = `
${info.name} (${info.sym}) 未做深度回踩，直接放量強勢貫穿阻力位！

🚀 當前現價：$${curPrice.toFixed(4)}
⚡ 突破關鍵阻力：$${info.resistanceCeiling.toFixed(4)}
🎯 波段目標位：$${info.tpTarget.toFixed(4)} (${info.tpDesc})
🛑 追高移動防守：$${info.retestHigh.toFixed(4)} (突破阻力位轉化為即時防守底線)
🔥 核心驅動：${info.setupDesc}

==================================================
💡 操盤 SOP：
==================================================
1. 多頭動能極強，直接開啟主升浪加速。
2. 若追單建倉，移動止損不可低於 $${info.retestHigh.toFixed(4)}，嚴防高位假突破。
==================================================
          `;
        }
      }

      props.setProperty(stateKey, state);

      if (shouldAlert) {
        MailApp.sendEmail(YOUR_EMAIL, subject, body);
        props.setProperty(lastAlertKey, now.toString());
        Logger.log(`[${info.sym} 警報] 已發送 Email: ${subject}`);
      } else {
        Logger.log(`[${info.sym} 巡檢正常] 現價: $${curPrice.toFixed(4)} | 狀態機: ${state} (支撐 $${info.retestLow.toFixed(4)}~$${info.retestHigh.toFixed(4)}, 突破 $${info.resistanceCeiling.toFixed(4)}, 證偽底 $${info.invalidationFloor.toFixed(4)})`);
      }
    }
  } catch (err) {
    Logger.log("候補幣雷達監控異常: " + err.toString());
  }
}

// 保持相容性：舊版 checkDogeRetestAlert 呼叫
function checkDogeRetestAlert(dogePrice) {
  const map = {};
  if (dogePrice) map["DOGE-USDT"] = dogePrice;
  checkCandidateRadarAlert(map);
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


