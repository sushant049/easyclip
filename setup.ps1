$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$py = $null
foreach ($c in @("python", "py")) {
  try { & $c -c "import sys; assert sys.version_info >= (3,9)" 2>$null; if ($LASTEXITCODE -eq 0) { $py = $c; break } } catch {}
}
if (-not $py) {
  Write-Host "Installing Python 3.12..."; winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  Write-Host "Done. If 'python' still opens the Microsoft Store: Settings > Apps > Advanced app settings > App execution aliases > turn OFF python.exe and python3.exe. Then run this script again."
  Read-Host "Press Enter to exit"; exit
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host "Installing ffmpeg..."; winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
& $py -m pip install -q -U yt-dlp
& $py scripts\ch.py doctor
Write-Host "`nIf ffmpeg shows MISS, close this window, open a NEW one and run: $py scripts\ch.py doctor"
Read-Host "Press Enter to exit"
