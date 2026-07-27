param(
  [string]$Destination = (Join-Path (Split-Path -Parent $PSScriptRoot) "build\webview2-fixed")
)

$ErrorActionPreference = "Stop"
$RuntimeVersion = "150.0.4078.99"
$RuntimeUrl = "https://msedge.sf.dl.delivery.mp.microsoft.com/filestreamingservice/files/1c394b0d-2689-4d8b-af57-2f2018abccf6/Microsoft.WebView2.FixedVersionRuntime.150.0.4078.99.x64.cab"
$Root = Split-Path -Parent $PSScriptRoot
$Archive = Join-Path $Root "build\Microsoft.WebView2.FixedVersionRuntime.$RuntimeVersion.x64.cab"

if (Test-Path $Destination) {
  $existing = Get-ChildItem -Path $Destination -Recurse -Filter "msedgewebview2.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($existing) {
    Write-Host "WebView2 Fixed Runtime already present: $($existing.DirectoryName)"
    return
  }
  Remove-Item $Destination -Recurse -Force
}

New-Item -ItemType Directory -Path (Split-Path -Parent $Archive) -Force | Out-Null
if (-not (Test-Path $Archive)) {
  Write-Host "Downloading WebView2 Fixed Runtime $RuntimeVersion..."
  Invoke-WebRequest -Uri $RuntimeUrl -OutFile $Archive
}

New-Item -ItemType Directory -Path $Destination -Force | Out-Null
expand.exe $Archive -F:* $Destination | Out-Null

$runtimeExe = Get-ChildItem -Path $Destination -Recurse -Filter "msedgewebview2.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $runtimeExe) {
  throw "WebView2 Fixed Runtime extraction failed."
}

Write-Host "WebView2 Fixed Runtime ready: $($runtimeExe.DirectoryName)"
