# Builds dist\CiciByteMediaFactory-Setup-<version>.exe. Needs: .venv with ".[desktop]", Inno Setup 6.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
.\.venv\Scripts\pyinstaller --noconfirm --clean --onedir --windowed --name CiciByteMediaFactory `
  --icon "$root\packaging\app.ico" --paths backend --add-data "$root\backend\mediafactory\web;mediafactory/web" `
  --distpath dist --workpath build\pyi --specpath build packaging\desktop_entry.py
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
& $iscc "$root\packaging\installer.iss"
