$ErrorActionPreference = "Stop"
$stateFile = Join-Path $PSScriptRoot "state\video-processes.json"

if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Output "Hornbill video streaming is not running."
    exit 0
}

$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
foreach ($processId in @($state.FfmpegPid, $state.MediaMtxPid)) {
    if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
        Stop-Process -Id $processId -Force
    }
}

Remove-Item -LiteralPath $stateFile -Force
Write-Output "Hornbill video streaming stopped."
