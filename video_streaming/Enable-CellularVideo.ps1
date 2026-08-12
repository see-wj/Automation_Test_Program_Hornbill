param(
    [string]$BlynkPin = "V15"
)

$ErrorActionPreference = "Stop"
$tailscale = "C:\Program Files\Tailscale\tailscale.exe"
if (-not (Test-Path -LiteralPath $tailscale)) {
    throw "Tailscale is not installed."
}

$status = & $tailscale status --json | ConvertFrom-Json
if ($status.BackendState -ne "Running" -or -not $status.Self.DNSName) {
    throw "Tailscale is not connected. Run 'tailscale up' and sign in first."
}

$localVideoUrl = "http://127.0.0.1:8888/hornbill/index.m3u8"
try {
    $localResponse = Invoke-WebRequest -UseBasicParsing `
        -Uri $localVideoUrl -TimeoutSec 5
} catch {
    throw (
        "The local webcam stream is unavailable. Run " +
        "video_streaming\Start-HornbillVideo.ps1 first. " +
        "Original error: $($_.Exception.Message)"
    )
}
if ($localResponse.StatusCode -ne 200) {
    throw "The local webcam stream returned HTTP $($localResponse.StatusCode)."
}

& $tailscale serve --bg --yes --http=8080 http://127.0.0.1:8888
if ($LASTEXITCODE -ne 0) {
    throw "Unable to configure Tailscale Serve."
}

$dnsName = $status.Self.DNSName.TrimEnd(".")
$videoUrl = "http://${dnsName}:8080/hornbill/index.m3u8"
try {
    $tailnetResponse = Invoke-WebRequest -UseBasicParsing `
        -Uri $videoUrl -TimeoutSec 10
} catch {
    throw "The Tailscale webcam URL is unavailable: $($_.Exception.Message)"
}
if ($tailnetResponse.StatusCode -ne 200) {
    throw "The Tailscale webcam URL returned HTTP $($tailnetResponse.StatusCode)."
}
$token = [Environment]::GetEnvironmentVariable("BLYNK_AUTH_TOKEN", "User")
$server = [Environment]::GetEnvironmentVariable("BLYNK_SERVER", "User")
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "BLYNK_AUTH_TOKEN is not configured."
}
if ([string]::IsNullOrWhiteSpace($server)) {
    $server = "blynk.cloud"
}
$server = ($server -replace "^https?://", "").TrimEnd("/")
$query = "token={0}&pin={1}&url={2}" -f `
    [uri]::EscapeDataString($token), `
    [uri]::EscapeDataString($BlynkPin), `
    [uri]::EscapeDataString($videoUrl)
$apiUrl = "https://$server/external/api/update/property?$query"
$response = Invoke-WebRequest -UseBasicParsing -Uri $apiUrl -TimeoutSec 10
if ($response.StatusCode -ne 200) {
    throw "Blynk rejected the video URL with HTTP $($response.StatusCode)."
}

Write-Output "Cellular video access configured."
Write-Output "Blynk video URL: $videoUrl"
Write-Output "Local and tailnet HLS checks passed."
Write-Output "Keep Tailscale connected on both this PC and the phone."
