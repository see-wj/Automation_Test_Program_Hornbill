# Hornbill Camera Streaming

This folder streams the `Logi C270 HD WebCam` to a Blynk Video Stream widget.

## Blynk Setup

Create a virtual datastream:

- Name: `Instrument Camera`
- Pin: `V15`
- Type: `String`

Add a **Video Stream** widget in the mobile dashboard and bind it to `V15`.

## Start Local Video

```powershell
powershell -ExecutionPolicy Bypass -File video_streaming\Start-HornbillVideo.ps1
```

The local HLS URL is:

```text
http://127.0.0.1:8888/hornbill/index.m3u8
```

## Enable Cellular Access

Install Tailscale on the phone and sign in to the same tailnet as this PC. Sign in
on the PC once:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" up
```

Then configure private tailnet access and update the Blynk widget URL:

```powershell
powershell -ExecutionPolicy Bypass -File video_streaming\Enable-CellularVideo.ps1
```

The stream remains private to authenticated devices in the same Tailscale network.
Blynk stores the URL but does not relay or host the video.

The enable script now verifies both the local HLS playlist and the tailnet URL
before updating Blynk. If the phone shows no video, confirm that Tailscale is
connected on the phone, then open the printed URL in the phone browser. If the
browser works, close and reopen the Blynk mobile dashboard to refresh the
Video Stream widget URL.

## Stop Video

```powershell
powershell -ExecutionPolicy Bypass -File video_streaming\Stop-HornbillVideo.ps1
```
