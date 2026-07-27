param(
  [string]$Configuration = "Release",
  [string]$Runtime = "win-x64"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root "dist\MarketingAnalytics"
$Frontend = Join-Path $Root "frontend"
$Backend = Join-Path $Root "backend"
$Desktop = Join-Path $Root "desktop-webview2"
$Publish = Join-Path $Desktop "bin\$Configuration\net9.0-windows\$Runtime\publish"
$RuntimeOut = Join-Path $Dist "runtime"
$BackendBuild = Join-Path $Root "build\backend-runtime"
$BackendWork = Join-Path $Root "build\backend-work"
$BackendSpec = Join-Path $Root "build\backend-spec"
$WebView2Build = Join-Path $Root "build\webview2-fixed"

if (Test-Path $Dist) {
  Remove-Item $Dist -Recurse -Force
}
New-Item -ItemType Directory -Path $Dist | Out-Null

Push-Location $Frontend
npm.cmd run build
Pop-Location

Push-Location $Desktop
dotnet publish -c $Configuration -r $Runtime --self-contained true
Pop-Location

Copy-Item "$Publish\*" $Dist -Recurse -Force

$BackendOut = Join-Path $Dist "backend"
$FrontendOut = Join-Path $Dist "frontend"
New-Item -ItemType Directory -Path $BackendOut | Out-Null
New-Item -ItemType Directory -Path $FrontendOut | Out-Null

Copy-Item "$Backend\*.py" $BackendOut -Force
Copy-Item "$Backend\*.json" $BackendOut -Force -ErrorAction SilentlyContinue
Copy-Item "$Backend\charts" $BackendOut -Recurse -Force -ErrorAction SilentlyContinue

if (Test-Path $BackendBuild) { Remove-Item $BackendBuild -Recurse -Force }
if (Test-Path $BackendWork) { Remove-Item $BackendWork -Recurse -Force }
if (Test-Path $BackendSpec) { Remove-Item $BackendSpec -Recurse -Force }
New-Item -ItemType Directory -Path $RuntimeOut | Out-Null
Push-Location $Backend
python -m PyInstaller --noconfirm --clean --onedir --name MarketingAnalyticsBackend `
  --distpath $BackendBuild --workpath $BackendWork --specpath $BackendSpec `
  --collect-all matplotlib --collect-all seaborn main.py
Pop-Location
Copy-Item (Join-Path $BackendBuild "MarketingAnalyticsBackend") (Join-Path $RuntimeOut "backend") -Recurse -Force
$NodeExe = (Get-Command node -ErrorAction Stop).Source
Copy-Item $NodeExe (Join-Path $RuntimeOut "node.exe") -Force

& (Join-Path $PSScriptRoot "get-webview2-runtime.ps1") -Destination $WebView2Build
Copy-Item $WebView2Build (Join-Path $RuntimeOut "webview2") -Recurse -Force

Copy-Item "$Frontend\.next\standalone\*" $FrontendOut -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $FrontendOut ".next") -Force | Out-Null
Copy-Item "$Frontend\.next\static" (Join-Path $FrontendOut ".next\static") -Recurse -Force
Copy-Item "$Frontend\public" $FrontendOut -Recurse -Force

Copy-Item (Join-Path $Desktop "Assets") $Dist -Recurse -Force

@"
Тракдрайв Маркетинг

Запуск: TrackdriveMarketing.exe
Отчеты: Documents\Trackdrive Marketing\Reports

Требования для текущей сборки:
- WebView2 Runtime
- Python с зависимостями backend
- Node.js для запуска Next standalone
"@ | Set-Content -Encoding UTF8 (Join-Path $Dist "README.txt")

@"
Marketing Analytics

Launch: MarketingAnalytics.exe

This package includes the backend, Node.js, .NET runtime, and WebView2 runtime.
No Python, Node.js, .NET, or WebView2 installation is required on the user's PC.
"@ | Set-Content -Path (Join-Path $Dist "README.txt") -Encoding UTF8

Write-Host "Desktop package ready: $Dist"
