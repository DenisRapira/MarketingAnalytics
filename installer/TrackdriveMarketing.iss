#define AppName "Marketing Analytics"
#define AppExe "MarketingAnalytics.exe"
#define AppVersion "1.0.0"
#define DistDir "..\dist\MarketingAnalytics"

[Setup]
AppId={{F50B7C8E-4F6D-48C2-B210-8D8E918D6C01}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\Marketing Analytics
DefaultGroupName={#AppName}
OutputDir=..\dist\installer
OutputBaseFilename=MarketingAnalyticsSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\desktop-webview2\Assets\marketing.ico
UninstallDisplayIcon={app}\{#AppExe}
PrivilegesRequired=lowest

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
