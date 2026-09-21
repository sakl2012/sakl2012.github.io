$url = "https://api1.binance.com/api/v3/klines?symbol=DOGEUSDT&interval=1d&limit=30"
$klines = Invoke-RestMethod -Uri $url -Headers @{ "User-Agent" = "Mozilla/5.0" }
Write-Host "=== DOGE Daily K-Lines ==="
foreach ($k in $klines) {
    $dt = [datetimeoffset]::FromUnixTimeMilliseconds($k[0]).LocalDateTime.ToString("yyyy-MM-dd")
    $o = [double]$k[1]
    $h = [double]$k[2]
    $l = [double]$k[3]
    $c = [double]$k[4]
    $v = [math]::Round([double]$k[7] / 1e6, 2)
    $chg = [math]::Round((($c - $o) / $o) * 100, 2)
    Write-Host "[$dt] O: $o | H: $h | L: $l | C: $c ($chg%) | Vol: ${v}M"
}
