; =====================================================
; CubeLab-UserTesting - Inno Setup Script
; Creates a Windows installer (.exe)
; =====================================================

#define MyAppName "Cube Lab - User Testing"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Cube Lab Team"
#define MyAppURL "https://github.com/cubelab"
#define MyAppExeName "CubeLab-UserTesting.exe"

[Setup]
AppId={{9F5E0B8C-4D3E-5F6G-0B2C-3D4E5F6G7B8C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\CubeLab-UserTesting
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installers
OutputBaseFilename=CubeLab-UserTesting-{#MyAppVersion}-Windows-Setup
SetupIconFile=src\resources\images\Icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\CubeLab-UserTesting\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
