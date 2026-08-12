param(
    [string]$CameraName = "Logi C270 HD WebCam",
    [int]$Width = 1280,
    [int]$Height = 720,
    [int]$FrameRate = 30,
    [string]$BitRate = "1200k"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$logs = Join-Path $root "logs"
$stateDirectory = Join-Path $root "state"
$stateFile = Join-Path $stateDirectory "video-processes.json"
New-Item -ItemType Directory -Force -Path $logs, $stateDirectory | Out-Null

function Find-WingetExecutable {
    param([Parameter(Mandatory)][string]$FileName)

    $command = Get-Command $FileName -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $packages = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    $match = Get-ChildItem -LiteralPath $packages -Recurse -File `
        -Filter $FileName -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $match) {
        throw "$FileName is not installed. Install the video dependencies first."
    }
    return $match.FullName
}

if (Test-Path -LiteralPath $stateFile) {
    $existing = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    $running = @($existing.MediaMtxPid, $existing.FfmpegPid) |
        Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }
    if ($running) {
        throw "Hornbill video streaming is already running."
    }
}

$ffmpeg = Find-WingetExecutable "ffmpeg.exe"
$mediamtx = Find-WingetExecutable "mediamtx.exe"
$config = Join-Path $root "mediamtx.yml"
$ffmpegLog = Join-Path $logs "ffmpeg.log"

$mediaProcess = Start-Process `
    -FilePath $mediamtx `
    -ArgumentList "`"$config`"" `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -PassThru

try {
    $deadline = (Get-Date).AddSeconds(10)
    do {
        Start-Sleep -Milliseconds 250
        $rtspReady = Test-NetConnection -ComputerName 127.0.0.1 `
            -Port 8554 -InformationLevel Quiet -WarningAction SilentlyContinue
    } while (-not $rtspReady -and (Get-Date) -lt $deadline)
    if (-not $rtspReady) {
        throw "MediaMTX did not open RTSP port 8554."
    }

    $input = "video=$CameraName"
    $arguments = @(
        "-hide_banner",
        "-loglevel", "warning",
        "-f", "dshow",
        "-video_size", "${Width}x${Height}",
        "-framerate", "$FrameRate",
        "-i", "`"$input`"",
        "-an",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-profile:v", "baseline",
        "-pix_fmt", "yuv420p",
        "-b:v", $BitRate,
        "-maxrate", $BitRate,
        "-bufsize", "2400k",
        "-g", "$($FrameRate * 2)",
        "-f", "rtsp",
        "-rtsp_transport", "tcp",
        "rtsp://127.0.0.1:8554/hornbill"
    )
    $ffmpegProcess = Start-Process `
        -FilePath $ffmpeg `
        -ArgumentList $arguments `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -RedirectStandardError $ffmpegLog `
        -PassThru

    @{
        MediaMtxPid = $mediaProcess.Id
        FfmpegPid = $ffmpegProcess.Id
        StartedAt = (Get-Date).ToString("o")
        Camera = $CameraName
    } | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8

    $streamUrl = "http://127.0.0.1:8888/hornbill/index.m3u8"
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $streamUrl `
                -TimeoutSec 2
            $hlsReady = $response.StatusCode -eq 200
        } catch {
            $hlsReady = $false
        }
    } while (-not $hlsReady -and (Get-Date) -lt $deadline)

    if (-not $hlsReady) {
        throw "The HLS stream did not become ready. Check $ffmpegLog."
    }

    Write-Output "Hornbill C270 stream is running."
    Write-Output "Local HLS URL: $streamUrl"
} catch {
    if ($ffmpegProcess) {
        Stop-Process -Id $ffmpegProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $mediaProcess.Id -Force -ErrorAction SilentlyContinue
    throw
}
