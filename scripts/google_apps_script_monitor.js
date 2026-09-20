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
👉 👑 核心 1 (20% 資金): BTC 65% | QQQB 25% | PAXG 10% (偏差1%)
👉 🏛️ 核心 2 (20% 資金): ETH 65% | QQQB 25% | PAXG 10% (偏差1%)
👉 🤖 核心 3 (10% 資金): TAO 65% | QQQB 25% | PAXG 10% (偏差1%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 65% | QQQB 25% | PAXG 10% (BNB, UNI, AAVE, LINK, NEAR, ONDO)`;
  }
  else if (zone === 1) {
    return `【Zone 1: 初牛修復】(防震盪過渡模式 - 均勢動態累積)
👉 👑 核心 1 (20% 資金): BTC 50% | QQQB 30% | PAXG 20% (偏差1%)
👉 🏛️ 核心 2 (20% 資金): ETH 50% | QQQB 30% | PAXG 20% (偏差1%)
👉 🤖 核心 3 (10% 資金): TAO 50% | QQQB 30% | PAXG 20% (偏差1%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 50% | QQQB 30% | PAXG 20% (BNB, UNI, AAVE, LINK, NEAR, ONDO)`;
  } 
  else if (zone === 2) {
    return `【Zone 2: 牛市巡航】(穩健主升浪模式 - 現正運行 ⭐)
👉 👑 核心 1 (20% 資金): BTC 45% | QQQB 35% | PAXG 20% (偏差1%)
👉 🏛️ 核心 2 (20% 資金): ETH 40% | QQQB 35% | PAXG 25% (偏差1%)
👉 🤖 核心 3 (10% 資金): TAO 35% | QQQB 35% | PAXG 30% (偏差1%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 35% | QQQB 35% | PAXG 30% (BNB, UNI, AAVE, LINK, NEAR, ONDO)`;
  } 
  else if (zone === 3) {
    return `【Zone 3: 過熱警戒】(高位鎖利模式 - 大幅沉澱美股與黃金)
👉 👑 核心 1 (20% 資金): BTC 30% | QQQB 35% | PAXG 35% (偏差1%)
👉 🏛️ 核心 2 (20% 資金): ETH 25% | QQQB 35% | PAXG 40% (偏差1%)
👉 🤖 核心 3 (10% 資金): TAO 20% | QQQB 40% | PAXG 40% (偏差1%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 20% | QQQB 40% | PAXG 40% (BNB, UNI, AAVE, LINK, NEAR, ONDO)`;
  } 
  else if (zone === 4) {
    return `【Zone 4: 極度貪婪/逃頂】(終極避險逃頂模式 - 物理金條封存)
👉 👑 核心 1 (20% 資金): BTC 5% | SPYB 30% | PAXG 65% (偏差1%)
👉 🏛️ 核心 2 (20% 資金): ETH 5% | SPYB 30% | PAXG 65% (偏差1%)
👉 🤖 核心 3 (10% 資金): TAO 5% | SPYB 25% | PAXG 70% (偏差1%)
👉 ⚡ 6大 Alpha 艦隊 (各 8.33% = 50%): 各幣 5% | SPYB 25% | PAXG 70% (BNB, UNI, AAVE, LINK, NEAR, ONDO)`;
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

// ==========================================================
// === 補漲智能持倉換幣 / 止盈輪動監控 (LINK, ICP, LTC, ENA) ===
// ==========================================================

function checkCoinRotationAlert() {
  try {
    const targets = {
      LINKUSDT: { sym: "LINK", name: "Chainlink", tpTarget: 14.50, slFloor: 11.00, nextRotate: "AAVE 或 NEAR" },
      ICPUSDT:  { sym: "ICP",  name: "Internet Computer", tpTarget: 3.30, slFloor: 2.45, nextRotate: "UNI 或 ONDO" },
      LTCUSDT:  { sym: "LTC",  name: "Litecoin", tpTarget: 65.00, slFloor: 52.00, nextRotate: "AAVE 或 LINK" },
      ENAUSDT:  { sym: "ENA",  name: "Ethena", tpTarget: 0.2080, slFloor: 0.1650, nextRotate: "本金撤出或投入現貨三幣持倉" }
    };

    const symbolsParam = encodeURIComponent(JSON.stringify(Object.keys(targets)));
    const url = `https://data-api.binance.vision/api/v3/ticker/price?symbols=${symbolsParam}`;
    const data = safeFetchJson(url);

    if (!data || !Array.isArray(data)) {
      Logger.log("⚠️ 換幣輪動監控：無法獲取即時幣價。");
      return;
    }

    const props = PropertiesService.getScriptProperties();
    const now = new Date().getTime();

    for (let item of data) {
      const info = targets[item.symbol];
      if (!info) continue;
      const curPrice = parseFloat(item.price);
      
      const lastAlertKey = `LAST_ALERT_${info.sym}`;
      const lastAlertTime = parseInt(props.getProperty(lastAlertKey) || "0");
      const COOLDOWN_MS = 12 * 60 * 60 * 1000; // 同一幣種 12 小時冷卻，避免洗信

      if (now - lastAlertTime < COOLDOWN_MS) continue;

      // 1. 觸發補漲達成 ➔ 獲利了結換幣信號
      if (curPrice >= info.tpTarget) {
        const subject = `🎯【智能持倉換幣提醒】${info.sym} 補漲目標已達成 ($${curPrice})！建議獲利了結換倉！`;
        const body = `
哈囉！您設定的補漲智能持倉出現了【獲利了結 / 換幣輪動】信號！

🔥 標的：${info.name} (${info.sym})
📈 當前現價：$${curPrice.toFixed(4)}
🎯 原定補漲目標位：$${info.tpTarget.toFixed(4)} (已達成突破！)

==================================================
💡 建議操盤執行 SOP：
==================================================
1. 打開幣安 App ➔ 進入「智能持倉」機器人列表。
2. 找到【${info.sym} + QQQB + PAXG】機器人，點擊「終止並以市價平倉現貨」。
   - 此時該輪補漲波段利潤已全數鎖定（且一部分已自然沉澱在 QQQB/PAXG 中）。
3. 資金換倉下一位低位補漲標的：
   - 推薦接力換入：【${info.nextRotate}】！
   - 重新創建新的 3 幣機器人（例如：新幣 35% / QQQB 35% / PAXG 30%，偏差 1%）。
==================================================

祝 獲利滿滿，複利長青！
        `;
        MailApp.sendEmail(YOUR_EMAIL, subject, body);
        Logger.log(`Email 換幣提醒已發送: ${info.sym}`);
        props.setProperty(lastAlertKey, now.toString());
      }
      // 2. 觸發破位跌破強支撐 ➔ 防守止損換幣信號
      else if (curPrice <= info.slFloor) {
        const subject = `⚠️【智能持倉破位警告】${info.sym} 跌破關鍵支撐 ($${curPrice})！`;
        const body = `
注意！您設定的補漲標的已跌破防守頸線！

🚨 標的：${info.name} (${info.sym})
📉 當前現價：$${curPrice.toFixed(4)}
🛑 關鍵防守底線：$${info.slFloor.toFixed(4)} (已跌破)

建議立即檢查盤面，評估是否手動關閉該機器人以防資金被深套，或換入更強勢的 Alpha 龍頭。
        `;
        MailApp.sendEmail(YOUR_EMAIL, subject, body);
        Logger.log(`Email 破位提醒已發送: ${info.sym}`);
        props.setProperty(lastAlertKey, now.toString());
      }
    }
  } catch (err) {
    Logger.log("換幣監控全域異常: " + err.toString());
  }
}
