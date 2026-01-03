; =====================================================
; CubeLab-UserTesting - Inno Setup Script (FIXED)
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

; Output - current directory
OutputDir=.
OutputBaseFilename=CubeLab-UserTesting-{#MyAppVersion}-Windows-Setup

; NO ICON LINES - prevents errors when icon doesn't exist

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Appearance
WizardStyle=modern

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\CubeLab-UserTesting\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
