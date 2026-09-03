; KakaoAuto Windows installer (Inno Setup 6)
; Builds KakaoAuto-Setup.exe from the PyInstaller output dist\KakaoAuto.exe.
; Version can be overridden from CI:  ISCC /DMyAppVersion=1.0.1 installer.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppName "KakaoAuto"
#define MyAppPublisher "AidanKR"
#define MyAppURL "https://github.com/AidanKR/kakao-auto"
#define MyAppExeName "KakaoAuto.exe"

[Setup]
AppId={{9F3B2A64-1C2E-4E7A-9E2B-7A1E2C3D4E5F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
; Install into a user-writable folder (the app stores config.json / kakao.db
; next to the exe, so it must NOT go under Program Files).
DefaultDirName={localappdata}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer_out
OutputBaseFilename=KakaoAuto-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=LICENSE
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\KakaoAuto.exe";     DestDir: "{app}"; Flags: ignoreversion
; ship the template, and seed config.json on first install only (never overwrite user's)
Source: "config.example.json";    DestDir: "{app}"; Flags: ignoreversion
Source: "config.example.json";    DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist
Source: "README.md";              DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE";                DestDir: "{app}"; Flags: ignoreversion
Source: "NOTICE";                 DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}";               Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autoprograms}\Edit config.json";           Filename: "notepad.exe"; Parameters: """{app}\config.json"""
Name: "{autoprograms}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";                Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
