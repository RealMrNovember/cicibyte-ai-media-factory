# Puts ffmpeg.exe, ffprobe.exe and their license into packaging\ffmpeg for the Windows installer.
# Pinned BtbN GPL build (needs libx264 for rendering), verified by SHA-256. ffmpeg ships as a separate
# program next to the app (GPL-3.0); its source: https://github.com/FFmpeg/FFmpeg/tree/n8.1.3
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$name = "ffmpeg-n8.1.3-35-gf1acb0a266-win64-gpl-8.1"
$url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-11-15-12-40/$name.zip"
$sha = "ce121fcc8fe8097d6ab65c97ce34dc38b9e17006c31af26088ac6c91634dff28"
$cache = Join-Path $root "packaging\.cache"
$zip = Join-Path $cache "ffmpeg-gpl.zip"
$out = Join-Path $root "packaging\ffmpeg"
New-Item -ItemType Directory -Force $cache | Out-Null
if (-not (Test-Path $zip) -or (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $sha) {
  Invoke-WebRequest -Uri $url -OutFile $zip
}
if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $sha) { throw "ffmpeg download does not match the pinned checksum" }
$tmp = Join-Path $cache "unzip"
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
Expand-Archive -Path $zip -DestinationPath $tmp
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item "$tmp\$name\bin\ffmpeg.exe", "$tmp\$name\bin\ffprobe.exe" $out -Force
Copy-Item "$tmp\$name\LICENSE.txt" (Join-Path $out "LICENSE-ffmpeg.txt") -Force
Set-Content -Path (Join-Path $out "SOURCE.txt") -Encoding utf8 -Value @"
ffmpeg $name (GPL-3.0), built by https://github.com/BtbN/FFmpeg-Builds (release autobuild-2026-11-15-12-40).
Source code: https://github.com/FFmpeg/FFmpeg/tree/n8.1.3 and the build scripts at https://github.com/BtbN/FFmpeg-Builds
"@
Remove-Item -Recurse -Force $tmp
Write-Host "ffmpeg ready in $out"
