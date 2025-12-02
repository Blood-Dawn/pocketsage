; /**
;  * (Bloodawn)
;  * File: PocketSage.iss
;  * Purpose: Windows installer for PocketSage desktop app
;  */

#define MyAppName        "PocketSage"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "PocketSage Team"
#define MyAppURL         "https://github.com/Blood-Dawn/pocketsage"
#define MyAppExeName     "PocketSage.exe"
#define MyAppId          "{{3A8C0E4C-6F42-4BCE-9E1B-POCKETSAGE-0001}}" ; generate a GUID once and keep it

[Setup]
; --- Core metadata ---
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; --- Install location / shortcuts ---
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=no

; --- Output installer settings ---
OutputDir=..\dist\installer
OutputBaseFilename=PocketSage-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; --- General UX ---
SetupLogging=yes
ShowLanguageDialog=no
Uninstallable=yes
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no

; NOTE: User data (SQLite DB, exports) are kept on uninstall.
; Wiping data is done from inside the app via Admin -> Delete Data.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Core app binary produced by PyInstaller / flet pack
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Optionally include README / license / demo script
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PocketSage_Demo_Script.md"; DestDir: "{app}"; Flags: ignoreversion; Tasks:

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Optional: link to README
Name: "{group}\PocketSage Demo Script"; Filename: "{app}\PocketSage_Demo_Script.md"; Check: FileExists(ExpandConstant('{app}\PocketSage_Demo_Script.md'))

; Desktop shortcut (optional task)
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch PocketSage after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch PocketSage now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; If later you decide to store logs under {app}\logs or temp data
; you can selectively remove them here. For now we keep user data.
; Type: filesandordirs; Name: "{app}\logs"
