@echo off
chcp 65001 >nul
setlocal
set "APPDIR=%LOCALAPPDATA%\Programs\MarketingAnalytics"
set "ZIP=%~dp0MarketingAnalytics.zip"

if exist "%APPDIR%" rmdir /s /q "%APPDIR%"
mkdir "%APPDIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%APPDIR%' -Force"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Marketing Analytics.lnk'); $s.TargetPath='%APPDIR%\MarketingAnalytics.exe'; $s.WorkingDirectory='%APPDIR%'; $s.IconLocation='%APPDIR%\Assets\marketing.ico'; $s.Save()"

start "" "%APPDIR%\MarketingAnalytics.exe"
exit /b 0
