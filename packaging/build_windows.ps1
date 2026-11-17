# Builds dist\CiciByteMediaFactory-Setup-<version>.exe. Needs: .venv with ".[desktop]" plus the engine
# packages (pip install -e ".[desktop]" pgserver), Inno Setup 6. The app carries the whole engine: embedded
# PostgreSQL (pgserver), Piper voices, faster-whisper, and ffmpeg (fetched and checksum-verified below).
$ErrorActionPreference = "Continue"  # PyInstaller logs to stderr
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
& "$root\packaging\fetch_ffmpeg.ps1"
if (-not (Test-Path "$root\packaging\ffmpeg\ffmpeg.exe")) { throw "ffmpeg is missing" }
.\.venv\Scripts\pyinstaller --noconfirm --clean --onedir --windowed --name CiciByteMediaFactory `
  --icon "$root\packaging\app.ico" --paths backend `
  --add-data "$root\backend\mediafactory\web;mediafactory/web" --add-data "$root\packaging\app.ico;." `
  --add-data "$root\backend\mediafactory\db\migrations;mediafactory/db/migrations" `
  --add-data "$root\packaging\ffmpeg;ffmpeg" `
  --collect-submodules mediafactory --collect-submodules uvicorn `
  --collect-all pgserver --collect-all piper --collect-all faster_whisper --collect-all ctranslate2 `
  --collect-all onnxruntime --collect-all tzdata --collect-all psycopg_binary `
  --hidden-import winotify --hidden-import psycopg `
  --distpath dist\app --workpath build\pyi --specpath build packaging\desktop_entry.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (is the app still running from dist\app?)" }
if (-not (Select-String -Quiet -Path "$root\dist\app\CiciByteMediaFactory\_internal\mediafactory\web\setup.js" -Pattern "Easy Setup")) {
  throw "the bundled panel is stale"
}
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
& $iscc "$root\packaging\installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
