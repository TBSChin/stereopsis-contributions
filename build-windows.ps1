$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m unittest discover -s . -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name Stereopsis-Contributor-Installer --add-data 'ui.html;.' --add-data 'manifest.json;.' desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Compress-Archive -LiteralPath 'dist/Stereopsis-Contributor-Installer' -DestinationPath 'dist/Stereopsis-Contributor-Installer-Windows-dev.zip' -Force
Get-FileHash 'dist/Stereopsis-Contributor-Installer-Windows-dev.zip' -Algorithm SHA256
