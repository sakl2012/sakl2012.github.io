$targets = @(
    @{ sym = "BTCUSDT"; name = "Bitcoin" },
    @{ sym = "SUIUSDT"; name = "Sui"; cost = 0.8552; tp = 1.050; sl = 0.940 },
    @{ sym = "LINKUSDT"; name = "Chainlink"; cost = 12.291; tp = 14.50; sl = 12.35 },
    @{ sym = "AAVEUSDT"; name = "Aave"; cost = 137.16; tp = 165.00; sl = 138.00 },
    @{ sym = "ICPUSDT"; name = "Internet Computer"; cost = 2.761; tp = 3.25; sl = 2.800 }
)

Write-Host "=========================================================="
Write-Host "      REAL-TIME ROTATION HEALTH AUDIT (BINANCE SPOT)      "
Write-Host "=========================================================="

foreach ($t in $targets) {
    $sym = $t.sym
    $url = "https://api1.binance.com/api/v3/ticker/24hr?symbol=$sym"
    $kUrl = "https://api1.binance.com/api/v3/klines?symbol=$sym&interval=4h&limit=5"
    
    try {
        $ticker = Invoke-RestMethod -Uri $url -Headers @{ "User-Agent" = "Mozilla/5.0" } -TimeoutSec 5
    } catch {
        try {
            $url2 = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=$sym"
            $bRes = Invoke-RestMethod -Uri $url2 -TimeoutSec 5
            $item = $bRes.result.list[0]
            $ticker = @{
                lastPrice = $item.lastPrice
                priceChangePercent = ([double]$item.price24hPcnt * 100).ToString()
                highPrice = $item.highPrice24h
                lowPrice = $item.lowPrice24h
                quoteVolume = $item.turnover24h
            }
        } catch {
            Write-Host "Error fetching $sym"
            continue
        }
    }
    
    $curPrice = [double]$ticker.lastPrice
    $chg = [double]$ticker.priceChangePercent
    $volM = [math]::Round(([double]$ticker.quoteVolume / 1e6), 1)
    $high = [double]$ticker.highPrice
    $low = [double]$ticker.lowPrice
    
    try {
        $klines = Invoke-RestMethod -Uri $kUrl -Headers @{ "User-Agent" = "Mozilla/5.0" } -TimeoutSec 5
        $kSummary = @()
        foreach ($k in $klines) {
            $o = [double]$k[1]
            $c = [double]$k[4]
            $kPct = [math]::Round((($c - $o) / $o) * 100, 1)
            $sign = if ($kPct -ge 0) { "+" } else { "" }
            $kSummary += "$c ($sign$kPct%)"
        }
        $kStr = $kSummary -join " -> "
    } catch {
        $kStr = "N/A"
    }

    if ($t.ContainsKey("cost")) {
        $cost = [double]$t.cost
        $tp = [double]$t.tp
        $sl = [double]$t.sl
        $pnl = [math]::Round((($curPrice - $cost) / $cost) * 100, 2)
        $pnlSign = if ($pnl -ge 0) { "+" } else { "" }
        $distTp = [math]::Round((($tp - $curPrice) / $curPrice) * 100, 1)
        $cushionSl = [math]::Round((($curPrice - $sl) / $curPrice) * 100, 1)
        
        $health = "🟢 健康持倉中"
        if ($curPrice -le $sl) {
            $health = "🔴 跌破防守底線 (警報)"
        } elseif ($cushionSl -lt 2.0) {
            $health = "🟡 貼近止損頸線 (警戒)"
        } elseif ($curPrice -ge $tp) {
            $health = "🚀 抵達止盈目標 (建議獲利了結)"
        }

        Write-Host "[$($t.name) - $sym]" -ForegroundColor Cyan
        Write-Host "  現價: `$$curPrice ($chg% 24h) | 建倉成本: `$$cost | 當前浮盈虧: $pnlSign$pnl%"
        Write-Host "  止盈目標: `$$tp (距離 +$distTp%) | 止損底線: `$$sl (緩衝空間: +$cushionSl%)"
        Write-Host "  24H 振幅: [`$$low - `$$high] | 24H 成交量: ${volM}M USDT"
        Write-Host "  近期 4H K線收盤: $kStr"
        Write-Host "  評估狀態: $health"
        Write-Host "----------------------------------------------------------"
    } else {
        Write-Host "[$($t.name) - $sym - 大盤定海神針]" -ForegroundColor Yellow
        Write-Host "  BTC 現價: `$$curPrice ($chg% 24h) | 24H 振幅: [`$$low - `$$high] | 24H 成交量: ${volM}M USDT"
        Write-Host "----------------------------------------------------------"
    }
}
