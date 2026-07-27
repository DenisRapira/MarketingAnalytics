$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root "dist"
$AppDir = Join-Path $Dist "MarketingAnalytics"
$Zip = Join-Path $Dist "MarketingAnalytics.zip"
$InstallerWork = Join-Path $env:TEMP "MarketingAnalyticsIExpress"
$SetupExe = Join-Path $Dist "MarketingAnalyticsSetup.exe"
$TempSetupExe = Join-Path $env:TEMP "MarketingAnalyticsSetup.exe"
$InstallCmd = Join-Path $Root "installer\install.cmd"
$Sed = Join-Path $InstallerWork "MarketingAnalytics.sed"

if (!(Test-Path $AppDir)) {
  throw "Desktop package not found. Run scripts\publish-desktop.ps1 first."
}

if (Test-Path $Zip) { Remove-Item $Zip -Force }
if (Test-Path $InstallerWork) { Remove-Item $InstallerWork -Recurse -Force }
if (Test-Path $SetupExe) { Remove-Item $SetupExe -Force }
if (Test-Path $TempSetupExe) { Remove-Item $TempSetupExe -Force }
New-Item -ItemType Directory -Path $InstallerWork | Out-Null

Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $Zip -Force
Copy-Item $InstallCmd (Join-Path $InstallerWork "install.cmd") -Force
Copy-Item $Zip (Join-Path $InstallerWork "MarketingAnalytics.zip") -Force

$sedContent = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
TargetNTVersion=6.0.0
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$TempSetupExe
FriendlyName=Marketing Analytics
AppLaunched=install.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
FILE0=install.cmd
FILE1=MarketingAnalytics.zip
[SourceFiles]
SourceFiles0=$InstallerWork
[SourceFiles0]
%FILE0%=
%FILE1%=
[FileVersion]
FILE0=install.cmd
FILE1=MarketingAnalytics.zip
"@

$sedContent | Set-Content -Encoding ASCII $Sed
& "$env:SystemRoot\System32\iexpress.exe" /N /Q $Sed
if (!(Test-Path $TempSetupExe)) {
  throw "IExpress did not create $TempSetupExe"
}
Copy-Item $TempSetupExe $SetupExe -Force

Write-Host "Installer ready: $SetupExe"
