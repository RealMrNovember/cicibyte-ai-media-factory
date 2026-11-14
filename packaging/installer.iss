; CiciByte AI Media Factory — Windows installer (Inno Setup 6)
; Build: packaging\build_windows.ps1  (PyInstaller app folder in dist\CiciByteMediaFactory, then this script)

#define AppName "CiciByte AI Media Factory"
#define AppVersion "0.3.0"
#define AppExe "CiciByteMediaFactory.exe"

[Setup]
AppId={{6E8C2C4B-3E8D-4C55-9C0B-6F0D1C1B7A11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=CiciByte Technology
AppPublisherURL=https://cicibyte.com
AppSupportURL=https://mediafactory.cicibyte.com
DefaultDirName={autopf}\CiciByte\MediaFactory
UsePreviousAppDir=no
DefaultGroupName=CiciByte
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=CiciByteMediaFactory-Setup-{#AppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\CiciByteMediaFactory\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; after an automatic update (silent install) start the app again
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent
