# Builds dist\CiciByteMediaFactory-Setup-<version>.exe. Needs: .venv with ".[desktop]", Inno Setup 6.
$ErrorActionPreference = "Continue"  # PyInstaller logs to stderr
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
.\.venv\Scripts\pyinstaller --noconfirm --clean --onedir --windowed --name CiciByteMediaFactory `
  --icon "$root\packaging\app.ico" --paths backend --add-data "$root\backend\mediafactory\web;mediafactory/web" --add-data "$root\packaging\app.ico;." `
  --hidden-import winotify `
  --distpath dist\app --workpath build\pyi --specpath build packaging\desktop_entry.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (is the app still running from dist\app?)" }
if (-not (Select-String -Quiet -Path "$root\dist\app\CiciByteMediaFactory\_internal\mediafactory\web\app.js" -Pattern "pywebview-drag-region")) {
  throw "the bundled panel is stale"
}
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
& $iscc "$root\packaging\installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
