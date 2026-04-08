[Setup]
AppName=RateEye
AppVersion=1.0.6
WizardStyle=modern
DefaultDirName={autopf}\RateEye
DefaultGroupName=RateEye
UninstallDisplayIcon={app}\rateeye.exe
Compression=lzma2
SolidCompression=yes
OutputDir=..
OutputBaseFilename=rateeye-windows-setup

[Files]
Source: "..\dist\rateeye.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\INSTALL_GUIDE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\COPYRIGHT.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\RateEye"; Filename: "{app}\rateeye.exe"
Name: "{autodesktop}\RateEye"; Filename: "{app}\rateeye.exe"
Name: "{autodesktop}\RateEye Dashboard"; Filename: "http://127.0.0.1:8000"; IconFilename: "{app}\rateeye.exe"

[Run]
Filename: "{app}\rateeye.exe"; Description: "Launch RateEye"; Flags: nowait postinstall skipifsilent
