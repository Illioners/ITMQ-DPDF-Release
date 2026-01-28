; Inno Setup Script for ITMQ-Lite (Proglite - Tkinter Version)
; Requires Inno Setup 6.x

#define MyAppName "ClasificadorPDF"
#define MyAppVersion "1.4.25"
#define MyAppPublisher "Intramaq"
#define MyAppURL "https://github.com/Illioners/ITMQ-DPDF"
#define MyAppExeName "ClasificadorPDF.exe"

[Setup]
AppId={{C9F6E3D2-AB5F-5G4C-9E8D-2B3C4D5E6F7G}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output settings
OutputDir=..\dist
OutputBaseFilename=ClasificadorPDF_Setup_v{#MyAppVersion}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Visual
WizardStyle=modern
SetupIconFile=..\assets\Intramaq-logo-mail.ico
; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application - Single onefile executable
Source: "..\dist\ClasificadorPDF.exe"; DestDir: "{app}"; Flags: ignoreversion
; Include Manager (Application Manager)
Source: "..\dist\ITMQ-Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
; Include Updater (Legacy - onefile)
Source: "..\dist\ITMQ-Updater.exe"; DestDir: "{app}"; Flags: ignoreversion
; VC++ Redistributable (if present)
Source: "..\installer\prerequisites\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Install VC++ Redistributable silently if not already installed
; Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Instalando Visual C++ Redistributable..."; Flags: waituntilterminated skipifdoesntexist
; Unblock all files in the installation directory
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""Get-ChildItem -Path '{app}' -Recurse | Unblock-File"""; StatusMsg: "Desbloqueando archivos..."; Flags: runhidden waituntilterminated
; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
