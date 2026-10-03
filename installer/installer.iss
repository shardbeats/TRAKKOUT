; TRAKKOUT installer for inexpert users (Inno Setup 6).
; Compiled by build_installer.py, which passes /DAPP_VERSION=x.y.z.
; Layout installed:
;   {app}\TRAKKOUT.exe
;   {app}\ffmpeg\ffmpeg.exe + ffprobe.exe   (auto-detected, no PATH needed)
;   {app}\GOOGLE_SETUP.txt                  (how to connect their YouTube)
; Per-user install: no admin rights needed. Python NOT needed (inside the exe).

#ifndef APP_VERSION
  #define APP_VERSION "1.0.1"
#endif

#define APP_NAME "TRAKKOUT"
#define APP_PUBLISHER "TRAKKOUT"
#define APP_URL "https://github.com/shardbeats/TRAKKOUT"

[Setup]
AppId={{8A3B4E2F-7C1D-4E5A-9F0A-TRAKKOUT01}
AppName={#APP_NAME}
AppVersion={#APP_VERSION}
AppVerName={#APP_NAME} {#APP_VERSION}
AppPublisher={#APP_PUBLISHER}
AppPublisherURL={#APP_URL}
DefaultDirName={autopf}\{#APP_NAME}
DefaultGroupName={#APP_NAME}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
OutputDir=..\dist-installer
OutputBaseFilename=Setup_{#APP_NAME}_{#APP_VERSION}
SetupIconFile=..\trakkout.ico
UninstallDisplayIcon={app}\TRAKKOUT.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayName={#APP_NAME}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
Source: "..\dist\TRAKKOUT.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\thirdparty\ffmpeg\ffmpeg.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "..\thirdparty\ffmpeg\ffprobe.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\GOOGLE_SETUP.md"; DestDir: "{app}"; DestName: "GOOGLE_SETUP.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#APP_NAME}"; Filename: "{app}\TRAKKOUT.exe"
Name: "{group}\Desinstalar {#APP_NAME}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#APP_NAME}"; Filename: "{app}\TRAKKOUT.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TRAKKOUT.exe"; Description: "Abrir {#APP_NAME} ahora"; Flags: nowait postinstall skipifsilent
